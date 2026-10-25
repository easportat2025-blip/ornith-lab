# -*- coding: utf-8 -*-
"""upload_traj_zip.py - upload dataset traj (slug MOI) voi ANH GAI TRONG 1 FILE ZIP.

Ly do: `kaggle datasets create` voi NHIEU file (818) BI TREO (3 tien trinh kaggle.exe
ke tu toi qua) => upload 2 file (traj.jsonl + traj_images.zip) nhanh hon nhieu.
Loader se tu giai nen .zip trong thu muc dataset (logic `_resolve` + extractall) =>
anh van resolve duoc ✓.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGEN = os.path.join(os.environ.get("TEMP", "."), "traj_regen")
STAGE = os.path.join(ROOT, "phase13-gui", "traj_zip_staging")
NEW_DID = "khoadangnguye/ornith-gui-traj2"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"


def sh(c, t=3600):
    p = subprocess.run(c, shell=True, capture_output=True, env=ENV, timeout=t)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


src_imgs = os.path.join(REGEN, "images")
src_jsonl = os.path.join(REGEN, "traj.jsonl")
if not os.path.isdir(src_imgs) or not os.path.exists(src_jsonl):
    print("thieu bo sinh lai:", src_imgs)
    sys.exit(1)

rows = [json.loads(l) for l in io.open(src_jsonl, encoding="utf-8") if l.strip()]
shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
zp = os.path.join(STAGE, "traj_images.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in os.listdir(src_imgs):
        if f.lower().endswith(".png"):
            z.write(os.path.join(src_imgs, f), f)
print("zip:", round(os.path.getsize(zp) / 1e6, 1), "MB |", len(rows), "row")

# giu duong dan anh PHANG (ten file) - loader se tim basename sau khi giai nen zip
keep = 0
with io.open(os.path.join(STAGE, "traj.jsonl"), "w", encoding="utf-8",
             newline="\n") as fh:
    for r in rows:
        b = os.path.basename(r.get("image") or "")
        if b:
            r["image"] = b
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            keep += 1
meta = {"title": "Ornith GUI traj v2 (anh trong zip)",
        "id": NEW_DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("staged:", os.listdir(STAGE), "| rows:", keep)

rc, o, e = sh("kaggle datasets create -p \"%s\"" % STAGE)
print("create rc=%s" % rc, o[-160:], e[-200:])
for i in range(40):
    q = sh("kaggle datasets status %s" % NEW_DID)
    t = (q[1] + q[2]).strip()
    print("  [%d] %s" % (i + 1, t[:70]))
    if "ready" in t.lower():
        print("READY", NEW_DID)
        break
    time.sleep(15)
