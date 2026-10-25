# -*- coding: utf-8 -*-
"""
peek_none_steps.py - xem cac step co mode 'none' (model viet ra KHONG co
action) trong 1 b15_result.json + do dai raw => biet model "im lang" hay
parser that.
ASCII-only source.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = sys.argv[1]
d = json.load(io.open(p, encoding="utf-8", errors="replace"))
eps = d.get("episodes") or []
n_none = 0
shown = 0
for e in eps:
    for st in (e.get("trace") or []):
        if st.get("mode") == "none":
            n_none += 1
            if shown < 6:
                shown += 1
                raw = (st.get("raw") or "")
                print("--- %s v%s step%s | len(raw)=%d | act=%r"
                      % (e.get("task_id"), e.get("variant"), st.get("step"),
                         len(raw), (st.get("act") or "")[:40]))
                print("    tail: %s" % raw[-220:].replace("\n", " | "))
print("TONG step mode=none: %d" % n_none)
