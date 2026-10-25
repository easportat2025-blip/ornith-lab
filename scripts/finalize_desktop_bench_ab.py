# -*- coding: utf-8 -*-
"""finalize_desktop_bench_ab.py - kernel desktop-bench A/B: enable_internet=FALSE
(Kaggle cam internet + accelerator + competition) + mount dataset xdotool offline
(env se cai X11 bang dpkg -i).
"""
import io
import json

for d, ds in [("kernel_desktop_bench_a", "khoadangnguye/ornith-gui-xdotool"),
               ("kernel_desktop_bench_b", "dieniw/ornith-gui-xdotool")]:
    p = "phase13-gui/%s/kernel-metadata.json" % d
    md = json.load(io.open(p, encoding="utf-8"))
    md["enable_internet"] = False
    if ds not in md["dataset_sources"]:
        md["dataset_sources"].append(ds)
    json.dump(md, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%-28s net=%s | datasets=%s" % (d, md["enable_internet"],
                                         md["dataset_sources"]))
