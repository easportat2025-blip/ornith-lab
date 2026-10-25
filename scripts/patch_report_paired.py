# -*- coding: utf-8 -*-
"""
patch_report_paired.py - them muc "DO LAP LAI (cung cell, 2 acc)" vao
report_fixed_suite.py: so PAIRED theo task + danh dau task FLAKY.

Y do: tong win_rate che mat 2 task lat co (da do: B16-A 2 task flaky,
B15.5 0 task flaky) => quyet dinh recipe phai dua vao bang per-task.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "report_fixed_suite.py")

PAIRS = '''    print("=" * 78)
    print("DO LAP LAI (CUNG 1 CELL, 2 ACC) - so PAIRED theo task:")
    _pairs = [
        ("B15.5 (v22, task MOI)",
         ["phase13-gui/out_bench_v155_v22/b15_result.json",
          "phase13-gui/out_bench_v155_v22_b/b15_result.json"]),
        ("B16-A (v22, task MOI)",
         ["phase13-gui/out_bench_v16_v22/b15_result.json",
          "phase13-gui/out_bench_v16_v22b_B/b15_result.json"]),
    ]
    for _lbl, _fs in _pairs:
        _fs = [os.path.join(ROOT, f.replace("/", os.sep)) for f in _fs]
        _fs = [f for f in _fs if os.path.exists(f)]
        if len(_fs) < 2:
            print("   %-22s (chua co 2 lan chay de so sanh)" % _lbl)
            continue
        print("   --- %s" % _lbl)
        _o = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
        for _l in _o.splitlines():
            if ("FLAKY" in _l or "TASK FLAKY" in _l or "cell" in _l
                    or "out_bench" in _l):
                print("      " + _l.rstrip())
'''

ANCHOR = '''    print("LUU Y: chi so so sanh duoc giua CUNG mot suite.'''


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    if "DO LAP LAI (CUNG 1 CELL" in s:
        print("da co -> bo qua")
        return 0
    if ANCHOR not in s:
        print("FAIL: khong tim thay anchor")
        return 1
    s = s.replace(ANCHOR, PAIRS + ANCHOR, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("da them muc so-paired vao:", P)
    return 0


if __name__ == "__main__":
    sys.exit(main())
