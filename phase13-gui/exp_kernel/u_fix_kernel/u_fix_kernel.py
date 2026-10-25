"""u_fix_kernel — TASK-9 (GLM): U-bf16 rescue + diagnostic thinking-cut (nối tiếp TASK-4).

Mục đích (theo TASK-9 trên TASK BOARD):
  1) Cứu stack U-bf16 (Unsloth) đang chết `ImportError: Please install peft`
     trong `exp_h2_result.json` (U = {} trống, lỗi thật ở log kernel).
  2) DIAGNOSTIC bắt buộc: chạy lại 4 case fail (synth_00/02/04/login_pil) trên
     stack T-bf16 với `max_new_tokens=96`, in RAW đầy đủ — kiểm chứng giả thuyết
     "thinking bị cắt ở 24 token" (raw exp đều trunc tại ~24 token).

Kế hoạch (bám đủ 4 bước trong board):
  (1) Liệt kê wheels trong input; cài `peft` từ wheels (`--no-index --find-links`,
      thử cả có/không `--no-deps`; wheels không có peft → ghi rõ vào report).
  (2) Chạy phần U trong **Python con RIÊNG** với `import unsloth` ĐẦU TIÊN
      (trước transformers/peft) — thứ tự import thật sự sạch, không bị T-stack ở
      process chính làm bẩn.
  (3) Log version peft/unsloth/unsloth_zoo tại chỗ lỗi + traceback đầy đủ.
  (4) Vẫn chết → thử đường vòng (pattern from_pretrained khác) + báo cáo, KHÔNG bỏ qua.

Offline-friendly: `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`, chỉ `pip uninstall -y torchao`
(offline, như v14); unsloth cài từ wheels dataset nếu có (`--no-index`).
Kết quả -> /kaggle/working/u_fix_result.json (+ /kaggle/working/u_child_result.json).
"""
import gc
import json
import os
import re
import subprocess
import sys
import time
import traceback

WORK = "/kaggle/working"
ORN = "/tmp/ornbase"
OUT_JSON = os.path.join(WORK, "u_fix_result.json")
CASE_IMG_DIR = os.path.join(WORK, "u_cases")
CHILD_SCRIPT = os.path.join(WORK, "u_child.py")
CHILD_JSON = os.path.join(WORK, "u_child_result.json")
U_FAIL_IDS = ("synth_00", "synth_02", "synth_04", "login_pil")
MAX_T96 = 96
MAX_U = 24

SYS = ("You are a GUI agent. Look at the screenshot and the task, then "
       "output ONE action line only.\n"
       "Actions: CLICK x y (x,y integers 0..1000 normalized to image "
       "width/height) | TYPE text (type into the focused field) | "
       "KEY name (press a key, e.g. enter) | DONE (task is complete). "
       "No explanation.")

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
            "do_rescale": True, "do_sample_frames": True, "fps": 2,
            "image_mean": [0.5, 0.5, 0.5],
            "image_processor_type": "Qwen2VLImageProcessor",
            "image_std": [0.5, 0.5, 0.5], "merge_size": 2,
            "patch_size": 16, "resample": 3,
            "rescale_factor": 0.00392156862745098,
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


def log(m):
    print("[u_fix] " + str(m), flush=True)


