"""list_ds_files.py - liet ke TAT CA file cua 1 dataset (co phan trang).

Dung: python scripts/list_ds_files.py <owner/slug> [--json]
"""
import json
import os
import sys

from kaggle.api.kaggle_api_extended import KaggleApi

api = KaggleApi()
api.authenticate()

slug = sys.argv[1]
files = []
token = None
while True:
    if token:
        res = api.dataset_list_files(slug, page_token=token)
    else:
        res = api.dataset_list_files(slug)
    files += [{"name": f.ref, "size": f.total_bytes} for f in res.dataset_files]
    token = getattr(res, "next_page_token", None)
    if not token:
        break
non_png = [f for f in files if not f["name"].lower().endswith(".png")]
print("TONG %d file | %d khong phai png" % (len(files), len(non_png)))
for f in non_png[:25]:
    print("   %-40s %10d" % (f["name"], f["size"]))
dirs = sorted(set(f["name"].split("/")[0] for f in files if "/" in f["name"]))
print("   thu muc:", dirs[:10])
