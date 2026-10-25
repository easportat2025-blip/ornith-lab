"""Loop SFT tren Kaggle RTX: 5 game song song, moi lap = 1 TURN
(turn index chung). Cu 20 turns = 1 phase train (merge -> ma tran
MOI -> SFT tren buffer, loc reward>0). R4 lam goc (ban manh nhat).
"""
import gc
import json
import os
import random
import shutil
import subprocess
import sys
import time

WORK = "/kaggle/working"
GAMES = os.path.join(WORK, "games")
RANK, ALPHA, DROPOUT, LR = 128, 128, 0.1, 1e-4
SEQ_LEN = 2048
TURNS_TOTAL = 200
TRAIN_EVERY = 20
TIME_BUDGET = 8 * 3600
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj",
           "gate_proj", "up_proj", "down_proj"]
TASKS = [
    "Snake an moi co diem",
    "Platformer chay nhay qua gai ve dich",
    "Shooter doc 3 loai dich",
    "Puzzle 2048 don gian",
    "Catcher hung do roi ne bom",
]
SYS_GEN = ("You are a game code generator. Output ONE complete single-file "
           "python pygame program only, no explanation. Headless-safe "
           "(SDL_VIDEODRIVER=dummy). BAT BUOC: get_state() tra dict JSON "
           "gom score (so), alive (bool), actions (list string); "
           "do_action(action: str) tra dict. KHONG game-loop o top-level.")
ALPACA = ("Below is an instruction. Write a response.\n\n"
          "### Instruction:\n{}\n\n### Input:\n{}\n\n### Response:\n{}")


def log(m):
    print(f"[loop] {m}", flush=True)


def sh(cmd, timeout=600):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
    return r


SEED0 = random.SystemRandom().randint(1, 10**9)
random.seed(SEED0)
T0 = time.time()


def finddir(fname, extra=""):
    for root, _, files in os.walk("/kaggle/input"):
        if fname in files and extra in root:
            return root
    return None


