# -*- coding: utf-8 -*-
"""show_err.py - in cac dong loi tu file output cua shell (bo ANSI)."""
import io
import re
import sys

path = sys.argv[1]
pats = sys.argv[2:] or ["grpo]", "Error", "Traceback", "line ", "raise", "assert"]
txt = io.open(path, encoding="utf-8", errors="replace").read()
txt = re.sub(r"\x1b\[[0-9;]*m", "", txt)
lines = txt.replace("\r", "\n").split("\n")
hit = [l for l in lines if any(p in l for p in pats)]
for l in hit[-30:]:
    l = l.strip()
    if l:
        print("  " + l[:145])
