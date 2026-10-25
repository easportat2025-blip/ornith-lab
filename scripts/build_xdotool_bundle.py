# -*- coding: utf-8 -*-
"""
build_xdotool_bundle.py - chay kernel CPU tren Kaggle de tao bundle xdotool
OFFLINE (plan B cho desktop-bench: image Kaggle thieu xdotool, apt treo do
DNS security.ubuntu.com -> 38' GPU slot/run).

Day la lenh 'push kernel' => can --push (mac dinh chi kiem tra chuan bi).
KHONG dung GPU (enable_gpu=false) => khong ton GPU slot.

Dung:
    python scripts/build_xdotool_bundle.py --push             # push + tai output
    python scripts/build_xdotool_bundle.py --push --upload    # + upload dataset
    python scripts/build_xdotool_bundle.py --check            # chi kiem tra
ASCII-only source. KHONG ghi key vao file.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.join(ROOT, "phase13-gui", "kernel_xdotool_bundle")
OUTDIR = os.path.join(ROOT, "phase13-gui", "xdotool_bundle_out")
STAGE = os.path.join(ROOT, "phase13-gui", "xdotool_ds_staging",
                     "khoadangnguye__ornith-gui-xdotool")
KID = "khoadangnguye/ornith-build-xdotool"
SLUG = "khoadangnguye/ornith-gui-xdotool"
FLAGS = 0x08000000 if os.name == "nt" else 0


def sh(cmd, timeout=1800, env=None):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, env=env, creationflags=FLAGS)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 1, "EXC %s" % e


def acc_env():
    """Env voi key acc A (doc tu HKCU nhu cac script khac)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    key = os.environ.get("KAGGLE_KEY_A", "")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v, _t = winreg.QueryValueEx(k, "KAGGLE_KEY_A")
                key = str(v).strip()
        except Exception:
            key = ""
    if key:
        env["KAGGLE_KEY"] = key
    env["KAGGLE_USERNAME"] = "khoadangnguye"
    return env, bool(key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--wait", type=int, default=60)
    a = ap.parse_args()
    env, has_key = acc_env()

    if a.check or not a.push:
        print("kernel dir : %s" % os.path.relpath(KDIR, ROOT))
        print("code_file  : %s" % os.path.join(KDIR, "build_xdotool_bundle.py"))
        md = json.load(io.open(os.path.join(KDIR, "kernel-metadata.json"),
                               encoding="utf-8"))
        print("kernel id  : %s (enable_gpu=%s, enable_internet=%s)"
              % (md.get("id"), md.get("enable_gpu"), md.get("enable_internet")))
        print("slug du kien: %s" % SLUG)
        print("key acc A  : %s" % ("co" if has_key else "THIEU"))
        print("=> de chay that, them --push (KHONG ton GPU slot)")
        return 0

    if not has_key:
        print("!! thieu key acc A (KAGGLE_KEY_A / HKCU)")
        return 2

    print("=== push kernel CPU %s ===" % KID)
    rc, out = sh("kaggle kernels push -p \"%s\"" % KDIR, timeout=900, env=env)
    print(out.strip()[-400:])
    if rc != 0 or "successfully pushed" not in out.lower():
        print("PUSH FAIL")
        return 3

    print("=== wait COMPLETE ===")
    ok = False
    for i in range(1, a.wait + 1):
        rc, st = sh("kaggle kernels status %s" % KID, timeout=300, env=env)
        st = st.strip().replace("\n", " ")[:120]
        print("  [%2d] %s" % (i, st))
        if "COMPLETE" in st:
            ok = True
            break
        if "ERROR" in st:
            print("KERNEL ERROR")
            return 4
        time.sleep(30)
    if not ok:
        print("WARN: chua COMPLETE sau %d lan" % a.wait)
        return 5

    print("=== tai output ===")
    if os.path.isdir(OUTDIR):
        shutil.rmtree(OUTDIR, ignore_errors=True)
    os.makedirs(OUTDIR, exist_ok=True)
    rc, out = sh("kaggle kernels output %s -p \"%s\" --force" % (KID, OUTDIR),
                 timeout=1800, env=env)
    print(out.strip()[-300:])
    zp = os.path.join(OUTDIR, "xdotool_bundle.zip")
    if not os.path.exists(zp):
        print("!! khong thay xdotool_bundle.zip trong output")
        for root, _d, files in os.walk(OUTDIR):
            for f in files[:20]:
                print("   ", os.path.relpath(os.path.join(root, f), OUTDIR))
        return 6

    print("=== chuan bi staging dataset %s ===" % SLUG)
    os.makedirs(STAGE, exist_ok=True)
    import zipfile
    with zipfile.ZipFile(zp) as z:
        z.extractall(STAGE)
    meta = {"title": "Ornith xdotool offline bundle (xdotool + libXdo)",
            "id": SLUG, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    n = 0
    for root, _d, files in os.walk(STAGE):
        n += len(files)
    print("staging: %s (%d file, %.1f MB)"
          % (os.path.relpath(STAGE, ROOT), n,
             sum(os.path.getsize(os.path.join(r, f))
                 for r, _d, fs in os.walk(STAGE) for f in fs) / 1048576.0))

    if a.upload:
        print("=== upload dataset ===")
        rc, out = sh("kaggle datasets version -p \"%s\" -m \"xdotool bundle\""
                     % STAGE, timeout=1800, env=env)
        print(out.strip()[-300:])
        if rc != 0:
            rc, out = sh("kaggle datasets create -p \"%s\"" % STAGE,
                         timeout=1800, env=env)
            print(out.strip()[-300:])
    print("xong. Buoc tiep (neu can): them '%s' vao dataset_sources cua 4 "
          "kernel desktop + giai nen bundle vao /usr/local/bin." % SLUG)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
