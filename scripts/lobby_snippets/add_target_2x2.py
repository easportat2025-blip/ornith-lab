# -*- coding: utf-8 -*-
"""them_target_2x2.py - them kernel o 2x2 (v22 tren task B15.5 CU) vao
watchdog_targets.json de watchdog tu theo doi + tai ket qua ve.

Khong them => kernel chay xong nhung watchdog BO QUA (khong co target) => ket qua
khong duoc tai => o 2x2 cua thu nghiem 2x2 bi bo qua.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "watchdog_targets.json")
KID = "khoadangnguye/ornith-gui-bench-v155-v22-old"
NEW = {
    "label": "bench-v155-v22-old",
    "kernel": KID,
    "outdir": "phase13-gui/out_bench_v155_v22_old",
    "pattern": "b15_result\\.json|.*\\.log",
}

t = json.load(io.open(P, encoding="utf-8"))
if any(x.get("kernel") == KID for x in t):
    print("da co target, khong doi")
else:
    t.append(NEW)
    with io.open(P, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(t, fh, ensure_ascii=False, indent=1)
    print("da them target:", json.dumps(NEW, ensure_ascii=False))
print("tong targets:", len(t))
