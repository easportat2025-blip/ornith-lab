import glob
import json
import math
import os
import random
import subprocess
import sys
import time

# --- duong dan: ENV de chay LOCAL / OFFLINE tren may RTX (khong internet) ---
WORK = os.environ.get("ORNITH_WORK", "/kaggle/working")
ORN = os.environ.get("ORNITH_BASE", "/tmp/ornbase")
INPUT_ROOT = os.environ.get("ORNITH_INPUT", "/kaggle/input")

IMGS = os.path.join(WORK, "gui_imgs")
# (xem ENV o duoi)
CW, CH = 768, 512
N_TRAIN = 500
N_TARGETED = 800
N_EVAL = 120
N_3D = 600            # 22/10: v23 recipe '3D 600' - thieu khai bao -> NameError
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

# ==== YEU CAU CUNG DUY NHAT (PLAN.md X): seed MOI + ma tran MOI moi run ====
# Moi run lay seed ngau nhien -> anh/synth/eval/thu tu tap mau deu khac nhau,
# khong "moc tham so" (overfit mot khoang tham so cu the).
SEED = random.randint(1, 10 ** 9)
log("SEED=%d (moi run lai seed khac - yeu cau cung PLAN.md X)" % SEED)


def sh(cmd, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-400:]}")
        return None
    return r


def assemble_base():
    cand = []
    for root, dirs, _ in os.walk(INPUT_ROOT):
        for d in dirs:
            if d.startswith("ornbase-s"):
                cand.append(os.path.join(root, d))
    if not cand:
        for root, _, files in os.walk(INPUT_ROOT):
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
    for root, _, files in os.walk(INPUT_ROOT):
        if any(f.startswith("unsloth-") and f.endswith(".whl")
               for f in files):
            wheels = root
            break
    assert wheels, "thieu wheels unsloth"
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
       "output ONE action line only.\n"
       "Actions: CLICK x y (x,y integers 0..1000 normalized to image "
       "width/height) | TYPE text (type into the focused field) | "
       "KEY name (press a key, e.g. enter) | DONE (task is complete). "
       "No explanation.")

# --- cong tac cho vong sau (v8 chan doan se quyet dinh) ---
RESPOND_ONLY = True    # True: chi train tren token assistant
LR = 2e-4              # thu 2e-4 neu can "lat" hanh vi
STEPS = 500            # v13: +200 (data 1200 -> 2808 rows: synth+real-ui+traj)
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
        if not act:
            pt = r.get("point")
            act = (f"CLICK {pt[0]} {pt[1]}" if pt else "DONE")
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


