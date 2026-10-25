# -*- coding: utf-8 -*-
"""
patch_bench_rawcap_all.py - sua gioi han 300 ky tu (raw) trong TAT CA file
kernel bench/rollout tren dia (phase13-gui + phase14-space).

LY DO (22/10, @MiMo): xem patch_bench_rawcap.py (giai thich). "raw" bi cat
300 ky tu => analyzer parse lai raw bi cat => mode/commit/cluster SAI (phantom)
=> moi kernel dung cap 300 deu can sua truoc khi do lai.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
ROOTS = ["phase13-gui", "phase14-space"]
OLD = '"raw": ans[:300]'
NEW = '"raw": ans[:4000]'
n_files = 0
n_repl = 0
for r in ROOTS:
    base = os.path.join(ROOT, r)
    if not os.path.isdir(base):
        continue
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dirpath, f)
            try:
                s = io.open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if OLD not in s:
                continue
            n = s.count(OLD)
            with io.open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(s.replace(OLD, NEW))
            n_files += 1
            n_repl += n
            print("   %s" % os.path.relpath(p, ROOT))
print("=> %d file, %d cho da doi 300 -> 4000" % (n_files, n_repl))
