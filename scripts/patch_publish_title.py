# -*- coding: utf-8 -*-
"""
patch_publish_title.py - publish_lora.py: cat title toi da 50 ky tu (Kaggle
yeu cau 6..50) va bo dau/cuoi thua.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "publish_lora.py")

OLD = '''    meta = {"title": a.title or ("Ornith GUI LoRA %s" % a.slug.split("/")[-1]),
            "id": a.slug, "licenses": [{"name": "other"}]}'''
NEW = '''    _t = (a.title or ("Ornith GUI LoRA %s" % a.slug.split("/")[-1])).strip()
    if not (6 <= len(_t) <= 50):   # Kaggle: title 6..50 ky tu
        _t = _t[:50].rstrip(" -_,")
        if len(_t) < 6:
            _t = "Ornith GUI LoRA"
        print("   [FIX] title cat con %d ky tu: %s" % (len(_t), _t))
    meta = {"title": _t, "id": a.slug, "licenses": [{"name": "other"}]}'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay khoi title")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da them cat title 6..50")
