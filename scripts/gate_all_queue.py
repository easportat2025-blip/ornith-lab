# -*- coding: utf-8 -*-
"""
gate_all_queue.py - chay prepush_gate.py cho TAT CA muc trong queue (A va B)
de biet muc nao se bi gate chan TRUOC khi watchdog restart (gate moi G11/G12).

Dung: python scripts/gate_all_queue.py [A|B]
ASCII-only source.
"""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def main():
    which = (sys.argv[1] if len(sys.argv) > 1 else "B").upper()
    qp = os.path.join(ROOT, "scripts",
                      "gpu_queue_B.json" if which == "B" else "gpu_queue.json")
    q = json.load(io.open(qp, encoding="utf-8"))
    n_ok = n_bad = 0
    for item in q:
        kid = item.get("id", "")
        d = item.get("dir", "")
        if not d:
            print("   [??] %-46s (khong co dir)" % kid)
            continue
        p = subprocess.run([PY, os.path.join(ROOT, "scripts", "prepush_gate.py"),
                            d], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        blob = (p.stdout or "") + (p.stderr or "")
        ok = "KET QUA: 0 FAIL" in blob
        fails = [l.strip() for l in blob.splitlines()
                 if l.strip().startswith("FAIL") or " FAIL " in l]
        print("   [%s] %-46s %s" % ("OK " if ok else "FAIL", kid,
                                    "" if ok else fails[0][:120] if fails else ""))
        if ok:
            n_ok += 1
        else:
            n_bad += 1
    print("== queue %s: %d OK, %d FAIL ==" % (which, n_ok, n_bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
