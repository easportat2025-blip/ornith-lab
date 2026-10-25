# -*- coding: utf-8 -*-
"""fix_desktop_bench_b.py - kernel desktop-bench tren acc B phai mount adapter
 tren acc B (khoadangnguye/... khong mount duoc qua acc khac).
"""
import io
import json

P = "phase13-gui/kernel_desktop_bench_b/kernel-metadata.json"
md = json.load(io.open(P, encoding="utf-8"))
old = "khoadangnguye/ornith-gui-lora-v21"
new = "dieniw/ornith-gui-lora-v21"
if old in md["dataset_sources"]:
    md["dataset_sources"] = [new if x == old else x for x in md["dataset_sources"]]
    json.dump(md, io.open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("da doi:", old, "->", new)
else:
    print("khong can doi")
print("datasets:", md["dataset_sources"])
print("id:", md.get("id"))
