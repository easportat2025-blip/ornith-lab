# -*- coding: utf-8 -*-
"""
analyze_desktop_actions.py - PHAN TICH model "lam gi" trong desktop bench
(doc actions.jsonl cua run sac).

Tra ve:
 - ty le buoc lap lai hanh dong truoc do (dong vat lo trong episode)
 - ty le buoc lap lai NGUYEN VAN BAN reasoning (bi ket)
 - phan bo loai hanh dong (click/type/key/done)
 - phan bo "ket thuc bang DONE nhung reward=0" (bo cua)
 - so buoc trung binh / so hanh dong DISTINCT moi episode
 - bang theo task
ASCII-only.
"""
import collections
import io
import json
import os
import re
import sys


def classify(action):
    a = (action or "").strip().upper()
    if a.startswith("CLICK"):
        return "click"
    if a.startswith("TYPE"):
        return "type"
    if a.startswith("KEY"):
        return "key"
    if a.startswith("DONE"):
        return "done"
    return "other"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "phase13-gui/out_desktop_bench_b3/desktop_bench/actions.jsonl"
    eps = collections.defaultdict(list)
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            eps[(d.get("task_id"), d.get("episode"))].append(d)

    tot = rep_act = rep_raw = 0
    types = collections.Counter()
    tasks = collections.defaultdict(lambda: [0, 0, 0, 0, 0])  # ep, win, steps, rep, done0
    dist_list = []
    for (tid, epi), steps in sorted(eps.items()):
        steps.sort(key=lambda s: s.get("step", 0))
        last_a = last_r = None
        rep_a_n = rep_r_n = 0
        for s in steps:
            a = s.get("action") or ""
            r = s.get("raw") or ""
            types[classify(a)] += 1
            tot += 1
            if last_a is not None and a == last_a and a.strip():
                rep_a_n += 1
            if last_r is not None and r == last_r and len(r.strip()) > 20:
                rep_r_n += 1
            last_a, last_r = a, r
        rep_act += rep_a_n
        rep_raw += rep_r_n
        t = tasks[tid]
        t[0] += 1
        t[2] += len(steps)
        t[3] += rep_a_n
        distinct = len(set((s.get("action") or "").strip() for s in steps))
        dist_list.append((tid, epi, len(steps), distinct))
        fin = (steps[-1].get("action") or "").strip().upper()
        rew = steps[-1].get("reward", 0) or 0
        if fin.startswith("DONE") and rew < 1:
            t[4] += 1
        if rew >= 1:
            t[1] += 1

    print("== TONG QUAN (%d episode, %d buoc) ==" % (len(eps), tot))
    print("  buoc LAP LAI HANG DONG truoc do : %d/%d = %.1f%%"
          % (rep_act, tot, 100.0 * rep_act / max(1, tot)))
    print("  buoc LAP LAI NGUYEN VAN reasoning: %d/%d = %.1f%%"
          % (rep_raw, tot, 100.0 * rep_raw / max(1, tot)))
    print("  phan bo loai hanh dong: %s"
          % ", ".join("%s=%d" % (k, v) for k, v in types.most_common()))
    print("  episode KET THUC bang DONE nhung reward<1 (bo cua): %d"
          % sum(v[4] for v in tasks.values()))

    print("\n== THEO TASK ==")
    print("  %-22s %5s %5s %7s %8s %8s" % ("task", "ep", "win", "steps",
                                            "rep_act", "done0"))
    for tid in sorted(tasks):
        e, w, st, rp, d0 = tasks[tid]
        print("  %-22s %5d %5d %7d %8d %8d" % (tid, e, w, st, rp, d0))

    print("\n== EPISODE (buoc / distinct action) ==")
    for tid, epi, st, dist in dist_list:
        print("  %-22s ep%-2d %2d buoc, %2d hanh dong khac nhau%s"
              % (tid, epi, st, dist, "   <-- LOOP" if dist <= max(1, st // 2)
                 else ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
