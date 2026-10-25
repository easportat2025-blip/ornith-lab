# -*- coding: utf-8 -*-
"""
colab_to_kaggle_ds.py - chuyen 1 file .zip (ket qua Colab) thanh 1 DATASET
KAGGLE (de kernel SFT tren Kaggle train duoc) + verify layout.

VI SAO CAN: kernel Kaggle chi mount dataset KAGGLE (khong mount HF) => data
sinh tren Colab (host HF) phai: HF -> local -> 'kaggle datasets create'.

Layout can mount (giong dataset policy-replay):
    traj.jsonl            (moi row: image / instruction / action / task_id / ...)
    <task>_eNN_sNN.png    (anh o ROOT - 'image' trong row la TEN file phang)

Dung:
    python scripts/colab_to_kaggle_ds.py <zip> --slug dieniw/ornith-gui-desktop-replay --acc B
ASCII-only source.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import zipfile
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "phase13-gui", "colab_staging")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--slug", required=True, help="owner/slug tren Kaggle")
    ap.add_argument("--acc", default="B", choices=["A", "B"])
    ap.add_argument("--title", default="Ornith GUI desktop-replay (GT traj)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    zp = a.zip if os.path.isabs(a.zip) else os.path.join(
        ROOT, a.zip.replace("/", os.sep))
    if not os.path.exists(zp):
        print("FAIL: khong ton tai", zp)
        return 1
    d = os.path.join(STAGE, "ds_" + a.slug.replace("/", "_"))
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        z.extractall(d)
    tj = os.path.join(d, "traj.jsonl")
    if not os.path.exists(tj):
        print("FAIL: khong co traj.jsonl trong zip")
        return 1
    rows = [json.loads(l) for l in io.open(tj, encoding="utf-8") if l.strip()]
    pngs = set(f for f in os.listdir(d) if f.lower().endswith(".png"))
    miss = [r.get("image") for r in rows
            if os.path.basename(r.get("image") or "") not in pngs]
    tasks = Counter(r.get("task_id") for r in rows)
    print("== staging: %s" % d)
    print("   n_row=%d | n_png=%d | task=%s" % (len(rows), len(pngs),
                                               dict(tasks)))
    print("   anh thieu trong row: %d" % len(miss))
    if miss:
        print("   first missing: %s" % miss[:3])
        return 1
    meta = {"title": a.title[:50], "id": a.slug,
            "licenses": [{"name": "other"}]}
    with io.open(os.path.join(d, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    if a.dry_run:
        print("== DRY-RUN (khong upload)")
        return 0
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts", "upload_staging.py"),
                        d, "--acc", a.acc], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    print(out[-1500:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
