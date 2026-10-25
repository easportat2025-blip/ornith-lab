# -*- coding: utf-8 -*-
"""bench_summary.py - in TOM TAT ket qua bench tu file result json (gọn)."""
import glob
import io
import json
import os
import sys

for pat in sys.argv[1:]:
    for p in sorted(glob.glob(pat, recursive=True)):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
        except Exception as e:
            print("  %s -> doc loi: %s" % (p, e))
            continue
        if "episodes" in d and isinstance(d.get("episodes"), list):
            eps = d["episodes"]
            wins = sum(1 for e in eps if e.get("win"))
            n = len(eps)
            print("  %s" % p)
            print("     suite=%s  wins=%d/%d = %.1f%%" % (d.get("suite"), wins, n,
                                                        100.0 * wins / max(1, n)))
            bt = {}
            for e in eps:
                k = e.get("task_id", "?")
                bt.setdefault(k, [0, 0])
                bt[k][1] += 1
                if e.get("win"):
                    bt[k][0] += 1
            for k in sorted(bt):
                w, t = bt[k]
                print("       %-22s %d/%d" % (k, w, t))
            continue
        print("  %s" % p)
        for k in ("suite", "n", "wins", "win_rate", "parse_rate", "prose_leak",
                  "adapter", "reason_max", "t_sec", "mode"):
            if k in d:
                v = d[k]
                if isinstance(v, float):
                    v = round(v, 4)
                print("     %-12s %s" % (k, v))
        if isinstance(d.get("by_task"), dict):
            for k, v in d["by_task"].items():
                if isinstance(v, dict):
                    print("       %-20s %s" % (k, {kk: v[kk] for kk in
                                                 ("wins", "n", "win_rate")
                                                 if kk in v}))