def main():
    os.makedirs(GAMES, exist_ok=True)
    wh = finddir("unsloth", "")
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.endswith(".whl") for f in files):
            wheels = root
            break
    assert wheels, "thieu wheels"
    sh(f"pip install --no-index --no-deps --find-links {wheels} "
       f"unsloth unsloth_zoo trl bitsandbytes")
    import torch
    basedirs = [os.path.dirname(p) for p in
                sum([[os.path.join(r, f) for f in fs
                      if f == "model.safetensors"]
                     for r, _, fs in os.walk("/kaggle/input")], [])]
    adirs = [os.path.dirname(p) for p in
             sum([[os.path.join(r, f) for f in fs
                   if f == "adapter_model.safetensors"]
                  for r, _, fs in os.walk("/kaggle/input")], [])]
    r4 = next((d for d in adirs if "adapter-r4" in d), None)
    log(f"base={basedirs} merge_src={r4}")
    assert basedirs and r4, "thieu input"

    from transformers import AutoModelForCausalLM, AutoTokenizer, \
        BitsAndBytesConfig
    from peft import PeftModel
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True)
    base_q = AutoModelForCausalLM.from_pretrained(
        basedirs[0], quantization_config=bnb, device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(basedirs[0])
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = PeftModel.from_pretrained(base_q, r4).merge_and_unload()
    del base_q
    gc.collect()
    torch.cuda.empty_cache()
    t, u, fr = shutil.disk_usage("/tmp")
    mdir = "/tmp/merged_loop" if fr > 40 * 2**30 else \
        os.path.join(WORK, "merged_loop")
    os.makedirs(mdir, exist_ok=True)
    model.save_pretrained(mdir, safe_serialization=True)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    log(f"merge r4 xong -> {mdir}")

    from unsloth import FastLanguageModel
    cur_seed = random.SystemRandom().randint(1, 10**9)
    model, _ = FastLanguageModel.from_pretrained(
        model_name=mdir, max_seq_length=SEQ_LEN,
        dtype=None, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(
        model, r=RANK, target_modules=TARGETS, lora_alpha=ALPHA,
        lora_dropout=DROPOUT, bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=cur_seed, use_rslora=False)
    use_bf16 = torch.cuda.is_bf16_supported()
    log(f"unsloth adapter moi r={RANK} seed={cur_seed}")

    # --- TAO 5 game (1 lan) ---
    import importlib.util
    alive = {}
    for i, spec in enumerate(TASKS):
        prompt = ALPACA.format(SYS_GEN, spec, "")
        ids = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=512,
                                 do_sample=True, temperature=0.3,
                                 top_p=0.9,
                                 pad_token_id=tokenizer.eos_token_id)
        code = tokenizer.decode(out[0][ids["input_ids"].shape[1]:],
                                skip_special_tokens=True)
        import re
        m = re.search(r"```(?:python)?\s*\n(.*?)```", code, re.S)
        if m:
            code = m.group(1).strip()
        fp = os.path.join(GAMES, f"game{i}.py")
        open(fp, "w", encoding="utf-8").write(code)
        try:
            s = importlib.util.spec_from_file_location(f"g{i}", fp)
            mod = importlib.util.module_from_spec(s)
            s.loader.exec_module(mod)
            st = mod.get_state()
            assert isinstance(st, dict) and "score" in st \
                and "alive" in st and "actions" in st
            alive[i] = {"mod": mod, "spec": spec, "score": 0}
            log(f"game{i} OK actions={st['actions']}")
        except Exception as e:
            log(f"game{i} HON (bo qua): {e}")
    if not alive:
        raise SystemExit("khong co game nao song")

    # --- TURNS song song + train theo phase ---
    from datasets import Dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
    import inspect
    buf, phase = [], 0

    def train_phase():
        nonlocal phase, model
        good = [b for b in buf if b["reward"] > 0]
        log(f"phase {phase}: buffer={len(buf)} good={len(good)}")
        if len(good) < 50:
            log("it mau tot, bo qua phase")
            return
        # MA TRAN MOI: nap lai base sach + adapter random moi
        import gc as _gc
        new_seed = random.SystemRandom().randint(1, 10**9)
        try:
            del model
        except Exception:
            pass
        _gc.collect()
        torch.cuda.empty_cache()
        m, _ = FastLanguageModel.from_pretrained(
            model_name=mdir, max_seq_length=SEQ_LEN,
            dtype=None, load_in_4bit=True)
        m = FastLanguageModel.get_peft_model(
            m, r=RANK, target_modules=TARGETS, lora_alpha=ALPHA,
            lora_dropout=DROPOUT, bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=new_seed, use_rslora=False)
        model = m
        log(f"phase {phase}: adapter MOI seed={new_seed}")
        texts = [ALPACA.format(
            f"Choi game. State: {b['state']}\nActions: {b['actions']}",
            "", b["action"]) + tokenizer.eos_token for b in good]
        ds = Dataset.from_dict({"text": texts})
        sft_kw = dict(
            model=model, train_dataset=ds,
            args=TrainingArguments(
                per_device_train_batch_size=8,
                gradient_accumulation_steps=2,
                warmup_steps=10,
                max_steps=max(50, len(texts) // 16),
                learning_rate=LR,
                fp16=not use_bf16, bf16=use_bf16,
                logging_steps=10, optim="adamw_8bit",
                weight_decay=0.01, lr_scheduler_type="linear",
                seed=random.SystemRandom().randint(1, 10**9),
                output_dir=os.path.join(WORK, "out"),
                save_steps=200, save_total_limit=2))
        sig = inspect.signature(SFTTrainer.__init__).parameters
        if "processing_class" in sig:
            sft_kw["processing_class"] = tokenizer
        elif "tokenizer" in sig:
            sft_kw["tokenizer"] = tokenizer
        for k, v in [("dataset_text_field", "text"),
                     ("max_seq_length", SEQ_LEN),
                     ("packing", False), ("dataset_num_proc", 2)]:
            if k in sig:
                sft_kw[k] = v
        SFTTrainer(**sft_kw).train()
        adir = os.path.join(WORK, f"loop_adapt_p{phase}")
        model.save_pretrained(adir)
        json.dump({"phase": phase, "n_buf": len(buf), "n_good": len(good)},
                  open(os.path.join(adir, "phase_info.json"), "w"))
        phase += 1
        log(f"xong phase, adapter -> {adir}")

    for turn in range(TURNS_TOTAL):
        if time.time() - T0 > TIME_BUDGET:
            log("het gio, dung turns")
            break
        for i in sorted(alive):
            g = alive[i]
            try:
                st = g["mod"].get_state()
                acts = st.get("actions", ["noop"])
                p = ALPACA.format(
                    f"Choi game. State: {json.dumps(st)[:800]}",
                    f"Chon 1 action trong {acts}", "")
                ids = tokenizer(p, return_tensors="pt").to(model.device)
                with torch.no_grad():
                    out = model.generate(
                        **ids, max_new_tokens=32, do_sample=True,
                        temperature=0.3, top_p=0.9,
                        pad_token_id=tokenizer.eos_token_id)
                act = tokenizer.decode(
                    out[0][ids["input_ids"].shape[1]:],
                    skip_special_tokens=True).strip().split("\n")[0][:40]
                if act not in acts:
                    act = acts[0]
                res = g["mod"].do_action(act)
                res = res if isinstance(res, dict) else {"info": str(res)}
                sc = float(res.get("score", st.get("score", 0)))
                rw = (sc - g["score"]) * 1.0
                rw += 0.1 if res.get("alive", True) else -5.0
                g["score"] = sc
                buf.append({"turn": turn, "task": i, "state": st,
                            "actions": acts, "action": act,
                            "reward": rw})
            except Exception as e:
                buf.append({"turn": turn, "task": i, "state": {},
                            "actions": [], "action": "ERR",
                            "reward": -5.0})
                log(f"turn {turn} game{i} loi: {e}")
        if (turn + 1) % 20 == 0:
            train_phase()
        if turn % 20 == 0:
            log(f"turn {turn}/{TURNS_TOTAL} buf={len(buf)} "
                f"elapsed={int(time.time() - T0)}s")
    json.dump({"turns_done": turn + 1, "buf": len(buf), "phases": phase},
              open(os.path.join(WORK, "loop_state.json"), "w"))
    # Soup tat ca adapter cac phase (trung binh, cung base/rank/target)
    try:
        from safetensors.torch import load_file, save_file
        pads = sorted([os.path.join(WORK, d, "adapter_model.safetensors")
                       for d in os.listdir(WORK)
                       if d.startswith("loop_adapt_p") and os.path.isfile(
                           os.path.join(WORK, d,
                                        "adapter_model.safetensors"))])
        log(f"soup {len(pads)} adapters")
        if len(pads) >= 2:
            acc, n = None, 0
            for p in pads:
                sd = load_file(p, device="cpu")
                if acc is None:
                    acc = {k: v.float() / len(pads) for k, v in sd.items()}
                else:
                    for k in acc:
                        acc[k] += sd[k].float() / len(pads)
                del sd
                gc.collect()
                n += 1
            sdir = os.path.join(WORK, "loop_soup")
            os.makedirs(sdir, exist_ok=True)
            save_file({k: v.to(torch.float16) for k, v in acc.items()},
                      os.path.join(sdir, "adapter_model.safetensors"))
            log(f"SOUP DONE {n} adapters -> {sdir}")
    except Exception as e:
        log(f"soup loi (bo qua): {e}")
    log(f"LOOP DONE turns={turn + 1} buf={len(buf)} phases={phase}")


if __name__ == "__main__":
    main()
