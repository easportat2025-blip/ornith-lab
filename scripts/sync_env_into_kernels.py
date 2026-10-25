# -*- coding: utf-8 -*-
"""sync_env_into_kernels.py - cap nhat ban INLINE cua env.py trong cac kernel
desktop-bench (Kaggle chi upload code_file -> phai inline).

Dung: python scripts/sync_env_into_kernels.py
"""
import io
import os
import re

HP = "phase14-desktop/env.py"
KERNELS = [
    "phase13-gui/kernel_desktop_bench_a/desktop_bench_kernel.py",
    "phase13-gui/kernel_desktop_bench_b/desktop_bench_kernel.py",
    "phase13-gui/kernel_desktop_bench_smoke/desktop_bench_kernel.py",
    "phase13-gui/kernel_desktop_bench/desktop_bench_kernel.py",
]

h = io.open(HP, encoding="utf-8").read().lstrip("\n")
if "'''" in h:
    raise SystemExit("env.py co chuoi ''' -> can cach khac")

for kp in KERNELS:
    if not os.path.exists(kp):
        print("skip (khong co):", kp)
        continue
    s = io.open(kp, encoding="utf-8").read()
    m = re.search(r"ENV_SRC = ", s)
    if not m:
        print("skip (khong co ENV_SRC):", kp)
        continue
    start = m.end()
    rest = s[start:]
    if rest.startswith("'''"):
        end_rel = rest.find("'''", 3) + 3
    else:
        i = 1
        while i < len(rest):
            if rest[i] == "\\":
                i += 2
                continue
            if rest[i] == "'":
                break
            i += 1
        end_rel = i + 1
    new = "r'''" + h + "'''"
    s2 = s[:start] + new + rest[end_rel:]
    io.open(kp, "w", encoding="utf-8", newline="\n").write(s2)
    print("dong bo ENV_SRC ->", kp, "(%d char)" % len(new))
