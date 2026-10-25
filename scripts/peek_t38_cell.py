# -*- coding: utf-8 -*-
"""
peek_t38_cell.py - in cell code cua app t38.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users/Admin/Desktop\New folder"
p = os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks", "t38_recovery.html")
s = io.open(p, encoding="utf-8", errors="replace").read()
i = s.find('id="c0"')
print(repr(s[i - 5:i + 20]))
