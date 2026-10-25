"""split_queues.py - tach hang doi GPU thanh 2 queue (acc A va acc B).

Acc A (khoadangnguye): train v21 + cac gate cua v21 + rollout v21
Acc B (dieniw):        baseline v18 (B15.5/B16/3D) + train v22 + gate v22
Watchdog doc duong dan queue tu env GPU_QUEUE (mac dinh gpu_queue.json).
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
Q = os.path.join(HERE, "gpu_queue.json")

items = json.load(io.open(Q, encoding="utf-8"))
A_KEYS = [
    "khoadangnguye/ornith-gui-sft-v21",
    "khoadangnguye/ornith-gui-bench-v21",
    "khoadangnguye/ornith-gui-bench-v155-v21",
    "khoadangnguye/ornith-gui-bench-v14-v21",
    "khoadangnguye/ornith-gui-bench-v16-v21",
    "khoadangnguye/ornith-gui-rollout-v21",
    "khoadangnguye/ornith-gui-bench-3d-v21",
    "khoadangnguye/ornith-gui-bench-3d-hard-v21",
    "khoadangnguye/ornith-gui-bench-v15-think0",
]
B_KEYS = [
    "khoadangnguye/ornith-gui-bench-v155",
    "khoadangnguye/ornith-gui-bench-v16",
    "khoadangnguye/ornith-gui-bench-3d",
    "khoadangnguye/ornith-gui-bench-3d-hard",
    "khoadangnguye/ornith-gui-sft-v22",
    "khoadangnguye/ornith-gui-bench-v22",
    "khoadangnguye/ornith-gui-bench-v155-v22",
    "khoadangnguye/ornith-gui-bench-v16-v22",
]
by_id = {i["id"]: i for i in items}
qa = [by_id[k] for k in A_KEYS if k in by_id]
qb = [by_id[k] for k in B_KEYS if k in by_id]
# doi id sang namespace acc B cho cac muc cua B
for it in qb:
    it["id"] = it["id"].replace("khoadangnguye/", "dieniw/")
    if it.get("needs_dataset"):
        it["needs_dataset"] = it["needs_dataset"].replace("khoadangnguye/",
                                                         "dieniw/")
    if it.get("after"):
        it["after"] = it["after"].replace("khoadangnguye/", "dieniw/")
    it["dir"] = it["dir"]
json.dump(qa, io.open(os.path.join(HERE, "gpu_queue.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(qb, io.open(os.path.join(HERE, "gpu_queue_B.json"), "w",
                       encoding="utf-8"), ensure_ascii=False, indent=1)
print("queue A (%d):" % len(qa))
for i in qa:
    print("   ", i["id"])
print("queue B (%d):" % len(qb))
for i in qb:
    print("   ", i["id"], "| after:", i.get("after", "-"))
