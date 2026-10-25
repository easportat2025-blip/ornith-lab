import glob
import json
import math
import os
import random
import subprocess
import sys
import time

WORK = "/kaggle/working"
IMGS = os.path.join(WORK, "gui_imgs")
ORN = "/tmp/ornbase"
CW, CH = 768, 512
N_TRAIN = 1200
N_EVAL = 120
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
        # TASK-21: Kaggle auto-extract zip -> anh nam trong <ten-zip>/<path>,
        # va file zip bi STRIP -> phai tim trong TOAN BO dataset base.
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
    real_rows = load_ds_rows("real-fixtures", "grounding.jsonl")
    real_train = load_ds_rows("real-ui", "grounding.jsonl")
    traj_rows = load_ds_rows("gui-traj", "traj.jsonl")
    # TASK-18: self-play (rollout -> curate) cap 30% tong du lieu
    sp_rows = load_ds_rows("gui-selfplay", "traj.jsonl")
    base_n = len(synth_rows) + len(real_train) + len(traj_rows)
    cap_sp = int(0.30 * base_n / 0.70)
    if len(sp_rows) > cap_sp:
        log(f"selfplay {len(sp_rows)} -> cap {cap_sp} (30%)")
        sp_rows = sp_rows[:cap_sp]
    train_rows = synth_rows + real_train + traj_rows + sp_rows
    STEPS_V21 = max(200, int(STEPS * len(train_rows) / 2808))
    log(f"STEPS_V21 = max(200, {STEPS} * {len(train_rows)} / 2808) = {STEPS_V21}")
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
        f"selfplay {len(sp_rows)}) "
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
        max_steps=STEPS_V21,
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

    acc1 = evaluate(model, processor, eval_rows, "after", n=100, samples=5,
                    adapter_probe=True)
    accT = evaluate(model, processor, train_rows, "train-sub", n=12,
                    samples=5, adapter_probe=True)
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
                   "n_train": len(train_rows), "steps": STEPS_V21,
        "n_selfplay": len(sp_rows),
        "recipe": "v18-action-only + selfplay",
                   "t_sec": time.time() - t0}, f)
    log(f"ALL DONE before={acc0:.3f} after={acc1:.3f} "
        f"train_sub={accT:.3f} traj_sub={accTj:.3f} "
        f"real_before={accR0:.3f} real_after={accR1:.3f}")


if __name__ == "__main__":
    main()
