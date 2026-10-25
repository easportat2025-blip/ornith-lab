"""TASK-9 - U-bf16 fix + diagnostic 256 token (DeepSeek hoan thien khi GLM chua xong).

Muc tieu:
  1. U-bf16 (Unsloth FastVisionModel + PeftModel) load duoc adapter v18: cai
     peft tu wheels (neu co) + `import unsloth` TRUOC transformers/peft
     (warning trong log TASK-4: "Unsloth should be imported before [transformers, peft]").
  2. DIAGNOSTIC 256 token tren 4 case fail cua exp H2 (synth_00, synth_02,
     synth_04, login_pil): chung minh "thinking bi cat o 24 token" -> 256 token
     se co action (theo lenh user: CHO PHEP REASONING).
  3. Luon co ket qua doc lap tu stack T-bf16 (transformers thuan + PeftModel)
     chay trong TIEN TRINH RIENG (children), nen du U-bf16 fail thi diagnostic
     van co. Child cung chay FULL 11 case cho day du.

Che do chay: `python u_fix.py` (main). Main tu copy chinh no sang /tmp/t_diag.py
roi chay `python /tmp/t_diag.py --tdiag` cho stack T. Output:
  /kaggle/working/t_diag_result.json   (T-bf16, 11 case, 256 token)
  /kaggle/working/u_fix_result.json    (merge: t_bf16_256 + u_bf16 + meta)
"""
import gc
import json
import os
import re
import shutil
import subprocess
import sys
import time

WORK = "/kaggle/working"
ORN = "/tmp/ornbase"
OUT_JSON = os.path.join(WORK, "u_fix_result.json")
T_JSON = os.path.join(WORK, "t_diag_result.json")
CASE_IMG_DIR = os.path.join(WORK, "exp_imgs")
MAX_NEW = 256
FAIL_IDS = ["synth_00", "synth_02", "synth_04", "login_pil"]

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
    print("[u-fix] " + str(m), flush=True)


