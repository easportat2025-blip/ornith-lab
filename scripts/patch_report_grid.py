# -*- coding: utf-8 -*-
"""
patch_report_grid.py - them o (v21, task MOI) vao bang 2x2 cua
report_fixed_suite.py (o thieu that cua phep do tach "sua task" vs "data").
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "report_fixed_suite.py")

OLD = '''    grid = [
        ("v21 (buoc rong cao)",
         ["phase13-gui/out_bench_v155_v21/b15_result.json"], None),
        ("v22 (buoc rong 0%)",
         ["phase13-gui/out_bench_v155_v22_old_B/b15_result.json",
          "phase13-gui/out_bench_v155_v22old_B/b15_result.json",
          "phase13-gui/out_bench_v155_v22_old/b15_result.json"],
         ["phase13-gui/out_bench_v155_v22/b15_result.json"]),
    ]
'''

NEW = '''    grid = [
        # (nhan model, ket qua [task CU], ket qua [task MOI])
        # O THIEU that cua 2x2 = (v21, task MOI) -> kernel
        # dieniw/ornith-gui-bench-v155-v21new (adapter v21 + task MOI).
        ("v21 (buoc rong cao)",
         ["phase13-gui/out_bench_v155_v21/b15_result.json",
          "phase13-gui/out_bench_v155_B/b15_result.json"],
         ["phase13-gui/out_bench_v155_v21new_B/b15_result.json"]),
        ("v22 (buoc rong 0%)",
         ["phase13-gui/out_bench_v155_v22_old_B/b15_result.json",
          "phase13-gui/out_bench_v155_v22old_B/b15_result.json",
          "phase13-gui/out_bench_v155_v22_old/b15_result.json"],
         ["phase13-gui/out_bench_v155_v22/b15_result.json"]),
    ]
'''

s = io.open(P, encoding="utf-8", newline="").read()
if "v21new_B" in s:
    print("da sua roi")
    sys.exit(0)
if OLD not in s:
    print("FAIL: khong tim thay khoi grid")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua:", P)
