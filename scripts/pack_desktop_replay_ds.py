# -*- coding: utf-8 -*-
"""
pack_desktop_replay_ds.py - dong goi dataset KAGGLE cho data desktop-replay:
    traj.jsonl                 (234 row)
    desktop_replay_images.zip  (264 anh PNG o GOC zip)
    dataset-metadata.json

LY DO (22/10, @MiMo): Kaggle CLI BO QIA thu muc/anh khi upload dataset (chi
upload duoc file) => phai DONG GOI anh vao ZIP (cung cach nhu dataset R2).
Loader (load_ds_rows) tu giiai nen ZIP va resolve duoc 'image' o goc zip.
=> upload phai chay o DUONG DAN KHONG CO DAU CACH (CLI Windows vo loi voi
   "New folder").

Dung:
    python scripts/pack_desktop_replay_ds.py
    cd /d C:\mimo_ds\desktop_replay && kaggle datasets create -p .
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
SLUG = "dieniw/ornith-gui-desktop-replay"
TITLE = "Ornith GUI desktop-replay GT (234 row)"


def main():
    if not os.path.exists(SRC_ZIP):
        print("FAIL: thieu", SRC_ZIP)
        return 1
    shutil.rmtree(os.path.dirname(DST), ignore_errors=True)
    os.makedirs(DST, exist_ok=True)
    rows = []
    with zipfile.ZipFile(SRC_ZIP) as z:
        names = z.namelist()
        with z.open("traj.jsonl") as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8"):
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        keep = set(os.path.basename(r["image"]) for r in rows)
        zp = os.path.join(DST, "desktop_replay_images.zip")
        n_png = 0
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as zo:
            for n in names:
                if n.lower().endswith(".png") and os.path.basename(n) in keep:
                    zo.writestr(os.path.basename(n), z.read(n))
                    n_png += 1
        with z.open("traj.jsonl") as fh:
            data = fh.read()
    with io.open(os.path.join(DST, "traj.jsonl"), "wb") as fh:
        fh.write(data)
    meta = {"title": TITLE[:50], "id": SLUG, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(DST, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("staging : %s" % DST)
    print("   traj.jsonl: %d row | images.zip: %d anh (%.1f MB)"
          % (len(rows), n_png,
             os.path.getsize(zp) / 1048576.0))
    print("=> lenh upload (KHONG duong dan co dau cach):")
    print('   cd /d C:\\mimo_ds\\desktop_replay && kaggle datasets create -p .')
    return 0


if __name__ == "__main__":
    sys.exit(main())
