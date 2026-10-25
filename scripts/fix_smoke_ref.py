# -*- coding: utf-8 -*-
"""fix_smoke_ref.py - bo dataset 'ornith-gui-xdotool' (chua ton tai) khoi kernel
smoke (CPU + internet: apt chay duoc) + kernel A/B.
"""
import io
import json

for d in ["kernel_desktop_bench_smoke", "kernel_desktop_bench_a",
          "kernel_desktop_bench_b"]:
    p = "phase13-gui/%s/kernel-metadata.json" % d
    md = json.load(io.open(p, encoding="utf-8"))
    b = list(md["dataset_sources"])
    md["dataset_sources"] = [x for x in md["dataset_sources"]
                             if "ornith-gui-xdotool" not in x]
    if md["dataset_sources"] != b:
        json.dump(md, io.open(p, "w", encoding="utf-8"), ensure_ascii=False,
                  indent=1)
        print("%-30s bo xdotool" % d)
