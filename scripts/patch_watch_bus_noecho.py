# -*- coding: utf-8 -*-
# patch_watch_bus_noecho.py - watch_bus khong day tin cua chinh "DeepSeek" vao
# session cua ta (tranh echo), van day tin cua agent khac.
import io

P = "scripts/watch_bus.py"
s = io.open(P, encoding="utf-8").read()
OLD = '''def handle(m):
    txt = "[BUS %s%s] %s" % (m.get("from", "?"),'''
NEW = '''SELF = os.environ.get("BUS_SELF", "DeepSeek")


def handle(m):
    if m.get("from") == SELF and os.environ.get("BUS_NO_ECHO", "1") == "1":
        # tin cua chinh ta: da gui truc tiep vao session agent khuc roi
        log("(bo echo tin cua ta: %s)" % str(m.get("text", ""))[:60])
        return
    txt = "[BUS %s%s] %s" % (m.get("from", "?"),'''
if OLD in s:
    s = s.replace(OLD, NEW, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da them: bo echo tin cua ta")
else:
    print("khong khop (co the da sua)")
