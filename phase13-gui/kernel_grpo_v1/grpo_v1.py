# -*- coding: utf-8 -*-
"""
grpo_v1.py - GRPO (Group Relative Policy Optimization) cho GUI agent.

Muc tieu: dung REWARD THAT de toi uu hoa hanh vi (SFT chi hoc hanh vi da co).
Dung: trl 1.14.1 GRPOTrainer + Unsloth FastVisionModel (API doc tu WHEEL THAT,
khong doan: scripts/inspect_trl_grpo.py).

Tieu chi (xem PLAN.md muc W3):
 - prompt = (anh, instruction) -- cung format voi lúc SFT (SYS + 'Task: ...')
 - G=8 mau/prompt, reward VERIFIABLE: parse action -> so voi GT
 - advantage GRPO = (r - mean_G)/std_G (trl tu lo) + KL vs adapter SFT (beta)
 - reward set TACHO tap eval (web/desktop) -> khong trung prompt
 - LUON gate bang bench THAT sau moi lan RL (keo len + do lai)
 - Giu 20-30% SFT: trainer bat buoc co mot buoc SFT? -> tro ve bang cach
   'init tu adapter SFT' + KL penalty (beta) de khong bay.

Bien moi (env):
 - GRPO_NPROMPT   so prompt dung (mac dinh 300)
 - GRPO_G        so mau/prompt (mac dinh 8)
 - GRPO_LR       lr (mac dinh 1e-6; RL can LR nho hon SFT ~200 lan)
 - GRPO_BETA     KL beta (mac dinh 0.02)
 - GRPO_EPOCHS   so epoch (mac dinh 1)
 - GRPO_ADAPTER  duong dan adapter SFT khoi tao (mac dinh /kaggle/input/ornith-gui-lora-v24)
"""
import io
import json
import os
import random
import re
import shutil
import sys
import time

T0 = time.time()


def log(m):
    print("[grpo] %s (t=%.0fs)" % (m, time.time() - T0), flush=True)


WORK = "/kaggle/working"
ORN = "/tmp/ornbase"
INPUT_ROOT = "/kaggle/input"

N_PROMPT = int(os.environ.get("GRPO_NPROMPT", "300"))
G = int(os.environ.get("GRPO_G", "8"))
LR = float(os.environ.get("GRPO_LR", "1e-6"))
BETA = float(os.environ.get("GRPO_BETA", "0.02"))
EPOCHS = int(os.environ.get("GRPO_EPOCHS", "1"))
SEED = random.randint(1, 10 ** 9)
ADAPTER_SRC = os.environ.get(
    "GRPO_ADAPTER", "/kaggle/input/ornith-gui-lora-v24")

# ---------------------------------------------------------------- prompt
SYS = ("You are a GUI agent. Look at the screenshot and the task, then "
       "decide the next action.\n"
       "You MAY reason briefly first. Reply format:\n"
       "THINK: <one or two short sentences about what you see and what "
       "to do>\n"
       "ACTION: <CLICK x y | TYPE text | KEY name | DONE>\n"
       "Rules: the LAST line MUST start with 'ACTION:'; x,y are integers "
       "0..1000 normalized to image width/height; never write anything "
       "after the ACTION line; if the task is already complete, "
       "output ACTION: DONE.")

# ---------------------------------------------------------------- parser
ACT_RE = re.compile(
    r"(CLICK|TYPE|KEY|DONE)\s*([^\n]*)", re.I)


def parse_action_v2(text):
    """-> ('click', arg) | ('type', arg) | ('key', arg) | ('done', None)
    | None. Ban cua benchmark (bench_v15_kernel.py) - dung de reward khop
    DUNG format cua lúc SFT."""
    if not text:
        return None
    t = text.replace("\r", "")
    lines = [l.strip() for l in t.split("\n") if l.strip()]
    cand = []
    for l in reversed(lines):                     # dong CUOI chua ACTION:
        if l.upper().startswith("ACTION:"):
            cand.append(l.split(":", 1)[1].strip())
            break
    if not cand:                                  # fallback: dong cuoi
        for l in reversed(lines):
            if l.upper().startswith(("THINK:", "ACTION:")):
                continue
            cand.append(l)
            break
    for c in cand:
        m = ACT_RE.search(c)
        if not m:
            continue
        verb = m.group(1).upper()
        arg = m.group(2).strip()
        if verb == "CLICK":
            mm = re.search(r"(\d+)\s*[, ]\s*(\d+)", arg)
            if not mm:
                continue
            return ("click", (int(mm.group(1)), int(mm.group(2))))
        if verb == "TYPE":
            return ("type", arg)
        if verb == "KEY":
            return ("key", arg.upper())
        return ("done", None)
    return None


