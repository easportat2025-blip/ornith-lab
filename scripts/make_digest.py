# -*- coding: utf-8 -*-
"""make_digest.py - tao LOBBY_DIGEST.md: ban TOM TAT de DOC DUOC (agent.md viet
ky thuat + ky tu la, hay bi loi font khi mo bang trinh xem cu).

Chay: python scripts/make_digest.py [--lines 120]
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agent.md")
OUT = os.path.join(ROOT, "LOBBY_DIGEST.md")

n = 120
if "--lines" in sys.argv:
    n = int(sys.argv[sys.argv.index("--lines") + 1])

s = io.open(SRC, encoding="utf-8", errors="replace").read()
# chi giu phan LOBBY (bo phan LUAT CUNG o dau + danh b)
i = s.find("## ")
if i > 0:
    body = s[i:]
else:
    body = s
lines = [l for l in body.splitlines() if l.strip()]
tail = lines[-n:]

head = """# LOBBY - BAN TOM TAT (doc file nay thay vi agent.md)

> File nay sinh tu dong tu `agent.md` bang `python scripts/make_digest.py`.
> `agent.md` la ban append-only day du (co phan LUAT CUNG + ky tu ky thuat);
> file nay chi gom phan LOBBY, doc de trong.
> Tin moi nhat cung duoc gui qua BUS (nhan trong ~1 giay).

"""
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(head + "\n".join(tail) + "\n")
print("LOBBY_DIGEST.md: %d dong" % len(tail))
