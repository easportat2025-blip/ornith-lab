# -*- coding: utf-8 -*-
"""
patch_b17_confirm.py - B17-2 (scroll code): dat nut Confirm o vi tri co dinh
(duoi man hinh) de policy click duoc sau khi sort (khong bi che).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "build_b17_apps.py")

OLD = '''<button id="sub">Confirm</button>'''
NEW = '''<button id="sub" style="position:fixed;right:20px;bottom:20px">Confirm</button>'''

s = io.open(P, encoding="utf-8", newline="").read()
if NEW in s:
    print("da sua roi")
    sys.exit(0)
if OLD not in s:
    print("FAIL: khong tim thay nut Confirm")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua: Confirm -> position fixed")