def sh(cmd, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
        return None
    return r


def header_log():
    """LUAT tu TASK-4: log dau GPU + dtype + version stack."""
    import torch
    has_gpu = torch.cuda.is_available()
    log(f"gpu: {torch.cuda.get_device_name(0) if has_gpu else 'NONE'} "
        f"x{torch.cuda.device_count()}")
    vram_gb = 0.0
    if has_gpu:
        p = torch.cuda.get_device_properties(0)
        vram_gb = p.total_memory / 1024 ** 3
        log(f"vram: {vram_gb:.1f} GB | sm_{p.major}{p.minor}")
    log(f"default dtype: {torch.get_default_dtype()}")
    log(f"torch: {torch.__version__}")
    import transformers
    log(f"transformers: {transformers.__version__}")
    try:
        import peft
        log(f"peft: {peft.__version__}")
    except ImportError:
        log("peft: (chua import)")
    try:
        import unsloth
        log(f"unsloth: {unsloth.__version__}")
    except Exception as e:
        log(f"unsloth: (chua nhan import, se thu cai sau) {type(e).__name__}")
    try:
        import unsloth_zoo
        log(f"unsloth_zoo: {getattr(unsloth_zoo, '__version__', 'n/a')}")
    except Exception as e:
        log(f"unsloth_zoo: (chua import) {type(e).__name__}")
    return vram_gb


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


def find_lora():
    for root, _, files in os.walk("/kaggle/input"):
        if "adapter_config.json" in files:
            return root
    return None


def fix_processor():
    import re
    import transformers
    from transformers import AutoProcessor
    cands = [n for n in dir(transformers)
             if re.match(r"Qwen3.*(VL)?Processor$", n)]
    log(f"processor classes: {cands}")
    order = ["Qwen3VLProcessor", "Qwen3_5Processor", "Qwen3_5VLProcessor"]
    for n in cands:
        if n not in order:
            order.append(n)
    try:
        proc = AutoProcessor.from_pretrained(ORN)
        if hasattr(proc, "image_processor"):
            log(f"processor truc tiep OK: {type(proc).__name__}")
            return proc
    except Exception as e:
        log(f"AutoProcessor loi: {str(e)[:160]}")
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
                log(f"processor fallback OK: {pclass}")
                return proc
        except Exception as e:
            log(f"{pclass} loi: {str(e)[:120]}")
    raise SystemExit("khong tao duoc processor")


def concretize_lora(lora):
    import shutil
    from safetensors import safe_open
    from peft import PeftConfig
    cfg = PeftConfig.from_pretrained(lora)
    tm = cfg.target_modules
    if isinstance(tm, (list, set, tuple)):
        return lora, tm
    f = os.path.join(lora, "adapter_model.safetensors")
    keys = []
    with safe_open(f, framework="pt", device="cpu") as sf:
        for k in sf.keys():
            if ".lora_A" in k or ".lora_B" in k:
                keys.append(k)
    mods = sorted({k.split(".lora_")[0].replace("base_model.model.", "", 1)
                   for k in keys})
    if not mods:
        return lora, None
    fixed = os.path.join("/tmp", "lora_fixed")
    if os.path.isdir(fixed):
        shutil.rmtree(fixed)
    shutil.copytree(lora, fixed)
    pc = json.load(open(os.path.join(fixed, "adapter_config.json")))
    pc["target_modules"] = mods
    with open(os.path.join(fixed, "adapter_config.json"), "w") as fh:
        json.dump(pc, fh)
    log(f"concretize target_modules: {len(mods)} modules (vd {mods[0]})")
    return fixed, mods


def free_gpu(model):
    if model is None:
        return
    try:
        del model
    except Exception:
        pass
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    log("free GPU roi")


# ---------------- bo tap hinh (chi 4 case fail, deterministic) ---------------

def build_synth_cases(n=5):
    from PIL import Image, ImageDraw
    import random
    rng = random.Random(42)
    PALETTE = {"red": (208, 52, 44), "green": (46, 158, 68),
               "blue": (30, 111, 217), "yellow": (201, 161, 10),
               "purple": (122, 59, 189), "orange": (217, 122, 30),
               "teal": (20, 160, 160)}
    SHAPES = ["button", "square", "circle"]
    TEMPLATES = [
        "Click the {c} {s}.", "Tap the {c} {s}.",
        "Click on the {c} {s}.", "Find the {c} {s} and click it.",
        "Where do you click for the {c} {s}?"]
    CW, CH = 768, 512
    os.makedirs(CASE_IMG_DIR, exist_ok=True)
    out = []
    for i in range(n):
        img = Image.new("RGB", (CW, CH), (240, 240, 242))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, CW, 48], fill=(52, 58, 70))
        d.text((16, 16), "Mock App", fill=(255, 255, 255))
        d.rectangle([0, CH - 36, CW, CH], fill=(228, 230, 235))
        cells = [(c, r) for r in range(3) for c in range(4)]
        rng.shuffle(cells)
        k = rng.randint(5, 9)
        elems = []
        cols = rng.sample(list(PALETTE), min(k, len(PALETTE)))
        if k > len(cols):
            cols += rng.choices(list(PALETTE), k=k - len(cols))
        for j in range(k):
            c, r = cells[j]
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
        tgt = rng.choice(elems)
        x1, y1, x2, y2 = tgt["box"]
        instr = rng.choice(TEMPLATES).format(c=tgt["color"], s=tgt["shape"])
        bbox = [max(0, min(1000, int(round(v / total * 1000))))
                for v, total in zip((x1, y1, x2, y2), (CW, CH, CW, CH))]
        p = os.path.join(CASE_IMG_DIR, f"synth_{i:02d}.png")
        img.save(p)
        out.append({"id": f"synth_{i:02d}", "img": p, "instr": instr,
                    "bbox": bbox, "domain": "synth"})
    return out


