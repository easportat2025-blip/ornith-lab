# -*- coding: utf-8 -*-
"""fetch_dataset_files.py - tai dataset bang PYTHON API (CLI hay treo khi output
bị redirect) - giu duy ten file, khong giai nen (Kaggle tu giai nen zip).

Dung: python scripts/fetch_dataset_files.py <slug> <dest> [--extract] [--only .whl]
"""
import argparse
import os
import sys
import zipfile

from kaggle.api.kaggle_api_extended import KaggleApi

ap = argparse.ArgumentParser()
ap.add_argument("slug")
ap.add_argument("dest")
ap.add_argument("--extract", action="store_true")
ap.add_argument("--only", default="")
a = ap.parse_args()

api = KaggleApi()
api.authenticate()
os.makedirs(a.dest, exist_ok=True)
print("tai", a.slug, "->", a.dest, flush=True)
api.dataset_download_files(a.slug, path=a.dest, unzip=a.extract, quiet=False)
files = sorted(os.listdir(a.dest))
if a.only:
    for f in files:
        p = os.path.join(a.dest, f)
        if os.path.isfile(p) and not f.lower().endswith(a.only.lower()):
            os.remove(p)
    files = sorted(os.listdir(a.dest))
print("xong:", len(files), "file")
for f in files[:6]:
    print("   ", f)
