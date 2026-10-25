# -*- coding: utf-8 -*-
"""
patch_b17_distinct.py - T38: 4 CODE phai KHAC NHAU (neu trung, hang target
khong xac dinh duoc bang index -> policy click sai hang).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "build_b17_apps.py")

OLD = '''const CODES=[R(["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"]),
    R(["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"]),
    R(["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"]),
    R(["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"])];'''

NEW = '''const POOL=["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"];
const CODES=POOL.slice().sort(()=>Math.random()-0.5).slice(0,4);'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay CODES")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da doi CODES -> 4 ma KHAC NHAU")
