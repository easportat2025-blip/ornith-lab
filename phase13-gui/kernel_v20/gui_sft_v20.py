"""gui_sft_v20.py — REASONING SFT (TASK-14, DeepSeek), nen tren gui_sft_v19.py.

Theo MAIN_QUEST.md §2/§3 (lenh user 19/10: CHO PHEP REASONING):
  + Assistant target = 2 dong: `THINK: <ly do ngan>` (template CO KIEM CHUNG
    tu metadata label/instruction + toa do target) roi `ACTION: <lenh>`.
  + SYS moi: duoc THINK ngan; dong CUOI bat buoc `ACTION: ...`.
  + Decode/eval `max_new_tokens=REASON_MAX=256` — 24 token chinh la tran cat
    thinking (bang chung TASK-9: T-bf16 8/11 -> 11/11 parse @256; U-bf16 load OK).
  + parse_output(): uu tien dong `ACTION:` CUOI, fallback bare legacy; do
    prose_leak (prose ngoai THINK) + legacy_leak (metric v19) + trunc_rate +
    mean_new_tokens; EVAL_STATS ghi vao gui_result.json["reason_stats"].
  + Slot dataset self-play `gui-selfplay` (traj.jsonl) fail-soft — cho vong
    self-improving Day-1/Day-2 (MAIN_QUEST §3). Cung giu slot `gui-traj-v19`.
  + install_unsloth(): cai peft tu wheels truoc neu co (fix TASK-9:
    "Please install peft" + import order).
  + Giu nguyen: synth regen seed/run, eval held-out seed 202/offset 90000,
    lora r=64 dropout 0.05, 2.0 epoch auto, mini-eval moi save_steps.
"""
import glob
import json
import math
import os
import random
import re
import subprocess
import sys
import time

from transformers import TrainerCallback

WORK = "/kaggle/working"
IMGS = os.path.join(WORK, "gui_imgs")
ORN = "/tmp/ornbase"
CW, CH = 768, 512
N_TRAIN = 1200
N_EVAL = 120
# --- v19 config (plan §3) ---
WARMUP = 15               # v18: 10
LORA_DROPOUT = 0.05       # v18: 0.0
SAVE_STEPS = 100          # v18: 150 -> mini-eval moi ckpt
EPOCH_TARGET = 2.0        # dung 2 epoch (draft §5: chong overfit)
REASON_MAX = 256          # v20: tran decode — 24 token cat thinking
EVAL_STATS = {}           # v20: gom moi ket qua evaluate theo tag
EFFECTIVE_BS = 16         # = per_device 2 x grad_accum 8 (giu v18)
SEED_V19 = random.randint(1001, 999999)  # moi run 1 seed — ghi vao result
PALETTE = {
    "red": (208, 52, 44), "green": (46, 158, 68),
    "blue": (30, 111, 217), "yellow": (201, 161, 10),
    "purple": (122, 59, 189), "orange": (217, 122, 30),
    "teal": (20, 160, 160),
}
SHAPES = ["button", "square", "circle"]
TEMPLATES = [
    "Click the {c} {s}.", "Tap the {c} {s}.",
    "Click on the {c} {s}.", "Find the {c} {s} and click it.",
    "Where do you click for the {c} {s}?",
]


def log(m):
    print("[gui] " + str(m), flush=True)


def sh(cmd, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-400:]}")
        return None
    return r


def assemble_base():
    cand = []
    for root, dirs, _ in os.walk("/kaggle/input"):
        for d in dirs:
            if d.startswith("ornbase-s"):
                cand.append(os.path.join(root, d))
    if not cand:
        for root, _, files in os.walk("/kaggle/input"):
            if any(f.startswith("model-") and f.endswith(".safetensors")
                   for f in files) and "adapter_config.json" not in files:
                cand.append(root)
    cand = sorted(set(cand))
    assert cand, "khong thay ornbase-s*"
    log(f"base dirs: {cand}")
    os.makedirs(ORN, exist_ok=True)
    got = set()
    for base in cand:
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith((".safetensors", ".json", ".jinja", ".model")):
                    src = os.path.join(root, f)
                    dst = os.path.join(ORN, f)
                    if f in got or os.path.exists(dst):
                        got.add(f)
                        continue
                    try:
                        os.link(src, dst)
                    except Exception:
                        import shutil
                        shutil.copy(src, dst)
                    got.add(f)
    for f in ("adapter_config.json", "adapter_model.safetensors"):
        p = os.path.join(ORN, f)
        if os.path.exists(p):
            os.remove(p)
            log(f"xoa {f} khoi ORN")
    cfg = json.load(open(os.path.join(ORN, "config.json")))
    assert cfg.get("model_type") == "qwen3_5", "ORN config khong phai qwen3_5"
    idx = os.path.join(ORN, "model.safetensors.index.json")
    miss = []
    if os.path.exists(idx):
        wm = json.load(open(idx)).get("weight_map", {})
        miss = sorted({v for v in wm.values()
                       if not os.path.exists(os.path.join(ORN, v))})
    if miss:
        log(f"THIEU SHARDS: {miss}")
    assert not miss, "thieu model shards (dataset ornbase thieu?)"
    log(f"base: {len(os.listdir(ORN))} files -> {ORN}")


