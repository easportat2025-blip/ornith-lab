"""Run 5 — MERGE truoc (PEFT) roi MOI import Unsloth train.
- Khong cung steps: chay toi khi het gio (max_steps rat cao).
- Bo [viwiki] + data cu da train; chi lay tag moi + unity-complete + bpy.
- Cau cung: seed moi, ma tran moi, subset moi moi run.
"""
import json
import os
import random
import shutil
import subprocess

RANK = 128
ALPHA = 128
LORA_DROPOUT = 0.1            # > 0 bat buoc
MAX_STEPS = 30000            # khong cung steps: het gio thi dung
LR = 1e-4
SEQ_LEN = 2048
WARMUP_STEPS = 100
SAVE_STEPS = 1000
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj",
           "gate_proj", "up_proj", "down_proj"]  # all-linear coverage
FRESH_TAGS = {"fable", "xlam", "glaive", "turnstile", "ood"}
# Nhanh phu: CHI tool-use (main lo game/3D). Cung base/rank/target de soup.
assert ALPHA == RANK, "alpha phai = rank"
assert LORA_DROPOUT > 0, "dropout phai > 0"

SEED = random.SystemRandom().randint(1, 10**9)
print(f"[train] SEED ngau nhien run nay: {SEED}", flush=True)
random.seed(SEED)


def sh(cmd):
    print(f"[train] + {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1500:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd}")


def row_keep(r):
    instr = str(r.get("instruction", ""))
    out = str(r.get("output", ""))
    if instr.startswith("[viwiki]"):
        return False  # bo kien thuc xa hoi
    if instr.startswith("["):
        tag = instr[1:].split("]")[0].split()[0]
        return tag in FRESH_TAGS
    return False  # nhanh phu bo het non-tool


def main():
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        names = [f for f in files if f.endswith(".whl")]
        if any("unsloth" in f or f.startswith("trl-") for f in names):
            wheels = root
            break
    if not wheels:
        raise SystemExit("khong thay dataset wheels")
    sh(f"pip install --no-index --no-deps --find-links {wheels} "
       f"unsloth unsloth_zoo trl bitsandbytes")

    import torch
    model_dir, data_files, merge_dir = None, [], None
    for root, _, files in os.walk("/kaggle/input"):
        if "config.json" in files and "model.safetensors" in files:
            model_dir = root
        for f in files:
            if f.endswith(".jsonl"):
                data_files.append(os.path.join(root, f))
        if "adapter_config.json" in files and \
                "adapter_model.safetensors" in files:
            if "adapter-r4" in root:
                merge_dir = root
    print(f"[train] model={model_dir} merge_src={merge_dir} "
          f"n_jsonl={len(data_files)}", flush=True)
    if not model_dir or not data_files or not merge_dir:
        raise SystemExit("thieu model/data/adapter input")

    rows = []
    for fp in data_files:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if row_keep(r):
                    rows.append(r)
    print(f"[train] loc duoc {len(rows)} records moi "
          f"(bo viwiki + data cu)", flush=True)
    if not rows:
        raise SystemExit("khong con data moi de train")
    random.shuffle(rows)

    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    from peft import PeftModel
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True)
    base_q = AutoModelForCausalLM.from_pretrained(
        model_dir, quantization_config=bnb, device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    tmp = PeftModel.from_pretrained(base_q, merge_dir)
    merged = tmp.merge_and_unload()
    del tmp, base_q
    import gc
    gc.collect()
    torch.cuda.empty_cache()
    t, u, fr = shutil.disk_usage("/tmp")
    mdir = "/tmp/merged_r5" if fr > 40 * 2**30 else "/kaggle/working/mr5"
    os.makedirs(mdir, exist_ok=True)
    merged.save_pretrained(mdir, safe_serialization=True)
    tokenizer.save_pretrained(mdir)  # unsloth can tokenizer tai cho (offline)
    del merged
    gc.collect()
    torch.cuda.empty_cache()
    print(f"[train] MERGE xong, base moi o {mdir}", flush=True)

    # MOI IMPORT UNSLOTH SAU KHI MERGE (theo lenh)
    from unsloth import FastLanguageModel
    model, _ = FastLanguageModel.from_pretrained(
        model_name=mdir, max_seq_length=SEQ_LEN,
        dtype=None, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(
        model, r=RANK, target_modules=TARGETS, lora_alpha=ALPHA,
        lora_dropout=LORA_DROPOUT, bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=SEED, use_rslora=False)
    print(f"[train] unsloth adapter moi r={RANK} seed={SEED}",
          flush=True)

    ALPACA = ("Below is an instruction. Write a response.\n\n"
              "### Instruction:\n{}\n\n### Input:\n{}\n\n### Response:\n{}")
    eos = tokenizer.eos_token
    from datasets import Dataset
    ds = Dataset.from_dict({"text": [
        ALPACA.format(r.get("instruction", ""), r.get("input", ""),
                      r.get("output", "")) + eos for r in rows]})
    use_bf16 = torch.cuda.is_bf16_supported()
    import inspect
    from trl import SFTTrainer
    from transformers import TrainingArguments
    sft_kw = dict(
        model=model, train_dataset=ds,
        args=TrainingArguments(
            per_device_train_batch_size=8,
            gradient_accumulation_steps=2,
            warmup_steps=WARMUP_STEPS, max_steps=MAX_STEPS,
            learning_rate=LR, fp16=not use_bf16, bf16=use_bf16,
            logging_steps=10, optim="adamw_8bit",
            weight_decay=0.01, lr_scheduler_type="linear",
            seed=SEED, output_dir="/kaggle/working/out",
            save_steps=SAVE_STEPS, save_total_limit=3))
    sig_params = inspect.signature(SFTTrainer.__init__).parameters
    if "processing_class" in sig_params:
        sft_kw["processing_class"] = tokenizer
    elif "tokenizer" in sig_params:
        sft_kw["tokenizer"] = tokenizer
    for k, v in [("dataset_text_field", "text"),
                 ("max_seq_length", SEQ_LEN),
                 ("packing", False),
                 ("dataset_num_proc", 2)]:
        if k in sig_params:
            sft_kw[k] = v
    trainer = SFTTrainer(**sft_kw)
    trainer.train()

    out = "/kaggle/working/gemma12b-lora-r5b"
    model.save_pretrained(out)
    with open(os.path.join(out, "run_info.json"), "w") as f:
        json.dump({"seed": SEED, "backend": "unsloth-after-merge",
                   "rank": RANK, "max_steps": MAX_STEPS, "lr": LR,
                   "n_rows": len(rows), "merged_from": merge_dir},
                  f, indent=2)
    print(f"[train] DONE seed={SEED} adapter -> {out}", flush=True)


if __name__ == "__main__":
    main()
