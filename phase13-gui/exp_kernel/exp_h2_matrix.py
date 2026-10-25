"""EXP tách biến H1/H2 — serving-stack × dtype trên adapter v18 (TASK-4, GLM).

Mục đích (theo TASK-4 + v19_plan_draft.md §4.3):
  Ha H2 ("dtype/máy RTX làm prose") khỏi H1 ("pha loãng anchor domain"):
  chạy CÙNG adapter v18 trên CÙNG 11 ảnh qua CÁC stack khác nhau, in nguyên văn output.

Rows của matrix (tất cả cùng 11 ảnh, cùng SYS + prompt). THỨ TỰ = nhóm T trước,
Unsloth SAU CÙNG (import unsloth patch toàn cục — đổi theo @DeepSeek 12:55, để
các hàng T chạy sạch trước khi unsloth đụng vào):
  - BASE   : transformers-thuần, bf16, KHÔNG adapter (tham chiếu cho H1).
  - T-bf16 : transformers-thuần + PeftModel (conda concretize + probe, chuẩn v14).
  - T-fp16 : transformers-thuần + PeftModel, torch.float16 (MỚI @DeepSeek 12:55:
             bench v14 = bf16 nếu GPU hỗ trợ, ngược lại fp16 -> T4=fp16 / RTX=bf16;
             nghi H2 mạnh nhất: v8-bf16 prose vs v14-fp16 parse).
  - T-fp32 : transformers-thuần + PeftModel với dtype float32 (chỉ chạy khi VRAM >= 40GB).
  - U-bf16 : Unsloth FastVisionModel + PeftModel.from_pretrained (kiểu v1 bench —
             nghi forward-patch Unsloth bypass LoRA). U-fp16: BỎ (load U lần 2 đắt
             + API dtype của unsloth không chắc chắn; thêm sau nếu cần).

Offline-friendly: KHÔNG pip install (duy nhất `pip uninstall -y torchao` — offline, như v14;
HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE; unsloth cài từ wheels dataset nếu có — --no-index).
Kết quả -> /kaggle/working/exp_h2_result.json
"""
import gc
import json
import os
import re
import subprocess
import sys
import time

WORK = "/kaggle/working"
ORN = "/tmp/ornbase"
OUT_JSON = os.path.join(WORK, "exp_h2_result.json")
CASE_IMG_DIR = os.path.join(WORK, "exp_imgs")

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
    print("[exp] " + str(m), flush=True)


