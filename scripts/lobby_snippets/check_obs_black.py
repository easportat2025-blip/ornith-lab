# -*- coding: utf-8 -*-
"""check_obs_black.py - kiem anh quan sat (obs) cua desktop-bench co bi DEN khong
(=> model mu, action la doan) + thong ke raw 'completely black' theo task."""
import io
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
from PIL import Image

for lbl, d in (("A", "phase13-gui/out_desktop_bench_a/desktop_bench"),
               ("B2", "phase13-gui/out_desktop_bench_b2/desktop_bench")):
    p = os.path.join(ROOT, d.replace("/", os.sep), "desktop_result.json")
    r = json.load(io.open(p, encoding="utf-8"))
    print("=" * 76)
    print(lbl, "by_task:", json.dumps(r.get("by_task"), ensure_ascii=False)[:420])
    eps = r.get("episodes") or []
    black = sum(1 for e in eps if "completely black" in str(e.get("raw_first") or ""))
    print("  ep co raw 'completely black':", black, "/", len(eps))
    c = Counter(e.get("task_id") for e in eps
                if "completely black" in str(e.get("raw_first") or ""))
    print("  theo task:", dict(c))
    obs = []
    for root, _dd, files in os.walk(os.path.join(ROOT, d.replace("/", os.sep))):
        for f in files:
            if f.endswith(".png"):
                obs.append(os.path.join(root, f))
    obs = obs[:10]
    if not obs:
        print("  khong tim thay .png trong", d)
    for o in obs:
        try:
            im = Image.open(o).convert("L")
            dark = sum(1 for px in im.getdata() if px < 12) / float(im.size[0] * im.size[1])
            print("   %-40s size=%s min/max=%s frac_dark=%.2f" % (
                os.path.basename(o), im.size, im.getextrema(), dark))
        except Exception as e:
            print("   ", os.path.basename(o), "ERR", e)
