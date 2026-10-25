# -*- coding: utf-8 -*-
"""
patch_split_eps.py - cho phep gan so EPISODE khac nhau cho tung split
desktop-bench (mac dinh 20). b3 = 5 episode (validate pipeline nhanh: acc B
chi con ~12.4h GPU quota, 6 task x 20 ep x 16 buoc = 6-11h).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "phase13-gui", "make_desktop_bench_split.py")

OLD_EP = """    src = src.replace('os.environ.get("DB_EPISODES", "20")',
                      'os.environ.get("DB_EPISODES", "20")')
"""
NEW_EP = """    # FIX 22/10 (MiMo): so episode co the gian khac nhau (b3 = 5 de validate
    # nhanh; acc B con ~12.4h GPU quota).
    eps = EPISODES.get(tag, 20)
    src = src.replace('os.environ.get("DB_EPISODES", "20")',
                      'os.environ.get("DB_EPISODES", "%d")' % eps)
"""

OLD_DICT = "for tag, (tasks, acc, dsmap) in SPLITS.items():"
NEW_DICT = "for tag, (tasks, acc, dsmap) in SPLITS.items():"

s = io.open(P, encoding="utf-8", newline="").read()
if "EPISODES = {" in s:
    print("da sua roi")
    sys.exit(0)
if OLD_EP not in s:
    print("FAIL: khong tim thay khoi episodes")
    sys.exit(1)
s = s.replace(OLD_EP, NEW_EP, 1)
# them dict EPISODES ngay truoc vong for
anchor = "for tag, (tasks, acc, dsmap) in SPLITS.items():"
eps_dict = ('# FIX 22/10 (MiMo): b3 chay 5 episode/task (validate nhanh).\n'
            'EPISODES = {"b3": 5}\n')
s = s.replace(anchor, eps_dict + anchor, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da sua:", P)
