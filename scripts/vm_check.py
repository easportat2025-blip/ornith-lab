# -*- coding: utf-8 -*-
"""vm_check.py - in trang thai VM (dung de debug, khong can token swap)."""
import os
log = "/content/out.log"
pidf = "/content/job.pid"
alive = False
try:
    pid = int(open(pidf).read().strip())
    os.kill(pid, 0)
    alive = True
except Exception as e:
    print("pid check:", e)
size = os.path.getsize(log) if os.path.exists(log) else 0
print("ALIVE=%s SIZE=%d" % ("1" if alive else "0", size))
print("files in /content:")
for f in sorted(os.listdir("/content")):
    p = os.path.join("/content", f)
    if os.path.isfile(p):
        print("   %-30s %d" % (f, os.path.getsize(p)))
    elif os.path.isdir(p):
        print("   %-30s <dir>" % f)
# print last 5 lines of the log
if os.path.exists(log):
    lines = open(log, encoding="utf-8", errors="replace").read().splitlines()
    print("=== log tail ===")
    for l in lines[-6:]:
        print("   ", l[:150])
