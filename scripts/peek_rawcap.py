# -*- coding: utf-8 -*-
"""
peek_rawcap.py - tim moi noi cat 'raw' (gioi han ky tu) trong 1 file .py
(ASCII-only source).
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = sys.argv[1]
if not os.path.isabs(p):
    p = os.path.join(ROOT, p.replace("/", os.sep))
s = io.open(p, encoding="utf-8", errors="replace").read()
for i, line in enumerate(s.split("\n"), 1):
    if re.search(r"\[:\s*\d{2,5}\s*\]", line) and re.search(
            r"raw|ans|prose|text|think", line, re.I):
        print("L%-5d %s" % (i, line.strip()[:118]))
