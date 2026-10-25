# -*- coding: utf-8 -*-
"""bus_digest.py - doc bus theo yeu cau (pull), thay vi push moi tin.

Tu 23/10: bus chi push tin critical/targeted vao session; tin thuong nam
trong bus.jsonl + phong OpenChat. Khi can tong hop:

    python scripts/bus_digest.py                 # 8 gio gan nhat
    python scripts/bus_digest.py --hours 24 --max 30
    python scripts/bus_digest.py --sender MiMo
"""
import argparse
import io
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "bus.jsonl")
sys.path.insert(0, HERE)
import bus_policy  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=8)
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--sender", default="")
    a = ap.parse_args()

    cut = time.time() - a.hours * 3600
    rows = []
    try:
        with io.open(LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if m.get("ts", 0) < cut:
                    continue
                if a.sender and bus_policy.norm(m.get("from")) != \
                        bus_policy.norm(a.sender):
                    continue
                rows.append(m)
    except Exception as e:
        print("FAIL doc bus: %s" % e)
        return 1

    cnt = Counter(bus_policy.classify(m.get("text"), m.get("priority"))
                  for m in rows)
    print("== %d tin trong %.1f gio | %s" % (len(rows), a.hours, dict(cnt)))
    per = Counter((m.get("from") or "?") for m in rows)
    print("   nguoi gui: %s" % dict(per.most_common(8)))
    for m in rows[-a.max:]:
        t = (m.get("text") or "").replace("\n", " ")
        pri = bus_policy.classify(t, m.get("priority"))
        print("\n[%s] %s (%s)%s\n  %s"
              % (time.strftime("%d/%m %H:%M", time.localtime(m.get("ts", 0))),
                 m.get("from", "?"), pri,
                 (" -> " + m.get("to")) if m.get("to") else "",
                 t[:300]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
