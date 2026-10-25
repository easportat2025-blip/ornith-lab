# -*- coding: utf-8 -*-
"""patch_offline_paths.py - dua duong dan cua kernel train ve ENV (de chay
LOCAL tren may RTX khong internet).

WORK      <- ORNITH_WORK   (mac dinh /kaggle/working)
ORN (base)<- ORNITH_BASE   (mac dinh /tmp/ornbase)
dataset root <- ORNITH_INPUT (mac dinh /kaggle/input)

Ap dung cho kernel_v22 + kernel_v23 (va moi kernel train sau nay: nhớ dùng
WORK/ORN/INPUT_ROOT thay vi duong dan hard-code).
"""
import io
import os

TARGETS = [
    "phase13-gui/kernel_v22/gui_sft_v22.py",
    "phase13-gui/kernel_v23/gui_sft_v23.py",
]

HEAD = '''# --- duong dan: ENV de chay LOCAL / OFFLINE tren may RTX (khong internet) ---
WORK = os.environ.get("ORNITH_WORK", "/kaggle/working")
ORN = os.environ.get("ORNITH_BASE", "/tmp/ornbase")
INPUT_ROOT = os.environ.get("ORNITH_INPUT", "/kaggle/input")
'''

for p in TARGETS:
    if not os.path.exists(p):
        print("skip (khong co):", p)
        continue
    s = io.open(p, encoding="utf-8").read()
    if "ORNITH_INPUT" in s:
        print("da co env paths:", p)
        continue
    # 1) thay 2 hang WORK/ORN
    s = s.replace('WORK = "/kaggle/working"', "# (xem ENV o duoi)")
    s = s.replace('ORN = "/tmp/ornbase"', "# (xem ENV o duoi)")
    # 2) chen khoi ENV ngay sau cac hang do
    anchor = "# (xem ENV o duoi)"
    first = s.find(anchor)
    s = s[:first] + HEAD + s[first + len(anchor):]
    # 3) thay "/kaggle/input" -> INPUT_ROOT
    s = s.replace('"/kaggle/input"', "INPUT_ROOT")
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", p)
    for l in s.splitlines()[:24]:
        if "ORNITH_" in l or "INPUT_ROOT" in l:
            print("   ", l.strip()[:80])
