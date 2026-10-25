# -*- coding: utf-8 -*-
"""inspect_desktop_actions.py - xem cac hanh dong 'other' + mau episode T21."""
import collections
import io
import json
import os
import sys

P = "phase13-gui/out_desktop_bench_b3/desktop_bench/actions.jsonl"


def kind(a):
    u = (a or "").strip().upper()
    if u.startswith("CLICK"):
        return "click"
    if u.startswith("TYPE"):
        return "type"
    if u.startswith("KEY"):
        return "key"
    if u.startswith("DONE"):
        return "done"
    return "OTHER"


def main():
    others = collections.Counter()
    types = collections.Counter()
    ep = []
    for l in io.open(P, encoding="utf-8"):
        l = l.strip()
        if not l:
            continue
        d = json.loads(l)
        a = (d.get("action") or "").strip()
        k = kind(a)
        types[k] += 1
        if k == "OTHER":
            others[a[:70]] += 1
        if d.get("task_id") == "T21_form_desktop" and d.get("episode") == 0:
            ep.append(d)
    print("  phan bo:", dict(types))
    print()
    print("  cac chuoi 'other' (theo tan suat):")
    for a, c in others.most_common(15):
        print("    %3d x %r" % (c, a))
    print()
    print("  === episode T21_form_desktop ep0: %d buoc ===" % len(ep))
    for d in ep[:8]:
        print("   step%-3d act=%-18s desc=%-22s raw=%s"
              % (d.get("step"), str(d.get("action"))[:18],
                 str(d.get("act_desc"))[:22],
                 str(d.get("raw"))[:120].replace("\n", " | ")))
    if len(ep) > 8:
        print("   ...")
        for d in ep[-2:]:
            print("   step%-3d act=%-18s desc=%-22s raw=%s"
                  % (d.get("step"), str(d.get("action"))[:18],
                     str(d.get("act_desc"))[:22],
                     str(d.get("raw"))[:120].replace("\n", " | ")))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
