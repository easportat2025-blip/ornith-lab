# -*- coding: utf-8 -*-
"""
check_queue_targets.py - doi chieu QUEUE voi TARGETS cua watchdog.
Kernel co trong queue nhung THIEU target => ket qua se khong duoc tai ve
(da xay ra >=2 lan: bench-v155-v22-b, sft-v24).

Dung:
    python scripts/check_queue_targets.py          (ca A va B)
    python scripts/check_queue_targets.py B
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAIRS = [
    ("A", "scripts/gpu_queue.json", "scripts/watchdog_targets.json"),
    ("B", "scripts/gpu_queue_B.json", "scripts/watchdog_targets_B.json"),
]


def load(p):
    try:
        return json.load(io.open(os.path.join(ROOT, p.replace("/", os.sep)),
                                 encoding="utf-8"))
    except Exception:
        return []


def main():
    only = (sys.argv[1].upper() if len(sys.argv) > 1 else "")
    n_bad = 0
    for acc, qp, tp in PAIRS:
        if only and acc != only:
            continue
        q = load(qp)
        t = load(tp)
        have = set(x.get("kernel") for x in t if isinstance(x, dict))
        miss = [x.get("id") for x in q
                if isinstance(x, dict) and x.get("id") and x.get("id") not in have]
        print("== acc %s: %d muc queue, %d target" % (acc, len(q), len(t)))
        for m in miss:
            print("   THIEU TARGET: %s" % m)
        if miss:
            n_bad += len(miss)
        else:
            print("   OK: moi kernel trong queue deu co target")
    print("== %d kernel thieu target ==" % n_bad)
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
