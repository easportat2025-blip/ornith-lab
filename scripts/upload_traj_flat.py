# -*- coding: utf-8 -*-
"""upload_traj_flat.py - upload lai dataset 'ornith-gui-traj' voi ANH PHANG
(CLI bo qua thu muc con -> truoc do dataset chi con traj.jsonl, 0 anh).
- anh: sinh lai boi gen_traj.py (816 anh) + anh tu dataset cu (neu co)
- rows: 972 dong R2 (da tai ve), duong dan anh -> phang
"""
import io
import json
import os
import shutil
import subprocess
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(os.environ.get("TEMP", "."), "traj_flat")
REGEN = os.path.join(os.environ.get("TEMP", "."), "traj_regen")
STAGE = os.path.join(ROOT, "phase13-gui", "traj_flat_staging")
DID = "khoadangnguye/ornith-gui-traj"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"


def sh(c, t=3600):
    p = subprocess.run(c, shell=True, capture_output=True, env=ENV, timeout=t)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


# 1) lay rows R2 (972) tu dataset (zip) + anh cu (neu co)
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
sh("kaggle datasets download %s -p \"%s\" --force" % (DID, TMP))
imgs = {}
for root, _d, files in os.walk(TMP):
    for f in files:
        if f.lower().endswith(".png"):
            imgs[f] = os.path.join(root, f)
rows = []
tj = [os.path.join(r, f) for r, _d, fs in os.walk(TMP) for f in fs
      if f == "traj.jsonl"]
if tj:
    for line in io.open(tj[0], encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
print("R2 rows:", len(rows), "| anh trong dataset:", len(imgs))

# 2) them anh sinh lai
regen_imgs = os.path.join(REGEN, "images")
n_regen = 0
if os.path.isdir(regen_imgs):
    for f in os.listdir(regen_imgs):
        if f.lower().endswith(".png"):
            imgs.setdefault(f, os.path.join(regen_imgs, f))
            n_regen += 1
print("anh sinh lai them:", n_regen, "| tong anh:", len(imgs))

# 3) stage: anh phang + rows voi duong dan phang
shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
for f, p in imgs.items():
    shutil.copy2(p, os.path.join(STAGE, f))
keep = 0
with io.open(os.path.join(STAGE, "traj.jsonl"), "w", encoding="utf-8",
             newline="\n") as fh:
    for r in rows:
        b = os.path.basename(r.get("image") or "")
        if b in imgs:
            r["image"] = b
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            keep += 1
meta = {"title": "Ornith GUI traj R2 (anh phang)",
        "id": DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("staged:", len(os.listdir(STAGE)), "file | rows giu:", keep)

# 4) upload
rc, o, e = sh("kaggle datasets version -p \"%s\" -m \"R2: %d rows, anh phang\""
              % (STAGE, keep))
print("upload:", o[-160:], e[-160:])
for i in range(40):
    q = sh("kaggle datasets status %s" % DID)
    t = (q[1] + q[2]).strip()
    if "ready" in t.lower():
        print("READY")
        break
    time.sleep(15)