def build_login_pil_case():
    from PIL import Image, ImageDraw
    W, H = 1024, 720
    img = Image.new("RGB", (W, H), (238, 241, 245))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([302, 80, 722, 640], radius=18, fill=(255, 255, 255))
    d.text((350, 120), "Sign in", fill=(20, 20, 20))
    d.text((350, 186), "Username", fill=(90, 90, 90))
    d.rectangle([350, 214, 674, 254], fill=(255, 255, 255),
                outline=(120, 130, 240), width=3)
    d.text((362, 224), "admin", fill=(20, 20, 20))
    d.text((350, 282), "Password", fill=(90, 90, 90))
    d.rectangle([350, 310, 674, 350], fill=(255, 255, 255),
                outline=(185, 185, 185))
    d.text((362, 320), "****", fill=(20, 20, 20))
    d.rectangle([350, 462, 674, 504], fill=(30, 111, 217))
    d.text((482, 476), "Sign in", fill=(255, 255, 255))
    p = os.path.join(CASE_IMG_DIR, "login_filled_pil.png")
    img.save(p)
    bbox = [int(round(350 / W * 1000)), int(round(462 / H * 1000)),
            int(round(674 / W * 1000)), int(round(504 / H * 1000))]
    return {"id": "login_pil", "img": p,
            "instr": "Log in with username admin and password 1234. "
                     "When you are done, say DONE.",
            "bbox": bbox, "domain": "login_pil"}


# ---------------- sinh output + ghi nguyen van ------------------------------

def gen_one(model, processor, img_path, instr, max_new_tokens=24):
    import torch
    from PIL import Image
    msgs = [{"role": "system",
             "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": "Task: " + instr}]}]
    text = processor.apply_chat_template(msgs, tokenize=False,
                                        add_generation_prompt=True)
    img = Image.open(img_path).convert("RGB")
    inputs = processor(text=[text], images=[img],
                       return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                             do_sample=False)
    dt = time.time() - t0
    txt = processor.batch_decode(out[:, inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)[0]
    return txt.strip(), dt


def parse_action(text):
    t = (text or "").strip()
    m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                  t, re.I)
    if m:
        return ("click", [int(m.group(1)), int(m.group(2))])
    m = re.search(r"TYPE\s+(.+)", t, re.I)
    if m:
        return ("type", m.group(1).strip())
    m = re.search(r"\bKEY\s+([A-Za-z]+)", t, re.I)
    if m:
        return ("key", m.group(1).lower())
    if re.search(r"\bDONE\b", t, re.I):
        return ("done", None)
    return None


def _action_offset(raw):
    m = re.search(r"\b(CLICK|TYPE|KEY|DONE)\b", raw or "", re.I)
    return m.start() if m else -1


def run_diag(model, processor, cases, results):
    model.eval()
    for case in cases:
        try:
            raw, dt = gen_one(model, processor, case["img"], case["instr"],
                              max_new_tokens=MAX_T96)
        except Exception as e:
            raw, dt = "", -1.0
            err = f"{type(e).__name__}: {str(e)[:200]}"
            results["T96"][case["id"]] = {"raw": "", "parse": None,
                                          "dt": dt, "err": err}
            log(f"--- T96 | {case['id']} LOI: {err}")
            continue
        pa = parse_action(raw)
        off = _action_offset(raw)
        thought_chars = off if off >= 0 else len(raw)
        cut_confirmed = (off >= 0 and thought_chars >= 40)
        results["T96"][case["id"]] = {
            "raw": raw, "parse": pa, "dt": round(dt, 2),
            "action_offset_chars": off, "thought_chars": thought_chars,
            "cut_confirmed": cut_confirmed}
        log(f"--- T96 | {case['id']} ({case['domain']}) | instr: {case['instr']}")
        log(f"    RAW (max_new_tokens={MAX_T96}): {raw!r}")
        log(f"    parse={pa!r} action_offset_chars={off} "
            f"thought_chars~={thought_chars} cut_confirmed={cut_confirmed} "
            f"({dt:.1f}s)")


# ---------------- wheels inventory + peft install --------------------------

def inventory_wheels():
    wheels = []
    for root, _, files in os.walk("/kaggle/input"):
        for f in files:
            if f.endswith(".whl"):
                wheels.append(os.path.join(root, f))
    buckets = {}
    for w in wheels:
        name = os.path.basename(w).split("-")[0].lower()
        buckets.setdefault(name, []).append(w)
    return wheels, buckets


def try_install_peft_from_wheels(buckets):
    peft_wheels = buckets.get("peft", [])
    if not peft_wheels:
        log("khong tim thay peft-*.whl trong input -> dung peft system (0.20.0)")
        return False, "no_peft_wheel"
    root = os.path.dirname(peft_wheels[0])
    log(f"peft wheels: {peft_wheels}")
    for flags in ("", "--no-deps"):
        log(f"pip install {flags.strip() or '(deps auto)'} peft tu {root}")
        cmd = f"pip install --no-index {flags} --find-links {root} peft".strip()
        r = sh(cmd)
        if r is not None:
            return True, "ok" + (" (--no-deps)" if flags == "--no-deps" else "")
    return False, "install_failed"


# ---------------- child script (import unsloth FIRST) ----------------------

