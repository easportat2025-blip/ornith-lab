# -*- coding: utf-8 -*-
"""
cmp_ds_hashes.py - so sanh 2 dataset tren Kaggle bang hash file
(dung khi can chung minh "dataset A tren acc B == dataset B tren acc A",
vi dataset bi copy sang acc khac co the doi ten / bi version).

Dung:
    python scripts/cmp_ds_hashes.py <slugA> <slugB> [--only .json,.safetensors]
Ket qua: cac file giong nhau / khac nhau (theo ten duoi).
ASCII-only source.
"""
import argparse
import hashlib
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def grab(slug):
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    dest = os.path.join(tempfile.gettempdir(), "mimo_cmp_" +
                        slug.replace("/", "_"))
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)
    api.dataset_download_files(slug, path=dest, unzip=True, quiet=False)
    out = {}
    for base, _d, files in os.walk(dest):
        for f in files:
            p = os.path.join(base, f)
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            out[f] = (h, os.path.getsize(p))
    shutil.rmtree(dest, ignore_errors=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    ha, hb = grab(a.a), grab(a.b)
    only = [x.strip() for x in a.only.split(",") if x.strip()]
    keys = sorted(set(ha) | set(hb))
    same = diff = 0
    for k in keys:
        if only and not any(k.endswith(x) for x in only):
            continue
        if k in ha and k in hb:
            if ha[k][0] == hb[k][0]:
                same += 1
                print("   GIONG   %-34s %d bytes" % (k, ha[k][1]))
                continue
            diff += 1
            print("   KHAC    %-34s A=%d B=%d bytes" % (k, ha[k][1], hb[k][1]))
        else:
            only_a = k in ha
            print("   %-8s %-34s (chi co o %s)"
                  % ("CHIA", k, "A" if only_a else "B"))
    print("-" * 70)
    print("A=%s (%d file) | B=%s (%d file) | giong=%d khac=%d"
          % (a.a, len(ha), a.b, len(hb), same, diff))
    if diff == 0 and same > 0:
        print("=> VERDICT: 2 dataset GIONG NHAU (theo file)")
        return 0
    if diff:
        print("=> VERDICT: KHAC NHAU (%d file)" % diff)
        return 2
    return 3


if __name__ == "__main__":
    sys.exit(main())
