# -*- coding: utf-8 -*-
"""upload_x11_dataset.py - upload x11_bundle.zip lam dataset
'khoadangnguye/ornith-gui-xdotool' (de kernel GPU internet OFF cai duoc X11 tools).
"""
import io
import json
import os
import shutil
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "out_x11", "x11_bundle.zip")
STAGE = os.path.join(ROOT, "phase13-gui", "x11_dataset")
DID = "khoadangnguye/ornith-gui-xdotool"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"

if not os.path.exists(SRC):
    print("thieu", SRC)
    raise SystemExit(1)
shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
shutil.copy2(SRC, os.path.join(STAGE, "x11_bundle.zip"))
meta = {"title": "X11 tools offline (.deb) cho desktop-env - Xvfb, x11-utils, xdotool, imagemagick",
        "id": DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("staged:", os.listdir(STAGE))

p = subprocess.run(["kaggle", "datasets", "create", "-p", STAGE],
                   capture_output=True, env=ENV, timeout=3600)
print((p.stdout or b"").decode("utf-8", "replace")[-300:])
print((p.stderr or b"").decode("utf-8", "replace")[-300:])
for i in range(30):
    q = subprocess.run(["kaggle", "datasets", "status", DID], capture_output=True,
                       env=ENV, timeout=180)
    t = ((q.stdout or b"").decode("utf-8", "replace")
         + (q.stderr or b"").decode("utf-8", "replace")).strip()
    print("  [%d] %s" % (i + 1, t[:90]))
    if "ready" in t.lower():
        print("READY")
        break
    time.sleep(15)
