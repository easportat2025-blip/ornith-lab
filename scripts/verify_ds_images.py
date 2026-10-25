# -*- coding: utf-8 -*-
"""
verify_ds_images.py - KIEM TRA dataset tren Kaggle co that: moi row tro toi
mot ANH TON TAI (resolve theo DUNG quy tac cua loader) - truoc khi dua vao
kernel SFT.

LY DO (22/10, @MiMo): khi upload, Kaggle CLI dua file PNG vao thu muc con
ten dataset ("<slug>_images/") => rows tro ten phang => KHONG resolve =>
train im lang (anh khong co) hoac kernel crash. Day la loi "silent".

Quy tac resolve (giong load_ds_rows cua kernel SFT):
  1) <dataset_root>/<rel>            (file phang trong dataset)
  2) <extracted_zip_root>/<rel>      (sau khi giai nen .zip trong dataset)
=> module nay tai dataset ve, giai nen moi zip, roi kiem TUNG row.

Dung:
    python scripts/verify_ds_images.py dieniw/ornith-gui-desktop-replay
ASCII-only source.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from upload_staging import env_for  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/verify_ds_images.py <owner/slug>")
        return 2
    slug = sys.argv[1]
    tmp = os.path.join(tempfile.gettempdir(), "mimo_vds_" +
                       slug.replace("/", "_"))
    if os.path.isdir(tmp):
        shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    owner = slug.split("/", 1)[0]
    env, has_key = env_for(owner)
    if not has_key:
        print("FAIL: khong co key cho owner %s" % owner)
        return 2
    r = subprocess.run(["kaggle", "datasets", "download", slug, "-p", tmp,
                        "--unzip", "--force"], capture_output=True, text=True,
                       env=env, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("FAIL download: %s" % ((r.stderr or r.stdout or "")[:400]))
        return 1
    files = []
    for base, _d, fs in os.walk(tmp):
        for f in fs:
            files.append(os.path.relpath(os.path.join(base, f), tmp)
                         .replace("\\", "/"))
    tj = None
    for base, _d, fs in os.walk(tmp):
        for f in fs:
            if f == "traj.jsonl":
                tj = os.path.join(base, f)
    if not tj:
        print("FAIL: khong tim thay traj.jsonl trong dataset (files: %d)"
              % len(files))
        return 1
    rows = [json.loads(l) for l in io.open(tj, encoding="utf-8") if l.strip()]
    # giai nen moi zip (nhu loader)
    ext = os.path.join(tmp, "_ext")
    os.makedirs(ext, exist_ok=True)
    for f in files:
        if f.lower().endswith(".zip"):
            with zipfile.ZipFile(os.path.join(tmp, f)) as z:
                z.extractall(ext)
    ext_files = set()
    for base, _d, fs in os.walk(ext):
        for f in fs:
            ext_files.add(os.path.relpath(os.path.join(base, f), ext)
                          .replace("\\", "/"))
    ds_root = os.path.dirname(tj)
    ds_files = set()
    ds_basenames = set()
    for base, _d, fs in os.walk(ds_root):
        for f in fs:
            rel = os.path.relpath(os.path.join(base, f), ds_root).replace("\\", "/")
            ds_files.add(rel)
            ds_basenames.add(f)
    ext_basenames = set(os.path.basename(f) for f in ext_files)
    ok = miss = 0
    miss_list = []
    for r0 in rows:
        rel = r0.get("image") or ""
        if (rel in ds_files) or (rel in ext_files) or \
                (os.path.basename(rel) in ds_basenames) or \
                (os.path.basename(rel) in ext_basenames):
            ok += 1
        else:
            miss += 1
            if len(miss_list) < 3:
                miss_list.append(rel)
    print("== %s" % slug)
    print("   n_row=%d | n_file_dataset=%d | n_file_zip=%d"
          % (len(rows), len(ds_files), len(ext_files)))
    print("   ANH RESOLVE: %d/%d (%.1f%%)"
          % (ok, len(rows), 100.0 * ok / max(len(rows), 1)))
    if miss_list:
        print("   KHONG RESOLVE (vi du): %s" % miss_list)
    print("   verbs: %s" % dict(Counter(
        (r0.get("action") or "?").split()[0] for r0 in rows).most_common(6)))
    print("   task: %s" % dict(Counter(r0.get("task_id")
                                       for r0 in rows).most_common(8)))
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
