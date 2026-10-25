"""Phase 3 — eval adapter r1: generate 30 mau (15 game + 15 bpy),
check co ban + luu ket qua. Chay GPU T4, OFFLINE."""
import ast
import json
import os
import random
import subprocess

WORK = "/kaggle/working"
EVAL_SEED = 123  # eval co dinh de so sanh giua cac run
N_GAME, N_BPY = 15, 15
MAX_NEW = 256


def log(m):
    print(f"[eval] {m}", flush=True)


def sh(cmd):
    log(f"+ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print((r.stdout or "")[-1000:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1000:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd}")


def find(pred):
    hits = []
    for root, _, files in os.walk("/kaggle/input"):
        for f in files:
            if pred(f, root):
                hits.append(os.path.join(root, f))
    return hits


def main():
    # 1. tim input
    adapters = find(lambda f, r: f == "adapter_model.safetensors")
    bases = find(lambda f, r: f == "model.safetensors")
    jsonls = find(lambda f, r: f.endswith(".jsonl"))
    bnbs = find(lambda f, r: "bitsandbytes" in f and f.endswith(".whl"))
    log(f"adapter={adapters}")
    log(f"base={bases}")
    log(f"jsonl={len(jsonls)} bnb_wheels={len(bnbs)}")
    if not adapters or not bases or not jsonls:
        raise SystemExit("thieu input")
    if bnbs:
        sh(f"pip install --no-index --no-deps --find-links "
           f"{os.path.dirname(bnbs[0])} bitsandbytes")

    # 2. load base 4bit + adapter r1
    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    use_bf16 = torch.cuda.is_bf16_supported()
    base_dir = os.path.dirname(bases[0])
    ad_dir = os.path.dirname(adapters[0])
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16
        else torch.float16,
        bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        base_dir, quantization_config=bnb, device_map="auto")
    tok = AutoTokenizer.from_pretrained(base_dir)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, ad_dir)
    model.eval()
    log("load xong base+r1")

    # 3. chon prompts co dinh
    game_rows, bpy_rows = [], []
    for fp in jsonls:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                (bpy_rows if "blender" in fp else game_rows).append(r)
    rnd = random.Random(EVAL_SEED)
    rnd.shuffle(game_rows)
    rnd.shuffle(bpy_rows)
    picks = ([("game", r) for r in game_rows[:N_GAME]] +
             [("bpy", r) for r in bpy_rows[:N_BPY]])
    log(f"prompts: game={len(game_rows)} bpy={len(bpy_rows)} "
        f"chon {len(picks)}")

    # 4. generate + check
    ALPACA = ("Below is an instruction. Write a response.\n\n"
              "### Instruction:\n{}\n\n### Input:\n{}\n\n### Response:\n{}")
    results, n_ok = [], 0
    for kind, r in picks:
        prompt = ALPACA.format(r.get("instruction", ""),
                               r.get("input", ""), "")
        ids = tok(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=MAX_NEW,
                                 do_sample=True, temperature=0.7,
                                 top_p=0.9, pad_token_id=tok.eos_token_id)
        gen = tok.decode(out[0][ids["input_ids"].shape[1]:],
                         skip_special_tokens=True)
        ok, why = True, "ok"
        if kind == "bpy":
            try:
                ast.parse(gen)
            except SyntaxError as e:
                ok, why = False, f"py-syntax: {e}"
        else:
            if len(gen.strip()) < 50:
                ok, why = False, "qua ngan"
            elif gen.count("{") != gen.count("}") and \
                    ("{" in gen or "}" in gen):
                ok, why = False, "lech brace"
        n_ok += ok
        results.append({"kind": kind,
                        "instruction": r.get("instruction", "")[:200],
                        "generation": gen, "pass": ok, "why": why})
    score = f"{n_ok}/{len(results)}"
    log(f"EVAL SCORE r1: {score}")
    with open(os.path.join(WORK, "eval_r1.jsonl"), "w",
              encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log("EVAL DONE " + score)


if __name__ == "__main__":
    main()
