# -*- coding: utf-8 -*-
"""
patch_cmp_labels.py - sua nhan "FLAKY" trong cmp_cells.py cho chinh xac:
  - cung model + cung task (2 lan chay) => task "KHAC" = co nhiu ENV (flaky)
  - KHAC model (so recipe) => task "KHAC" = model that tot hon
=> nhan chung "KHAC" + ghi chu ro nghia, tranh bi doc nham la nhiu.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "cmp_cells.py")

s = io.open(P, encoding="utf-8", newline="").read()
old1 = '''            line += "   <== FLAKY (khac giua cac lan chay)"'''
new1 = '''            line += "   <== KHAC"'''
old2 = '''    print("=> TASK FLAKY: %s" % (", ".join(flaky) if flaky else "(khong co)"))
    print("=> nen so SANH THEO TASK (paired) cho suite co task flaky; "
          "tong win_rate se an mat 2 task lat")'''
new2 = '''    print("=> TASK KHAC GIUA 2 LAN CHAY: %s"
          % (", ".join(flaky) if flaky else "(khong co)"))
    print("=> y nghia: cung model+cung task => nhiu ENV (flaky); "
          "khac model => model that tot hon tren task do")
    print("=> nen so SANH THEO TASK (paired); tong win_rate se an mat "
          "thay doi tren tung task")'''
if old1 not in s or old2 not in s:
    print("FAIL: khong tim thay khoi can sua")
    sys.exit(1)
s = s.replace(old1, new1, 1).replace(old2, new2, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da sua nhan trong cmp_cells.py")
