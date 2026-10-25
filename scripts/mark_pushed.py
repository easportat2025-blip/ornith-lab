"""mark_pushed.py - danh dau 1 muc trong gpu_queue da push (tranh push trung)."""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "gpu_queue_state.json")
ids = sys.argv[1:]
d = {}
if os.path.exists(P):
    d = json.load(io.open(P, encoding="utf-8"))
for i in ids:
    rec = d.setdefault(i, {})
    rec["pushed"] = True
    rec["status"] = "RUNNING"
    rec["pushed_at"] = "manual"
with io.open(P, "w", encoding="utf-8") as fh:
    json.dump(d, fh, ensure_ascii=False, indent=1)
print("marked pushed:", ids)
print("state keys:", len(d))
