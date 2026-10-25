# -*- coding: utf-8 -*-
"""
fix_desktop_replay_paths.py - sua duong dan 'image' trong traj.jsonl cho
khop voi layout THAT cua dataset Kaggle.

LY DO (22/10, @MiMo): khi upload dataset, Kaggle CLI dua cac file PNG vao
thu muc con TEN DATASET ("desktop_replay_images/") => rows tro ten phang
("T20_2048_e00_s00.png") => loader resolve base/<ten> KHONG tim thay =>
ANH KHONG RESOLVE (loi im lang, dung lo 'silent-drop' cua dataset).
=> sua rows thanh "desktop_replay_images/<ten>.png" (khop ca 2 layout:
   Kaggle bo thu muc con) va re-upload bang 'datasets version'.

Dung:
    python scripts/fix_desktop_replay_paths.py
    cd /d C:\\mimo_ds\\desktop_replay && kaggle datasets version -p .
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
SRC_ZIP = os.path.join(ROOT, "phase13-gui", "colab_out", "desktop_replay.zip")
DST = r"C:\mimo_ds\desktop_replay"
SUBDIR = "desktop_replay_images"
SLUG = "dieniw/ornith-gui-desktop-replay"


def main():
    if not os.path.exists(SRC_ZIP):
        print("FAIL: thieu", SRC_ZIP)
        return 1
    shutil.rmtree(os.path.dirname(DST), ignore_errors=True)
    os.makedirs(os.path.join(DST, SUBDIR), exist_ok=True)
    rows = []
    with zipfile.ZipFile(SRC_ZIP) as z:
        with z.open("traj.jsonl") as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8"):
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        keep = set(os.path.basename(r["image"]) for r in rows)
        n = 0
        for nm in z.namelist():
            if nm.lower().endswith(".png") and os.path.basename(nm) in keep:
                with open(os.path.join(DST, SUBDIR, os.path.basename(nm)),
                          "wb") as out:
                    out.write(z.read(nm))
                n += 1
    n_fix = 0
    for r in rows:
        b = os.path.basename(r["image"])
        new = "%s/%s" % (SUBDIR, b)
        if r["image"] != new:
            r["image"] = new
            n_fix += 1
    with io.open(os.path.join(DST, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {"title": "Ornith GUI desktop-replay GT (234 row)",
            "id": SLUG, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(DST, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("staging : %s" % DST)
    print("   %d row | %d anh | %d duong dan da sua" % (len(rows), n, n_fix))
    print("   vi du image: %s" % rows[0]["image"])
    print("=> upload: cd /d C:\\mimo_ds\\desktop_replay && "
          "kaggle datasets version -p .")
    return 0


if __name__ == "__main__":
    sys.exit(main())
