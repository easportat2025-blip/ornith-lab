# -*- coding: utf-8 -*-
"""append_diary.py - them ghi chu thu cong vao phan NHAT KY cua result.md."""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "result.md")
DS = "<!-- DIARY:BEGIN -->"
DE = "<!-- DIARY:END -->"

text = ""
if len(sys.argv) > 2 and sys.argv[1] == "--file":
    text = io.open(sys.argv[2], encoding="utf-8").read()
elif len(sys.argv) > 1:
    text = sys.argv[1]
if not text:
    raise SystemExit("dung: python scripts/append_diary.py \"<noi dung>\""
                     " | python scripts/append_diary.py --file <path>")
old = io.open(OUT, encoding="utf-8").read()
if DS in old and DE in old:
    a = old.index(DS) + len(DS)
    b = old.index(DE)
    diary = old[a:b].rstrip()
    new = old[:a] + "\n" + text.strip() + "\n" + diary + old[b:]
else:
    new = old + "\n" + DS + "\n" + text.strip() + "\n" + DE + "\n"
io.open(OUT, "w", encoding="utf-8", newline="\n").write(new)
print("result.md: da them ghi chu (%d char)" % len(text))