def sh(cmd, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
        return None
    return r


# ---------------------------------------------------------------- base/proc

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


def load_model_t(dtype):
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


def free_gpu(model):
    del model
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    log("free GPU roi")


# ---------------------------------------------------------------- cases

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


def load_real_cases(n=5):
    import zipfile
    base = None
    for root, _, files in os.walk("/kaggle/input"):
        if "grounding.jsonl" in files and ("real-ui" in root.replace("\\", "/")):
            base = root
            break
    if not base:
        log("KHONG THAY dataset real-ui -> bo row real")
        return []
    rows = []
    with open(os.path.join(base, "grounding.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    ext = os.path.join(CASE_IMG_DIR, "real_imgs")
    os.makedirs(ext, exist_ok=True)
    for fn in os.listdir(base):
        if fn.endswith(".zip"):
            try:
                with zipfile.ZipFile(os.path.join(base, fn)) as z:
                    z.extractall(ext)
            except Exception as e:
                log(f"unzip loi {fn}: {e}")
    LOGIN_RX = re.compile(
        r"sign ?in|log ?in|submit|password|username|enter\b|press", re.I)
    scored = sorted(
        enumerate(rows),
        key=lambda t: (0 if LOGIN_RX.search(str(t[1].get("instruction", "")))
                       else 1, t[0]))
    order = [idx for idx, _ in scored]

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

    seen, out = set(), []
    for idx in order:
        if len(out) >= n:
            break
        r = rows[idx]
        p = _resolve(r.get("image", ""))
        key = (os.path.basename(r.get("image", "")), r.get("instruction"))
        if not p or key in seen:
            continue
        seen.add(key)
        out.append({"id": f"real_{len(out):02d}", "img": p,
                    "instr": r.get("instruction", ""),
                    "bbox": r.get("bbox"), "domain": "real",
                    "login_like": bool(LOGIN_RX.search(
                        str(r.get("instruction", ""))))})
    n_login = sum(1 for c in out if c.get("login_like"))
    log(f"cases real: {len(out)} (login-like {n_login})")
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


def build_cases():
    cases = build_synth_cases(5) + load_real_cases(5)
    cases.append(build_login_pil_case())
    return cases


# ---------------------------------------------------------------- gen/parse

def gen_one(model, processor, img_path, instr, max_new=MAX_NEW):
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
        out = model.generate(**inputs, max_new_tokens=max_new, do_sample=False)
    dt = time.time() - t0
    n_in = inputs["input_ids"].shape[1]
    n_new = int(out.shape[1] - n_in)
    txt = processor.batch_decode(out[:, n_in:],
                                 skip_special_tokens=True)[0]
    return txt.strip(), dt, n_new


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


def run_cases(tag, model, proc, cases, max_new=MAX_NEW, only_ids=None):
    res = {}
    n_parse = 0
    for case in cases:
        cid = case["id"]
        if only_ids and cid not in only_ids:
            continue
        try:
            raw, dt, n_new = gen_one(model, proc, case["img"], case["instr"],
                                     max_new=max_new)
        except Exception as e:
            res[cid] = {"raw": "", "err": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"--- {tag} | {cid} LOI: {type(e).__name__}: {str(e)[:200]}")
            continue
        pa = parse_action(raw)
        if pa:
            n_parse += 1
        hit = None
        if pa and pa[0] == "click" and case.get("bbox"):
            x, y = pa[1]
            bx = case["bbox"]
            hit = bool(bx[0] <= x <= bx[2] and bx[1] <= y <= bx[3])
        res[cid] = {"raw": raw, "parse": pa, "hit": hit, "dt": round(dt, 2),
                    "n_new_tokens": n_new, "max_new": max_new,
                    "truncated_maybe": n_new >= max_new,
                    "instr": case["instr"]}
        log(f"--- {tag} | {cid} ({case['domain']}) | n_new={n_new} dt={dt:.1f}s")
        log(f"    RAW NGUYEN VAN: {raw!r}")
        log(f"    parse={pa!r} hit={hit}")
    log(f"==> {tag}: parse {n_parse}/{len(res)}")
    return res, n_parse


# ---------------------------------------------------------------- child mode

def t_diag_main():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    import transformers
    import peft
    log(f"[TDIAG] gpu: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'}")
    log(f"[TDIAG] torch {torch.__version__} | transformers {transformers.__version__} "
        f"| peft {peft.__version__}")
    t0 = time.time()
    assemble_base()
    proc = fix_processor()
    lora = find_lora()
    assert lora, "khong thay adapter (dataset ornith-gui-lora)"
    lora_used, _ = concretize_lora(lora)
    model = load_model_t(torch.bfloat16)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, lora_used)
    log("[TDIAG] T-bf16 adapter ON (PeftModel + concretize)")
    cases = build_cases()
    log(f"[TDIAG] case ids: {[c['id'] for c in cases]}")
    res, n_parse = run_cases("T-bf16-256", model, proc, cases)
    out = {"tag": "T-bf16-256", "n_parse": n_parse, "n": len(res),
           "results": res, "t_sec": time.time() - t0,
           "versions": {"torch": torch.__version__,
                        "transformers": transformers.__version__,
                        "peft": peft.__version__}}
    with open(T_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"[TDIAG] XONG -> {T_JSON}")


# ---------------------------------------------------------------- main mode

def find_wheels_dir():
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("unsloth-") and f.endswith(".whl") for f in files):
            return root
    return None


def install_unsloth_offline():
    whl = find_wheels_dir()
    if not whl:
        log("KHONG thay unsloth-*.whl trong input -> bo stack Unsloth")
        return False
    names = sorted([f for f in os.listdir(whl) if f.endswith(".whl")])
    log(f"wheels dir {whl} ({len(names)} whl): {names[:25]}")
    has_peft = any(n.startswith("peft-") for n in names)
    log(f"co peft wheel: {has_peft}")
    if has_peft:
        r1 = sh(f"pip install --no-index --find-links {whl} peft")
        if r1 is None:
            log("pip install peft (co deps) fail -> thu --no-deps")
            sh(f"pip install --no-index --no-deps --find-links {whl} peft")
    r = sh(f"pip install --no-index --no-deps --find-links {whl} "
           f"unsloth unsloth_zoo trl bitsandbytes")
    return r is not None


def main():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log("TASK-9: U-bf16 fix (import order + peft wheels) + diagnostic 256 token")
    sh("pip uninstall -y torchao")

    # ---- 1) Child process: T-bf16 thuan + 11 case + 256 token (doc lap) ----
    child = "/tmp/t_diag.py"
    shutil.copy(os.path.abspath(__file__), child)
    log(f"chay child T-bf16: {child} --tdiag")
    try:
        r = subprocess.run([sys.executable, child, "--tdiag"], timeout=3600)
        log(f"child exit={r.returncode}")
    except Exception as e:
        log(f"child exception: {type(e).__name__}: {e}")
    t_res = None
    if os.path.exists(T_JSON):
        t_res = json.load(open(T_JSON, encoding="utf-8"))
        log(f"T-bf16-256: parse {t_res['n_parse']}/{t_res['n']}")

    # ---- 2) U-bf16: import unsloth TRUOC transformers/peft ----
    u_ok = install_unsloth_offline()
    u_out = {}
    meta = {"fail_ids_target": FAIL_IDS, "max_new": MAX_NEW}
    if u_ok:
        try:
            sys.path.insert(0, "")
            import unsloth  # noqa: F401  - MUST be before transformers/peft
            from unsloth import FastVisionModel
            import transformers
            import peft
            import torch
            meta["versions_u"] = {"unsloth": unsloth.__version__,
                                  "transformers": transformers.__version__,
                                  "peft": peft.__version__,
                                  "torch": torch.__version__}
            log(f"unsloth {unsloth.__version__} | peft {peft.__version__} | "
                f"transformers {transformers.__version__}")
            assemble_base()
            proc = fix_processor()
            lora = find_lora()
            assert lora, "khong thay adapter"
            lora_used, _ = concretize_lora(lora)
            u_model, _u_proc = FastVisionModel.from_pretrained(
                ORN, load_in_4bit=False, max_seq_length=4096)
            try:
                FastVisionModel.for_inference(u_model)
                u_model.eval()
            except Exception as e:
                log(f"for_inference API thay doi: {type(e).__name__}")
            from peft import PeftModel
            u_model2 = PeftModel.from_pretrained(u_model, lora_used)
            log(f"U-bf16 OK: {type(u_model2).__name__}")
            cases = build_cases()
            res, n_parse = run_cases("U-bf16-256", u_model2, proc, cases,
                                     only_ids=set(FAIL_IDS))
            meta["versions_u"]["param_dtype"] = str(
                next(u_model2.parameters()).dtype)
            u_out = {"tag": "U-bf16-256", "n_parse": n_parse,
                     "n": len(res), "results": res, "load_ok": True}
            free_gpu(u_model2)
        except Exception as e:
            log(f"STACK U-bf16 THAT BAI: {type(e).__name__}: {str(e)[:500]}")
            u_out = {"tag": "U-bf16-256", "load_ok": False,
                     "error": f"{type(e).__name__}: {str(e)[:500]}"}
    else:
        u_out = {"tag": "U-bf16-256", "load_ok": False,
                 "error": "thieu wheels unsloth offline"}

    out = {"meta": meta, "t_bf16_256": t_res, "u_bf16_256": u_out}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"U-FIX XONG -> {OUT_JSON}")


if __name__ == "__main__":
    if "--tdiag" in sys.argv:
        t_diag_main()
    else:
        main()
