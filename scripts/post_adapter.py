# -*- coding: utf-8 -*-
"""
post_adapter.py - tai adapter (LoRA) tu 1 kernel SFT da train xong, va upload
len Kaggle duoi slug adapter, de kernel bench moi (v23/v23a/v23b) mount duoc.

Vong truoc: scripts/post_v22_adapter.ps1 (rieng cho v22, va chay sai key).
B nay: 1 lenh cho moi model, doc key theo acc, verify file that tren remote.

Dung:
    python scripts/post_adapter.py khoadangnguye/ornith-gui-sft-v23 \
        khoadangnguye/ornith-gui-lora-v23
    # them --check de chi xem trang thai (khong upload)
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
P13 = os.path.join(ROOT, "phase13-gui")
FLAGS = 0x08000000 if os.name == "nt" else 0


def sh(cmd, env=None, timeout=3600):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env,
                           timeout=timeout, creationflags=FLAGS)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 1, "EXC %s" % e


def acc_env(owner):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    var = ("KAGGLE_KEY_A" if owner == "khoadangnguye"
           else "KAGGLE_KEY_B" if owner == "dieniw" else "KAGGLE_KEY")
    key = os.environ.get(var, "")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v, _t = winreg.QueryValueEx(k, var)
                key = str(v).strip()
        except Exception:
            key = ""
    if key:
        env["KAGGLE_KEY"] = key
    env["KAGGLE_USERNAME"] = owner
    return env, bool(key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kernel", help="slug kernel SFT (vd khoadangnguye/ornith-gui-sft-v23)")
    ap.add_argument("adapter", help="slug dataset adapter (vd khoadangnguye/ornith-gui-lora-v23)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if "/" not in a.kernel or "/" not in a.adapter:
        print("can owner/slug cho ca hai")
        return 2
    kowner, kslug = a.kernel.split("/", 1)
    aowner, aslug = a.adapter.split("/", 1)
    env, has_key = acc_env(kowner)
    if not has_key:
        print("!! thieu key cho acc '%s' (can %s)" % (kowner, a.owner_key if False else "KAGGLE_KEY_A/B"))
        return 3

    # 1) tai output kernel SFT
    out = a.out or os.path.join(P13, "out_sft_%s" % kslug)
    if os.path.isdir(out):
        shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    print("=== 1) tai output %s ===" % a.kernel)
    rc, out_txt = sh("kaggle kernels output %s -p \"%s\" --force" % (a.kernel, out),
                      env=env)
    print("  " + out_txt.strip()[-200:].replace("\n", " "))
    lora = os.path.join(out, "gui_lora")
    if not os.path.exists(os.path.join(lora, "adapter_config.json")):
        print("!! khong thay gui_lora/adapter_config.json trong output")
        for root, _d, files in os.walk(out):
            for f in files[:10]:
                print("   ", os.path.relpath(os.path.join(root, f), out))
        return 4

    # 2) staging dataset voi id = slug adapter
    stage = os.path.join(P13, "lora_ds_staging", "%s__%s" % (aowner, aslug))
    if os.path.isdir(stage):
        shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)
    for f in os.listdir(lora):
        shutil.copy2(os.path.join(lora, f), os.path.join(stage, f))
    meta = {"title": "Ornith GUI LoRA %s" % aslug, "id": a.adapter,
            "licenses": [{"name": "other"}]}
    with io.open(os.path.join(stage, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    n = len(os.listdir(stage))
    print("=== 2) staging %s (%d file) ===" % (os.path.relpath(stage, ROOT), n))

    if a.check:
        print("(CHECK: khong upload)")
        return 0

    # 3) upload
    print("=== 3) upload dataset %s ===" % a.adapter)
    rc, o = sh("kaggle datasets version -p \"%s\" -m \"adapter %s\""
               % (stage, aslug), env=env)
    if rc != 0:
        print("  version rc=%s -> thu create" % rc)
        rc, o = sh("kaggle datasets create -p \"%s\"" % stage, env=env)
    print("  " + o.strip()[-200:].replace("\n", " "))

    # 4) wait READY + verify file that
    print("=== 4) doi READY + verify file remote ===")
    for i in range(1, 41):
        rc, st = sh("kaggle datasets status %s" % a.adapter, env=env, timeout=300)
        low = st.lower()
        if ("ready" in low or "active" in low) and "processing" not in low:
            print("  READY (%d)" % i)
            break
        time.sleep(15)
    rc, files = sh("kaggle datasets files %s" % a.adapter, env=env, timeout=300)
    names = [l.split()[0] for l in files.splitlines()
             if l.split() and "." in l.split()[0]
             and l.split()[0].lower() not in ("name", "size", "creationdate")]
    print("  file tren remote: %d" % len(names))
    for f in names[:8]:
        print("    -", f)
    if "adapter_config.json" not in names:
        print("  !! FAIL: remote khong co adapter_config.json")
        return 5
    print("  OK: adapter tren Kaggle, san sang cho kernel bench mount")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
