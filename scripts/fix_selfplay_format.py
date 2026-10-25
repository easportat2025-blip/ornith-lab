# -*- coding: utf-8 -*-
"""fix_selfplay_format.py - sua format selfplay (TASK GĐ-A cua @DeepSeek).

Van de thuc te (da xac minh tren dataset khoadangnguye/gui-selfplay, file
traj.jsonl 118 row = phase13-gui/selfplay/gui-selfplay-v21.jsonl):
  1. Row win=False (traj tu choi THAT BAI) van nam trong data -> lam GT sai
     (eval + train deu hoc tu hanh dong dan den that bai).
  2. Action 'CLICK x y' nhung THIEU field 'point' -> evaluate() khong so
     sanh duoc toa do (dung .get + fallback good=True -> acc_selfplay_sub
     GIA, khong kiem tra thuc toa do).

Sua: drop row win=False; bo sung point=[x,y] tu chuoi action (giu nguyen
action + instruction + anh).

Dataset MOI: khoadangnguye/ornith-gui-selfplay-v2 (KHONG sua dataset dang chay)
  - traj.jsonl top-level (loader doc truc tiep, khong qua zip)
  - shots/ -> upload bang dir_mode='zip' -> shots.zip; loader giai nen vao
    ext/ -> resolve ext/rel nhu binh thuong
Verify sau upload: hash traj.jsonl khop + audit_datasets.audit_one = OK.

Chay: python scripts/fix_selfplay_format.py [--no-upload]
ASCII-only source. KHONG push kernel.
"""
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

TMP = os.path.join(os.environ.get("TEMP", "."), "selfplay_fix")
SRC_SLUG = "khoadangnguye/gui-selfplay"
SRC_JSONL_LOCAL = os.path.join("phase13-gui", "selfplay",
                               "gui-selfplay-v21.jsonl")