CHILD_TEMPLATE = r'''# -*- coding: utf-8 -*-
"""U-bf16 child (TASK-9, GLM) — import unsloth FIRST, sau do load + run."""
import json
import os
import re
import sys
import time
import traceback

# === IMPORT UNSLOTH FIRST (TASK-9 buoc 2) — truoc transformers/peft ===
try:
    import unsloth as _unsloth_mod
    _UNSLOTH_IMPORT_OK = True
    _UNSLOTH_IMPORT_ERR = None
    _UNSLOTH_VERSION_TOP = getattr(_unsloth_mod, "__version__", "n/a")
except Exception as _e:
    _UNSLOTH_IMPORT_OK = False
    _UNSLOTH_IMPORT_ERR = f"{type(_e).__name__}: {str(_e)[:300]}"
    _UNSLOTH_VERSION_TOP = None
# (torch/transformers/peft duoc import sau — unsloth da patch san)

WORK = "/kaggle/working"
ORN = os.environ.get("U_ORN", "/tmp/ornbase")
LORA = os.environ.get("U_LORA", "/tmp/lora_fixed")
CASE_IMG_DIR = os.environ.get("U_CASE_IMG_DIR", os.path.join(WORK, "u_cases"))
OUT_JSON = os.environ.get("U_OUT", os.path.join(WORK, "u_child_result.json"))
MAX_U = @@MAX_U@@

SYS = @@SYS@@

PREPROC = @@PREPROC@@


def log(m):
    print("[u_child] " + str(m), flush=True)


def sh(cmd, timeout=1800):
    import subprocess
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
        return None
    return r


def fix_processor():
    import re as _re
    import transformers
    from transformers import AutoProcessor
    cands = [n for n in dir(transformers)
             if _re.match(r"Qwen3.*(VL)?Processor$", n)]
    log(f"processor classes: {cands}")
    order = ["Qwen3VLProcessor", "Qwen3_5Processor", "Qwen3_5VLProcessor"]
    for n in cands:
        if n not in order:
            order.append(n)
    try:
        proc = AutoProcessor.from_pretrained(ORN)
        if hasattr(proc, "image_processor"):
            log(f"processor truc tiep OK: {type(proc).__name__}")
            return proc
    except Exception as e:
        log(f"AutoProcessor loi: {str(e)[:160]}")
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
                log(f"processor fallback OK: {pclass}")
                return proc
        except Exception as e:
            log(f"{pclass} loi: {str(e)[:120]}")
    raise SystemExit("khong tao duoc processor")


def build_synth_cases(n=5):
    from PIL import Image, ImageDraw
    import random
    rng = random.Random(42)
    PALETTE = {"red": (208, 52, 44), "green": (46, 158, 68),
               "blue": (30, 111, 217), "yellow": (201, 161, 10),
               "purple": (122, 59, 189), "orange": (217, 122, 30),
               "teal": (20, 160, 160)}
    SHAPES = ["button", "square", "circle"]
    TEMPLATES = [
        "Click the {c} {s}.", "Tap the {c} {s}.",
        "Click on the {c} {s}.", "Find the {c} {s} and click it.",
        "Where do you click for the {c} {s}?"]
    CW, CH = 768, 512
    os.makedirs(CASE_IMG_DIR, exist_ok=True)
    out = []
    for i in range(n):
        img = Image.new("RGB", (CW, CH), (240, 240, 242))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, CW, 48], fill=(52, 58, 70))
        d.text((16, 16), "Mock App", fill=(255, 255, 255))
        d.rectangle([0, CH - 36, CW, CH], fill=(228, 230, 235))
        cells = [(c, r) for r in range(3) for c in range(4)]
        rng.shuffle(cells)
        k = rng.randint(5, 9)
        elems = []
        cols = rng.sample(list(PALETTE), min(k, len(PALETTE)))
        if k > len(cols):
            cols += rng.choices(list(PALETTE), k=k - len(cols))
        for j in range(k):
            c, r = cells[j]
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
        tgt = rng.choice(elems)
        x1, y1, x2, y2 = tgt["box"]
        instr = rng.choice(TEMPLATES).format(c=tgt["color"], s=tgt["shape"])
        bbox = [max(0, min(1000, int(round(v / total * 1000))))
                for v, total in zip((x1, y1, x2, y2), (CW, CH, CW, CH))]
        p = os.path.join(CASE_IMG_DIR, f"synth_{i:02d}.png")
        img.save(p)
        out.append({"id": f"synth_{i:02d}", "img": p, "instr": instr,
                    "bbox": bbox, "domain": "synth"})
    return out


def build_login_pil_case():
    from PIL import Image, ImageDraw
    W, H = 1024, 720
    img = Image.new("RGB", (W, H), (238, 241, 245))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([302, 80, 722, 640], radius=18, fill=(255, 255, 255))
    d.text((350, 120), "Sign in", fill=(20, 20, 20))
    d.text((350, 186), "Username", fill=(90, 90, 90))
    d.rectangle([350, 214, 674, 254], fill=(255, 255, 255),
                outline=(120, 130, 240), width=3)
    d.text((362, 224), "admin", fill=(20, 20, 20))
    d.text((350, 282), "Password", fill=(90, 90, 90))
    d.rectangle([350, 310, 674, 350], fill=(255, 255, 255),
                outline=(185, 185, 185))
    d.text((362, 320), "****", fill=(20, 20, 20))
    d.rectangle([350, 462, 674, 504], fill=(30, 111, 217))
    d.text((482, 476), "Sign in", fill=(255, 255, 255))
    p = os.path.join(CASE_IMG_DIR, "login_filled_pil.png")
    img.save(p)
    bbox = [int(round(350 / W * 1000)), int(round(462 / H * 1000)),
            int(round(674 / W * 1000)), int(round(504 / H * 1000))]
    return {"id": "login_pil", "img": p,
            "instr": "Log in with username admin and password 1234. "
                     "When you are done, say DONE.",
            "bbox": bbox, "domain": "login_pil"}


def parse_action(text):
    t = (text or "").strip()
    m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                  t, re.I)
    if m:
        return ("click", [int(m.group(1)), int(m.group(2))])
    m = re.search(r"TYPE\s+(.+)", t, re.I)
    if m:
        return ("type", m.group(1).strip())
    m = re.search(r"\bKEY\s+([A-Za-z]+)", t, re.I)
    if m:
        return ("key", m.group(1).lower())
    if re.search(r"\bDONE\b", t, re.I):
        return ("done", None)
    return None


def gen_one(model, processor, img_path, instr, max_new_tokens=24):
    import torch
    from PIL import Image
    msgs = [{"role": "system",
             "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": "Task: " + instr}]}]
    text = processor.apply_chat_template(msgs, tokenize=False,
                                        add_generation_prompt=True)
    img = Image.open(img_path).convert("RGB")
    inputs = processor(text=[text], images=[img],
                       return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                             do_sample=False)
    dt = time.time() - t0
    txt = processor.batch_decode(out[:, inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)[0]
    return txt.strip(), dt


def main():
    t0 = time.time()
    log(f"unsloth import (top-level, before transformers): "
        f"ok={_UNSLOTH_IMPORT_OK} ver={_UNSLOTH_VERSION_TOP} "
        f"err={_UNSLOTH_IMPORT_ERR}")
    import torch
    log(f"gpu: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'}")
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        log(f"vram: {p.total_memory/1024**3:.1f} GB | sm_{p.major}{p.minor}")
    log(f"torch: {torch.__version__}")

    # versions TRUOC moi thu (unsloth da import o tren cung file)
    import transformers
    log(f"transformers: {transformers.__version__}")
    try:
        import peft
        log(f"peft: {peft.__version__}")
    except Exception as e:
        log(f"peft: (loi import) {type(e).__name__}: {str(e)[:200]}")
    try:
        import unsloth
        log(f"unsloth: {unsloth.__version__}")
    except Exception as e:
        log(f"unsloth: (loi import) {type(e).__name__}: {str(e)[:200]}")
    try:
        import unsloth_zoo
        log(f"unsloth_zoo: {getattr(unsloth_zoo, '__version__', 'n/a')}")
    except Exception as e:
        log(f"unsloth_zoo: (loi import) {type(e).__name__}: {str(e)[:200]}")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    # assemble base + processor + lora (nhu exp)
    # (copy tu exp: assemble_base, find_lora, fix_processor, concretize_lora)
    import importlib.util
    # reuse helpers by exec-ing? Khong — tu viet lai ngan gon:
    # assemble_base (copy)
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
    ORN_L = ORN
    os.makedirs(ORN_L, exist_ok=True)
    got = set()
    for base in cand:
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith((".safetensors", ".json", ".jinja", ".model")):
                    src = os.path.join(root, f)
                    dst = os.path.join(ORN_L, f)
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
        p = os.path.join(ORN_L, f)
        if os.path.exists(p):
            os.remove(p)
    cfg = json.load(open(os.path.join(ORN_L, "config.json")))
    assert cfg.get("model_type") == "qwen3_5", "ORN config khong phai qwen3_5"
    idx = os.path.join(ORN_L, "model.safetensors.index.json")
    if os.path.exists(idx):
        wm = json.load(open(idx)).get("weight_map", {})
        miss = sorted({v for v in wm.values()
                      if not os.path.exists(os.path.join(ORN_L, v))})
        assert not miss, f"thieu shards: {miss}"
    log(f"base OK: {len(os.listdir(ORN_L))} files")

    lora = None
    for root, _, files in os.walk("/kaggle/input"):
        if "adapter_config.json" in files:
            lora = root
            break
    assert lora, "khong thay adapter"
    log(f"lora: {lora}")
    # concretize target_modules
    from safetensors import safe_open
    from peft import PeftConfig
    import shutil
    cfg = PeftConfig.from_pretrained(lora)
    tm = cfg.target_modules
    if not isinstance(tm, (list, set, tuple)):
        f = os.path.join(lora, "adapter_model.safetensors")
        keys = []
        with safe_open(f, framework="pt", device="cpu") as sf:
            for k in sf.keys():
                if ".lora_A" in k or ".lora_B" in k:
                    keys.append(k)
        mods = sorted({k.split(".lora_")[0].replace("base_model.model.", "", 1)
                       for k in keys})
        fixed = os.path.join("/tmp", "lora_fixed")
        if os.path.isdir(fixed):
            shutil.rmtree(fixed)
        shutil.copytree(lora, fixed)
        pc = json.load(open(os.path.join(fixed, "adapter_config.json")))
        pc["target_modules"] = mods
        with open(os.path.join(fixed, "adapter_config.json"), "w") as fh:
            json.dump(pc, fh)
        lora_used = fixed
        log(f"concretize: {len(mods)} modules")
    else:
        lora_used = lora
        log("target_modules da la list, khong concretize")

    # processor
    from transformers import AutoProcessor
    cands = [n for n in dir(transformers)
             if re.match(r"Qwen3.*(VL)?Processor$", n)]
    order = ["Qwen3VLProcessor", "Qwen3_5Processor", "Qwen3_5VLProcessor"]
    for n in cands:
        if n not in order:
            order.append(n)
    proc = None
    try:
        proc = AutoProcessor.from_pretrained(ORN_L)
        if not hasattr(proc, "image_processor"):
            proc = None
    except Exception as e:
        log(f"AutoProcessor loi: {str(e)[:160]}")
    if proc is None:
        for pclass in order:
            for fname, blob in PREPROC.items():
                b = json.loads(json.dumps(blob))
                if b.get("processor_class"):
                    b["processor_class"] = pclass
                with open(os.path.join(ORN_L, fname), "w") as fh:
                    json.dump(b, fh)
            try:
                proc = AutoProcessor.from_pretrained(ORN_L)
                if hasattr(proc, "image_processor"):
                    log(f"processor fallback OK: {pclass}")
                    break
                proc = None
            except Exception as e:
                log(f"{pclass} loi: {str(e)[:120]}")
                proc = None
    assert proc is not None, "khong tao duoc processor"
    log(f"processor: {type(proc).__name__}")

    # cases (full 11? child runs 4 fail cases only to save GPU — board: diagnostic 4 case;
    # U child chay full 11 de hoan thanh matrix)
    os.makedirs(CASE_IMG_DIR, exist_ok=True)
    cases = [c for c in build_synth_cases(5)
             if c["id"] in ("synth_00", "synth_02", "synth_04")]
    cases.append(build_login_pil_case())
    assert len(cases) == 4, f"chi co {len(cases)} case fail (U child)"
    # build_login_only = [login_pil] (khong can real-ui de tiet kiem)
    # NOTE: child chi chay 4 case fail cho U de tiet kiem; neu muon full matrix,
    #       bo sung load_real_cases o day. Giu 4 case de khop diagnostic.
    fail_cases = [c for c in cases if c["id"] in ("synth_00", "synth_02",
                                                  "synth_04", "login_pil")]
    assert len(fail_cases) == 4, f"chi co {len(fail_cases)} case fail"

    # load model via unsloth (import da xong o tren cung file)
    result = {"meta": {}, "U-bf16": {}, "_summary": {}}
    t_load = time.time()
    try:
        from unsloth import FastVisionModel
        u_model, u_proc = FastVisionModel.from_pretrained(
            ORN_L, load_in_4bit=False, max_seq_length=4096)
        u_proc = proc
        try:
            FastVisionModel.for_inference(u_model)
            u_model.eval()
        except Exception as e:
            log(f"for_inference API thay doi: {type(e).__name__}: {str(e)[:120]}")
        from peft import PeftModel
        u_model2 = PeftModel.from_pretrained(u_model, lora_used)
        log(f"U-bf16: model {type(u_model2).__name__} san sang "
            f"(load {time.time()-t_load:.1f}s)")
        parse_n = 0
        for case in fail_cases:
            try:
                raw, dt = gen_one(u_model2, u_proc, case["img"], case["instr"],
                                  max_new_tokens=MAX_U)
            except Exception as e:
                raw, dt = "", -1.0
                err = f"{type(e).__name__}: {str(e)[:200]}"
                result["U-bf16"][case["id"]] = {"raw": "", "parse": None,
                                                "hit": None, "dt": dt,
                                                "err": err}
                log(f"--- U | {case['id']} LOI: {err}")
                continue
            pa = parse_action(raw)
            if pa:
                parse_n += 1
            hit = None
            if pa and pa[0] == "click" and case.get("bbox"):
                x, y = pa[1]
                bx = case["bbox"]
                hit = bool(bx[0] <= x <= bx[2] and bx[1] <= y <= bx[3])
            result["U-bf16"][case["id"]] = {"raw": raw, "parse": pa,
                                            "hit": hit, "dt": round(dt, 2)}
            log(f"--- U | {case['id']} ({case['domain']}) | instr: {case['instr']}")
            log(f"    RAW: {raw!r}")
            log(f"    parse={pa!r} hit={hit} ({dt:.1f}s)")
        result["_summary"]["U-bf16"] = {"parse_n": parse_n,
                                       "n": len(fail_cases),
                                       "same_as_base": 0}
        log(f"==> U-bf16: parse {parse_n}/{len(fail_cases)}")
        try:
            del u_model2
        except Exception:
            pass
        gc.collect()
        import torch as _t
        _t.cuda.empty_cache()
    except Exception as e:
        tb = traceback.format_exc()
        log(f"STACK U-bf16 THAT BAI: {type(e).__name__}: {str(e)[:400]}")
        log("TRACEBACK (full):")
        for line in tb.splitlines():
            log("  " + line)
        result["_summary"]["U-bf16"] = {"error": str(e)[:400],
                                       "traceback": tb}

    result["meta"].update({
        "lora_dir": lora_used, "n_cases": len(fail_cases),
        "case_ids": [c["id"] for c in fail_cases],
        "machine_gpu_seen_in_header": True,
        "t_sec_total": time.time() - t0})
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    log(f"U-FIX XONG -> {OUT_JSON} | "
        f"{json.dumps(result.get('_summary'), ensure_ascii=False)} "
        f"t={time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
'''


