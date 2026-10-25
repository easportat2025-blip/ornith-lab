# -*- coding: utf-8 -*-
"""fix_v16_v22_dataset.py - kernel gate v22 tren B16 phai mount dataset B16 DA SUA
(khoadangnguye/ornith-gui-bench-v16b), khong phai slug cu (chua co fix "lo dap an").
"""
import io
import json

P = "phase13-gui/kernel_bench_v16_v22/kernel-metadata.json"
md = json.load(io.open(P, encoding="utf-8"))
old = "khoadangnguye/ornith-gui-bench-v16"
new = "khoadangnguye/ornith-gui-bench-v16b"
if old in md["dataset_sources"]:
    md["dataset_sources"] = [new if x == old else x for x in md["dataset_sources"]]
    json.dump(md, io.open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("da doi:", old, "->", new)
else:
    print("khong can doi (da dung slug moi hoac khong co slug cu)")
print("bench datasets:", [x for x in md["dataset_sources"] if "bench" in x])

# them vao queue B tuong ung (de baseline tren B16 cung dung dataset moi)
PB = "scripts/gpu_queue_B.json"
q = json.load(io.open(PB, encoding="utf-8"))
for i in q:
    if i.get("id") == "dieniw/ornith-bench-v16-b1":
        mp = "phase13-gui/kernel_bench_v16_B/kernel-metadata.json"
        m2 = json.load(io.open(mp, encoding="utf-8"))
        if "dieniw/ornith-gui-bench-v16" in m2["dataset_sources"]:
            m2["dataset_sources"] = [new2 if x == "dieniw/ornith-gui-bench-v16"
                                      else x
                                      for x, new2 in zip(
                                          m2["dataset_sources"],
                                          ["dieniw/ornith-gui-bench-v16b"
                                           if x == "dieniw/ornith-gui-bench-v16"
                                           else x
                                           for x in m2["dataset_sources"]])]
            json.dump(m2, io.open(mp, "w", encoding="utf-8"), ensure_ascii=False,
                      indent=1)
            print("B: doi dataset B16 -> v16b")
        print("  B bench:", [x for x in m2["dataset_sources"] if "bench" in x])
json.dump(q, io.open(PB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
