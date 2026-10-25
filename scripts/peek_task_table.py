# -*- coding: utf-8 -*-
"""
peek_task_table.py - in mot khoi cua bang TASK trong file bench_*.py (de
viet linter doc dung cau truc).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, sys.argv[1].replace("/", os.sep))
s = io.open(p, encoding="utf-8", errors="replace").read()
key = sys.argv[2] if len(sys.argv) > 2 else "T13_wizard"
i = s.find(key)
print(s[max(0, i - 400):i + 900])
