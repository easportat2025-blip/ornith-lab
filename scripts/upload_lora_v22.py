# -*- coding: utf-8 -*-
"""upload_lora_v22.py - upload adapter v22 len dataset (bo qua BOM, dung python
de khong loi encoding cua PowerShell).
"""
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "out_sft_v22", "gui_lora")
STAGE = os.path.join(ROOT, "phase13-gui", "lora_v22_dataset")
DID = "khoadangnguye/ornith-gui-lora-v22"
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"
ENV["PYTHONIOENCODING"] = "utf-8"

if not os.path.exists(os.path.join(SRC, "adapter_config.json")):
    print("thieu adapter o", SRC)
    sys.exit(1)

os.makedirs(STAGE, exist_ok=True)
import shutil
for f in os.listdir(SRC):
    s = os.path.join(SRC, f)
    if os.path.isfile(s):
        shutil.copy2(s, os.path.join(STAGE, f))
meta = {"title": "Ornith GUI LoRA v22 (5802 row: targeted+policy-replay+3D)",
        "id": DID, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("staged:", sorted(os.listdir(STAGE)))

p = subprocess.run(["kaggle", "datasets", "create", "-p", STAGE],
                   capture_output=True, env=ENV, timeout=3600)
out = (p.stdout or b"").decode("utf-8", "replace")
err = (p.stderr or b"").decode("utf-8", "replace")
print("create rc=%s\n%s\n%s" % (p.returncode, out[-400:], err[-400:]))

# doi trang thai den READY
for i in range(40):
    q = subprocess.run(["kaggle", "datasets", "status", DID], capture_output=True,
                       env=ENV, timeout=180)
    t = ((q.stdout or b"").decode("utf-8", "replace")
         + (q.stderr or b"").decode("utf-8", "replace")).strip()
    print("  [%d] %s" % (i + 1, t[:90]))
    if "ready" in t.lower():
        print("READY")
        break
    time.sleep(15)
