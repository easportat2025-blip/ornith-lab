# -*- coding: utf-8 -*-
"""
patch_publish_key.py - publish_lora.py: fallback sang KAGGLE_KEY khi env
KAGGLE_KEY_A/B khong co (shell thuong dat dat KAGGLE_KEY).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "publish_lora.py")

OLD = '''    keyvar = "KAGGLE_KEY_B" if a.acc == "B" else "KAGGLE_KEY_A"
    ENV["KAGGLE_KEY"] = os.environ.get(keyvar, "")'''
NEW = '''    keyvar = "KAGGLE_KEY_B" if a.acc == "B" else "KAGGLE_KEY_A"
    ENV["KAGGLE_KEY"] = (os.environ.get(keyvar)
                         or os.environ.get("KAGGLE_KEY") or "")'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay khoi key")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da them fallback KAGGLE_KEY")
