# -*- coding: utf-8 -*-
"""
patch_report_dup.py - bo in trung trong muc "SO SANH RECIPE" (2 vong loc in
cung mot dong task).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "report_fixed_suite.py")

OLD = '''        _o = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
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

NEW = '''        _o = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
        for _l in _o.splitlines():
            _ls = _l.strip()
            if ("TASK FLAKY" in _ls or "cell" in _ls or "out_bench" in _ls
                    or (_ls.startswith("T") and "/" in _ls)):
                print("      " + _ls)
'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay khoi can sua")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua in trung")
