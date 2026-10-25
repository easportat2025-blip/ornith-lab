# -*- coding: utf-8 -*-
# stage_and_upload.py - stage + upload 2 dataset (adapter v22 + loop-recovery data)
# QUY TAC: dataset = it nhat 1 file .zip (CLI hang khi nhieu file!)
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"


def sh(c, t=3600):
    p = subprocess.run(c, shell=True, capture_output=True, env=ENV, timeout=t)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


def upload(stage):
    meta = json.load(io.open(os.path.join(stage, "dataset-metadata.json"),
                             encoding="utf-8"))
    did = meta["id"]
    print("--- upload %s" % did, flush=True)
    rc, o, e = sh("kaggle datasets create -p \"%s\"" % stage)
    if "already" in (o + e).lower() or "version" in (o + e).lower():
        rc, o, e = sh("kaggle datasets version -p \"%s\" -m \"update\"" % stage)
    print("   ", (o + e).strip()[-160:], flush=True)
    return did


# ---------- 1) adapter v22 ----------
S1 = os.path.join(ROOT, "phase13-gui", "lora_v22_dataset")
SRC1 = os.path.join(ROOT, "phase13-gui", "out_sft_v22", "gui_lora")
if os.path.isdir(SRC1):
    shutil.rmtree(S1, ignore_errors=True)
    os.makedirs(S1, exist_ok=True)
    for f in os.listdir(SRC1):
        p = os.path.join(SRC1, f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(S1, f))
    io.open(os.path.join(S1, "dataset-metadata.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(
        {"title": "Ornith GUI LoRA v22 (adapter)",
         "id": "khoadangnguye/ornith-gui-lora-v22",
         "licenses": [{"name": "other"}]}, ensure_ascii=False, indent=1))
    print("staged adapter:", len(os.listdir(S1)), "file")
    upload(S1)
else:
    print("!! thieu adapter tai", SRC1)

# ---------- 2) loop-recovery data (GLM) -> 1 zip ----------
S2 = os.path.join(ROOT, "phase13-gui", "synth_recipe_ds_staging",
                   "khoadangnguye__ornith-gui-synth-recipe")
SRC2 = os.path.join(ROOT, "phase13-gui", "synth_recipe")
rows_p = os.path.join(SRC2, "rows.jsonl")
imgs_d = os.path.join(SRC2, "images")
if os.path.exists(rows_p) and os.path.isdir(imgs_d):
    shutil.rmtree(os.path.dirname(S2), ignore_errors=True)
    os.makedirs(S2, exist_ok=True)
    rows = [json.loads(l) for l in io.open(rows_p, encoding="utf-8") if l.strip()]
    zp = os.path.join(S2, "synth_recipe_bundle.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(imgs_d)):
            if f.lower().endswith(".png"):
                z.write(os.path.join(imgs_d, f), "images/" + f)
    n = 0
    with io.open(os.path.join(S2, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in rows:
            r["image"] = "images/" + os.path.basename(r.get("image", ""))
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    io.open(os.path.join(S2, "dataset-metadata.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(
        {"title": "Ornith synth recipe (loop-recovery, 2 chu ky lap)",
         "id": "khoadangnguye/ornith-gui-synth-recipe",
         "licenses": [{"name": "other"}]}, ensure_ascii=False, indent=1))
    print("staged recipe:", n, "row,", len(os.listdir(S2)), "file,",
          round(os.path.getsize(zp) / 1e6, 1), "MB")
    upload(S2)
else:
    print("!! thieu synth_recipe tai", SRC2)