NEW_SLUG = "khoadangnguye/ornith-gui-selfplay-v2"
HF_REPO = "kkouadn/ornith-colab-data"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fix_rows(rows):
    kept, dropped, pts, click_bad = [], 0, 0, 0
    stats = {}
    for r in rows:
        a = (r.get("action") or "").strip()
        pref = a.split()[0] if a.split() else "EMPTY"
        stats[pref] = stats.get(pref, 0) + 1
        if r.get("win") is False:
            dropped += 1
            continue
        if pref == "CLICK" and r.get("point") is None:
            m = re.match(r"CLICK\s+(\d+)\s+(\d+)$", a)
            if m:
                r = dict(r)
                r["point"] = [int(m.group(1)), int(m.group(2))]
                pts += 1
            else:
                click_bad += 1
        kept.append(r)
    return kept, dropped, pts, click_bad, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true",
                    help="chi tao thu muc dataset + zip, khong len Kaggle/HF")
    args = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from kaggle_keys import kaggle_env
    user, key_env = kaggle_env("A")
    os.environ["KAGGLE_USERNAME"] = user
    os.environ["KAGGLE_KEY"] = key_env
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()

    shutil.rmtree(TMP, ignore_errors=True)
    dl = os.path.join(TMP, "src")
    os.makedirs(dl, exist_ok=True)

    # 1) tai dataset goc (traj.jsonl + anh)
    print("1) tai dataset goc %s ..." % SRC_SLUG)
    api.dataset_download_files(SRC_SLUG, path=dl, quiet=True)
    zs = [f for f in os.listdir(dl) if f.lower().endswith(".zip")]
    if not zs:
        print("   !! khong co zip trong dataset goc")
        return 1
    src_jsonl = None
    shots = []
    with zipfile.ZipFile(os.path.join(dl, zs[0])) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            if name == "traj.jsonl":
                src_jsonl = z.read(info)
            elif name.lower().endswith((".png", ".jpg", ".jpeg")):
                shots.append((name, z.read(info)))
    if not src_jsonl:
        print("   !! khong thay traj.jsonl top-level")
        return 1
    print("   traj.jsonl %d bytes, anh %d" % (len(src_jsonl), len(shots)))

    # doi chieu voi file local (source da biet)
    if os.path.exists(SRC_JSONL_LOCAL):
        h_k = hashlib.sha256(src_jsonl).hexdigest()
        h_l = sha256_file(SRC_JSONL_LOCAL)
        print("   hash Kaggle=%s local=%s -> %s"
              % (h_k[:12], h_l[:12], "KHOP" if h_k == h_l else "KHAC!"))

    rows = []
    for line in src_jsonl.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    kept, dropped, pts, click_bad, stats = fix_rows(rows)
    print("2) fix: %d row -> GIU %d, drop win=False %d, them point %d, "
          "CLICK le %d" % (len(rows), len(kept), dropped, pts, click_bad))
    print("   action prefix: %s" % stats)

    # anh chi giu cua row giu duoc
    need = set()
    for r in kept:
        need.add(os.path.basename(str(r.get("image", ""))))
    img_dir = os.path.join(TMP, "folder", "shots")
    os.makedirs(img_dir, exist_ok=True)
    n_img = 0
    for name, b in shots:
        if os.path.basename(name) in need:
            with open(os.path.join(img_dir, os.path.basename(name)),
                      "wb") as f:
                f.write(b)
            n_img += 1
    print("   anh giu: %d/%d (row giu co %d anh duy nhat)"
          % (n_img, len(shots), len(need)))

    # 3) ghi traj.jsonl top-level + zip tam de hash/host
    out_dir = os.path.join(TMP, "folder")
    jsonl_path = os.path.join(out_dir, "traj.jsonl")
    with io.open(jsonl_path, "w", encoding="utf-8", newline="\n") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    h_local_jsonl = sha256_file(jsonl_path)

    zip_path = os.path.join(TMP, "ornith-gui-selfplay-v2.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
        z.write(jsonl_path, "traj.jsonl")
        for fn in sorted(os.listdir(img_dir)):
            z.write(os.path.join(img_dir, fn), "shots/" + fn)
    print("3) zip ornith-gui-selfplay-v2.zip (%.1f MB) sha256=%s"
          % (os.path.getsize(zip_path) / 1e6, sha256_file(zip_path)[:16]))
    print("   traj.jsonl sha256=%s" % h_local_jsonl[:16])

    if args.no_upload:
        print("4) --no-upload: dung lai tai day (folder + zip trong %s)" % TMP)
        return 0

    # 4) upload dataset moi (shots/ -> shots.zip bang dir_mode='zip')
    print("4) tao dataset moi %s (public=False, dir_mode=zip) ..." % NEW_SLUG)
    meta = {
        "title": "Ornith GUI selfplay v2 (fixed format)",
        "id": NEW_SLUG,  # SDK can dang owner/slug
        "summary": "gui-selfplay loc: chi row win=True (bo 80 row that bai) "
                   "+ field point=[x,y] tu action CLICK x y (eval kiem "
                   "toa do duoc). traj.jsonl top-level + shots.zip.",
        "licenses": [{"name": "CC0-1.0"}],
    }
    with io.open(os.path.join(out_dir, "dataset-metadata.json"), "w",
                 encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    resp = api.dataset_create_new(out_dir, public=False, quiet=True,
                                  convert_to_csv=False, dir_mode="zip")
    print("   resp: %s" % type(resp).__name__)

    # 5) verify: hash traj.jsonl + audit resolve
    print("5) verify sau upload ...")
    vdir = os.path.join(TMP, "verify")
    os.makedirs(vdir, exist_ok=True)
    api.dataset_download_file(NEW_SLUG, "traj.jsonl", path=vdir, quiet=True)
    h_new = sha256_file(os.path.join(vdir, "traj.jsonl"))
    ok_hash = (h_new == h_local_jsonl)
    print("   hash traj.jsonl moi=%s -> %s"
          % (h_new[:16], "KHOP" if ok_hash else "KHAC (LOI!)"))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ad", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "audit_datasets.py"))
    ad = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ad)
    r = ad.audit_one(api, "A", NEW_SLUG, None,
                     os.path.join(TMP, "audit"), 150)
    print("   audit_one: %s img=%s/%s rows=%s"
          % (r.get("ket_luan"), r.get("img_ok"), r.get("img_refs"),
             r.get("n_rows")))
    ok_audit = (r.get("ket_luan") == "OK")

    # 6) host zip len HF (cho DeepSeek/Colab tai lai)
    print("6) host zip len HF %s ..." % HF_REPO)
    rc = subprocess.call([sys.executable,
                          os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "hf_host_data.py"),
                          "--repo", HF_REPO, zip_path])

    print("\n== TOM TAT ==")
    print("  row: %d -> %d (drop win=False %d); point them %d; anh %d"
          % (len(rows), len(kept), dropped, pts, n_img))
    print("  traj.jsonl sha256: %s" % h_local_jsonl)
    print("  zip sha256       : %s" % sha256_file(zip_path))
    print("  Kaggle dataset   : %s (verify hash %s, audit %s)"
          % (NEW_SLUG, "KHOP" if ok_hash else "LOI",
             r.get("ket_luan")))
    print("  HF zip           : https://huggingface.co/datasets/%s/"
          "resolve/main/ornith-gui-selfplay-v2.zip" % HF_REPO)
    print("  tai lai (Colab)  : wget -q https://huggingface.co/datasets/%s/"
          "resolve/main/ornith-gui-selfplay-v2.zip" % HF_REPO)
    return 0 if (ok_hash and ok_audit and rc == 0) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