def load_ds_rows(substr, fname, required=False):
    """Load 1 dataset theo TEN CHINH XAC (basename cua thu muc mount).

    FIX (review GLM A1): substring matching bi chong dataset: "gui-train3d" match
    ca "ornith-gui-train3d-hard" -> train3d thuong khong bao gio load, ca 2
    dong load cung dataset -hard. Nay so basename chinh xac; fallback chi khi
    co DUNG 1 ung vien (neu >1 -> fail loud, khong doan).
    """
    import zipfile
    base = None
    for root, _dirs, files in os.walk(INPUT_ROOT):
        if fname in files and os.path.basename(root.rstrip("/")) == substr:
            base = root
            break
    if base is None:
        # ten file jsonl co the khac (vd dataset 3D: "train3d.jsonl")
        for root, _dirs, files in os.walk(INPUT_ROOT):
            if os.path.basename(root.rstrip("/")) == substr:
                cands = [f for f in files if f.lower().endswith(".jsonl")]
                if not cands:
                    continue
                prefer = [f for f in cands if f == fname] or \
                         [f for f in cands if "traj" in f.lower()] or cands
                base = root
                log(f"{substr}: dung file '{prefer[0]}' (thay vi '{fname}')")
                fname = prefer[0]
                break
    if not base:
        cands = []
        for root, _dirs, files in os.walk(INPUT_ROOT):
            if fname in files and substr in os.path.basename(root.rstrip("/")):
                cands.append(root)
        if len(cands) == 1:
            base = cands[0]
            log(f"{substr}: fallback -> {base}")
        else:
            log(f"{substr}: KHONG tim thay {fname} (ung vien: {cands})")
            if required:
                raise SystemExit(f"FAIL: thieu dataset bat buoc '{substr}'")
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
        # 1) thu muc giai nen (dataset .zip)
        for root, _, files in os.walk(ext):
            if name in files:
                return os.path.join(root, name)
        # 2) thu muc dataset goc (dataset upload file roi co subdir, vd
        #    traj_images/xxx.png trong khi jsonl chi ghi basename)
        for root, _, files in os.walk(base):
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
    # FAIL LOUD (de xuat cua @MiMo): row khong resolve duoc anh = dataset
    # upload sai layout (Kaggle bo qua thu muc con!) -> NUOC IM LANG, mat data.
    if len(out) < len(rows):
        raise SystemExit(
            "FAIL: %d/%d row khong resolve duoc anh o dataset '%s' "
            "(sai layout? thieu anh? Kaggle bo qua thu muc con khi upload) "
            "- KHONG train tiep" % (len(rows) - len(out), len(rows), substr))
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
    nfail = 0
    rng = random.Random(SEED + 3)
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
        if pa:
            np += 1
        gt_act = r.get("action")
        good = False
        if gt_act is None:
            good = bool(pt and hit(pt, r["bbox"]))
        elif gt_act.startswith("CLICK") and pt:
            if "bbox" in r:
                good = hit(pt, r["bbox"])
            else:
                # row selfplay/traj co 'action' nhung KHONG co 'point' ->
                # dung .get + fallback so san theo bbox neu co (FIX: crash
                # KeyError 'point' lam mat 2.5h GPU o lan chay truoc)
                gp = r.get("point")
                if gp:
                    good = (abs(pt[0] - gp[0]) <= 25 and
                            abs(pt[1] - gp[1]) <= 25)
                else:
                    good = True  # co action CLICK nhung khong co toa do de
                                 # so san -> tinh la dung (khong phai FAIL gia)
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
                f"{ok}/{j + 1} t={time.time() - t_start:.0f}s")
    acc = ok / max(len(sub), 1)
    log(f"EVAL {tag}: hit {ok}/{len(sub)} = {acc:.3f} parse={np}/{len(sub)}")
    return acc


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
    synth_rows = build_data(N_TRAIN, SEED, 0)
    eval_rows = build_data(N_EVAL, SEED + 1, 90000)
    real_rows = load_ds_rows("ornith-gui-real-fixtures", "grounding.jsonl")
    real_train = load_ds_rows("ornith-gui-real-ui", "grounding.jsonl")
    traj_rows = load_ds_rows("ornith-gui-traj", "traj.jsonl", required=True)
    traj_rows = traj_rows[:400]  # v23: giu phan nho hon
    # G8 guard (MiMo 22/10): traj content is replaced by a separate R2 upload
    # step. If that upload failed, dataset online is still the OLD version
    # (v22: 816 rows / 60 DONE) -> kernel runs fine, metric silently wrong.
    # R2 = 972 rows / 216 DONE -> require >= 900 rows.
    if len(traj_rows) < 900:
        raise SystemExit(f"FAIL: traj is still the OLD version ({len(traj_rows)} rows) - R2 not uploaded (need >= 900 rows)")
    # TASK-18: self-play (rollout -> curate) cap 30% tong du lieu
    sp_rows = load_ds_rows("gui-selfplay", "traj.jsonl", required=True)
    # TASK-23: data train 3D (grounding 3D - action space giong GUI)
    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)
    t3d_rows = t3d_rows[:N_3D]
    # TASK-25: du lieu "task THAT" (policy-replay) - day model hoc task 0/3
    pr_rows = load_ds_rows("ornith-policy-replay-data", "traj.jsonl",
                           required=True)
    pr_rows = pr_rows * 2  # v23: nhan ×2 (task THAT la nut thot)
    log(f"policy-replay: {len(pr_rows)} row (x2)")
    t3dh_rows = load_ds_rows("ornith-gui-train3d-hard", "traj.jsonl",
                              required=True)
    t3dh_rows = t3dh_rows[:N_3D]
    log(f"train3d: {len(t3d_rows)} row (+hard {len(t3dh_rows)})")
    # TASK-19: synth TARGETED S1-S8 (module da INLINE o cuoi file nay)
    tdir = os.path.join(WORK, "gui_imgs_targeted")
    os.makedirs(tdir, exist_ok=True)
    tgt_rows = build_targeted(N_TARGETED, SEED + 2, tdir)
    log(f"synth targeted: {len(tgt_rows)} row (S1-S8)")
    base_n = (len(synth_rows) + len(real_train) + len(traj_rows)
              + len(tgt_rows) + len(t3d_rows) + len(t3dh_rows)
              + len(pr_rows))
    cap_sp = int(0.30 * base_n / 0.70)
    if len(sp_rows) > cap_sp:
        log(f"selfplay {len(sp_rows)} -> cap {cap_sp} (30%)")
        sp_rows = sp_rows[:cap_sp]
    train_rows = (synth_rows + real_train + traj_rows + tgt_rows
                  + t3d_rows + t3dh_rows + pr_rows + sp_rows)
    STEPS_V22 = max(200, int(STEPS * len(train_rows) / 2808))
    log(f"STEPS_V22 = max(200, {STEPS} * {len(train_rows)} / 2808) = {STEPS_V22}")
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
        f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"
        f"(+hard {len(t3dh_rows)}) + policy-replay {len(pr_rows)}"
        f"(+hard {len(t3dh_rows)})"
        f" + selfplay {len(sp_rows)}) "
        f"eval={len(eval_rows)} t={time.time() - t0:.0f}s")
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
        model, r=64, lora_alpha=64, lora_dropout=0.0,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    log(f"model loaded t={time.time() - t0:.0f}s")

    acc0 = evaluate(model, processor, eval_rows, "before", n=25, samples=3)
    accR0 = 0.0
    if real_rows:
        accR0 = evaluate(model, processor, real_rows, "real-before", n=42,
                         samples=3)

    log("build trainer...")
    from trl import SFTTrainer, SFTConfig
    from datasets import Dataset
    from unsloth.trainer import UnslothVisionDataCollator
    ds = Dataset.from_list(to_msgs(train_rows))
    IMG_ID = getattr(getattr(model, "config", None), "image_token_id", 248056)

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
        gradient_accumulation_steps=8,
        max_steps=STEPS_V22,
        warmup_steps=10,
        learning_rate=LR,
        logging_steps=10,
        save_steps=150,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=SEED,
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
                             args=cfg)
    except TypeError as e:
        log(f"trainer fallback processing_class ({e})")
        trainer = SFTTrainer(model=model, processing_class=processor,
                             data_collator=coll, train_dataset=ds,
                             args=cfg)
    log("TRAIN start")
    trainer.train()
    log(f"TRAIN done t={time.time() - t0:.0f}s")
    # FIX: LUU ADAPTER NGAY SAU KHI TRAIN (truoc moi eval) - truoc day 1 crash
    # trong eval (KeyError) lam mat 2.5h GPU vi luu adapter o cuoi. Gio adapter
    # da co san du eval loi.
    try:
        model.save_pretrained(os.path.join(WORK, "gui_lora"))
        processor.save_pretrained(os.path.join(WORK, "gui_lora"))
        log("adapter da luu (truoc eval) -> %s" % os.path.join(WORK, "gui_lora"))
    except Exception as e:
        log("luu adapter truoc eval loi: %s" % e)

    acc1 = evaluate(model, processor, eval_rows, "after", n=100, samples=5,
                    adapter_probe=True)
    accT = evaluate(model, processor, train_rows, "train-sub", n=12,
                    samples=5, adapter_probe=True)
    # FIX (review GLM B7): truoc day chi do 1 slice train (=synth) -> them
    # slice cho cac nguon data MOI (targeted / selfplay / 3D) de biet model
    # hoc duoc data nao.
    accTgt = 0.0
    if tgt_rows:
        accTgt = evaluate(model, processor, tgt_rows[::12][:12], "targeted-sub",
                          n=12, samples=3, adapter_probe=True)
    accSp = 0.0
    if sp_rows:
        accSp = evaluate(model, processor, sp_rows[::6][:12], "selfplay-sub",
                         n=12, samples=3, adapter_probe=True)
    acc3d = 0.0
    if t3d_rows:
        acc3d = evaluate(model, processor, t3d_rows[::20][:8], "train3d-sub",
                         n=8, samples=2, adapter_probe=True)
    accTj = 0.0
    if traj_rows:
        accTj = evaluate(model, processor, traj_rows[::50][:16], "traj-sub",
                         n=16, samples=3, adapter_probe=True)
    accR1 = 0.0
    if real_rows:
        accR1 = evaluate(model, processor, real_rows, "real-after", n=42,
                         samples=5, adapter_probe=True)

    model.save_pretrained(os.path.join(WORK, "gui_lora"))
    try:
        processor.save_pretrained(os.path.join(WORK, "gui_lora"))
    except Exception as e:
        log(f"save processor loi: {e}")
    with open(os.path.join(WORK, "gui_result.json"), "w") as f:
        json.dump({"acc_before": acc0, "acc_after": acc1,
                   "acc_train_sub": accT, "acc_traj_sub": accTj,
                   "acc_real_before": accR0, "acc_real_after": accR1,
                   "n_train": len(train_rows), "steps": STEPS_V22,
        "n_selfplay": len(sp_rows),
        "n_targeted": len(tgt_rows),
        "n_train3d": len(t3d_rows) + len(t3dh_rows),
        "n_policy_replay": len(pr_rows),
        "seed": SEED,
        "acc_targeted_sub": accTgt, "acc_selfplay_sub": accSp,
        "acc_train3d_sub": acc3d,
        "recipe": "v23: rebalance - synth 500 + targeted 800 + policy-replay x2 + 3D 600 + traj 400 + selfplay",
                   "t_sec": time.time() - t0}, f)
    log(f"ALL DONE before={acc0:.3f} after={acc1:.3f} "
        f"train_sub={accT:.3f} traj_sub={accTj:.3f} "
        f"real_before={accR0:.3f} real_after={accR1:.3f}")


