# -*- coding: utf-8 -*-
"""
fix_n3d.py - them hang so N_3D vao moi ban gui_sft_v23.py.

Loi (22/10): kernel_v24 tren acc B chay toi dong 't3d_rows = t3d_rows[:N_3D]'
roi NameError: name 'N_3D' is not defined -> kernel ERROR sau khi load duoc
tat ca du lieu (traj 972/972, loop-recovery 600/600 ✓).
Hang so nay duoc them vao khi v23 sua recipe (3D 600) nhung quen khai bao.

Fix: them N_3D = 600 ngay canh N_TRAIN/N_TARGETED/N_EVAL.
ASCII-only.
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    "phase13-gui/kernel_v23/gui_sft_v23.py",
    "phase13-gui/kernel_v23b/gui_sft_v23.py",
    "phase13-gui/kernel_v24/gui_sft_v23.py",
    "phase13-gui/kernel_v24b/gui_sft_v23.py",
    "phase13-gui/kernel_v24_B/gui_sft_v23.py",
    "phase14-space/app/project/phase13-gui/kernel_v23/gui_sft_v23.py",
    "phase14-space/_push_docker/app/project/phase13-gui/kernel_v23/gui_sft_v23.py",
]
ANCHOR = "N_EVAL = 120\n"
NEW = "N_EVAL = 120\nN_3D = 600            # 22/10: v23 recipe '3D 600' - thieu khai bao -> NameError\n"


def main():
    for rel in TARGETS:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            print("  skip (khong co): %s" % rel)
            continue
        s = io.open(p, encoding="utf-8").read()
        if "N_3D = " in s:
            print("  skip (da co): %s" % rel)
            continue
        if ANCHOR not in s:
            print("  !! khong tim thay anchor trong %s" % rel)
            continue
        s = s.replace(ANCHOR, NEW, 1)
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("  PATCH: %s" % rel)
    # verify: bien nay co duoc dinh nghia o moi ban khong
    bad = []
    for rel in TARGETS:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding="utf-8").read()
        ok_def = "N_3D = " in s
        ok_use = "t3d_rows[:N_3D]" in s
        if ok_use and not ok_def:
            bad.append(rel)
        print("  %-62s def=%s use=%s" % (rel[-60:], ok_def, ok_use))
    if bad:
        print("\n!! VAN THIEU:", bad)
        return 1
    print("\nOK: moi ban dang dung N_3D deu co dinh nghia")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
