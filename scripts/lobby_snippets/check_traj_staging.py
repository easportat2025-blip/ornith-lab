# -*- coding: utf-8 -*-
"""Kiem tra cac staging traj: so row, co zip khong, id dataset."""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
for d in ("phase13-gui/traj_ds_staging", "phase13-gui/traj_flat_staging",
          "phase13-gui/traj_local_staging", "phase13-gui/traj_zip_staging"):
    p = os.path.join(ROOT, d.replace("/", os.sep))
    if not os.path.isdir(p):
        print("%-38s (khong co)" % d)
        continue
    for sub in sorted(os.listdir(p)):
        sp = os.path.join(p, sub)
        if not os.path.isdir(sp):
            continue
        files = sorted(os.listdir(sp))
        tj = os.path.join(sp, "traj.jsonl")
        n = done = 0
        if os.path.exists(tj):
            for line in io.open(tj, encoding="utf-8", errors="replace"):
                if line.strip():
                    n += 1
                    if '"DONE"' in line:
                        done += 1
        zips = [f for f in files if f.endswith(".zip")]
        mid = ""
        mp = os.path.join(sp, "dataset-metadata.json")
        if os.path.exists(mp):
            try:
                mid = (json.load(io.open(mp, encoding="utf-8-sig")).get("id") or "")
            except Exception:
                mid = "?"
        ndir = len([f for f in files if os.path.isdir(os.path.join(sp, f))])
        print("%-30s %-46s row=%-5s DONE=%-4s zip=%-18s dirs=%d id=%s"
              % (d, sub, n, done, ",".join(zips) or "-", ndir, mid))
