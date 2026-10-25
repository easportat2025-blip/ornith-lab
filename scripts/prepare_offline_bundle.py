# -*- coding: utf-8 -*-
"""prepare_offline_bundle.py (v2) - tai TRUOC moi thu can cho may RTX (KHONG internet).

Sua loi "peak" o v1: .zip + file giai nen cung ton tai -> can 2x dung luong.
v2: tai .zip vao TMP o C: (it dung, xoa ngay) -> giai nen THANG vao thu muc dich
(USB) -> xoa .zip. Peak tren dich = dung kich thuoc bundle.

Dung:
    python scripts/prepare_offline_bundle.py --dest D:\\ornith-offline
    python scripts/prepare_offline_bundle.py --dest D:\\ornith-offline --only base
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(os.environ.get("TEMP", "."), "ornith_bundle_dl")

BASE_SHARDS = ["dieniw/ornbase-s1", "dieniw/ornbase-s2", "dieniw/ornbase-s3",
               "dieniw/ornbase-s4"]
DATASETS = [
    "khoadangnguye/gui-selfplay",
    "khoadangnguye/ornith-policy-replay-data",
    "khoadangnguye/ornith-gui-train3d",
    "khoadangnguye/ornith-gui-train3d-hard",
    "khoadangnguye/ornith-gui-real-ui",
    "khoadangnguye/ornith-gui-real-fixtures",
    "khoadangnguye/ornith-gui-traj",
    "khoadangnguye/ornith-offline-browsers",
    "khoadangnguye/ornith-gui-bench-v155",
    "khoadangnguye/ornith-gui-bench-v16b",
]
WHEELS = ["khoadangnguye/gemma12b-wheels", "khoadangnguye/gemma12b-tools"]

ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"
ENV["PYTHONIOENCODING"] = "utf-8"


def sh(cmd, timeout=5400):
    p = subprocess.run(cmd, shell=True, capture_output=True, env=ENV,
                       timeout=timeout)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


def du(p):
    t = 0
    for root, _d, files in os.walk(p):
        for f in files:
            try:
                t += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return t


def fetch(slug, dest_dir, keep_ext=None, only_ext=None):
    """Tai dataset -> giai nen thang vao dest_dir -> xoa .zip (peak = 1 lan)."""
    name = slug.split("/")[1]
    tmp = os.path.join(TMP, name)
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    rc, o, e = sh("kaggle datasets download %s -p \"%s\" --force" % (slug, tmp))
    zips = [f for f in os.listdir(tmp) if f.endswith(".zip")]
    if not zips:
        print("  !! tai that bai: %s" % slug)
        shutil.rmtree(tmp, ignore_errors=True)
        return False
    zp = os.path.join(tmp, zips[0])
    print("   zip %.1f MB -> giai nen vao %s" % (os.path.getsize(zp) / 1e6, dest_dir))
    os.makedirs(dest_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(zp) as z:
            for m in z.namelist():
                if m.endswith("/"):
                    continue
                if only_ext and not m.lower().endswith(only_ext):
                    continue
                base = os.path.basename(m)
                if not base:
                    continue
                if keep_ext and not base.lower().endswith(keep_ext):
                    continue
                with z.open(m) as src, open(os.path.join(dest_dir, base), "wb") as dst:
                    shutil.copyfileobj(src, dst)
    except Exception as e:
        print("  !! giai nen loi:", e)
    os.remove(zp)                      # xoa ngay de giam peak
    shutil.rmtree(tmp, ignore_errors=True)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    dest = os.path.abspath(a.dest)
    os.makedirs(dest, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    man = {"base": [], "input": [], "wheels": []}
    mp = os.path.join(dest, "MANIFEST.json")
    if os.path.exists(mp):
        try:
            man = json.load(io.open(mp, encoding="utf-8"))
        except Exception:
            man = {}

    def want(k):
        return (not a.only) or (a.only == k)

    if want("base"):
        print("=== base model (4 shard) ===")
        bdir = os.path.join(dest, "base")
        for slug in BASE_SHARDS:
            print("  tai %s ..." % slug, flush=True)
            if fetch(slug, bdir):
                man["base"].append(slug)

    if want("input"):
        print("=== dataset train ===")
        idir = os.path.join(dest, "input")
        for slug in DATASETS:
            name = slug.split("/")[1]
            print("  tai %s ..." % slug, flush=True)
            if fetch(slug, os.path.join(idir, name)):
                man["input"].append(slug)

    if want("wheels"):
        print("=== wheels pip (.whl) ===")
        wdir = os.path.join(dest, "wheels")
        for slug in WHEELS:
            print("  tai %s ..." % slug, flush=True)
            if fetch(slug, wdir, only_ext=".whl"):
                man["wheels"].append(slug)

    shutil.rmtree(TMP, ignore_errors=True)
    for k in man:
        man[k] = sorted(set(man.get(k, [])))
    json.dump(man, io.open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n=== XONG ===")
    for k, v in (("base", "base"), ("input", "input"), ("wheels", "wheels")):
        p = os.path.join(dest, v)
        if os.path.isdir(p):
            print("  %-8s %8.1f MB (%d file)" % (k, du(p) / 1e6,
                                                len(os.listdir(p))))
    print("  MANIFEST.json + RUN.md")
    print("  -> copy sang may RTX: base\\ input\\ wheels\\ + code")


if __name__ == "__main__":
    main()
