# -*- coding: utf-8 -*-
"""upload_traj_local.py - upload dataset traj tu bo SINH LAI BO LOC (816 anh +
816 dong mot man hinh 1024x768 - nhat quan) + anh PHANG (Kaggle bo qua thu muc con).
Thay cho R2 (1280x720) ma anh khong ton tai o dau.
"""
import io
import json
import os
import shutil
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGEN = os.path.join(os.environ.get("TEMP", "."), "traj_regen")
STAGE = os.path.join(ROOT, "phase13-gui", "traj_local_staging")
DID = "khoadangnguye/ornith-gui-traj"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"


def sh(c, t=3600):
    p = subprocess.run(c, shell=True, capture_output=True, env=ENV, timeout=t)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


src_imgs = os.path.join(REGEN, "images")
src_jsonl = os.path.join(REGEN, "traj.jsonl")
if not os.path.isdir(src_imgs) or not os.path.exists(src_jsonl):
    print("thieu bo sinh lai:", src_imgs, src_jsonl)
    raise SystemExit(1)

rows = [json.loads(l) for l in io.open(src_jsonl, encoding="utf-8") if l.strip()]
print("rows local:", len(rows), "| anh:", len(os.listdir(src_imgs)))

shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
for f in os.listdir(src_imgs):
    if f.lower().endswith(".png"):
        shutil.copy2(os.path.join(src_imgs, f), os.path.join(STAGE, f))
keep = 0
with io.open(os.path.join(STAGE, "traj.jsonl"), "w", encoding="utf-8",
             newline="\n") as fh:
    for r in rows:
        b = os.path.basename(r.get("image") or "")
        if os.path.exists(os.path.join(STAGE, b)):
            r["image"] = b
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            keep += 1
meta = {"title": "Ornith GUI traj (sinh lai 1024x768, anh phang)",
        "id": DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("staged:", len(os.listdir(STAGE)), "file | rows giu:", keep)

rc, o, e = sh("kaggle datasets version -p \"%s\" -m \"sinh lai 1024x768, %d row, anh phang\""
              % (STAGE, keep))
print("upload:", o[-160:], e[-160:])
for i in range(40):
    q = sh("kaggle datasets status %s" % DID)
    t = (q[1] + q[2]).strip()
    if "ready" in t.lower():
        print("READY")
        break
    time.sleep(15)
