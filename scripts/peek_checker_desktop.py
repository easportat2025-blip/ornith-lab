# -*- coding: utf-8 -*-
"""
peek_checker_desktop.py - in cac ham kiem tra thanh cong cua checker_desktop.py
(ASCII-only source).
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, "phase14-desktop", "tasks", "checker_desktop.py")
s = io.open(p, encoding="utf-8", errors="replace").read()
for m in re.finditer(r"^def [A-Za-z_][A-Za-z0-9_]*\(.*$", s, re.M):
    i = m.start()
    print("---- " + m.group(0))
    print(s[i:i + 520].split("\n\n")[0][:520])