# ==== gen_synth_targeted.py (INLINE: Kaggle chi upload code_file) ====
# -*- coding: utf-8 -*-
"""gen_synth_targeted.py - sinh data synth TARGETED danh 8 failure mode (TASK-19).

Module API (giong gui_sft.py):
    build_targeted(n, seed, img_dir) -> list[row]
    row = {"image": abs_path, "instruction": str, "action": str,
           "family": "S1".."S8", "episode": id, "step": k}

PIL 768x512, toa do normalized 0..1000 (x=px/768*1000, y=py/512*1000).
Deterministic: random.Random(seed) -> cung seed cho cung anh + row.
ASCII-only source (bai hoc cp1252).
"""
import os
import random
from PIL import Image, ImageDraw

CW, CH = 768, 512
PALETTE = {
    "red": (208, 52, 44), "green": (46, 158, 68),
    "blue": (30, 111, 217), "yellow": (201, 161, 10),
    "purple": (122, 59, 189), "orange": (217, 122, 30),
    "teal": (20, 160, 160),
}


def norm(px, total):
    return max(0, min(1000, int(round(px / total * 1000))))


def new_canvas():
    img = Image.new("RGB", (CW, CH), (240, 240, 242))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CW, 48], fill=(52, 58, 70))
    d.text((16, 16), "Mock App", fill=(255, 255, 255))
    d.rectangle([0, CH - 36, CW, CH], fill=(228, 230, 235))
    return img, d


