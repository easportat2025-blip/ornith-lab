# -*- coding: utf-8 -*-
"""
test_gate_g11.py - CHUNG MINH gate G11 chan duoc kernel mount NHAM adapter.

3 tinh huong:
  1) adapter 'dieniw/ornith-gui-lora' (BAI: weights khac v21)  -> phai FAIL
  2) adapter chua co trong registry (chua chung minh)          -> phai WARN
  3) adapter 'dieniw/ornith-gui-lora-v21' (da chung minh)     -> phai PASS
  4) metadata co 'expected_adapter' khac slug attach           -> phai FAIL

Chay: python scripts/test_gate_g11.py
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
SRC = os.path.join(ROOT, "phase13-gui", "kernel_bench_v155_v21new_B")
GATE = os.path.join(ROOT, "scripts", "prepush_gate.py")
PY = sys.executable


def run(d):
    p = subprocess.run([PY, GATE, d], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def variant(adapter, expected=None):
    tmp = tempfile.mkdtemp(prefix="mimo_g11_")
    dst = os.path.join(tmp, "k")
    shutil.copytree(SRC, dst)
    mp = os.path.join(dst, "kernel-metadata.json")
    md = json.load(io.open(mp, encoding="utf-8"))
    md["dataset_sources"] = [adapter if "gui-lora" in d else d
                             for d in md.get("dataset_sources", [])]
    if expected is not None:
        md["expected_adapter"] = expected
    with io.open(mp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(md, fh, ensure_ascii=False, indent=1)
    return tmp, dst


def main():
    if not os.path.isdir(SRC):
        print("FAIL: thieu kernel mau", SRC)
        return 1
    ok = True
    # 1) adapter BAI -> FAIL
    tmp, d = variant("dieniw/ornith-gui-lora")
    out = run(d)
    good = ("G11" in out) and ("FAIL" in out)
    print("[%s] adapter BAI -> phai FAIL%s"
          % ("OK " if good else "FAIL",
             "" if good else " | " + " ".join(
                 l.strip() for l in out.splitlines() if "G11" in l)[:200]))
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    # 2) adapter chua biet -> WARN
    tmp, d = variant("dieniw/ornith-gui-lora-khong-ton-tai")
    out = run(d)
    good = ("G11" in out) and ("WARN" in out)
    print("[%s] adapter chua biet -> phai WARN%s"
          % ("OK " if good else "FAIL", "" if good else ""))
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    # 3) adapter tot -> PASS
    tmp, d = variant("dieniw/ornith-gui-lora-v21")
    out = run(d)
    good = ("G11" in out) and ("KET QUA: 0 FAIL" in out)
    print("[%s] adapter v21 that -> phai PASS" % ("OK " if good else "FAIL"))
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    # 4) expected_adapter sai -> FAIL
    tmp, d = variant("dieniw/ornith-gui-lora-v21",
                     expected="khoadangnguye/ornith-gui-lora-v22")
    out = run(d)
    good = ("G11" in out) and ("FAIL" in out)
    print("[%s] expected_adapter sai -> phai FAIL" % ("OK " if good else "FAIL"))
    ok = ok and good
    shutil.rmtree(tmp, ignore_errors=True)
    print("== %s ==" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
