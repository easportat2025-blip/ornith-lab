# -*- coding: utf-8 -*-
"""check_v24b.py - kiem tra moi fix da co trong code v24b se push len acc B."""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "phase13-gui", "kernel_v24b", "gui_sft_v23.py")
s = io.open(P, encoding="utf-8").read()
checks = [
    ("N_3D = 600", "N_3D = 600" in s),
    ("done_rate=0.75", "done_rate=0.75" in s),
    ('families="ALL"', 'families="ALL"' in s),
    ("khong truncate traj [:400]", "traj_rows[:400]" not in s),
    ("loop-recovery dataset", "ornith-gui-synth-recipe" in s),
    ("rec_rows trong train_rows", "+ rec_rows + sp_rows" in s),
    ("loader quet base/", "os.walk(base)" in s),
    ("guard traj >=900", "len(traj_rows) < 900" in s),
    ("policy-replay x2", "pr_rows = pr_rows * 2" in s),
    ("3D cap N_3D", "t3d_rows[:N_3D]" in s),
]
bad = 0
for n, ok in checks:
    print("  %-26s %s" % (n, "PASS" if ok else "FAIL"))
    if not ok:
        bad += 1
print("  ->", "ALL PASS" if not bad else "%d FAIL" % bad)
sys.exit(1 if bad else 0)
