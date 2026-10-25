# -*- coding: utf-8 -*-
"""Tim ban traj.jsonl co 972 row / 216 DONE (ban R2) trong repo."""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
hits = []
for root, dirs, files in os.walk(ROOT):
    if "node_modules" in root or "\\.git" in root:
        dirs[:] = []
        continue
    for f in files:
        if f != "traj.jsonl":
            continue
        p = os.path.join(root, f)
        try:
            n = 0
            done = 0
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    n += 1
                    if '"DONE"' in line or '"action": "DONE"' in line:
                        done += 1
        except Exception:
            continue
        hits.append((n, done, os.path.relpath(p, ROOT), os.path.getmtime(p)))
hits.sort(reverse=True)
print("%-8s %-8s %s" % ("rows", "DONE?", "path"))
for n, done, p, mt in hits[:14]:
    import time
    print("%-8d %-8s %s   (%s)" % (n, done, p, time.strftime("%m-%d %H:%M",
                                                         time.localtime(mt))))
