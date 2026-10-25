# -*- coding: utf-8 -*-
"""
patch_watchdog_running_live.py - dem session GPU bang trang thai SONG thay vi
state cache (state co the CU).

LY DO (22/10, @MiMo): `running` dem trong `qstate` (cache) => kernel da
COMPLETE nhung state chua cap nhat van duoc tinh la dang chay => watchdog
thong bao "da du 2 session GPU" 40 pham lien tuc TRONG KHI 0 kernel dang
chay (da verify bang `kaggle kernels list` + `kernels status`) => bay kernel
(b3) bi chan VO HAN.
=> FIX: voi muc ma state noi "RUNNING", hoi trang thai SONG (status_of) truoc
khi tinh vao `running`; dong thoi cap nhat state.
=> CHI hoi status cho <=3 muc (nho) => khong lo rate-limit.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "watchdog.py")

OLD = '''    running = 0
    for item in q:
        kid = item.get("id")
        st = qstate.get(kid, {}).get("status")
        if st in ("RUNNING", "QUEUED", "PENDING"):
            running += 1
'''

NEW = '''    running = 0
    for item in q:
        kid = item.get("id")
        st = qstate.get(kid, {}).get("status")
        if st in ("RUNNING", "QUEUED", "PENDING"):
            # FIX 22/10 (MiMo): state cache CO THE CU (kernel da COMPLETE nhung
            # state chua cap nhat) => 'running' dem sai => "da du 2 session
            # GPU" 40' lien tuc trong khi 0 kernel dang chay => bay kernel
            # bi chan vo han. => hoi TRANG THAI SONG truoc khi tinh.
            try:
                live = (status_of(kid) or "").upper()
            except Exception:
                live = ""
            if live in ("RUNNING", "QUEUED", "PENDING"):
                running += 1
            else:
                qstate.setdefault(kid, {})["status"] = live or "UNKNOWN"
'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay khoi dem running")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua dem session GPU theo trang thai song")
