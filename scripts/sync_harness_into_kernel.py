# -*- coding: utf-8 -*-
"""sync_harness_into_kernel.py - cap nhat ban INLINE cua harness.py trong
kernel desktop-bench (Kaggle chi upload code_file -> phai inline).

Dung: python scripts/sync_harness_into_kernel.py
"""
import io
import re
import sys

HP = "phase14-desktop/harness.py"
KP = "phase13-gui/kernel_desktop_bench/desktop_bench_kernel.py"

h = io.open(HP, encoding="utf-8").read()
if "'''" in h:
    print("harness co chuoi ''' -> can cach khac")
    sys.exit(1)
# bo phan doc mo ta dau file de tranh loi dedent
h = h.lstrip("\n")

k = io.open(KP, encoding="utf-8").read()
m = re.search(r"HARNESS_SRC = ", k)
if not m:
    print("khong tim thay HARNESS_SRC")
    sys.exit(1)
# tim het dong gan nhat (ket thuc bang `'` hoac `'''` + newline)
start = m.end()
# dung regex cho 1 phan gan nhat: giu nguyen phan con lai
rest = k[start:]
# xac dinh do dai chuoi gan nhat: quet den dau `'` + newline (hoac ''' + newline)
if rest.startswith("'''"):
    end_rel = rest.find("'''", 3) + 3
    quote = "'''"
else:
    # '...' dang thoat bang \' -> quet
    i = 1
    while i < len(rest):
        if rest[i] == "\\":
            i += 2
            continue
        if rest[i] == "'":
            break
        i += 1
    end_rel = i + 1
    quote = "'"
old = rest[:end_rel]
print("chuoi inline cu: %d char" % len(old))

new = "r'''" + h + "'''"
k2 = k[:start] + new + rest[end_rel:]
io.open(KP, "w", encoding="utf-8", newline="\n").write(k2)
print("da thay bang ban moi: %d char" % len(new))
