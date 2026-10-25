# -*- coding: utf-8 -*-
# add_2x2_to_queue.py - dua 2 phep do con treo (MiMo) vao queue acc A
import io
import json

P = "scripts/gpu_queue.json"
q = json.load(io.open(P, encoding="utf-8"))
items = [
    {"id": "khoadangnguye/ornith-gui-bench-v16-v22",
     "dir": "phase13-gui/kernel_bench_v16_v22",
     "note": "gate v22 tren B16 DA SUA (task moi) - tach do sua task vs do data"},
    {"id": "khoadangnguye/ornith-gui-bench-v155-v22-old",
     "dir": "phase13-gui/kernel_bench_v155_v22_old",
     "note": "O 2x2: v22 tren task B15.5 CU - tach do sua task vs do data (MiMo)"},
]
for it in items:
    q = [i for i in q if i.get("id") != it["id"]]
    idx = next((k for k, i in enumerate(q)
                if i.get("id") == "khoadangnguye/ornith-gui-sft-v23b"), len(q) - 1)
    q.insert(idx + 1, it)
json.dump(q, io.open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("queue A:")
for i in q[:9]:
    print("   %-44s %s" % (i["id"].split("/")[-1], i.get("note", "")[:58]))
