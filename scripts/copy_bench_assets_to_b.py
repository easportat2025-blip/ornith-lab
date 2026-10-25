# -*- coding: utf-8 -*-
"""
copy_bench_assets_to_b.py - copy sang acc B (dieniw) 2 tai nguyen can cho
phep do 2x2 (v22 tren task B15.5 CU) + bench B16-A tren task da sua:

  1) khoadangnguye/ornith-gui-lora-v22      -> dieniw/ornith-gui-lora-v22
  2) khoadangnguye/ornith-gui-bench-v155-old-> dieniw/ornith-gui-bench-v155-old

Acc A het quota GPU => pho do phai chay tren B (con 12.38h).
ASCII-only. Key doc tu HKCU.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def env_b():
    e = dict(os.environ)
    e["KAGGLE_USERNAME"] = "dieniw"
    e["KAGGLE_KEY"] = os.environ.get("KAGGLE_KEY_B") or hkcu("KAGGLE_KEY_B")
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def run(cmd, env, timeout=5400):
    p = subprocess.run(cmd, capture_output=True, env=env, timeout=timeout,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    return p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode(
        "utf-8", "replace")


def push_stage(src, slug, title):
    """Copy staging dir -> doi id/title -> upload len acc B."""
    owner, name = slug.split("/")
    dst = os.path.join(P13, "b_stage", "%s__%s" % (owner, name))
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        p = os.path.join(src, f)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(dst, f))
    mp = os.path.join(dst, "dataset-metadata.json")
    if os.path.exists(mp):
        m = json.load(io.open(mp, encoding="utf-8"))
    else:
        m = {"licenses": [{"name": "other"}]}
    m["id"] = slug
    m["title"] = title[:50]
    io.open(mp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(m, ensure_ascii=False, indent=1))
    env = env_b()
    rc, out = run(["kaggle", "datasets", "create", "-p", dst], env)
    if "already in use" in out or "already exists" in out.lower():
        rc, out = run(["kaggle", "datasets", "version", "-p", dst, "-m",
                       "copy to accB 22/10"], env)
    print("  %-34s create/version rc=%s | %s" % (slug, rc,
          out.strip()[-120:].replace("\n", " ")), flush=True)
    rc2, out2 = run(["kaggle", "datasets", "status", slug], env, timeout=180)
    print("  -> status: %s" % ("ready" if "ready" in out2.lower()
                               else out2.strip()[-90:]), flush=True)
    return dst


def main():
    jobs = [
        (os.path.join(P13, "lora_v22_dataset"), "dieniw/ornith-gui-lora-v22",
         "Ornith GUI LoRA v22 (adapter)"),
        (os.path.join(P13, "old_bench_ds",
                      "khoadangnguye__ornith-gui-bench-v155-old"),
         "dieniw/ornith-gui-bench-v155-old",
         "Ornith bench B15.5 OLD (truoc 15 fix)"),
    ]
    for src, slug, title in jobs:
        if not os.path.isdir(src):
            print("  !! thieu staging:", src, flush=True)
            continue
        n = len(os.listdir(src))
        mb = sum(os.path.getsize(os.path.join(src, f)) for f in os.listdir(src)
                 if os.path.isfile(os.path.join(src, f))) / 1e6
        print("--- %s (%d file, %.1f MB)" % (slug, n, mb), flush=True)
        push_stage(src, slug, title)
        time.sleep(5)
    print("HOAN TAT", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
