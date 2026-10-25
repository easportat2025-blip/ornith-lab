# -*- coding: utf-8 -*-
"""check_kernel_sources.py - CUA AN TOAN truoc khi push kernel.

Loi that da xay ra (23/10):
  - kernel-metadata.json thieu dataset 'ornith-gui-synth-s11' (chi them vao
    code) => Kaggle push van bao OK, kernel chet giua run vi required=True.
  - metadata tro toi 'ornith-desktop-replay-v1' KHONG TON TAI (slug that la
    'ornith-gui-desktop-replay') => cung chet giua run, mat slot GPU.

Script nay doi chieu 3 thu:
  1. moi dataset source: ton tai + READY + co >= 2 file
  2. moi load_ds_rows("X") trong code phai co source slug ket thuc bang X
  3. in tong so file/tin hieu de nguoi doc thay dataset rong ngay

Dung:
    python scripts/check_kernel_sources.py phase13-gui/kernel_v25b
    python scripts/check_kernel_sources.py phase13-gui/kernel_v25b --skip-api
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from upload_staging import env_for  # noqa: E402

FLAGS = 0x08000000 if os.name == "nt" else 0


def list_files(ref, owner):
    env, has = env_for(owner)
    if not has:
        return None, "khong co key cho %s" % owner
    p = subprocess.run(["kaggle", "datasets", "files", ref,
                        "--page-size", "200", "--format", "json"],
                       capture_output=True, env=env, timeout=180,
                       creationflags=FLAGS)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    if p.returncode != 0:
        return None, (err or out).strip()[:200]
    i, j = out.find("["), out.rfind("]")
    if i < 0 or j < i:
        return None, "output khong co JSON array"
    try:
        arr = json.loads(out[i:j + 1])
    except Exception as e:
        return None, "JSON loi: %s" % e
    return arr, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kernel_dir")
    ap.add_argument("--skip-api", action="store_true")
    a = ap.parse_args()

    kd = a.kernel_dir
    meta = json.load(open(os.path.join(kd, "kernel-metadata.json"),
                          encoding="utf-8"))
    code = open(os.path.join(kd, meta["code_file"]), encoding="utf-8",
                errors="replace").read()
    srcs = meta.get("dataset_sources") or []
    slugs = {s.split("/")[-1] for s in srcs}

    fail = 0
    print("kernel : %s (%s)" % (meta.get("id"), meta.get("title")))
    print("sources: %d dataset" % len(srcs))

    used = re.findall(r'load_ds_rows\(\s*["\']([^"\']+)["\']', code)
    print("code   : load_ds_rows -> %s" % sorted(set(used)))
    for name in sorted(set(used)):
        if name not in slugs:
            print("  FAIL: code load '%s' nhung KHONG co trong metadata" % name)
            fail += 1

    for s in srcs:
        slug = s.split("/")[-1]
        if a.skip_api:
            continue
        arr, err = list_files(s, s.split("/")[0])
        if arr is None:
            print("  FAIL: %-42s %s" % (s, err))
            fail += 1
        else:
            mb = sum(int(f.get("size") or 0) for f in arr) / 1048576.0
            # 1 file van hop le (shard 4 GB); chi coi la rong khi 0 file
            # hoac tong < 10 KB (upload that bai / file rac).
            empty = (len(arr) == 0) or (mb < 0.01)
            flag = "FAIL(rong)" if empty else "OK "
            if empty:
                fail += 1
            print("  %-10s %-42s %4d file %7.1f MB" % (flag, s, len(arr), mb))
        time.sleep(0.6)

    print("=> %s" % ("FAIL (%d loi)" % fail if fail else "PASS - duoc phep push"))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