def install_unsloth():
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("unsloth-") and f.endswith(".whl")
               for f in files):
            wheels = root
            break
    assert wheels, "thieu wheels unsloth"
    names = sorted(f for f in os.listdir(wheels) if f.endswith(".whl"))
    has_peft = any(n.startswith("peft-") for n in names)
    log(f"wheels {len(names)}: peft wheel = {has_peft}")
    if has_peft:  # v20 (fix TASK-9): cai peft tu wheels truoc
        sh(f"pip install --no-index --find-links {wheels} peft")
    sh(f"pip install --no-index --no-deps --find-links {wheels} "
       f"unsloth unsloth_zoo trl bitsandbytes")


def gen_one(rng, idx):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (CW, CH), (240, 240, 242))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CW, 48], fill=(52, 58, 70))
    d.text((16, 16), "Mock App", fill=(255, 255, 255))
    d.rectangle([0, CH - 36, CW, CH], fill=(228, 230, 235))
    cells = [(c, r) for r in range(3) for c in range(4)]
    rng.shuffle(cells)
    k = rng.randint(5, 9)
    elems = []
    used_colors = rng.sample(list(PALETTE), min(k, len(PALETTE)))
    if k > len(used_colors):
        used_colors += rng.choices(list(PALETTE), k=k - len(used_colors))
    for i in range(k):
        c, r = cells[i]
        cx = 40 + c * ((CW - 80) // 4) + rng.randint(4, 30)
        cy = 90 + r * ((CH - 190) // 3) + rng.randint(4, 24)
        w = rng.choice([70, 90, 110])
        h = rng.choice([56, 70])
        color = rng.choice(list(PALETTE))
        shape = rng.choice(SHAPES)
        box = [cx, cy, cx + w, cy + h]
        if shape == "circle":
            d.ellipse(box, fill=PALETTE[color])
        elif shape == "square":
            d.rectangle(box, fill=PALETTE[color])
        else:
            d.rounded_rectangle(box, radius=12, fill=PALETTE[color])
        elems.append({"color": color, "shape": shape, "box": box})
    path = os.path.join(IMGS, f"ui_{idx:05d}.png")
    img.save(path)
    return path, elems


def norm(v, total):
    return max(0, min(1000, int(round(v / total * 1000))))


def build_data(n, seed, start_idx=0):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        path, elems = gen_one(rng, start_idx + i)
        tgt = rng.choice(elems)
        x1, y1, x2, y2 = tgt["box"]
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        instr = rng.choice(TEMPLATES).format(c=tgt["color"],
                                             s=tgt["shape"])
        bbox_n = [norm(x1, CW), norm(y1, CH), norm(x2, CW), norm(y2, CH)]
        rows.append({
            "image": path,
            "instruction": instr,
            "point": [norm(cx, CW), norm(cy, CH)],
            "bbox": bbox_n,
        })
    return rows


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

# --- cong tac v19 (plan §3); STEPS khong dat o day nua -> steps_v19 in main() ---
RESPOND_ONLY = True    # True: chi train tren token assistant
LR = 2e-4              # giu 2e-4 + cosine nhu v18
INSTR_PART = "<|im_start|>user\n"
RESP_PART = "<|im_start|>assistant\n"

PREPROC = {
    "preprocessor_config.json": {
        "size": {"longest_edge": 16777216, "shortest_edge": 65536},
        "patch_size": 16, "temporal_patch_size": 2, "merge_size": 2,
        "image_mean": [0.5, 0.5, 0.5], "image_std": [0.5, 0.5, 0.5],
        "processor_class": "Qwen3VLProcessor",
        "image_processor_type": "Qwen2VLImageProcessorFast"},
    "processor_config.json": {
        "image_processor": {
            "do_convert_rgb": True, "do_normalize": True,
            "do_rescale": True, "do_resize": True,
            "image_mean": [0.5, 0.5, 0.5],
            "image_processor_type": "Qwen2VLImageProcessor",
            "image_std": [0.5, 0.5, 0.5], "merge_size": 2,
            "patch_size": 16, "resample": 3,
            "rescale_factor": 0.00392156862745098,
            "size": {"longest_edge": 16777216, "shortest_edge": 65536},
            "temporal_patch_size": 2},
        "processor_class": "Qwen3VLProcessor",
        "video_processor": {
            "do_convert_rgb": True, "do_normalize": True,
            "do_rescale": True, "do_resize": True,
            "do_sample_frames": True, "fps": 2,
            "image_mean": [0.5, 0.5, 0.5],
            "image_std": [0.5, 0.5, 0.5], "max_frames": 768,
            "merge_size": 2, "min_frames": 4, "patch_size": 16,
            "resample": 3, "rescale_factor": 0.00392156862745098,
            "return_metadata": False,
            "size": {"longest_edge": 25165824, "shortest_edge": 4096},
            "temporal_patch_size": 2,
            "video_processor_type": "Qwen3VLVideoProcessor"}},
    "video_preprocessor_config.json": {
        "size": {"longest_edge": 25165824, "shortest_edge": 4096},
        "patch_size": 16, "temporal_patch_size": 2, "merge_size": 2,
        "image_mean": [0.5, 0.5, 0.5], "image_std": [0.5, 0.5, 0.5],
        "processor_class": "Qwen3VLProcessor",
        "video_processor_type": "Qwen3VLVideoProcessor"},
}


def fix_processor():
    import re
    import transformers
    from transformers import AutoProcessor
    cands = [n for n in dir(transformers)
             if re.match(r"Qwen3.*(VL)?Processor$", n)]
    log(f"processor classes in transformers: {cands}")
    order = ["Qwen3VLProcessor", "Qwen3_5Processor", "Qwen3_5VLProcessor"]
    for n in cands:
        if n not in order:
            order.append(n)
    try:
        proc = AutoProcessor.from_pretrained(ORN)
        if hasattr(proc, "image_processor"):
            log(f"processor truc tiep OK: {type(proc).__name__}")
            return proc
        log("processor thieu image_processor, thu fallback configs")
    except Exception as e:
        log(f"AutoProcessor truc tiep loi: {str(e)[:200]}")
    for pclass in order:
        for fname, blob in PREPROC.items():
            b = json.loads(json.dumps(blob))
            if b.get("processor_class"):
                b["processor_class"] = pclass
            with open(os.path.join(ORN, fname), "w") as fh:
                json.dump(b, fh)
        try:
            proc = AutoProcessor.from_pretrained(ORN)
            if hasattr(proc, "image_processor"):
                log(f"processor fallback OK: {pclass} -> "
                    f"{type(proc).__name__}")
                return proc
            log(f"{pclass}: thieu image_processor")
        except Exception as e:
            log(f"{pclass} loi: {str(e)[:160]}")
    raise SystemExit("khong tao duoc processor co image_processor")


def to_msgs(rows):
    out = []
    for r in rows:
        act = r.get("action")
        if act is None:
            act = f"CLICK {r['point'][0]} {r['point'][1]}"
        out.append({"messages": [
            {"role": "system", "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": [
                {"type": "image", "image": r["image"]},
                {"type": "text", "text": f"Task: {r['instruction']}"}]},
            {"role": "assistant", "content": [
                {"type": "text", "text": act}]},
        ]})
    return out


def hit(point, bbox):
    x, y = point
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def parse_click(text):
    import re
    t = (text or "").strip()
    m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                  t, re.I)
    if not m:
        m = re.search(r"(\d{1,4})\s*[,;\s]\s*(\d{1,4})", t)
    if not m:
        return None
    return [int(m.group(1)), int(m.group(2))]


def parse_action(text):
    import re
    t = (text or "").strip()
    m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                  t, re.I)
    if m:
        return f"CLICK {int(m.group(1))} {int(m.group(2))}"
    m = re.search(r"TYPE\s+(.+)", t, re.I)
    if m:
        return "TYPE " + m.group(1).strip().split("\n")[0]
    m = re.search(r"KEY\s+(\w+)", t, re.I)
    if m:
        return "KEY " + m.group(1).lower()
    if re.search(r"\bDONE\b", t, re.I):
        return "DONE"
    return None