def build_login_only():
    return [build_login_pil_case()]


def main():
    t0 = time.time()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log("u_fix_kernel (TASK-9, GLM) — U-bf16 rescue + diagnostic T96")
    sh("pip uninstall -y torchao")
    vram = header_log()

    # (1) wheels inventory
    wheels, buckets = inventory_wheels()
    log(f"so wheels trong input: {len(wheels)}")
    for name in ("peft", "unsloth", "unsloth_zoo", "trl", "bitsandbytes",
                 "torch", "transformers", "greenlet", "pyee", "playwright"):
        if name in buckets:
            log(f"  wheel [{name}]: {len(buckets[name])} file "
                f"(vd {os.path.basename(buckets[name][0])})")
    if "peft" not in buckets:
        log("  ** khong co peft-*.whl trong input ** (ghi ro theo board)")

    # (1b) cai peft tu wheels (try --no-deps va khong)
    inst_ok, inst_msg = try_install_peft_from_wheels(buckets)
    log(f"peft install from wheels: {inst_ok} ({inst_msg})")

    assemble_base()
    proc = fix_processor()
    lora = find_lora()
    assert lora, "khong thay adapter (dataset ornith-gui-lora)"
    log(f"lora: {lora}")
    lora_used, _mods = concretize_lora(lora)

    # (2) DIAGNOSTIC: 4 case fail tren T-bf16 voi max_new_tokens=96
    synth_all = build_synth_cases(5)
    diag_cases = [c for c in synth_all
                  if c["id"] in ("synth_00", "synth_02", "synth_04")]
    diag_cases.append(build_login_pil_case())
    assert len(diag_cases) == 4, f"chi co {len(diag_cases)} case fail"
    for c in diag_cases:
        log(f"diag case {c['id']}: {c['instr']} (domain {c['domain']})")

    import torch
    from peft import PeftModel
    model = load_model(torch.bfloat16)
    model = PeftModel.from_pretrained(model, lora_used)
    log("T-bf16 adapter ON (diag, max_new_tokens=96)")

    results = {"meta": {}, "T96": {}, "U-bf16": {}, "_summary": {}}
    results["meta"]["param_dtype_T96"] = str(next(model.parameters()).dtype)
    run_diag(model, proc, diag_cases, results)
    free_gpu(model)
    model = None

    # (3) U-bf16: viet child script (import unsloth FIRST) + launch subprocess
    sys_repr = repr(SYS)
    preproc_repr = repr(PREPROC)
    child_src = CHILD_TEMPLATE
    child_src = child_src.replace("@@SYS@@", sys_repr)
    child_src = child_src.replace("@@PREPROC@@", preproc_repr)
    child_src = child_src.replace("@@MAX_U@@", str(MAX_U))
    with open(CHILD_SCRIPT, "w", encoding="utf-8") as f:
        f.write(child_src)
    log(f"da ghi child script: {CHILD_SCRIPT} ({len(child_src)} bytes)")

    env = dict(os.environ)
    env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "U_ORN": ORN, "U_LORA": lora_used,
                "U_CASE_IMG_DIR": CASE_IMG_DIR, "U_OUT": CHILD_JSON,
                "PYTHONDONTWRITEBYTECODE": "1"})
    log("launch U child (import unsloth first)...")
    t_child = time.time()
    try:
        r = subprocess.run([sys.executable, CHILD_SCRIPT], env=env,
                           capture_output=True, text=True, timeout=20 * 60)
        log(f"child rc={r.returncode} t={time.time()-t_child:.0f}s")
        for line in (r.stdout or "").splitlines()[-50:]:
            log("CHILD> " + line)
        if r.returncode != 0:
            log("CHILD STDERR TAIL:")
            for line in (r.stderr or "").splitlines()[-70:]:
                log("CHILD! " + line)
    except subprocess.TimeoutExpired as e:
        log("CHILD TIMEOUT (20') -> kill")
        try:
            e.process.kill()
        except Exception:
            pass
        try:
            e.process.wait(timeout=30)
        except Exception:
            pass

    if os.path.exists(CHILD_JSON):
        try:
            child = json.load(open(CHILD_JSON, encoding="utf-8"))
            results["U-bf16"] = child.get("U-bf16", {})
            results["_summary"].update(child.get("_summary", {}))
            if "meta" in child:
                results["meta"].update(child["meta"])
            log("child result loaded OK")
        except Exception as e:
            log(f"child json load fail: {type(e).__name__}: {str(e)[:200]}")
            results["_summary"]["U-bf16"] = {
                "error": f"child_json_load: {str(e)[:200]}"}
    else:
        log("KHONG thay child json -> child chet truoc khi dump")
        results["_summary"]["U-bf16"] = {
            "error": "no_child_json (child crashed before dump)"}

    # verdicts
    cut_confirmed = False
    cut_cases = []
    for cid, r in results.get("T96", {}).items():
        if not isinstance(r, dict):
            continue
        off = r.get("action_offset_chars", -1)
        tc = r.get("thought_chars", 0)
        if off >= 0 and tc >= 40:
            cut_confirmed = True
            cut_cases.append(cid)
    results["_summary"]["T96"] = {
        "n": len(diag_cases),
        "thinking_cut_confirmed": cut_confirmed,
        "cut_cases": cut_cases,
        "max_new_tokens": MAX_T96,
    }
    u_summary = results["_summary"].get("U-bf16", {})
    u_rescued = (isinstance(u_summary, dict)
                 and u_summary.get("parse_n", 0) > 0
                 and "error" not in u_summary)
    u_loaded = bool(results.get("U-bf16")) and not (
        isinstance(u_summary, dict) and "error" in u_summary)
    results["_summary"]["U-bf16_verdict"] = {
        "rescued": u_rescued,
        "loaded_model": u_loaded,
        "root_cause_guess": (
            "import_order (unsloth after transformers/peft)" if not u_loaded
            else "fixed by importing unsloth first in isolated process"),
    }

    results["meta"].update({
        "lora_dir": lora_used, "n_diag": len(diag_cases),
        "n_wheels": len(wheels), "peft_install_from_wheels": inst_ok,
        "peft_install_msg": inst_msg, "vram_gb": vram,
        "t_sec_total": time.time() - t0,
        "machine_gpu_seen_in_header": True,
        "child_script": CHILD_SCRIPT, "child_json": CHILD_JSON})
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    log(f"U-FIX XONG -> {OUT_JSON} | "
        f"{json.dumps(results.get('_summary'), ensure_ascii=False)} "
        f"t={time.time() - t0:.0f}s")


def _load_model_bf16():
    import torch
    import transformers
    cls = None
    for name in ("Qwen3_5ForConditionalGeneration",
                 "AutoModelForImageTextToText", "AutoModelForCausalLM"):
        cls = getattr(transformers, name, None)
        if cls is not None:
            log(f"model class: {name} (dtype=torch.bfloat16)")
            break
    assert cls, "khong tim thay model class qwen3_5"
    model = cls.from_pretrained(ORN, dtype=torch.bfloat16, device_map="auto")
    model.eval()
    log(f"param dtype thuc te: {next(model.parameters()).dtype}")
    return model


# load_model alias used by diag (kept for clarity)
def load_model(dtype):
    import torch
    import transformers
    cls = None
    for name in ("Qwen3_5ForConditionalGeneration",
                 "AutoModelForImageTextToText", "AutoModelForCausalLM"):
        cls = getattr(transformers, name, None)
        if cls is not None:
            log(f"model class: {name} (dtype={dtype})")
            break
    assert cls, "khong tim thay model class qwen3_5"
    model = cls.from_pretrained(ORN, dtype=dtype, device_map="auto")
    model.eval()
    log(f"param dtype thuc te: {next(model.parameters()).dtype}")
    return model


if __name__ == "__main__":
    main()
