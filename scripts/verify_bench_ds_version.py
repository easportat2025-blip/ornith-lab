# -*- coding: utf-8 -*-
"""
verify_bench_ds_version.py - CHUNG MINH mot dataset bench tren Kaggle chua
ban task CU hay ban task MOI (da sua).

Ly do: cung mot slug dataset co the da bi "version" (doi noi dung task).
Khi do, kernel nao chay dataset do se do TON task nao - phai chung minh bang
hash file, khong tin vao "da upload" hay vao thoi gian chay.

Dung:
    python scripts/verify_bench_ds_version.py dieniw/ornith-gui-bench-v155
    python scripts/verify_bench_ds_version.py <slug> --new <dir> --old <zip>

Mac dinh:
    --new phase13-gui/bench_v15/tasks_v15_5
    --old phase13-gui/old_bench_ds/khoadangnguye__ornith-gui-bench-v155-old/bench_v155_bundle.zip

ASCII-only source.
"""
import argparse
import hashlib
import io
import os
import shutil
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    with open(p, "rb") as fh:
        return sha256_bytes(fh.read())


def dir_hashes(d):
    """{ten file tuong doi: sha256} cho 1 thu muc (bo thu muc con)."""
    out = {}
    for base, _dirs, files in os.walk(d):
        for f in files:
            p = os.path.join(base, f)
            rel = os.path.relpath(p, d).replace("\\", "/")
            out[rel] = sha256_file(p)
    return out


def zip_hashes(zp):
    out = {}
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            out[n] = sha256_bytes(z.read(n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--new", default="phase13-gui/bench_v15/tasks_v15_5")
    ap.add_argument("--old", default=("phase13-gui/old_bench_ds/"
                                      "khoadangnguye__ornith-gui-bench-v155-old/"
                                      "bench_v155_bundle.zip"))
    ap.add_argument("--keep", default="")
    a = ap.parse_args()

    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    dest = a.keep or os.path.join(tempfile.gettempdir(),
                                  "mimo_dsver_" + a.slug.replace("/", "_"))
    os.makedirs(dest, exist_ok=True)
    print("tai %s -> %s" % (a.slug, dest), flush=True)
    api.dataset_download_files(a.slug, path=dest, unzip=True, quiet=False)

    # remote: gom theo thu muc con dau (bench_v155/...)
    rem = {}
    for base, _dirs, files in os.walk(dest):
        for f in files:
            p = os.path.join(base, f)
            rel = os.path.relpath(p, dest).replace("\\", "/")
            rem[rel] = sha256_file(p)
    print("remote: %d file" % len(rem))

    newp = a.new if os.path.isabs(a.new) else os.path.join(
        ROOT, a.new.replace("/", os.sep))
    oldp = a.old if os.path.isabs(a.old) else os.path.join(
        ROOT, a.old.replace("/", os.sep))
    new_h = dir_hashes(newp) if os.path.isdir(newp) else {}
    old_h = zip_hashes(oldp) if os.path.isfile(oldp) else {}

    n_match = o_match = other = 0
    diff = []
    for rel, h in sorted(rem.items()):
        # so sanh theo TEN DUOI (bo thu muc goc khac nhau)
        base = rel.split("/")[-1]
        hit_new = [k for k, v in new_h.items() if k.split("/")[-1] == base
                   and v == h]
        hit_old = [k for k, v in old_h.items() if k.split("/")[-1] == base
                   and v == h]
        tag = "?"
        if hit_new and hit_old:
            tag = "GIONG_CA_HAI"
        elif hit_new:
            tag = "MOI"
            n_match += 1
        elif hit_old:
            tag = "CU"
            o_match += 1
        else:
            tag = "KHAC"
            other += 1
        print("   %-28s %-12s %s" % (base, tag, h[:12]))
        if tag in ("KHAC",):
            diff.append(base)
    print("-" * 70)
    print("KET QUA: khop ban MOI = %d | khop ban CU = %d | khac = %d"
          % (n_match, o_match, other))
    if o_match == 0 and n_match > 0 and other == 0:
        print("=> VERDICT: dataset remote chua BAN MOI (task da sua) - OK")
        rc = 0
    elif n_match == 0 and o_match > 0 and other == 0:
        print("=> VERDICT: dataset remote van la BAN CU (chua co hieu luc fix)")
        rc = 2
    else:
        print("=> VERDICT: HON HOP (xem %d file khac)" % other)
        rc = 3
    if not a.keep:
        shutil.rmtree(dest, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
