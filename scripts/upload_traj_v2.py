# -*- coding: utf-8 -*-
"""upload_traj_v2.py - tao dataset traj MOI (slug moi) vi `datasets version` khong
cap nhat dung file traj.jsonl (file 0 byte).
Sau do: tro kernel v23b sang slug moi + push.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "phase13-gui", "traj_local_staging")
NEW_DID = "khoadangnguye/ornith-gui-traj2"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"


def sh(c, t=5400):
    p = subprocess.run(c, shell=True, capture_output=True, env=ENV, timeout=t)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


tj = os.path.join(STAGE, "traj.jsonl")
n = sum(1 for l in io.open(tj, encoding="utf-8") if l.strip())
print("staging traj.jsonl:", n, "row |", len(os.listdir(STAGE)), "file")
if n < 100:
    print("!! staging rong -> dung upload_traj_local.py truoc")
    sys.exit(1)

meta = {"title": "Ornith GUI traj v2 (816 row, anh phang)",
        "id": NEW_DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))

rc, o, e = sh("kaggle datasets create -p \"%s\"" % STAGE)
print("create:", o[-200:], e[-200:])
for i in range(40):
    q = sh("kaggle datasets status %s" % NEW_DID)
    t = (q[1] + q[2]).strip()
    if "ready" in t.lower():
        print("READY", NEW_DID)
        break
    time.sleep(15)

# tro kernel v23b sang slug moi
for kdir in ("kernel_v23b",):
    p = os.path.join(ROOT, "phase13-gui", kdir, "kernel-metadata.json")
    md = json.load(io.open(p, encoding="utf-8"))
    md["dataset_sources"] = [NEW_DID if x == "khoadangnguye/ornith-gui-traj" else x
                             for x in md["dataset_sources"]]
    json.dump(md, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(kdir, "-> ", [x for x in md["dataset_sources"] if "traj" in x])

# push
rc, o, e = sh("kaggle kernels push -p \"%s\""
              % os.path.join(ROOT, "phase13-gui", "kernel_v23b"))
print("push:", o[-200:], e[-200:])
