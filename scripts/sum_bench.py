# -*- coding: utf-8 -*-
"""
sum_bench.py - tom tat 1 file b15_result.json (KHONG in ca file).
In: n_ep, wins, win_rate, per-task wins, va (neu co) cac cluster loi.

Dung: python scripts/sum_bench.py <b15_result.json> [file2 ...]
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(p):
    return json.load(io.open(p, encoding="utf-8", errors="replace"))


def summarize(path):
    d = load(path)
    eps = d.get("episodes") or []
    if isinstance(d, list):
        eps = d
    n = len(eps)
    wins = sum(1 for e in eps if e.get("win") or e.get("success"))
    print("== %s" % os.path.basename(os.path.dirname(path)) or path)
    print("   file : %s" % path)
    print("   n_ep = %d | wins = %d | win_rate = %.1f%%"
          % (n, wins, 100.0 * wins / max(n, 1)))
    by = {}
    for e in eps:
        t = e.get("task_id") or "?"
        a = by.setdefault(t, [0, 0])
        a[0] += 1
        if e.get("win") or e.get("success"):
            a[1] += 1
    for t in sorted(by):
        c, w = by[t]
        print("      %-20s %d/%d" % (t, w, c))
    # clusters (neu co)
    cl = d.get("clusters") or d.get("cluster_counts")
    if cl:
        print("   clusters: %s" % json.dumps(cl, ensure_ascii=False)[:300])
    return n, wins


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/sum_bench.py <b15_result.json> [...]")
        return 2
    for p in sys.argv[1:]:
        try:
            summarize(p)
        except Exception as e:
            print("   %s -> LOI %s: %s" % (p, type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
