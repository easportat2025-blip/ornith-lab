# -*- coding: utf-8 -*-
"""klog2.py - doc log kernel Kaggle (JSON dong) va in cac dong khop mau."""
import io
import json
import re
import sys


def events(path):
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    out = []
    # 1) ca file la 1 JSON array
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            for o in arr:
                if isinstance(o, dict):
                    out.append((o.get("stream_name", "?"), str(o.get("data", ""))))
            return out
    except Exception:
        pass
    # 2) fallback: tung dong JSON
    buf = ""
    for line in raw.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        buf += line
        try:
            o = json.loads(buf)
            buf = ""
            out.append((o.get("stream_name", "?"), str(o.get("data", ""))))
        except Exception:
            if len(buf) > 20000:
                buf = ""
    return out


def main():
    path = sys.argv[1]
    pats = sys.argv[2:] or [""]
    ev = events(path)
    print("  so su kien: %d" % len(ev))
    for stream, data in ev:
        for line in data.split("\n"):
            line = line.strip()
            if not line:
                continue
            if any(re.search(p, line, re.I) for p in pats):
                print("   [%s] %s" % (stream[:3], line[:170]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
