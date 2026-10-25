# -*- coding: utf-8 -*-
"""Đo xem cac output KHONG parse duoc cua model co the 'salvage' bang
heuristic khong (vi du 'Pressing the right arrow key' -> KEY right)."""
import io
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"

ARROW = re.compile(r"(?:press|presses|pressing|use|using|hit|choose|select)\s+the\s+"
                    r"(left|right|up|down)\s*(?:arrow)?\s*key", re.I)
ARROW2 = re.compile(r"\b(left|right|up|down)\s+arrow\s+key\b", re.I)
CLICKX = re.compile(r"click(?:ing)?\s+(?:on\s+)?(?:the\s+)?['\"]?([\w \-]{2,25})", re.I)
TYPEX = re.compile(r"type(?:ing)?\s+['\"]?([\w@.\-]{2,30})", re.I)

for lbl, p in (("A", "phase13-gui/out_desktop_bench_a/desktop_bench/desktop_result.json"),
               ("B2", "phase13-gui/out_desktop_bench_b2/desktop_bench/desktop_result.json")):
    d = json.load(io.open(os.path.join(ROOT, p.replace("/", os.sep)), encoding="utf-8"))
    eps = d.get("episodes") or []
    n_act = 0
    n_unparsed = 0
    n_salv_arrow = 0
    n_salv_any = 0
    for e in eps:
        for a in (e.get("actions") or []):
            n_act += 1
            s = str(a)
            first = s.split()[0] if s.strip() else ""
            if first in ("CLICK", "KEY", "TYPE", "SCROLL", "DONE", "MOVE", "DRAG"):
                continue
            n_unparsed += 1
            if ARROW.search(s) or ARROW2.search(s):
                n_salv_arrow += 1
            if ARROW.search(s) or ARROW2.search(s) or CLICKX.search(s) or TYPEX.search(s):
                n_salv_any += 1
    print("=" * 74)
    print("%s: %d action | KHONG parse: %d (%.1f%%) | trong do salvage duoc:"
          % (lbl, n_act, n_unparsed, 100.0 * n_unparsed / max(1, n_act)))
    print("   co 'press the <dir> arrow key' : %d (%.1f%% cua toan bo action)"
          % (n_salv_arrow, 100.0 * n_salv_arrow / max(1, n_act)))
    print("   co the heuristic nao (arrow/click/type): %d (%.1f%%)"
          % (n_salv_any, 100.0 * n_salv_any / max(1, n_act)))
    print("   => parse_rate hien tai %.1f%% -> neu salvage het: %.1f%%" % (
        100.0 * (1 - n_unparsed / max(1, n_act)),
        100.0 * (1 - (n_unparsed - n_salv_any) / max(1, n_act))))
