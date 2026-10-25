# -*- coding: utf-8 -*-
"""patch_watchdog_bus.py - noi watchdog vao BUS (thong bao ngay lap tuc)."""
import io

P = "scripts/watchdog.py"
s = io.open(P, encoding="utf-8").read()

# 1) poll nhanh hon
if "POLL_SEC = int(" not in s:
    s = s.replace("POLL_SEC = 120",
                  'POLL_SEC = int(os.environ.get("POLL_SEC", "60"))')

# 2) bus khi kernel xong
old1 = ('                    log("%s (%s) fetch %s %s" % (label, st,\n'
        '                                                 "OK" if ok else "FAIL", detail))')
new1 = (old1 + '\n'
        '                    bus_post("[watchdog] %s (%s) XONG - ket qua da tai ve: %s"\n'
        '                             % (label, st, detail[:200]), tag="kernel")')
if "bus_post(\"[watchdog] %s (%s) XONG" not in s:
    assert old1 in s, "khong tim thay fetch log"
    s = s.replace(old1, new1)

# 3) bus khi push xong
old2 = ('        log("queue %s push %s %s" % (kid, "OK" if ok else "FAIL",\n'
        '                                     blob[-200:].replace("\\n", " ")))')
new2 = (old2 + '\n'
        '        bus_post("[watchdog] push %s %s" % (kid, "OK" if ok else "FAIL"),\n'
        '                 tag="queue")')
if 'bus_post("[watchdog] push %s' not in s:
    assert old2 in s, "khong tim thay push log"
    s = s.replace(old2, new2)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("watchdog -> da noi BUS")
for l in s.splitlines():
    if "POLL_SEC =" in l or "bus_post(" in l:
        print("   ", l.strip()[:100])
