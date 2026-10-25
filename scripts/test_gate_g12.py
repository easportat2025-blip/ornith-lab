# -*- coding: utf-8 -*-
"""
test_gate_g12.py - CHUNG MINH gate G12 bat loi "code doi adapter, metadata doi
adapter" TRUOC khi push (loi da lam kernel desktop b3 chet 18' GPU).

Tinh huong:
  1) code require 'ornith-gui-lora-v21', metadata attach '...lora-v22' -> FAIL
  2) code require dataset khong attach (bat ky ten)               -> FAIL
  3) code require dataset co attach                              -> PASS
  4) bien ADAPTER_NAME -> 'ornith-gui-lora-v22' (resolve)         -> FAIL
     (truoc khi sua: code require lora-v21, metadata mount lora-v22)

Chay: python scripts/test_gate_g12.py
ASCII-only source.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "kernel_desktop_bench_b3")
GATE = os.path.join(ROOT, "scripts", "prepush_gate.py")
PY = sys.executable


def run(d):
    p = subprocess.run([PY, GATE, d], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def variant(req_name=None, drop=None, var=None):
    """req_name: doi chuoi trong require_datasets; drop: bo dataset khoi metadata;
    var: gan lai bien ADAPTER_NAME trong source."""
    tmp = tempfile.mkdtemp(prefix="mimo_g12_")
    dst = os.path.join(tmp, "k")
    shutil.copytree(SRC, dst)
    cp = os.path.join(dst, "desktop_bench_kernel.py")
    s = io.open(cp, encoding="utf-8", errors="replace").read()
    if req_name:
        s = s.replace('ADAPTER_NAME = "ornith-gui-lora-v22"',
                      'ADAPTER_NAME = "%s"' % req_name)
    if var:
        s = s.replace('ADAPTER_NAME = "ornith-gui-lora-v22"',
                      'ADAPTER_NAME = "%s"' % var)
    io.open(cp, "w", encoding="utf-8", newline="\n").write(s)
    mp = os.path.join(dst, "kernel-metadata.json")
    md = json.load(io.open(mp, encoding="utf-8"))
    if drop:
        md["dataset_sources"] = [d for d in md.get("dataset_sources", [])
                                 if drop not in d]
    io.open(mp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(md, ensure_ascii=False, indent=1))
    return tmp, dst


def main():
    if not os.path.isdir(SRC):
        print("FAIL: thieu kernel mau", SRC)
        return 1
    ok = True
    # 1) code doi adapter v21, metadata v22 -> FAIL
    tmp, d = variant(req_name="ornith-gui-lora-v21")
    out = run(d)
    good = ("G12" in out) and ("FAIL" in out)
    print("[%s] code doi adapter (v21) vs metadata (v22) -> phai FAIL"
          % ("OK " if good else "FAIL"))
    if not good:
        print("      " + " ".join(l.strip() for l in out.splitlines()
                                  if "G12" in l)[:220])
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    # 2) dataset khong attach -> FAIL
    tmp, d = variant(drop="ornbase-s2")
    out = run(d)
    good = ("G12" in out) and ("FAIL" in out)
    print("[%s] dataset bi thieu khoi metadata -> phai FAIL"
          % ("OK " if good else "FAIL"))
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    # 3) het -> PASS
    tmp, d = variant()
    out = run(d)
    good = ("G12" in out) and ("KET QUA: 0 FAIL" in out)
    print("[%s] khop het -> phai PASS" % ("OK " if good else "FAIL"))
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    print("== %s ==" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