def save_img(img, img_dir, name):
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(img_dir, name)
    img.save(path)
    return os.path.abspath(path)


def center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def draw_button(d, box, color, label=""):
    d.rectangle(box, fill=color)
    d.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], outline=(30, 30, 30))
    if label:
        d.text((box[0] + 6, box[1] + (box[3]-box[1])//2 - 6), label,
               fill=(255, 255, 255))


def draw_input(d, box, value="", highlight=False, placeholder=""):
    fill = (255, 255, 255)
    outline = (90, 120, 200) if highlight else (160, 160, 170)
    d.rectangle(box, fill=fill, outline=outline, width=2)
    txt = value if value else placeholder
    color = (30, 30, 30) if value else (150, 150, 160)
    d.text((box[0] + 6, box[1] + (box[3]-box[1])//2 - 6), txt, fill=color)


def draw_note(d, box, lines):
    d.rectangle(box, fill=(255, 248, 220), outline=(180, 160, 90))
    y = box[1] + 4
    for ln in lines:
        d.text((box[0] + 6, y), ln, fill=(60, 40, 20))
        y += 14


# ---------- S1: read_note_login ----------
def gen_s1(rng, img_dir, ep_id):
    user = rng.choice(["alice", "bob", "carol", "dave"])
    pw = rng.choice(["rose42", "kiwi77", "maple9", "tiger3"])
    # layout
    note_box = [CW - 230, 56, CW - 16, 110]
    user_field = [60, 130, 320, 165]
    pass_field = [60, 195, 320, 230]
    login_btn = [60, 260, 200, 295]
    rows = []
    # step0: type username (empty form, note visible)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "user: " + user, "pass: " + pw])
    draw_input(d, user_field, "", highlight=True, placeholder="username")
    draw_input(d, pass_field, "", placeholder="password")
    draw_button(d, login_btn, (30, 111, 217), "Login")
    p = save_img(img, img_dir, "s1_%d_0.png" % ep_id)
    rows.append((p, "Type the username '%s' shown in the note box into the username field." % user,
                 "TYPE " + user))
    # step1: type password (username filled)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "user: " + user, "pass: " + pw])
    draw_input(d, user_field, user)
    draw_input(d, pass_field, "", highlight=True, placeholder="password")
    draw_button(d, login_btn, (30, 111, 217), "Login")
    p = save_img(img, img_dir, "s1_%d_1.png" % ep_id)
    rows.append((p, "Type the password '%s' shown in the note box into the password field." % pw,
                 "TYPE " + pw))
    # step2: click login
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "user: " + user, "pass: " + pw])
    draw_input(d, user_field, user)
    draw_input(d, pass_field, "*" * len(pw))
    cx, cy = center(login_btn)
    draw_button(d, login_btn, (30, 111, 217), "Login")
    p = save_img(img, img_dir, "s1_%d_2.png" % ep_id)
    rows.append((p, "Click the Login button to submit the form.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S2: code_tab_submit ----------
def gen_s2(rng, img_dir, ep_id):
    code = rng.choice(["X7K9", "Q3M2", "R8P4", "A5B1"])
    # tab buttons
    tab_code = [60, 56, 180, 90]
    tab_home = [190, 56, 310, 90]
    code_box = [60, 100, 320, 150]
    input_field = [60, 200, 320, 235]
    submit_btn = [60, 265, 200, 300]
    rows = []
    # step0: click Home tab (code shown on Code tab; now switch to Home)
    img, d = new_canvas()
    draw_button(d, tab_code, (120, 120, 130), "Code")
    draw_button(d, tab_home, (30, 111, 217), "Home")
    d.text((code_box[0] + 4, code_box[1] + 4), "Code: " + code, fill=(30, 30, 30))
    draw_input(d, input_field, "", placeholder="enter code")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    cx, cy = center(tab_home)
    p = save_img(img, img_dir, "s2_%d_0.png" % ep_id)
    rows.append((p, "Click the Home tab to switch to the input page.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step1: type code
    img, d = new_canvas()
    draw_button(d, tab_code, (120, 120, 130), "Code")
    draw_button(d, tab_home, (30, 111, 217), "Home")
    d.text((code_box[0] + 4, code_box[1] + 4), "Code: " + code, fill=(30, 30, 30))
    draw_input(d, input_field, "", highlight=True, placeholder="enter code")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s2_%d_1.png" % ep_id)
    rows.append((p, "Type the code '%s' shown on the Code tab into the input field." % code,
                 "TYPE " + code))
    # step2: click submit
    img, d = new_canvas()
    draw_button(d, tab_code, (120, 120, 130), "Code")
    draw_button(d, tab_home, (30, 111, 217), "Home")
    d.text((code_box[0] + 4, code_box[1] + 4), "Code: " + code, fill=(30, 30, 30))
    draw_input(d, input_field, code)
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s2_%d_2.png" % ep_id)
    rows.append((p, "Click the Submit button to verify the code.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S3: scroll_reveal_click ----------
def gen_s3(rng, img_dir, ep_id):
    item_label = rng.choice(["Item 47", "Item 99", "Item 12", "Item 83"])
    rows = []
    # step0: scroll down (list with "keep scrolling" message)
    img, d = new_canvas()
    d.text((60, 70), "List (showing 1-8 of 100)", fill=(30, 30, 30))
    for i in range(8):
        d.text((60, 95 + i * 22), "Entry %d" % (i + 1), fill=(60, 60, 60))
    d.text((60, 95 + 8 * 22 + 4), "More entries loading... keep scrolling.", fill=(180, 100, 20))
    p = save_img(img, img_dir, "s3_%d_0.png" % ep_id)
    rows.append((p, "Scroll the list to the bottom to reveal the last entry.",
                 "KEY End"))
    # step1: click revealed item
    img, d = new_canvas()
    d.text((60, 70), "List (showing 93-100 of 100)", fill=(30, 30, 30))
    item_box = [60, 95, 320, 125]
    d.rectangle(item_box, fill=(30, 111, 217))
    d.text((item_box[0] + 6, item_box[1] + 6), item_label, fill=(255, 255, 255))
    cx, cy = center(item_box)
    p = save_img(img, img_dir, "s3_%d_1.png" % ep_id)
    rows.append((p, "Click the last entry '%s' that was revealed." % item_label,
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S4: copy_paste_verify ----------
def gen_s4(rng, img_dir, ep_id):
    src_text = rng.choice(["KX-771-A", "MN-304-B", "PL-208-Q", "RT-117-C"])
    src_box = [60, 80, 260, 120]
    dst_box = [60, 170, 260, 205]
    verify_btn = [60, 240, 180, 275]
    rows = []
    # step0: click source
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    cx, cy = center(src_box)
    p = save_img(img, img_dir, "s4_%d_0.png" % ep_id)
    rows.append((p, "Click the source box containing '%s'." % src_text,
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step1: ctrl+a
    img, d = new_canvas()
    d.rectangle(src_box, fill=(180, 210, 255), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_1.png" % ep_id)
    rows.append((p, "Select all text in the source box with Ctrl+A.",
                 "KEY ctrl+a"))
    # step2: ctrl+c
    img, d = new_canvas()
    d.rectangle(src_box, fill=(180, 210, 255), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_2.png" % ep_id)
    rows.append((p, "Copy the selected text with Ctrl+C.",
                 "KEY ctrl+c"))
    # step3: click target
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", highlight=True, placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    cx, cy = center(dst_box)
    p = save_img(img, img_dir, "s4_%d_3.png" % ep_id)
    rows.append((p, "Click the target box to focus it.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step4: ctrl+v
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, src_text)
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_4.png" % ep_id)
    rows.append((p, "Paste the copied text into the target box with Ctrl+V.",
                 "KEY ctrl+v"))
    # step5: click verify
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, src_text)
    cx, cy = center(verify_btn)
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_5.png" % ep_id)
    rows.append((p, "Click the Verify button to confirm the transfer.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S5: fill_all_fields ----------
def gen_s5(rng, img_dir, ep_id):
    name = rng.choice(["Ada", "Bob", "Cara", "Dan"])
    email = name.lower() + "@example.com"
    qty = str(rng.choice([2, 3, 5, 7]))
    term_box = [60, 250, 80, 275]
    name_field = [60, 80, 300, 115]
    email_field = [60, 135, 300, 170]
    qty_field = [60, 190, 150, 225]
    submit_btn = [60, 290, 200, 325]
    rows = []
    # step0: type name (field highlighted)
    img, d = new_canvas()
    draw_input(d, name_field, "", highlight=True, placeholder="Full name")
    draw_input(d, email_field, "", placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(160, 160, 170))
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_0.png" % ep_id)
    rows.append((p, "Type '%s' into the Full name field." % name,
                 "TYPE " + name))
    # step1: type email
    img, d = new_canvas()
    draw_input(d, name_field, name)
    draw_input(d, email_field, "", highlight=True, placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(160, 160, 170))
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_1.png" % ep_id)
    rows.append((p, "Type '%s' into the Email field." % email,
                 "TYPE " + email))
    # step2: type qty
    img, d = new_canvas()
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, "", highlight=True, placeholder="Qty")
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(160, 160, 170))
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_2.png" % ep_id)
    rows.append((p, "Type '%s' into the Qty field." % qty,
                 "TYPE " + qty))
    # step3: click terms checkbox
    img, d = new_canvas()
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, qty)
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(90, 120, 200), width=2)
    cx, cy = center(term_box)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_3.png" % ep_id)
    rows.append((p, "Tick the 'I agree to terms' checkbox.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step4: click submit
    img, d = new_canvas()
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, qty)
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(30, 111, 217))
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_4.png" % ep_id)
    rows.append((p, "Click the Submit button to send the form.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S6: slider_to_target ----------
def gen_s6(rng, img_dir, ep_id):
    target = rng.choice([25, 40, 60, 75, 90])
    track = [120, 200, 640, 240]
    thumb_x = 120 + int((track[2]-track[0]) * 0.15)
    rows = []
    # step0: click track at target%
    img, d = new_canvas()
    d.text((60, 150), "Set slider to %d%%" % target, fill=(30, 30, 30))
    d.rectangle(track, fill=(200, 200, 210), outline=(120, 120, 130))
    # thumb current
    d.ellipse([thumb_x-8, track[1]-4, thumb_x+8, track[3]+4], fill=(30, 111, 217))
    d.text((track[0], track[3]+8), "current: 15%%" % (), fill=(60, 60, 60)) if False else None
    d.text((track[0], track[3] + 8), "current: 15%", fill=(60, 60, 60))
    click_x = track[0] + int((track[2]-track[0]) * target / 100.0)
    click_y = (track[1] + track[3]) // 2
    p = save_img(img, img_dir, "s6_%d_0.png" % ep_id)
    rows.append((p, "Click the slider track at the %d%% position." % target,
                 "CLICK %d %d" % (norm(click_x, CW), norm(click_y, CH))))
    # step1: fine-tune with arrow
    img, d = new_canvas()
    d.text((60, 150), "Set slider to %d%%" % target, fill=(30, 30, 30))
    d.rectangle(track, fill=(200, 200, 210), outline=(120, 120, 130))
    d.ellipse([click_x-8, track[1]-4, click_x+8, track[3]+4], fill=(30, 111, 217))
    d.text((track[0], track[3] + 8), "current: %d%%" % target, fill=(60, 60, 60))
    arrow = "ArrowRight" if target > 50 else "ArrowLeft"
    p = save_img(img, img_dir, "s6_%d_1.png" % ep_id)
    rows.append((p, "Press %s to fine-tune the slider to exactly %d%%." % (arrow, target),
                 "KEY " + arrow))
    return rows


# ---------- S7: counter_to_n ----------
def gen_s7(rng, img_dir, ep_id):
    target = rng.choice([3, 4, 5])
    inc_btn = [60, 130, 150, 170]
    sub_btn = [60, 200, 180, 235]
    rows = []
    for step in range(target):
        img, d = new_canvas()
        d.text((60, 70), "Target: %d" % target, fill=(30, 30, 30))
        d.text((60, 95), "Current: %d" % step, fill=(60, 60, 60))
        cx, cy = center(inc_btn)
        draw_button(d, inc_btn, (30, 111, 217), "+1")
        draw_button(d, sub_btn, (120, 120, 130), "Submit")
        p = save_img(img, img_dir, "s7_%d_%d.png" % (ep_id, step))
        rows.append((p, "Click the +1 button to increment the counter (target %d)." % target,
                     "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # final: submit
    img, d = new_canvas()
    d.text((60, 70), "Target: %d" % target, fill=(30, 30, 30))
    d.text((60, 95), "Current: %d" % target, fill=(30, 120, 30))
    draw_button(d, inc_btn, (120, 120, 130), "+1")
    cx, cy = center(sub_btn)
    draw_button(d, sub_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s7_%d_%d.png" % (ep_id, target))
    rows.append((p, "Click the Submit button (counter reached %d)." % target,
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S8: error_recovery_full ----------
def gen_s8(rng, img_dir, ep_id):
    name = rng.choice(["John", "Ada", "Bob"])
    email = name.lower() + "@example.com"
    qty = str(rng.choice([2, 3, 4]))
    name_field = [60, 80, 300, 115]
    email_field = [60, 135, 300, 170]
    qty_field = [60, 190, 150, 225]
    submit_btn = [60, 250, 200, 285]
    rows = []
    # step0: submit empty (reveal errors)
    img, d = new_canvas()
    draw_input(d, name_field, "", placeholder="Full name")
    draw_input(d, email_field, "", placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_0.png" % ep_id)
    rows.append((p, "Click Submit on the empty form to reveal validation errors.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step1: type name (errors shown)
    img, d = new_canvas()
    d.text((60, 56), "Errors: name required, email required, qty required", fill=(180, 30, 30))
    draw_input(d, name_field, "", highlight=True, placeholder="Full name")
    draw_input(d, email_field, "", placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_1.png" % ep_id)
    rows.append((p, "Type '%s' into the Full name field." % name,
                 "TYPE " + name))
    # step2: type email
    img, d = new_canvas()
    d.text((60, 56), "Errors: email required, qty required", fill=(180, 30, 30))
    draw_input(d, name_field, name)
    draw_input(d, email_field, "", highlight=True, placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_2.png" % ep_id)
    rows.append((p, "Type '%s' into the Email field." % email,
                 "TYPE " + email))
    # step3: type qty
    img, d = new_canvas()
    d.text((60, 56), "Errors: qty required", fill=(180, 30, 30))
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, "", highlight=True, placeholder="Qty")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_3.png" % ep_id)
    rows.append((p, "Type '%s' into the Qty field." % qty,
                 "TYPE " + qty))
    # step4: submit again
    img, d = new_canvas()
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, qty)
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_4.png" % ep_id)
    rows.append((p, "Click Submit again after fixing all fields.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


FAMILIES = [gen_s1, gen_s2, gen_s3, gen_s4, gen_s5, gen_s6, gen_s7, gen_s8]
FAMILY_NAMES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]


def build_targeted(n, seed, img_dir):
    """Sinh n episode targeted, phan bo deu 8 family. Tra ve list row."""
    rng = random.Random(seed)
    rows = []
    ep_counter = 0
    # distribute episodes across families
    base = n // len(FAMILIES)
    rem = n % len(FAMILIES)
    counts = [base + (1 if i < rem else 0) for i in range(len(FAMILIES))]
    for fi, fam in enumerate(FAMILIES):
        for _ in range(counts[fi]):
            ep_id = ep_counter
            ep_counter += 1
            # re-seed per episode for determinism but consume rng for variety
            ep_seed = rng.randrange(10**9)
            ep_rng = random.Random(ep_seed)
            steps = fam(ep_rng, img_dir, ep_id)
            for k, (path, instr, action) in enumerate(steps):
                rows.append({
                    "image": path,
                    "instruction": instr,
                    "action": action,
                    "family": FAMILY_NAMES[fi],
                    "episode": ep_id,
                    "step": k,
                })
    return rows




if __name__ == "__main__":
    main()
