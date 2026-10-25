# -*- coding: utf-8 -*-
"""
pack_synth_s11_ds.py - dong goi dataset KAGGLE cho synth-s11 (S11/S12/S13)
theo layout DA CHUNG MINH (R2 + desktop-replay): traj.jsonl (anh FLAT) +
images.zip (anh o GOC zip) + dataset-metadata.json.

LY DO (22/10, @MiMo): Kaggle CLI BO QUA thu muc 'images/' khi upload dataset
=> anh phai dong goi vao ZIP; rows phai tro ten phang (loader tu giai nen
ZIP vao ext/ va resolve duoc).

Dung:
    python scripts/pack_synth_s11_ds.py
    cd /d C:\\mimo_ds\\synth_s11 && kaggle datasets version -p .
ASCII-only source.
"""
import io
import json
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
SRC = os.path.join(ROOT, "phase13-gui", "s11_ds_staging",
                   "khoadangnguye__ornith-gui-synth-s11")
DST = r"C:\mimo_ds\synth_s11"
SLUG = "khoadangnguye/ornith-gui-synth-s11"


def main():
    tj = os.path.join(SRC, "traj.jsonl")
    imgdir = os.path.join(SRC, "images")
    if not (os.path.isfile(tj) and os.path.isdir(imgdir)):
        print("FAIL: thieu traj.jsonl hoac images/")
        return 1
    shutil.rmtree(os.path.dirname(DST), ignore_errors=True)
    os.makedirs(DST, exist_ok=True)
    rows = [json.loads(l) for l in io.open(tj, encoding="utf-8") if l.strip()]
    n_fix = 0
    for r in rows:
        b = os.path.basename(r["image"])
        if r["image"] != b:
            r["image"] = b
            n_fix += 1
    with io.open(os.path.join(DST, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_png = 0
    with zipfile.ZipFile(os.path.join(DST, "images.zip"), "w",
                        zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(imgdir):
            if f.lower().endswith(".png"):
                z.write(os.path.join(imgdir, f), f)
                n_png += 1
    meta = {"title": "Ornith GUI synth S11 (530 row)", "id": SLUG,
            "licenses": [{"name": "other"}]}
    with io.open(os.path.join(DST, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("staging : %s" % DST)
    print("   %d row | %d anh (images.zip) | %d duong dan da sua (flat)"
          % (len(rows), n_png, n_fix))
    print("=> upload: cd /d C:\\mimo_ds\\synth_s11 && "
          "kaggle datasets version -p . -m \"pack images into zip (fix paths)\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
