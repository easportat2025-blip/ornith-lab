# -*- coding: utf-8 -*-
"""
cmp_runs.py - so sanh 2 file result bench (cung adapter/harness) de kiem tra
tai lap: wins + breakdown theo task + episode-level.
"""
import io
import json
import sys


def load(p):
    d = json.load(io.open(p, encoding="utf-8"))
    eps = d.get("episodes") or []
    bt = {}
    for e in eps:
        k = e.get("task_id", "?")
        bt.setdefault(k, [0, 0])
        bt[k][1] += 1
        if e.get("win"):
            bt[k][0] += 1
    wins = sum(1 for e in eps if e.get("win"))
    return d, wins, len(eps), bt


def main():
    a, b = sys.argv[1], sys.argv[2]
    da, wa, na, ba = load(a)
    db, wb, nb, bb = load(b)
    print("  A: %s" % a)
    print("     wins %d/%d = %.1f%%  | adapter=%s reason_max=%s t=%.0fs"
          % (wa, na, 100.0 * wa / max(1, na), da.get("adapter"),
             da.get("reason_max"), da.get("t_sec", 0)))
    print("  B: %s" % b)
    print("     wins %d/%d = %.1f%%  | adapter=%s reason_max=%s t=%.0fs"
          % (wb, nb, 100.0 * wb / max(1, nb), db.get("adapter"),
             db.get("reason_max"), db.get("t_sec", 0)))
    print("  --- theo task ---")
    same = True
    for k in sorted(set(ba) | set(bb)):
        x = ba.get(k, [0, 0])
        y = bb.get(k, [0, 0])
        mark = "=" if x == y else ("+" if y[0] > x[0] else "-")
        if x != y:
            same = False
        print("    %-20s A %d/%d   B %d/%d  %s" % (k, x[0], x[1], y[0], y[1],
                                                  mark))
    print("  => %s" % ("IDENTICAL (tai lap tuyet doi)" if same and wa == wb
                        else "KHAC nhau (can xem lai)"))
    return 0


if __name__ == "__main__":
    import os
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