def sh(cmd, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
        return None
    return r


def header_log():
    """LUẬT từ TASK-4: log đầu GPU + dtype + version stack."""
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
    del model
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    log("free GPU roi")


# ---------------- bo tap hinh (10 anh KINH DINH, deterministic) -------------

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
    """5 anh THAT co dinh tu dataset hhjiji/ornith-gui-real-ui (grounding.jsonl).
    Uu tien truoc cac row kieu login/submit — dung vung leak end-action (tip @DeepSeek 12:25)."""
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
    """1 anh PIL login_form DA DIEN (admin + •••• + nut 'Sign in') — mui leak
    end-action theo tip @DeepSeek; instr trung wording cua task login_done bench."""
    from PIL import Image, ImageDraw
    W, H = 1024, 720
    img = Image.new("RGB", (W, H), (238, 241, 245))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([302, 80, 722, 640], radius=18, fill=(255, 255, 255))
    d.text((350, 120), "Sign in", fill=(20, 20, 20))
    d.text((350, 186), "Username", fill=(90, 90, 90))
    d.rectangle([350, 214, 674, 254], fill=(255, 255, 255),
                outline=(120, 130, 240), width=3)  # focus user field
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

def gen_one(model, processor, img_path, instr):
    import torch
    from PIL import Image
    msgs = [{"role": "system",
             "content": [{"type": "text", "text": SYS}]},
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": "Task: " + instr}]}]
    text = processor.apply_chat_template(msgs, tokenize=False,
                                         add_generation_prompt=True)
    img = Image.open(img_path).convert("RGB")  # nhu bench v14: PIL truoc
    inputs = processor(text=[text], images=[img],
                       return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=24, do_sample=False)
    dt = time.time() - t0
    txt = processor.batch_decode(out[:, inputs["input_ids"].shape[1]:],
                                 skip_special_tokens=True)[0]
    return txt.strip(), dt


def run_stack(tag, model, processor, cases, results):
    """Chay 11 anh, in NGUYEN VAN output tung anh (boss TASK-4)."""
    model.eval()
    try:
        p0 = next(model.parameters())
        log(f"### HANG {tag} | param dtype thuc te: {p0.dtype} | "
            f"device: {p0.device}")
    except Exception as e:
        log(f"### HANG {tag} | khong doc duoc dtype: {type(e).__name__}")
    parse_n = 0
    same_as_base = 0
    for i, case in enumerate(cases):
        try:
            raw, dt = gen_one(model, processor, case["img"], case["instr"])
        except Exception as e:
            raw, dt = "", -1.0
            results[tag][case["id"]] = {
                "raw": "", "parse": None, "hit": None, "dt": dt,
                "err": f"{type(e).__name__}: {str(e)[:200]}"}
            log(f"--- {tag} | {case['id']} ({case['domain']}) LOI: "
                f"{type(e).__name__}: {str(e)[:200]}")
            continue
        pa = parse_action(raw)
        if pa:
            parse_n += 1
        baseline = results.get("BASE", {}).get(case["id"], {})
        if raw == baseline.get("raw"):
            same_as_base += 1
        hit = None
        if pa and pa[0] == "click" and case.get("bbox"):
            x, y = pa[1]
            bx = case["bbox"]
            hit = bool(bx[0] <= x <= bx[2] and bx[1] <= y <= bx[3])
        results[tag][case["id"]] = {"raw": raw, "parse": pa, "hit": hit,
                                    "dt": round(dt, 2)}
        log(f"--- {tag} | {case['id']} ({case['domain']}) | "
            f"instr: {case['instr']}")
        log(f"    RAW NGUYEN VAN: {raw!r}")
        log(f"    parse={pa!r} hit={hit} ({dt:.1f}s)")
    log(f"==> {tag}: parse {parse_n}/{len(cases)} | "
        f"giong BASE {same_as_base}/{len(cases)}")
    results.setdefault("_summary", {})[tag] = {
        "parse_n": parse_n, "n": len(cases), "same_as_base": same_as_base}


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


def install_unsloth_offline():
    """Tuyet doi khong keo mang: chi cai tu wheels da attach (--no-index)."""
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("unsloth-") and f.endswith(".whl")
               for f in files):
            wheels = root
            break
    if not wheels:
        log("KHONG thay unsloth-*.whl trong input -> bo stack Unsloth")
        return False
    log(f"cai unsloth offline tu {wheels} (--no-index)")
    r = sh(f"pip install --no-index --no-deps --find-links {wheels} "
           f"unsloth unsloth_zoo trl bitsandbytes")
    return r is not None


def main():
    t0 = time.time()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log("EXP H2 matrix (TASK-4, GLM) — v14 loader + Unsloth cuu truong")
    sh("pip uninstall -y torchao")  # offline chinh; nhu v14 (gotcha peft/torchao)
    import torch
    vram = header_log()
    assemble_base()
    proc = fix_processor()
    lora = find_lora()
    assert lora, "khong thay adapter (dataset ornith-gui-lora)"
    log(f"lora: {lora}")
    lora_used, _mods = concretize_lora(lora)

    cases = build_synth_cases(5) + load_real_cases(5)
    cases.append(build_login_pil_case())  # anh login DA DIEN — mui leak
    # end-action (@DeepSeek 12:25); tong 11 anh kinh dinh, deterministic
    assert len(cases) >= 6, "qua it case (synth + real)"
    for c in cases:
        log(f"case {c['id']}: {c['instr']} (domain {c['domain']})")

    results = {"meta": {}, "BASE": {}, "T-bf16": {}, "T-fp16": {},
               "T-fp32": {}, "U-bf16": {}, "_summary": {}}

    # ---- NHOM T TRUOC (transformers thuan): doi thu tu theo @DeepSeek 12:55 —
    #      import unsloth patch toan cuc, de U SAU CUNG cho cac hang T sach ----

    # ---- Stack T-bf16: BASE (khong adapter) truoc, roi adapter ----
    model = load_model(torch.bfloat16)
    results["meta"]["param_dtype_T-bf16"] = str(next(model.parameters()).dtype)
    run_stack("BASE", model, proc, cases, results)
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, lora_used)
    log("T-bf16 adapter ON (PeftModel + concretize)")
    run_stack("T-bf16", model, proc, cases, results)
    free_gpu(model)

    # ---- Stack T-fp16 (MOI @DeepSeek 12:55): bench v14 chon dtype =
    #      bfloat16 neu GPU ho tro, nguoc lai float16 -> T4=fp16 / RTX=bf16.
    #      Nghi H2 manh nhat: v8-bf16 prose vs v14-fp16 parse. ----
    try:
        model16 = load_model(torch.float16)
        results["meta"]["param_dtype_T-fp16"] = str(
            next(model16.parameters()).dtype)
        model16 = PeftModel.from_pretrained(model16, lora_used)
        log("T-fp16 adapter ON (PeftModel + concretize)")
        run_stack("T-fp16", model16, proc, cases, results)
        free_gpu(model16)
    except Exception as e:
        log(f"STACK T-fp16 THAT BAI: {type(e).__name__}: {str(e)[:400]}")
        results["_summary"]["T-fp16"] = {"error": str(e)[:400]}
        free_gpu(locals().get("model16", None))

    # ---- Stack T-fp32 (chi VRAM >= 40GB — tren T4 se bo qua) ----
    if vram >= 40:
        try:
            model32 = load_model(torch.float32)
            results["meta"]["param_dtype_T-fp32"] = str(
                next(model32.parameters()).dtype)
            model32 = PeftModel.from_pretrained(model32, lora_used)
            run_stack("T-fp32", model32, proc, cases, results)
            free_gpu(model32)
        except Exception as e:
            log(f"STACK T-fp32 THAT BAI: {type(e).__name__}: {str(e)[:400]}")
            results["_summary"]["T-fp32"] = {"error": str(e)[:400]}
            free_gpu(locals().get("model32", None))
    else:
        log(f"bo STACK T-fp32 (VRAM {vram:.1f}GB < 40GB — tren T4 fps32 khong du)")

    # ---- Stack U-bf16 (Unsloth) SAU CUNG — import unsloth patch toan cuc,
    #      3 hang T da chay sach; U-fp16: BO (load U lan 2 dat + API dtype
    #      unsloth khong chac chan — them sau neu can). ----
    u_ok = install_unsloth_offline()
    if u_ok:
        try:
            sys.path.insert(0, "")
            from unsloth import FastVisionModel
            u_model, u_proc = FastVisionModel.from_pretrained(
                ORN, load_in_4bit=False, max_seq_length=4096)
            u_proc = proc  # truyen de processor = cai da hoc fix_processor
            try:
                FastVisionModel.for_inference(u_model)
                u_model.eval()
            except Exception as e:
                log(f"for_inference API thay doi: {type(e).__name__}")
            from peft import PeftModel
            u_model2 = PeftModel.from_pretrained(u_model, lora_used)
            log(f"U-bf16: model {type(u_model2).__name__} san sang")
            run_stack("U-bf16", u_model2, u_proc, cases, results)
            free_gpu(u_model2)
        except Exception as e:
            log(f"STACK U-bf16 THAT BAI: {type(e).__name__}: "
                f"{str(e)[:400]}")
            results["_summary"]["U-bf16"] = {"error": str(e)[:400]}
            free_gpu(locals().get("u_model2", None))
    else:
        log("=> bo STACK U-bf16 (thieu wheels offline)")

    results["meta"].update({
        "lora_dir": lora_used, "n_cases": len(cases),
        "case_ids": [c["id"] for c in cases],
        "machine_gpu_seen_in_header": True,
        "t_sec_total": time.time() - t0})
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    log(f"EXP XONG -> {OUT_JSON} | {json.dumps(results.get('_summary'), ensure_ascii=False)} "
        f"t={time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
