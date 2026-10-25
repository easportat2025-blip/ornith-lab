# -*- coding: utf-8 -*-
"""
preflight_ds.py - kiem tra dataset co THAT TON TAI + READY truoc khi push kernel.
Neu thieu -> bao bus (watchdog se bo qua kernel do) thay vì chay 2h GPU roi chet.

Usage: python scripts/preflight_ds.py <kernel-dir> [<kernel-dir> ...]
Doc dataset_sources tu kernel-metadata.json, kiem tra tung dataset bang
'kaggle datasets status' voi key dung theo owner (A/B).
"""
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def key_of(owner):
    var = "KAGGLE_KEY_A" if owner == "khoadangnguye" else "KAGGLE_KEY_B"
    return (os.environ.get(var) or hkcu(var) or hkcu("KAGGLE_KEY") or "")


def ds_ready(slug, tries=3):
    owner = slug.split("/")[0]
    key = key_of(owner)
    if not key:
        return False, "thieu key cho %s" % owner
    env = dict(os.environ)
    env["KAGGLE_USERNAME"] = owner
    env["KAGGLE_KEY"] = key
    env["PYTHONIOENCODING"] = "utf-8"
    last = ""
    for i in range(tries):
        p = subprocess.run(["kaggle", "datasets", "status", slug],
                           capture_output=True, env=env, timeout=180)
        out = ((p.stdout or b"") + (p.stderr or b"")).decode("utf-8", "replace")
        last = out.strip()[-160:]
        if p.returncode == 0 and re.search(r"\bready\b", out, re.I):
            return True, "ready"
        time.sleep(6)
    return False, last


def main():
    dirs = sys.argv[1:]
    if not dirs:
        print("dung: preflight_ds.py <kernel-dir> ...")
        return 2
    bad = []
    for d in dirs:
        p = os.path.join(ROOT, d.replace("/", os.sep), "kernel-metadata.json")
        if not os.path.exists(p):
            print("  !! thieu %s" % p)
            bad.append(d)
            continue
        m = json.load(io.open(p, encoding="utf-8"))
        srcs = m.get("dataset_sources", []) or []
        print("=== %s (%d dataset)" % (d, len(srcs)))
        for s in srcs:
            ok, info = ds_ready(s)
            print("   %-46s %s  %s" % (s, "OK " if ok else "BAD", info))
            if not ok:
                bad.append("%s :: %s" % (d, s))
            time.sleep(3)
    if bad:
        print("\n!! THIEU/CHUA READY (%d):" % len(bad))
        for b in bad:
            print("   " + b)
        return 1
    print("\nTAT CA dataset READY -> du dieu kien push")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
