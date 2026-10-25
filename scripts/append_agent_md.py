# -*- coding: utf-8 -*-
"""Append mot doan thong diep vao agent.md (sổ cái append-only).
Dung: python scripts/append_agent_md.py <file_voi_noi_dung>"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
AGENT_MD = os.path.join(ROOT, "agent.md")
src = sys.argv[1]
txt = io.open(src, encoding="utf-8").read()
if not txt.endswith("\n"):
    txt += "\n"
with io.open(AGENT_MD, "a", encoding="utf-8", newline="\n") as fh:
    fh.write("\n" + txt)
print("appended %d char -> agent.md (size %d)" % (len(txt), os.path.getsize(AGENT_MD)))
