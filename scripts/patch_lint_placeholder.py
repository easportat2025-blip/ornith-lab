# -*- coding: utf-8 -*-
"""
patch_lint_placeholder.py - lint_task_static.py: literal co placeholder
(VD 'Selected: TARGETCOUNT / TARGETCOUNT') phai duoc so bang regex
(placeholder -> .*) truoc khi bao loi S2 (tranh false positive).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "lint_task_static.py")

OLD = '''            if lit in html:
                continue
            if any(lit in h for h in (checker,)):
                continue
            # co phai la placeholder render duoc?
            if PH_RX.fullmatch(lit):
                continue
            problems.append((tid, "S2 instruction nhoi %r nhung khong co trong "
                                 "HTML (task do co do sai thu do?)" % lit))'''

NEW = '''            if lit in html:
                continue
            if any(lit in h for h in (checker,)):
                continue
            # co phai la placeholder render duoc?
            if PH_RX.fullmatch(lit):
                continue
            # literal CHUA placeholder (VD 'Selected: TARGETCOUNT / ...')
            # -> so bang regex: placeholder -> .*
            if PH_RX.search(lit):
                _pat = PH_RX.sub(".*", lit)
                _pat = re.escape(_pat).replace("\\\\.\\\\*", ".*")
                try:
                    if re.search(_pat, html, re.S) or re.search(_pat, checker,
                                                               re.S):
                        continue
                except Exception:
                    pass
            problems.append((tid, "S2 instruction nhoi %r nhung khong co trong "
                                 "HTML (task do co do sai thu do?)" % lit))'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay khoi S2")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua xu ly literal co placeholder")
