# -*- coding: utf-8 -*-
"""
patch_t23_confirm_fixed.py - app t23_table_sort (desktop): dat nut Confirm o
vi tri co dinh (duoi man hinh) de policy click duoc (khong bi che boi bang
12 hang).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
TARGETS = ["phase14-desktop/tasks/t23_table_sort.html",
           "phase13-gui/kernel_desktop_bench/apps/t23_table_sort.html"]

OLD = "button{background:#2f6fd0;color:#fff;border:0;border-radius:6px;padding:10px 20px;font-size:15px;cursor:pointer;margin-top:12px}"
NEW = ("button{background:#2f6fd0;color:#fff;border:0;border-radius:6px;"
       "padding:10px 20px;font-size:15px;cursor:pointer;margin-top:12px;"
       "position:fixed;right:20px;bottom:20px}")

n = 0
for rel in TARGETS:
    p = os.path.join(ROOT, rel.replace("/", os.sep))
    if not os.path.exists(p):
        print("   thieu:", rel)
        continue
    s = io.open(p, encoding="utf-8", newline="").read()
    if NEW in s:
        print("   da sua:", rel)
        continue
    if OLD not in s:
        print("   !! khong tim thay CSS trong", rel)
        continue
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
    n += 1
    print("   sua:", rel)
print("=> %d file sua" % n)
