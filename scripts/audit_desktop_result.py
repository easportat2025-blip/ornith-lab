# -*- coding: utf-8 -*-
"""
audit_desktop_result.py - audit 1 file desktop_result.json:
  - per-task: n ep / win / trung binh raw co chu "black" (man hinh den)
  - ket luan: ep nao la LOI HA TANG (app thieu -> anh den -> model that)
  - so ep "gia lap" voi mau khac (khac loai)

Dung: python scripts/audit_desktop_result.py <desktop_result.json> [...]
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BLACK = ("black", "completely black", "blank screen", "no content")


def audit(path):
    d = json.load(io.open(path, encoding="utf-8", errors="replace"))
    eps = d.get("episodes") or []
    by = {}
    for e in eps:
        t = e.get("task_id") or "?"
        raw = (e.get("raw_first") or "").lower()
        black = any(b in raw for b in BLACK)
        a = by.setdefault(t, {"n": 0, "win": 0, "black": 0, "sample": ""})
        a["n"] += 1
        if e.get("win"):
            a["win"] += 1
        if black:
            a["black"] += 1
            if not a["sample"]:
                a["sample"] = (e.get("raw_first") or "")[:90].replace("\n", " ")
    print("== %s" % os.path.basename(os.path.dirname(path)))
    print("   n_ep=%d | wins=%d | win_rate=%.1f%%"
          % (len(eps), sum(1 for e in eps if e.get("win")),
             100.0 * sum(1 for e in eps if e.get("win")) / max(len(eps), 1)))
    n_bad = 0
    for t in sorted(by):
        a = by[t]
        flag = ""
        if a["black"] == a["n"] and a["n"] > 0:
            flag = "  <== 100%% EP MANH HINH DEN (LOI HA TANG)"
            n_bad += a["n"]
        elif a["black"]:
            flag = "  <== %d ep den" % a["black"]
            n_bad += a["black"]
        print("   %-20s %d/%d win, %d ep den%s"
              % (t, a["win"], a["n"], a["black"], flag))
        if a["sample"]:
            print("        raw: %s..." % a["sample"])
    print("   => EP LOI HA TANG (anh den, tinh nham la model that): %d/%d (%.0f%%)"
          % (n_bad, len(eps), 100.0 * n_bad / max(len(eps), 1)))
    return n_bad, len(eps)


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/audit_desktop_result.py <desktop_result.json>")
        return 2
    for p in sys.argv[1:]:
        try:
            audit(p)
        except Exception as e:
            print("   %s -> LOI %s: %s" % (p, type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
