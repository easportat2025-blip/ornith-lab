# -*- coding: utf-8 -*-
"""
check_push_parity.py - kiem tra code tren KAGGLE co KHOP voi code LOCAL.

LY DO (22/10, @MiMo): kernel v24 tren acc B chet voi
  NameError: name 'N_3D' is not defined
dung khi source LOCAL da duoc sua (scripts/fix_n3d.py -> N_3D = 600).
=> "sua local" khong dong nghia "sua tren Kaggle" (push bang ban cu, hoac
push truoc khi sua, hoac build khac nhau) => mat ca slot GPU.

Dung:
    python scripts/check_push_parity.py phase13-gui/kernel_v24_B --kernel dieniw/ornith-gui-sft-v24
    python scripts/check_push_parity.py phase13-gui/kernel_desktop_bench_b3
Ket qua:
    MATCH  - code tren Kaggle == code local
    STALE  - khac nhau (Kaggle dang chay ban CU)
ASCII-only source.
"""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def local_code(d):
    mp = os.path.join(d, "kernel-metadata.json")
    if not os.path.exists(mp):
        return None, None
    md = json.load(io.open(mp, encoding="utf-8"))
    cf = md.get("code_file") or ""
    p = os.path.join(d, cf) if cf else None
    if not p or not os.path.exists(p):
        for f in sorted(os.listdir(d)):
            if f.endswith(".py"):
                p = os.path.join(d, f)
                break
    return (p, md.get("id")) if p else (None, md.get("id"))


def pull(kernel):
    tmp = os.path.join(tempfile.gettempdir(), "mimo_parity_" +
                       kernel.replace("/", "_"))
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    p = subprocess.run(["kaggle", "kernels", "pull", kernel, "-p", tmp, "-m"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        print("pull that bai: %s" % (p.stderr or p.stdout)[-200:])
        return None
    for base, _d, files in os.walk(tmp):
        for f in files:
            if f.endswith(".py"):
                return os.path.join(base, f)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--kernel", default="")
    a = ap.parse_args()
    d = a.dir if os.path.isabs(a.dir) else os.path.join(
        ROOT, a.dir.replace("/", os.sep))
    lp, kid = local_code(d)
    if not lp:
        print("FAIL: khong tim thay code file trong", d)
        return 1
    kernel = a.kernel or kid
    if not kernel:
        print("FAIL: khong biet kernel id (them --kernel)")
        return 1
    rp = pull(kernel)
    if not rp:
        print("FAIL: khong pull duoc code tu", kernel)
        return 1
    hl, hr = sha(lp), sha(rp)
    print("local : %s  %s" % (os.path.basename(lp), hl[:16]))
    print("remote: %s  %s  (%s)" % (os.path.basename(rp), hr[:16], kernel))
    if hl == hr:
        print("=> MATCH: code tren Kaggle == code local")
        return 0
    # diff dong: cho biet phan nao khac
    sl = io.open(lp, encoding="utf-8", errors="replace").read().splitlines()
    sr = io.open(rp, encoding="utf-8", errors="replace").read().splitlines()
    only_local = [x for x in sl if x.strip() and x not in sr]
    only_remote = [x for x in sr if x.strip() and x not in sl]
    print("=> STALE: code tren Kaggle KHAC code local")
    if only_local:
        print("   chi co LOCAL (%d dong, 5 dau):" % len(only_local))
        for x in only_local[:5]:
            print("      + %s" % x.strip()[:100])
    if only_remote:
        print("   chi co REMOTE (%d dong, 5 dau):" % len(only_remote))
        for x in only_remote[:5]:
            print("      - %s" % x.strip()[:100])
    print("   => phai PUSH LAI code local truoc khy vay tiep (sua local khong "
          "du, phai len Kaggle)")
    return 2


if __name__ == "__main__":
    sys.exit(main())
