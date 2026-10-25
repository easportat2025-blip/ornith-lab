"""show_kernel_log.py - doc log kernel (bo qua loi charmap) + rut cac dong [tag]."""
import io
import json
import os
import re
import sys

p = sys.argv[1]
tag = sys.argv[2] if len(sys.argv) > 2 else ""
n = int(sys.argv[3]) if len(sys.argv) > 3 else 25

s = io.open(p, encoding="utf-8", errors="replace").read()
out = []
# log kaggle: tung dong la 1 JSON {"stream_name":..,"data":".."}
for line in s.splitlines():
    line = line.strip().lstrip(",")
    if not line.startswith("{"):
        continue
    try:
        d = json.loads(line)
    except Exception:
        continue
    if isinstance(d, dict) and "data" in d:
        out.append(d["data"])
txt = "".join(out)
if not txt:
    txt = s
lines = [l for l in txt.splitlines() if l.strip()]
if tag:
    lines = [l for l in lines if tag in l]
for l in lines[-n:]:
    print(l[:220])
print("--- tong %d dong" % len(lines))
