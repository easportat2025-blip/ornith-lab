# -*- coding: utf-8 -*-
"""fix_smoke_cpu.py - kernel desktop-bench-smoke -> CPU + internet ON + KHONG
competition (de push duoc: Kaggle cam "Internet + accelerator + competition").

Muc tieu smoke: CHUNG MINH ENV (8 task + reward + anh + hanh dong that) - khong
can model nen CPU la du.
"""
import io
import json
import os

P = "phase13-gui/kernel_desktop_bench_smoke/kernel-metadata.json"
md = json.load(io.open(P, encoding="utf-8"))
md["enable_gpu"] = False
md["enable_internet"] = True
md["competition_sources"] = []
md["id"] = "khoadangnguye/ornith-gui-desktop-bench-smoke"
md["title"] = "ornith-gui-desktop-bench-smoke"
# bo dataset GPU-only (base model khong can cho smoke)
md["dataset_sources"] = [x for x in md["dataset_sources"]
                         if "ornbase" not in x and "gemma12b" not in x
                         and "stack-wheels" not in x and "lora" not in x]
json.dump(md, io.open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("smoke -> gpu=%s net=%s comp=%s" % (md["enable_gpu"],
                                          md["enable_internet"],
                                          md["competition_sources"]))
print("   datasets:", md["dataset_sources"])

# --- them bien moi truong de smoke chay policy dummy (khong can model) ---
C = "phase13-gui/kernel_desktop_bench_smoke/desktop_bench_kernel.py"
s = io.open(C, encoding="utf-8").read()
if "DB_POLICY" in s and "DB_EPISODES" in s:
    print("kernel co env DB_POLICY/DB_EPISODES ✓ (policy=dummy, episodes=2)")
else:
    print("!! kernel thieu env DB_POLICY/DB_EPISODES")