def norm_gt(act):
    """Chuan hoa GT string -> tuple de so sanh voi parse."""
    if act is None:
        return None
    a = str(act).strip()
    m = re.match(r"(?i)^CLICK\s+(\d+)\s+(\d+)", a)
    if m:
        return ("click", (int(m.group(1)), int(m.group(2))))
    m = re.match(r"(?i)^TYPE\s+(.*)$", a)
    if m:
        return ("type", m.group(1).strip())
    m = re.match(r"(?i)^KEY\s+(.*)$", a)
    if m:
        return ("key", m.group(1).strip().upper())
    if a.upper().startswith("DONE"):
        return ("done", None)
    return None


def action_reward(prompts, completions, gt=None, **kwargs):
    """Reward VERIFIABLE: 1.0 khi action parse ra == GT; 0.2 neu gan
    (click trong ban kinh 40/1000); -0.1 neu khong parse duoc (chan prose).
    gt: list[str] (moi prompt) - trainer tu lap cho moi mau."""
    outs = []
    n = len(completions)
    for i in range(n):
        text = completions[i]
        if isinstance(text, list):                # chat: lay phan text cuoi
            text = "".join(p.get("text", "") for p in text
                           if isinstance(p, dict)) or str(text)
        g = None
        if gt is not None and len(gt) > 0:
            g = gt[i % len(gt)]
        pa = parse_action_v2(text)
        pg = norm_gt(g)
        r = 0.0
        if pa is None:
            r = -0.1
        elif pg is None:
            r = 0.0
        elif pa[0] != pg[0]:
            r = 0.0
        elif pa[0] == "click":
            dx = abs(pa[1][0] - pg[1][0])
            dy = abs(pa[1][1] - pg[1][1])
            r = 1.0 if (dx <= 20 and dy <= 20) else (0.3 if (dx <= 80 and dy <= 80)
                                                     else 0.0)
        elif pa[0] == "type":
            r = 1.0 if pa[1].strip() == pg[1].strip() else 0.0
        elif pa[0] == "key":
            r = 1.0 if pa[1] == pg[1] else 0.0
        else:
            r = 1.0
        outs.append(float(r))
    return outs


