# -*- coding: utf-8 -*-
"""show_region.py - in 1 vung cua file theo vi tri can (tranh loi quoting PS)."""
import io
import sys

P = sys.argv[1]
needle = sys.argv[2]
before = int(sys.argv[3]) if len(sys.argv) > 3 else 200
after = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
s = io.open(P, encoding="utf-8").read()
i = s.find(needle)
if i < 0:
    raise SystemExit("khong tim thay: " + needle)
print(s[max(0, i - before):i + after])
