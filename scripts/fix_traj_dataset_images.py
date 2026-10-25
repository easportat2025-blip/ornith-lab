# -*- coding: utf-8 -*-
"""fix_traj_dataset_images.py - dataset 'ornith-gui-traj' (R2) bi thieu ANH:
`kaggle datasets create` BO QUA thu muc con (images/) -> chi con traj.jsonl.

Sua: tai dataset ve -> giai nen -> LAM PHANG anh ra cap goc + sua duong dan
trong row -> upload version moi (CLI).
"""
import io
import json
import os
import shutil
import subprocess
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(os.environ.get("TEMP", "."), "traj_fix")
STAGE = os.path.join(ROOT, "phase13-gui", "traj_fix_staging")
DID = "khoadangnguye/ornith-gui-traj"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"


def sh(c, t=3600):
    p = subprocess.run(c, shell=True, capture_output=True, env=ENV, timeout=t)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)
print("tai dataset...", flush=True)
sh("kaggle datasets download %s -p \"%s\" --force" % (DID, TMP))
zips = [f for f in os.listdir(TMP) if f.endswith(".zip")]
if not zips:
    print("tai that bai")
    raise SystemExit(1)
with zipfile.ZipFile(os.path.join(TMP, zips[0])) as z:
    z.extractall(TMP)
shutil.rmtree(TMP, ignore_errors=True)

# tim file traj.jsonl (co the nam trong thu muc con)
traj = None
imgs = {}
for root, _d, files in os.walk(TMP):
    for f in files:
        p = os.path.join(root, f)
        if f == "traj.jsonl":
            traj = p
        elif f.lower().endswith(".png"):
            imgs[os.path.basename(p)] = p
print("traj:", traj, "| anh:", len(imgs))
if not traj:
    raise SystemExit("khong thay traj.jsonl")

# doc row + sua duong dan anh -> phang
rows = []
for line in io.open(traj, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    im = r.get("image") or ""
    base = os.path.basename(im)
    if base in imgs:
        r["image"] = base
    rows.append(r)
print("rows:", len(rows), "| co image phang:", sum(1 for r in rows
                                                 if "/" not in r.get("image", "")))

# stage: anh phang o cap goc + traj.jsonl
shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
for base, p in imgs.items():
    shutil.copy2(p, os.path.join(STAGE, base))
with io.open(os.path.join(STAGE, "traj.jsonl"), "w", encoding="utf-8",
             newline="\n") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
meta = {"title": "Ornith GUI traj R2 (972 rows, anh phang)",
        "id": DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("staged:", len(os.listdir(STAGE)), "file")

rc, o, e = sh("kaggle datasets version -p \"%s\" -m \"R2 + anh phang (972 rows)\""
              % STAGE)
print("upload:", o[-200:], e[-200:])
for i in range(30):
    q = sh("kaggle datasets status %s" % DID)
    t = (q[1] + q[2]).strip()
    if "ready" in t.lower():
        print("READY")
        break
    time.sleep(15)
