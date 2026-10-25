# -*- coding: utf-8 -*-
"""
peek_loader_action.py - tim cach loader lay "action" tu row + loc row rong
(nghi do: commit_rate giam 15,1 diem, C1_no_action +3 o v24).
ASCII-only source.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, "phase13-gui", "kernel_v24", "gui_sft_v23.py")
s = io.open(p, encoding="utf-8", errors="replace").read()
pat = sys.argv[1] if len(sys.argv) > 1 else "action"
for i, line in enumerate(s.split("\n"), 1):
    ls = line.strip()
    if re.search(pat, ls, re.I) and any(
            k in ls for k in ("def ", "action", "row")):
        print("L%-5d %s" % (i, ls[:120]))