# leak v19: mot dong output la "action" khi bat dau bang CLICK/TYPE/KEY/DONE
# (phan con lai — prose/ke chuyen — dem la leak; metric leak-rate plan §3)
ACTION_RX = re.compile(r"^\s*(?:CLICK|TYPE|KEY|DONE)\b", re.I)


def load_ds_rows(substr, fname):
    import zipfile
    base = None
    for root, _, files in os.walk("/kaggle/input"):
        if fname in files and substr in root.replace("\\", "/"):
            base = root
            break
    if not base:
        log(f"{substr}: khong thay {fname} -> skip")
        return []
    rows = []
    with open(os.path.join(base, fname), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    ext = os.path.join(WORK, "real_imgs")
    os.makedirs(ext, exist_ok=True)
    for f in os.listdir(base):
        if f.endswith(".zip"):
            try:
                with zipfile.ZipFile(os.path.join(base, f)) as z:
                    z.extractall(ext)
            except Exception as e:
                log(f"{substr}: unzip loi {f}: {e}")

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
        return None
    out = []
    for r in rows:
        p = _resolve(r["image"])
        if p:
            r = dict(r)
            r["image"] = p
            out.append(r)
    log(f"{substr}: {len(out)}/{len(rows)} rows ({fname})")
    return out


def evaluate(model, processor, rows, tag, n=120, samples=0,
             adapter_probe=False):
    import time as _time
    import torch
    from unsloth import FastVisionModel
    t_start = _time.time()
    FastVisionModel.for_inference(model)
    model.eval()
    ok = 0
    np = 0
    nleak = 0
    nfail = 0
    rng = random.Random(7)
    sub = rows[:n]
    for j, r in enumerate(sub):
        from PIL import Image
        img = Image.open(r["image"]).convert("RGB")
        msgs = [{"role": "system", "content": [{"type": "text",
                                                "text": SYS}]},
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text",
                     "text": f"Task: {r['instruction']}"}]}]
        text = processor.apply_chat_template(msgs, tokenize=False,
                                             add_generation_prompt=True)
        inputs = processor(text=[text], images=[img],
                           return_tensors="pt").to(model.device)
        if j == 0:
            iid = getattr(model.config, "image_token_id", 248056)
            log(f"  [{tag}] input len={inputs['input_ids'].shape[1]} "
                f"img_pad={int((inputs['input_ids'] == iid).sum())}")
        with torch.no_grad():
            gen = model.generate(**inputs, max_new_tokens=24,
                                 do_sample=False)
        ans = processor.batch_decode(
            gen[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True)[0]
        pt = parse_click(ans)
        pa = parse_action(ans)
        first_word_action = bool(ACTION_RX.match(ans or ""))
        if pa:
            np += 1
        if not first_word_action:
            nleak += 1
        gt_act = r.get("action")
        good = False
        if gt_act is None:
            good = bool(pt and hit(pt, r["bbox"]))
        elif gt_act.startswith("CLICK") and pt:
            if "bbox" in r:
                good = hit(pt, r["bbox"])
            else:
                good = (abs(pt[0] - r["point"][0]) <= 25 and
                        abs(pt[1] - r["point"][1]) <= 25)
        elif gt_act == pa:
            good = True
        if not good and nfail < 3:
            nfail += 1
            log(f"  [{tag}] FAIL out={ans.strip()[:90]!r} "
                f"gt={gt_act or r.get('point')}")
        if good:
            ok += 1
        if j == 0 and adapter_probe:
            try:
                model.disable_adapter_layers()
                with torch.no_grad():
                    gen2 = model.generate(**inputs, max_new_tokens=24,
                                          do_sample=False)
                ans2 = processor.batch_decode(
                    gen2[:, inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True)[0]
                model.enable_adapter_layers()
                log(f"  [{tag}] adapter ON={ans.strip()[:45]!r} "
                    f"OFF={ans2.strip()[:45]!r}")
            except Exception as e:
                log(f"  [{tag}] adapter probe loi: {type(e).__name__} {e}")
        if j < samples:
            log(f"  [{tag}] out={ans.strip()[:60]!r} pa={pa} "
                f"gt={gt_act or [r.get('point'), r.get('bbox')]}")
        if (j + 1) % 20 == 0:
            log(f"  [{tag}] {j + 1}/{len(sub)} acc so bo "
                f"{ok}/{j + 1} leak={nleak}/{j + 1} "
                f"t={time.time() - t_start:.0f}s")
    acc = ok / max(len(sub), 1)
    leak = nleak / max(len(sub), 1)
    log(f"EVAL {tag}: hit {ok}/{len(sub)} = {acc:.3f} parse={np}/{len(sub)} "
        f"leak={nleak}/{len(sub)} = {leak:.3f}")
    return acc, leak


class MiniEvalCallback(TrainerCallback):
    """v19 plan §4: mini-eval moi khi save ckpt (save_steps=100):
    24 synth held-out + 8 traj + leak-rate. Loi eval KHONG BAO GIO lam chet
    train (try/except); xong luon restore for_training."""

    def __init__(self, peft_model, processor, eval_rows, traj_pool):
        self.model = peft_model
        self.proc = processor
        self.eval_rows = eval_rows
        self.traj_pool = traj_pool
        self.book = []  # ghi mini_eval_log.json — chon diem ngot theo ckpt

    def on_save(self, args, state, control, **kwargs):
        try:
            t0 = time.time()
            acc_s, leak_s = evaluate(self.model, self.proc, self.eval_rows,
                                     f"mini-synth@{state.global_step}",
                                     n=24, samples=0)
            acc_j, leak_j = 0.0, 0.0
            if self.traj_pool:
                acc_j, leak_j = evaluate(
                    self.model, self.proc, self.traj_pool[:64],
                    f"mini-traj@{state.global_step}", n=8, samples=0)
            self.book.append({
                "step": state.global_step,
                "acc_synth": round(acc_s, 4), "leak_synth": round(leak_s, 4),
                "acc_traj": round(acc_j, 4), "leak_traj": round(leak_j, 4),
                "t_sec": round(time.time() - t0, 1)})
            with open(os.path.join(WORK, "mini_eval_log.json"), "w",
                      encoding="utf-8") as f:
                json.dump(self.book, f, ensure_ascii=False, indent=1)
            log(f"MINI-EVAL step {state.global_step}: synth {acc_s:.3f} "
                f"(leak {leak_s:.3f}) traj {acc_j:.3f} (leak {leak_j:.3f})")
        except Exception as e:
            log(f"MINI-EVAL loi (KHONG chet train): {type(e).__name__}: "
                f"{str(e)[:200]}")
        finally:
            try:
                from unsloth import FastVisionModel
                FastVisionModel.for_training(self.model)
                self.model.train()
            except Exception as e:
                log(f"restore for_training loi (train tiep tuc): "
                    f"{type(e).__name__}: {str(e)[:120]}")
        return control


# ===================== v20: REASONING (TASK-14) ============================
# Theo MAIN_QUEST.md §2: target 2 dong THINK + ACTION; decode REASON_MAX=256;
# parser uu tien dong ACTION CUOI, fallback bare legacy. Metrics moi:
# prose_leak (prose ngoai THINK), legacy_leak (metric v19), trunc_rate,
# mean_new_tokens — tat ca ghi vao EVAL_STATS -> gui_result.json.

THINK_RX = re.compile(r"^\s*THINK\s*:", re.I)
ACTION_LINE_RX = re.compile(r"^\s*ACTION\s*:\s*(.*)$", re.I)
ACTION_RX = re.compile(r"^\s*(?:CLICK|TYPE|KEY|DONE)\b", re.I)


class EvalResult(dict):
    """dict + unpack (acc, leak) nhu tuple — khong vo call site cua v19."""

    def __iter__(self):
        return iter((self["acc"], self["leak"]))


def _split_verb(s):
    parts = (s or "").strip().split(None, 1)
    if not parts:
        return None, ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def _norm_action(verb, rest):
    verb = (verb or "").upper()
    rest = (rest or "").strip()
    if verb == "CLICK":
        m = re.search(r"(\d{1,4})\s*[,;\s]\s*(\d{1,4})", rest)
        if not m:
            return None, None
        return "CLICK", [int(m.group(1)), int(m.group(2))]
    if verb == "TYPE":
        t = rest.strip().strip('"').split("\n")[0].strip()
        return ("TYPE", t) if t else (None, None)
    if verb == "KEY":
        m = re.search(r"[A-Za-z0-9_\-+]+", rest)
        return ("KEY", m.group(0).lower()) if m else (None, None)
    if verb == "DONE":
        return "DONE", None
    return None, None


def act_to_str(act):
    if not act:
        return None
    v, a = act
    if v == "CLICK":
        return f"CLICK {a[0]} {a[1]}"
    if v == "TYPE":
        return f"TYPE {a}"
    if v == "KEY":
        return f"KEY {a}"
    return "DONE"


def parse_output(text):
    lines = [l.rstrip() for l in (text or "").splitlines() if l.strip()]
    act = None
    mode = "none"
    act_i = None
    for i, l in enumerate(lines):
        m = ACTION_LINE_RX.match(l)
        if m:
            v, a = _norm_action(*_split_verb(m.group(1)))
            if v:
                act, mode, act_i = (v, a), "action", i
    if act is None:
        for i, l in enumerate(lines):
            m = ACTION_RX.match(l)
            if m:
                verb, rest = _split_verb(l.strip())
                v, a = _norm_action(verb, rest)
                if v:
                    act, mode, act_i = (v, a), "legacy", i
                    break
    limit = act_i if act_i is not None else len(lines)
    extra_actions = sum(1 for l in lines[:limit] if ACTION_LINE_RX.match(l))
    prose = [l for l in lines[:limit]
             if not THINK_RX.match(l) and not ACTION_LINE_RX.match(l)]
    think = [l for l in lines[:limit] if THINK_RX.match(l)]
    return {"action": act, "mode": mode, "act_str": act_to_str(act),
            "prose_lines": len(prose), "think_lines": len(think),
            "think_text": "\n".join(think),
            "extra_actions": extra_actions}


def make_think(r, act):
    """Template reasoning CO KIEM CHUNG tu metadata (label/instruction + toa
    do cua chinh target) — MAIN_QUEST §2.4: khong bia suy doan."""
    lab = (r.get("label") or "").strip().lower()
    a = (act or "").strip()
    au = a.upper()
    if au.startswith("CLICK"):
        parts = a.split()
        x = parts[1] if len(parts) > 1 else "0"
        y = parts[2] if len(parts) > 2 else "0"
        if lab:
            return (f"THINK: I need to click the {lab}. I can see it in the "
                    f"screenshot near ({x}, {y}), so I will click there.")
        return (f"THINK: I need to click the target from the task. It is near "
                f"({x}, {y}) in the screenshot, so I will click there.")
    if au.startswith("TYPE"):
        return ("THINK: The input field is focused and the task tells me what "
                "to type. I will type it now.")
    if au.startswith("KEY"):
        key = a.split(None, 1)[1].strip().lower() if " " in a else "enter"
        return (f"THINK: I need to press the {key} key to move the task "
                f"forward. I will press it now.")
    return "THINK: The task goal has been reached, so I will finish now."


def to_msgs_v2(rows):
    out = []
    for r in rows:
        act = r.get("action")
        if act is None:
            act = f"CLICK {r['point'][0]} {r['point'][1]}"
        think = r.get("think") or make_think(r, act)
        if not think.upper().startswith("THINK"):
            think = "THINK: " + think
        out.append({"messages": [
            {"role": "system", "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": [
                {"type": "image", "image": r["image"]},
                {"type": "text", "text": f"Task: {r['instruction']}"}]},
            {"role": "assistant", "content": [
                {"type": "text", "text": think + "\nACTION: " + act}]},
        ]})
    return out


def evaluate_v2(model, processor, rows, tag, n=120, samples=0,
                adapter_probe=False):
    import time as _time
    import torch
    from unsloth import FastVisionModel
    t_start = _time.time()
    FastVisionModel.for_inference(model)
    model.eval()
    ok = 0
    np_ok = 0
    nprose = 0
    nlegacy = 0
    modes = {"action": 0, "legacy": 0, "none": 0}
    new_tokens = []
    ntrunc = 0
    nfail = 0
    sub = rows[:n]
    for j, r in enumerate(sub):
        from PIL import Image
        img = Image.open(r["image"]).convert("RGB")
        msgs = [{"role": "system", "content": [{"type": "text",
                                                "text": SYS}]},
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text",
                     "text": f"Task: {r['instruction']}"}]}]
        text = processor.apply_chat_template(msgs, tokenize=False,
                                             add_generation_prompt=True)
        inputs = processor(text=[text], images=[img],
                           return_tensors="pt").to(model.device)
        if j == 0:
            iid = getattr(model.config, "image_token_id", 248056)
            log(f"  [{tag}] input len={inputs['input_ids'].shape[1]} "
                f"img_pad={int((inputs['input_ids'] == iid).sum())}")
        with torch.no_grad():
            gen = model.generate(**inputs, max_new_tokens=REASON_MAX,
                                 do_sample=False)
        n_new = int(gen.shape[1] - inputs["input_ids"].shape[1])
        new_tokens.append(n_new)
        if n_new >= REASON_MAX:
            ntrunc += 1
        ans = processor.batch_decode(
            gen[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True)[0]
        po = parse_output(ans)
        pa = po["act_str"]
        modes[po["mode"]] = modes.get(po["mode"], 0) + 1
        if po["mode"] != "none":
            np_ok += 1
        if po["prose_lines"] > 0:
            nprose += 1
        if not bool(ACTION_RX.match((ans or "").strip())):
            nlegacy += 1
        act = po["action"]
        gt_act = r.get("action")
        good = False
        if gt_act is None:
            good = bool(act and act[0] == "CLICK" and hit(act[1], r["bbox"]))
        elif gt_act.startswith("CLICK"):
            if act and act[0] == "CLICK":
                if "bbox" in r:
                    good = hit(act[1], r["bbox"])
                else:
                    good = (abs(act[1][0] - r["point"][0]) <= 25 and
                            abs(act[1][1] - r["point"][1]) <= 25)
        elif act:
            good = (gt_act == pa)
        if not good and nfail < 3:
            nfail += 1
            log(f"  [{tag}] FAIL out={ans.strip()[:110]!r} "
                f"gt={gt_act or r.get('point')}")
        if good:
            ok += 1
        if j == 0 and adapter_probe:
            try:
                model.disable_adapter_layers()
                with torch.no_grad():
                    gen2 = model.generate(**inputs, max_new_tokens=64,
                                          do_sample=False)
                ans2 = processor.batch_decode(
                    gen2[:, inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True)[0]
                model.enable_adapter_layers()
                log(f"  [{tag}] adapter ON={ans.strip()[:60]!r} "
                    f"OFF={ans2.strip()[:60]!r}")
            except Exception as e:
                log(f"  [{tag}] adapter probe loi: {type(e).__name__} {e}")
        if j < samples:
            log(f"  [{tag}] out={ans.strip()[:110]!r} pa={pa} "
                f"gt={gt_act or [r.get('point'), r.get('bbox')]}")
        if (j + 1) % 20 == 0:
            log(f"  [{tag}] {j + 1}/{len(sub)} acc so bo "
                f"{ok}/{j + 1} prose={nprose}/{j + 1} "
                f"t={_time.time() - t_start:.0f}s")
    acc = ok / max(len(sub), 1)
    res = EvalResult(
        tag=tag, n=len(sub), acc=acc,
        leak=nprose / max(len(sub), 1),
        legacy_leak=nlegacy / max(len(sub), 1),
        parse=np_ok, parse_rate=np_ok / max(len(sub), 1),
        modes=modes, trunc_rate=ntrunc / max(len(sub), 1),
        mean_new=round(sum(new_tokens) / max(len(new_tokens), 1), 1),
        max_new=max(new_tokens) if new_tokens else 0,
        t_sec=round(_time.time() - t_start, 1))
    EVAL_STATS[tag] = res
    log(f"EVAL {tag}: hit {ok}/{len(sub)} = {acc:.3f} "
        f"parse={np_ok}/{len(sub)} prose_leak={nprose}/{len(sub)}="
        f"{res['leak']:.3f} legacy_leak={res['legacy_leak']:.3f} "
        f"trunc={ntrunc}/{len(sub)} mean_new={res['mean_new']:.0f}t")
    return res


# rebind ten cu -> ban v20 (call site trong main()/MiniEvalCallback khong doi)
to_msgs = to_msgs_v2
evaluate = evaluate_v2


def main():
    os.makedirs(IMGS, exist_ok=True)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    t0 = time.time()
    assemble_base()
    install_unsloth()
    sys.path.insert(0, "")
    from unsloth import FastVisionModel
    import torch

    log("gen data...")
    # v19: synth REGEN seed moi moi run (plan §3 — chong nho anh cu seed 101);
    # eval held-out GIU Y NGUYEN (seed 202, offset 90000) de so chieu voi v18.
    synth_rows = build_data(N_TRAIN, SEED_V19, 0)
    eval_rows = build_data(N_EVAL, 202, 90000)
    real_rows = load_ds_rows("real-fixtures", "grounding.jsonl")
    real_train = load_ds_rows("real-ui", "grounding.jsonl")
    traj_rows = load_ds_rows("gui-traj", "traj.jsonl")
    # slot dataset traj MOI (mui end-action login/counter-style) — fail-soft
    traj_rows2 = load_ds_rows("gui-traj-v19", "traj.jsonl")
    # slot v20: self-play Day-1/Day-2 (fail-soft — chua co dataset thi bo qua)
    selfplay_rows = load_ds_rows("gui-selfplay", "traj.jsonl")
    traj_pool = list(traj_rows) + list(traj_rows2) + list(selfplay_rows)
    train_rows = synth_rows + real_train + traj_pool
    n_train_by_domain = {"synth": len(synth_rows), "real": len(real_train),
                         "traj": len(traj_rows), "traj_v19": len(traj_rows2),
                         "selfplay": len(selfplay_rows)}
    # v19: STEPS tu dong = 2.0 epoch (khong tang khi khong them data — draft §3)
    steps_v19 = max(200, int(EPOCH_TARGET * len(train_rows) / EFFECTIVE_BS))
    log(f"steps_v19 = max(200, {EPOCH_TARGET} * {len(train_rows)} / "
        f"{EFFECTIVE_BS}) = {steps_v19} (target {EPOCH_TARGET} epoch)")
    _mx = 0
    from PIL import Image as _PILImage
    for _r in train_rows:
        try:
            with _PILImage.open(_r["image"]) as _im:
                _mx = max(_mx, _im.size[0] * _im.size[1])
        except Exception:
            pass
    log(f"img lon nhat {_mx} px -> ~{_mx // 1024} img tokens (budget 4096)")
    if _mx // 1024 > 3500:
        log("CANH BAO: anh qua lon cho max_seq_length 4096!")
    log(f"train={len(train_rows)} (synth {len(synth_rows)} + "
        f"real {len(real_train)} + traj {len(traj_rows)} + "
        f"traj_v19 {len(traj_rows2)} + selfplay {len(selfplay_rows)}) "
        f"eval={len(eval_rows)} "
        f"seed_v19={SEED_V19} t={time.time() - t0:.0f}s")
    with open(os.path.join(WORK, "gui_data_preview.json"), "w") as f:
        json.dump([{k: v for k, v in r.items() if k != "image"}
                   for r in train_rows[:20]], f)

    log("load FastVisionModel...")
    proc = fix_processor()
    model, processor = FastVisionModel.from_pretrained(
        ORN, load_in_4bit=False, max_seq_length=4096,
        use_gradient_checkpointing="unsloth")
    processor = proc
    model = FastVisionModel.get_peft_model(
        model, r=64, lora_alpha=64, lora_dropout=LORA_DROPOUT,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    log(f"model loaded t={time.time() - t0:.0f}s")

    acc0, leak_eval0 = evaluate(model, processor, eval_rows, "before",
                                n=25, samples=3)
    accR0, leak_real0 = 0.0, 0.0
    if real_rows:
        accR0, leak_real0 = evaluate(model, processor, real_rows,
                                     "real-before", n=42, samples=3)

    log("build trainer...")
    from trl import SFTTrainer, SFTConfig
    from datasets import Dataset
    from unsloth.trainer import UnslothVisionDataCollator
    ds = Dataset.from_list(to_msgs(train_rows))
    IMG_ID = getattr(getattr(model, "config", None), "image_token_id", 248056)
    mini_eval = MiniEvalCallback(model, processor, eval_rows, traj_pool)
    log(f"mini-eval callback: moi {SAVE_STEPS} steps (save) -> "
        f"24 synth + 8 traj")

    def _diag_inputs(ids_row, labs_row, tag):
        sup = processor.tokenizer.decode(
            [i for i, l in zip(ids_row, labs_row) if l != -100],
            skip_special_tokens=True)
        n_img = sum(1 for i in ids_row if i == IMG_ID)
        log(f"DIAG {tag}: len={len(ids_row)} img_pad={n_img} "
            f"supervised={sup[:120]!r}")
    cfg = SFTConfig(
        output_dir=os.path.join(WORK, "gui_trainer"),
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,   # effective bs 16 = EFFECTIVE_BS (giu v18)
        max_steps=steps_v19,             # 2.0 epoch tu dong theo n_train
        warmup_steps=WARMUP,             # v19: 10 -> 15
        learning_rate=LR,
        logging_steps=10,
        save_steps=SAVE_STEPS,           # v19: 150 -> 100 (mini-eval moi ckpt)
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=SEED_V19,                   # v19: seed moi run (v18: hardcode 13)
        report_to="none",
        max_seq_length=4096,
        dataset_text_field="",
        dataset_kwargs={"skip_prepare_dataset": True},
    )
    coll_kwargs = dict(resize="max")
    if RESPOND_ONLY:
        coll_kwargs.update(train_on_responses_only=True,
                           instruction_part=INSTR_PART,
                           response_part=RESP_PART)
    coll = UnslothVisionDataCollator(model, processor, **coll_kwargs)
    try:
        b0 = coll([ds[0]])
        _diag_inputs(b0["input_ids"][0].tolist(),
                     b0["labels"][0].tolist(), "collator")
        if "pixel_values" in b0:
            log(f"DIAG collator pixel_values: {tuple(b0['pixel_values'].shape)}")
    except Exception as e:
        log(f"DIAG collator loi: {type(e).__name__} {e}")
    try:
        trainer = SFTTrainer(model=model, tokenizer=processor.tokenizer,
                             data_collator=coll, train_dataset=ds,
                             args=cfg, callbacks=[mini_eval])
    except TypeError as e:
        log(f"trainer fallback processing_class ({e})")
        trainer = SFTTrainer(model=model, processing_class=processor,
                             data_collator=coll, train_dataset=ds,
                             args=cfg, callbacks=[mini_eval])
    log("TRAIN start")
    trainer.train()
    log(f"TRAIN done t={time.time() - t0:.0f}s")

    acc1, leak_eval1 = evaluate(model, processor, eval_rows, "after", n=100,
                                samples=5, adapter_probe=True)
    accT, leak_train = evaluate(model, processor, train_rows, "train-sub",
                                n=12, samples=5, adapter_probe=True)
    accTj, leak_traj = 0.0, 0.0
    if traj_pool:
        accTj, leak_traj = evaluate(model, processor, traj_pool[::50][:16],
                                    "traj-sub", n=16, samples=3,
                                    adapter_probe=True)
    accR1, leak_real1 = 0.0, 0.0
    if real_rows:
        accR1, leak_real1 = evaluate(model, processor, real_rows,
                                     "real-after", n=42, samples=5,
                                     adapter_probe=True)

    model.save_pretrained(os.path.join(WORK, "gui_lora"))
    try:
        processor.save_pretrained(os.path.join(WORK, "gui_lora"))
    except Exception as e:
        log(f"save processor loi: {e}")
    # v19: leak THEO TUNG DOMAIN + config v19 — doi chieu gate (leak <=0.05)
    leak_by_domain = {
        "synth_eval_before": round(leak_eval0, 4),
        "synth_eval_after": round(leak_eval1, 4),
        "real_before": round(leak_real0, 4),
        "real_after": round(leak_real1, 4),
        "train_sub": round(leak_train, 4),
        "traj_sub": round(leak_traj, 4)}
    with open(os.path.join(WORK, "gui_result.json"), "w") as f:
        json.dump({"acc_before": acc0, "acc_after": acc1,
                   "acc_train_sub": accT, "acc_traj_sub": accTj,
                   "acc_real_before": accR0, "acc_real_after": accR1,
                   "leak_by_domain": leak_by_domain,
                   "leak_max": max(leak_by_domain.values()),
                   "n_train": len(train_rows),
                   "n_train_by_domain": n_train_by_domain,
                   "seed": SEED_V19, "epoch_target": EPOCH_TARGET,
                   "epochs_eff": round(steps_v19 * EFFECTIVE_BS /
                                       max(len(train_rows), 1), 3),
                   "steps": steps_v19, "warmup": WARMUP,
                   "save_steps": SAVE_STEPS, "lora_dropout": LORA_DROPOUT,
                   "reason_max": REASON_MAX,
                   "reason_stats": EVAL_STATS,
                   "mini_eval_ckpt": mini_eval.book,
                   "t_sec": time.time() - t0}, f)
    log(f"ALL DONE before={acc0:.3f} after={acc1:.3f} "
        f"train_sub={accT:.3f} traj_sub={accTj:.3f} "
        f"real_before={accR0:.3f} real_after={accR1:.3f}")
    log("LEAK by domain: "
        + " | ".join(f"{k}={v:.3f}" for k, v in leak_by_domain.items())
        + f" (gate moi domain <= 0.05); mini_eval ckpt: "
        + (f"{len(mini_eval.book)} diem" if mini_eval.book else "khong co"))


if __name__ == "__main__":
    main()
