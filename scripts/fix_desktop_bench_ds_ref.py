# -*- coding: utf-8 -*-
"""fix_desktop_bench_ds_ref.py - bo tham chieu dataset 'ornith-gui-xdotool' (chua
ton tai -> Kaggle tra 400 Bad Request khi push). Giu duong apt (da sua toi thieu
va timeout 2700 trong env.py inline).
"""
import io
import json

for d in ["kernel_desktop_bench_a", "kernel_desktop_bench_b"]:
    p = "phase13-gui/%s/kernel-metadata.json" % d
    md = json.load(io.open(p, encoding="utf-8"))
    before = list(md["dataset_sources"])
    md["dataset_sources"] = [x for x in md["dataset_sources"]
                             if "ornith-gui-xdotool" not in x]
    if md["dataset_sources"] != before:
        json.dump(md, io.open(p, "w", encoding="utf-8"), ensure_ascii=False,
                  indent=1)
        print("%s: bo xdotool dataset" % d)
    print("   ", md["dataset_sources"])
