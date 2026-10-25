# -*- coding: utf-8 -*-
"""
peek_t23.py - in khoi code sort + top row cua app t23_table_sort.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, "phase13-gui", "colab_staging", "desktop_replay_in",
                 "t23_table_sort.html")
s = io.open(p, encoding="utf-8", errors="replace").read()
i = s.find("hscore.addEventListener")
print(s[i:i + 900])
