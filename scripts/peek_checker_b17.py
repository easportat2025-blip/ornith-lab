# -*- coding: utf-8 -*-
"""
peek_checker_b17.py - in check_t30 (checker cua GLM cho B17) de xem DOM id.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, "phase14-desktop", "tasks", "checker_desktop.py")
# GLM co the dat checker o bench_b17/tasks/checker.py
for cand in (p, os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks", "checker.py"),
             os.path.join(ROOT, "phase13-gui", "bench_b17", "checker.py")):
    if os.path.exists(cand):
        p = cand
        break
s = io.open(p, encoding="utf-8", errors="replace").read()
i = s.find("def check_t30")
print("file:", p)
print(s[i:i + 1400] if i >= 0 else "khong co check_t30")
