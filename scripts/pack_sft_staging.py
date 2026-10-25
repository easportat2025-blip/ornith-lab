# -*- coding: utf-8 -*-
"""
pack_sft_staging.py - dong goi staging du lieu SFT thanh ZIP + verify anh.

Ly do (22/10): staging 'ornith-gui-synth-recipe' gom 600 file rong
(images/*.png + traj.jsonl). Kaggle CLI **BO QUA thu muc khi upload dataset**
(bai hoc da ghi trong ferry_dataset.py) => dataset se chi con traj.jsonl,
KHONG co anh => loader resolve khong duoc anh => fail im lang luc train.
=> phai upload dang ZIP (anh nam trong zip, loader giai nen roi resolve
ext/<duong dan>).

Script nay:
  1) tao <staging>/<ten>_bundle.zip chua traj.jsonl + images/**
  2) VERIFY: moi row trong traj.jsonl phai co anh tuong ung TRONG zip
  3) in lenh upload

Dung:
    python scripts/pack_sft_staging.py phase13-gui/synth_recipe_ds_staging/khoadangnguye__ornith-gui-synth-recipe
ASCII-only source.
"""
import argparse
import io
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("staging")
    ap.add_argument("--top", default=None, help="ten top-dir trong zip (mac dinh: giong ten staging)")
    a = ap.parse_args()
    p = a.staging if os.path.isabs(a.staging) else os.path.join(
        ROOT, a.staging.replace("/", os.sep))
    if not os.path.isdir(p):
        print("KHONG TON TAI:", p)
        return 2
    tj = os.path.join(p, "traj.jsonl")
    if not os.path.exists(tj):
        print("khong co traj.jsonl trong staging")
        return 2
    rows = [json.loads(l) for l in io.open(tj, encoding="utf-8") if l.strip()]
    top = a.top or os.path.basename(p.rstrip("/\\"))
    zp = os.path.join(p, "%s_bundle.zip" % top)
    n_img = 0
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tj, "%s/traj.jsonl" % top)
        for fn in sorted(os.listdir(p)):
            if not fn.endswith(".zip"):
                continue
            if os.path.abspath(fn) == os.path.abspath(zp):
                continue
            z.write(os.path.join(p, fn), "%s/%s" % (top, fn))
        imdir = os.path.join(p, "images")
        if os.path.isdir(imdir):
            for fn in sorted(os.listdir(imdir)):
                z.write(os.path.join(imdir, fn), "%s/images/%s" % (top, fn))
                n_img += 1
    print("zip: %s (%.1f MB, %d anh)"
          % (os.path.relpath(zp, ROOT), os.path.getsize(zp) / 1048576.0, n_img))

    # ---- VERIFY: moi row phai co anh trong zip
    with zipfile.ZipFile(zp) as z:
        names = set(z.namelist())
        missing = []
        for r in rows:
            rel = r.get("image") or ""
            if ("%s/%s" % (top, rel)) not in names:
                missing.append(rel)
    print("row: %d | thieu anh trong zip: %d" % (len(rows), len(missing)))
    for m in missing[:5]:
        print("   thieu:", m)
    if missing:
        print("=> FAIL: co row tro toi anh khong co trong zip")
        return 1

    # ---- VERIFY theo DUNG logic loader cua kernel (3 ung vien):
    #   1) base/rel   2) ext/rel   3) basename bat ky trong ext
    # Loader BO QIA ROW khong resolve duoc (khong loi) => phai kiem het.
    import shutil
    import tempfile
    ext = tempfile.mkdtemp(prefix="sim_ext_")
    try:
        with zipfile.ZipFile(zp) as z:
            z.extractall(ext)
        n_ok = 0
        n_bad = []
        for r in rows:
            rel = r.get("image") or ""
            p1 = os.path.join(p, rel.replace("/", os.sep))
            p2 = os.path.join(ext, rel.replace("/", os.sep))
            hit = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else None)
            if hit is None:
                name = os.path.basename(rel)
                for root, _dd, files in os.walk(ext):
                    if name in files:
                        hit = os.path.join(root, name)
                        break
            if hit:
                n_ok += 1
            else:
                n_bad.append(rel)
        print("resolve theo logic loader: %d/%d row" % (n_ok, len(rows)))
        for b in n_bad[:5]:
            print("   khong resolve:", b)
        if n_bad:
            print("=> FAIL: loader se BO QIA %d row (im lang, khong loi)" % len(n_bad))
            return 1
    finally:
        shutil.rmtree(ext, ignore_errors=True)
    mp = os.path.join(p, "dataset-metadata.json")
    if os.path.exists(mp):
        md = json.load(io.open(mp, encoding="utf-8-sig"))
        print("slug: %s" % md.get("id"))
    print()
    print("=== LENH UPLOAD ===")
    print('  kaggle datasets create -p "%s"   # hoac version neu da ton tai'
          % os.path.relpath(p, ROOT))
    print("  # LUOI: bo thu muc images/ (de khong loi) - giu lai traj.jsonl + zip")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
