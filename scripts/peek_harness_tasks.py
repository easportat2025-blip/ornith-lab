# -*- coding: utf-8 -*-
"""
peek_harness_tasks.py - in bang task cua harness (desktop) de lay task_id +
instruction cho 5 app desktop (can cho policy-replay).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, "phase14-desktop", "harness.py")
s = io.open(p, encoding="utf-8", errors="replace").read()
i = s.find("BUILTIN_TASKS")
print(s[i:i + 2600])
