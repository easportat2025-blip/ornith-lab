# -*- coding: utf-8 -*-
"""
patch_colab_nolaunch.py - colab_run_task.py: them --no-launch (chi poll + tai
ket qua, KHONG tao session/launch lai) - dung khi job da chay tren VM.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_run_task.py")

s = io.open(P, encoding="utf-8", newline="").read()
if "--no-launch" in s:
    print("da co --no-launch")
    sys.exit(0)
s = s.replace('''    ap.add_argument("--download", action="append", default=[],''',
              '''    ap.add_argument("--no-launch", action="store_true",
                    help="job da chay tren VM: chi poll + tai ket qua")
    ap.add_argument("--download", action="append", default=[],''', 1)
OLD = '''    # 2) tao session (neu chua co) + launch - trong 1 cua so token nho
    with Swap(a.acc):'''
NEW = '''    # 2) tao session (neu chua co) + launch - trong 1 cua so token nho
    if a.no_launch:
        print("[runner] --no-launch: bo qua tao/launch (job da chay tren VM)")
        return _poll_and_fetch(a, cpath)
    with Swap(a.acc):'''
if OLD not in s:
    print("FAIL: khong tim thay khoi launch")
    sys.exit(1)
s = s.replace(OLD, NEW, 1)

# tach phan poll+fetch thanh ham de goi lai duoc
OLD2 = '''    # 3) poll (swap nho moi 60s)
    t0 = time.time()'''
NEW2 = '''    return _poll_and_fetch(a, cpath)


def _poll_and_fetch(a, cpath):
    """Poll (swap nho moi 60s) roi tai log + ket qua (swap nho)."""
    # 3) poll (swap nho moi 60s)
    t0 = time.time()'''
if OLD2 not in s:
    print("FAIL: khong tim thay khoi poll")
    sys.exit(1)
s = s.replace(OLD2, NEW2, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da them --no-launch")
