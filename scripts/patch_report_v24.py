# -*- coding: utf-8 -*-
"""
patch_report_v24.py - them muc "SO SANH RECIPE (paired theo task)" vao
report_fixed_suite.py: so model tren CUNG bo task MOI (v21 / v22 / v24) theo
 tung task => thay vi chi so tong win_rate.

Dung ly: 2x2 da chung minh suite co task flaky (B16-A) => tong win_rate an
mat task lat => phai so PAIRED.

Dung: python scripts/patch_report_v24.py
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "report_fixed_suite.py")

BLOCK = '''    # ---- SO SANH RECIPE tren cung bo task (paired theo task)
    _rc = [
        ("B15.5 task MOI",
         "phase13-gui/out_bench_v155_v21new_B/b15_result.json",
         "phase13-gui/out_bench_v155_v22/b15_result.json",
         "phase13-gui/out_bench_v155_v24_B/b15_result.json"),
        ("B15.5 task CU",
         "phase13-gui/out_bench_v155_v21/b15_result.json",
         "phase13-gui/out_bench_v155_v22_old_B/b15_result.json",
         None),
        ("B16-A task MOI",
         "phase13-gui/out_bench_v16_v21/b15_result.json",
         "phase13-gui/out_bench_v16_v22b_B/b15_result.json",
         "phase13-gui/out_bench_v16_v24_B/b15_result.json"),
    ]
    for _lbl, _a, _b, _c in _rc:
        _fs = [os.path.join(ROOT, f.replace("/", os.sep))
               for f in (_a, _b, _c) if f]
        _fs = [f for f in _fs if os.path.exists(f)]
        if len(_fs) < 2:
            continue
        print("=" * 78)
        print("SO SANH RECIPE - %s (paired theo task)" % _lbl)
        _o = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
        for _l in _o.splitlines():
            if ("FLAKY" in _l or "TASK FLAKY" in _l or "cell" in _l
                    or "out_bench" in _l):
                print("      " + _l.rstrip())
        # chay lai de lay dong "task ..." (cmp_cells in dong bang task)
        _o2 = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
        for _l in _o2.splitlines():
            _ls = _l.strip()
            if _ls.startswith("T") and "/" in _ls:
                print("      " + _ls)

'''

ANCHOR = '''    print("LUU Y: chi so so sanh duoc giua CUNG mot suite.'''


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    if "SO SANH RECIPE" in s:
        print("da co -> bo qua")
        return 0
    if ANCHOR not in s:
        print("FAIL: khong tim thay anchor")
        return 1
    s = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("da them muc so sanh recipe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
