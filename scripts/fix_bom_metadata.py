# -*- coding: utf-8 -*-
"""fix_bom_metadata.py - bo UTF-8 BOM trong dataset-metadata.json (PowerShell 5.1
`-Encoding utf8` them BOM -> Kaggle CLI parse loi "Unexpected UTF-8 BOM").

Sua moi file .ps1 (de lan sau khong them BOM nua) + sua file json dang co.
"""
import glob
import io
import json
import os

n = 0
for p in glob.glob("scripts/*.ps1"):
    s = io.open(p, encoding="utf-8", errors="replace").read()
    if "dataset-metadata.json" not in s:
        continue
    s2 = s.replace("-Encoding utf8", "-Encoding ascii")
    if s2 != s:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s2)
        print("ps1 -> ascii:", p)
        n += 1

for p in glob.glob("scripts/*/dataset-metadata.json") + \
        glob.glob("phase13-gui/*/dataset-metadata.json"):
    raw = io.open(p, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        io.open(p, "wb").write(raw[3:])
        print("bo BOM:", p)
        n += 1
print("tong sua:", n)
