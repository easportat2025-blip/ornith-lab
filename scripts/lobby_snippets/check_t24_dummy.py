# -*- coding: utf-8 -*-
import io
import re
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

app = io.open(r"C:\Users\Admin\Desktop\New folder\phase13-gui\kernel_desktop_bench\apps\t24_text_edit.html",
              encoding="utf-8", errors="replace").read()
print("=== app T24: WANT ===")
for m in re.finditer(r".{0,90}WANT\s*=.{0,90}", app):
    print("   ", m.group(0).replace("\n", " | ")[:170])
    break
for m in re.finditer(r"(?i)wants?\s*=\s*\[.{0,120}", app):
    print("   ", m.group(0).replace("\n", " | ")[:170])
    break

k = io.open(r"C:\Users\Admin\Desktop\New folder\phase13-gui\kernel_desktop_bench_a\desktop_bench_kernel.py",
            encoding="utf-8", errors="replace").read()
print()
print("=== dummy: hardcode 'Hotfix export...' trong kernel? ===")
i = k.find("Hotfix export")
print("   ", ("CO tai kernel dong %d" % (k[:i].count("\n") + 1)) if i > 0 else "KHONG co")
if i > 0:
    seg = k[max(0, i - 700):i + 200]
    print("   context:", seg.replace("\n", " | ")[-420:])
print()
print("=== dummy: co doc #want khong? ===")
for pat in ("want", "t24", "text_edit"):
    ms = [m.start() for m in re.finditer(pat, k)][:4]
    print("   %-10s so lan: %d" % (pat, len(ms)))
    for j in ms[:2]:
        ln = k[:j].count("\n") + 1
        print("      L%-5d %s" % (ln, k.splitlines()[ln - 1].strip()[:95]))
