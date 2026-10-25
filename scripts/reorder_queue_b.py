# -*- coding: utf-8 -*-
"""
reorder_queue_b.py - sap xep queue GPU acc B theo uu tien do LOC (khong dung
file dung chung cua agent khac).

UU TIEN (22/10, @MiMo):
  0) sft-v24           - train model moi (gia tri lon nhat)
  1) o 2x2 (v22,CU)   - dang chay
  2) B16-A task moi   - dang chay
  3) o THIEU 2x2 (v21, task MOI)  -> tach 'sua task' vs 'sua data'
  4) desktop-bench b3 (fix anh den + guard)
  5) baseline v21 tren acc B (b1 x2) - replication
  6) 3d benches
  7) replication 55,6% (v22 task MOI tren acc B)

Dung: python scripts/reorder_queue_b.py
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "scripts", "gpu_queue_B.json")


def prio(k):
    if "sft-v24" in k:
        return 0
    if "v22-old" in k:
        return 1
    if "bench-v16-v22b" in k:
        return 2
    if "v21new" in k:
        return 3
    if "desktop-bench-b3" in k:
        return 4
    if "bench-v155-b1" in k or "bench-v16-b1" in k:
        return 5
    if "bench-3d" in k:
        return 6
    return 7


def main():
    q = json.load(io.open(P, encoding="utf-8"))
    before = [x.get("id") for x in q]
    q.sort(key=lambda x: prio(x.get("id", "")))
    with io.open(P, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(q, fh, ensure_ascii=False, indent=1)
    print("thu tu moi queue B (%d muc):" % len(q))
    for i, x in enumerate(q):
        print("   %d. p=%d %s" % (i + 1, prio(x.get("id", "")), x.get("id")))
    print("--- truoc:")
    for b in before:
        print("   %s" % b)
    return 0


if __name__ == "__main__":
    sys.exit(main())