# ---------------------------------------------------------------- dataset
def load_ds_rows(substr, fname, required=False):
    """Giong loader cua kernel SFT (da fix: quet ca thu muc dataset goc)."""
    base = None
    for root, _d, files in os.walk(INPUT_ROOT):
        if fname in files and os.path.basename(root.rstrip("/")) == substr:
            base = root
            break
    if base is None:
        for root, _d, files in os.walk(INPUT_ROOT):
            if os.path.basename(root.rstrip("/")) == substr:
                cands = [f for f in files if f.lower().endswith(".jsonl")]
                if not cands:
                    continue
                prefer = ([f for f in cands if f == fname] or
                          [f for f in cands if "traj" in f.lower()] or cands)
                base = root
                fname = prefer[0]
                break
    if not base:
        cands = []
        for root, _d, files in os.walk(INPUT_ROOT):
            if fname in files and substr in os.path.basename(root.rstrip("/")):
                cands.append(root)
        if len(cands) == 1:
            base = cands[0]
        else:
            msg = "FAIL: khong tim thay dataset '%s' (%s)" % (substr, cands)
            if required:
                raise SystemExit(msg)
            log("WARN " + msg)
            return []
    rows = []
    with open(os.path.join(base, fname), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    ext = os.path.join(WORK, "ds_" + substr.replace("/", "_"))
    os.makedirs(ext, exist_ok=True)
    for f in os.listdir(base):
        if f.endswith(".zip"):
            try:
                import zipfile
                with zipfile.ZipFile(os.path.join(base, f)) as z:
                    z.extractall(ext)
            except Exception as e:
                log("unzip loi %s: %s" % (f, e))

    def _resolve(rel):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
        cand = os.path.join(ext, rel)
        if os.path.exists(cand):
            return cand
        name = os.path.basename(rel)
        for root, _, files in os.walk(ext):
            if name in files:
                return os.path.join(root, name)
        for root, _, files in os.walk(base):
            if name in files:
                return os.path.join(root, name)
        return None

    out = []
    for r in rows:
        if not r.get("image") or not r.get("action"):
            continue
        p = _resolve(r["image"])
        if p:
            r = dict(r)
            r["image"] = p
            out.append(r)
    log("%s: %d/%d rows (%s)" % (substr, len(out), len(rows), fname))
    if required and not out:
        raise SystemExit("FAIL: dataset '%s' khong resolve duoc anh nao" % substr)
    return out


def install_unsloth():
    """22/10: THIEU buoc nay -> kernel v1 chet 'No module named unsloth'.
    Cai tu dataset wheels (KHONG internet) - giong het kernel SFT."""
    import subprocess
    wheels = None
    for root, _d, files in os.walk(INPUT_ROOT):
        if any(f.startswith("unsloth-") and f.endswith(".whl") for f in files):
            wheels = root
            break
    assert wheels, "FAIL: thieu wheels unsloth (dataset gemma12b-wheels)"

    def sh(cmd, timeout=1800):
        log("pip: %s" % cmd[:100])
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        out = ((p.stdout or "") + (p.stderr or ""))[-300:]
        log("  rc=%s %s" % (p.returncode, out.replace("\n", " ")[:150]))
        return p.returncode

    sh("pip install --no-index --no-deps --find-links %s "
       "unsloth unsloth_zoo trl bitsandbytes" % wheels)
    # peft/transformers co san trong image; dam bao dung version
    sh("pip install --no-index --no-deps --find-links %s peft" % wheels)
    try:
        import unsloth  # noqa: F401
        log("unsloth OK")
    except Exception as e:
        raise SystemExit("FAIL: unsloth import loi: %s" % e)


def main():
    log("SEED=%d | N_PROMPT=%d G=%d LR=%g BETA=%g EPOCHS=%d"
        % (SEED, N_PROMPT, G, LR, BETA, EPOCHS))

    # 1) base model
    if not os.path.isdir(ORN):
        import glob
        import shutil as _sh
        dst = ORN
        os.makedirs(dst, exist_ok=True)
        files = []
        for d in sorted(glob.glob("/kaggle/input/datasets/*/ornbase-s*")):
            for f in glob.glob(os.path.join(d, "*")):
                files.append(f)
        log("base: %d file -> %s" % (len(files), dst))
        for f in files:
            try:
                _sh.copy2(f, dst)
            except Exception:
                pass

    # 2) reward set (TACH tap eval!)
    pr = load_ds_rows("ornith-policy-replay-data", "traj.jsonl", required=True)
    tr = load_ds_rows("ornith-gui-traj", "traj.jsonl", required=True)
    pool = pr + tr
    random.Random(SEED).shuffle(pool)
    log("reward pool: %d (policy-replay %d + traj %d) -> lay %d prompt"
        % (len(pool), len(pr), len(tr), N_PROMPT))

    from PIL import Image as PILImage
    from datasets import Dataset

    def to_row(r):
        try:
            img = PILImage.open(r["image"]).convert("RGB")
        except Exception:
            return None
        instr = str(r.get("instruction", ""))[:1200]
        gt = str(r.get("action", "")).strip()
        if not instr or not gt:
            return None
        msgs = [{"role": "system", "content": [{"type": "text", "text": SYS}]},
                {"role": "user", "content": [{"type": "image"},
                                             {"type": "text",
                                              "text": "Task: " + instr}]}]
        return {"prompt": msgs, "image": img, "gt": gt}

    rows = []
    for r in pool:
        if len(rows) >= N_PROMPT:
            break
        x = to_row(r)
        if x is not None:
            rows.append(x)
    if len(rows) < 16:
        raise SystemExit("FAIL: chi lay duoc %d prompt (<16 de GRPO chay)"
                         % len(rows))
    log("dataset: %d prompt (image + gt)" % len(rows))

    ds = Dataset.from_list(rows)

    # 3) model + adapter SFT
    install_unsloth()
    import torch
    from unsloth import FastVisionModel
    # 22/10: GRPO_4BIT=1 -> QLoRA 4-bit (T4 Colab 16GB khong vua bf16 ~20GB)
    use_4bit = os.environ.get("GRPO_4BIT", "0") == "1"
    max_seq = int(os.environ.get("GRPO_MAX_SEQ", "2048" if use_4bit else "4096"))
    log("load base (4bit=%s, max_seq=%d)..." % (use_4bit, max_seq))
    model, processor = FastVisionModel.from_pretrained(
        ORN, load_in_4bit=use_4bit, max_seq_length=max_seq,
        use_gradient_checkpointing="unsloth")
    adir = None
    for cand in (ADAPTER_SRC, "/kaggle/input/datasets/dieniw/ornith-gui-lora-v24",
                 "/kaggle/input/ornith-gui-lora-v24"):
        if os.path.isdir(cand) and os.path.exists(
                os.path.join(cand, "adapter_config.json")):
            adir = cand
            break
    if adir is None:
        log("!! khong thay adapter SFT -> khoi tao LoRA moi (RONG)")
        model = FastVisionModel.get_peft_model(
            model, r=64, lora_alpha=64, lora_dropout=0.0,
            finetune_vision_layers=False, finetune_language_layers=True,
            finetune_attention_modules=True, finetune_mlp_modules=True,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"])
    else:
        log("adapter SFT: %s" % adir)
        from peft import PeftModel
        try:
            model = PeftModel.from_pretrained(model, adir, is_trainable=True)
            log("PeftModel.from_pretrained OK")
        except Exception as e:
            log("PeftModel fail (%s) -> get_peft_model + load_adapter" % e)
            model = FastVisionModel.get_peft_model(
                model, r=64, lora_alpha=64, lora_dropout=0.0,
                finetune_vision_layers=False, finetune_language_layers=True,
                finetune_attention_modules=True, finetune_mlp_modules=True,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                "gate_proj", "up_proj", "down_proj"])
            model.load_adapter(adir, adapter_name="sft")
            model.set_adapter("sft")

    # 4) trainer
    from trl import GRPOConfig, GRPOTrainer
    cfg = GRPOConfig(
        output_dir=os.path.join(WORK, "grpo_out"),
        learning_rate=LR,
        num_train_epochs=EPOCHS,
        # 22/10: 60 step x 8 gen x 4 accum = 1920 generation VLM ~ 2-4h.
        # Acc B con ~1.8h quota => mac dinh 30 step (~1.6h) + checkpoint (15).
        max_steps=int(os.environ.get("GRPO_MAX_STEPS", "30")),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_generations=G,
        max_completion_length=64,
        max_prompt_length=1024,
        beta=BETA,
        loss_type="dr_grpo",
        scale_rewards="group",
        epsilon=0.2,
        epsilon_high=0.28,
        num_iterations=1,
        steps_per_generation=4,
        logging_steps=1,
        # 22/10: CHECKPOINT giua chung - acc B con ~1.8h quota nen 1 run GRPO
        # co the bi cat => mat toan bo adapter (adapter chi duoc luoi o CUOI).
        save_strategy="steps",
        save_steps=15,
        save_total_limit=3,
        bf16=bool(torch.cuda.is_bf16_supported()),
        fp16=bool(torch.cuda.is_available())
        and not bool(torch.cuda.is_bf16_supported()),
        gradient_checkpointing=True,
        report_to=[],
        log_completions=True,
        seed=SEED,
    )
    log("GRPOConfig: G=%d beta=%g lr=%g max_steps=60" % (G, BETA, LR))
    trainer = GRPOTrainer(model=model, reward_funcs=action_reward,
                          args=cfg, train_dataset=ds,
                          processing_class=processor)
    log("bat dau train GRPO...")
    trainer.train()
    log("train xong")

    # 22/10: luu adapter tu checkpoint giua chung (checkpoint-*) - neu bi cat
    # quota giua chung van co adapter dung duoc.
    import glob as _glob
    _cks = sorted(_glob.glob(os.path.join(WORK, "grpo_out", "checkpoint-*")),
                  key=lambda p: int(p.rsplit("-", 1)[-1])
                  if p.rsplit("-", 1)[-1].isdigit() else 0)
    os.makedirs(os.path.join(WORK, "gui_lora"), exist_ok=True)
    if _cks:
        _src = _cks[-1]
        log("adapter tu checkpoint %s" % _src)
        try:
            model.save_pretrained(os.path.join(WORK, "gui_lora"))
        except Exception:
            import shutil as _sh
            _sh.copytree(_src, os.path.join(WORK, "gui_lora"),
                         dirs_exist_ok=True)
    else:
        model.save_pretrained(os.path.join(WORK, "gui_lora"))
    try:
        processor.save_pretrained(os.path.join(WORK, "gui_lora"))
    except Exception:
        pass
    # ket qua: trung binh reward + vi du
    stats = {}
    try:
        stats = {k: v for k, v in trainer.state.log_history[-1].items()
                 if isinstance(v, (int, float))}
    except Exception:
        pass
    with open(os.path.join(WORK, "grpo_result.json"), "w") as f:
        json.dump({"seed": SEED, "n_prompt": len(rows), "G": G, "lr": LR,
                   "beta": BETA, "epochs": EPOCHS, "stats": stats}, f, indent=1)
    log("ALL DONE %s" % json.dumps(stats)[:200])


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        raise
