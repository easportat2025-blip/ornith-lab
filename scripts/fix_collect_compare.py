# -*- coding: utf-8 -*-
"""fix_collect_compare.py - phan so sanh trong collect_results.py phai so
v22 (moi nhat) voi v18 (baseline), va them ca v21.
"""
import io

P = "scripts/collect_results.py"
s = io.open(P, encoding="utf-8").read()
old = '''base = {(m, s): st for m, s, _p, st in rows if m == "v18"}
for model, suite, path, st in rows:
    if model != "v21" or "raw" in st:
        continue
    b = base.get(("v18", suite))
    if not b or "raw" in b:
        continue
    d = st["rate"] - b["rate"]
    print("SO SANH %-8s v21 %.3f vs v18 %.3f  => %+.1f%%  %s" % (
        suite, st["rate"], b["rate"], 100 * d, "TOT" if d > 0 else "XAU"))'''
new = '''base = {(m, s): st for m, s, _p, st in rows if m == "v18"}
for model in ("v22", "v21"):
    for suite in ("B15", "B15.5", "B16", "3D"):
        st = next((r[3] for r in rows if r[0] == model and r[1] == suite
                   and "raw" not in r[3]), None)
        b = base.get(("v18", suite))
        if not st or not b or "raw" in b:
            continue
        d = st["rate"] - b["rate"]
        print("SO SANH %-8s %s %.3f vs v18 %.3f  => %+.1f%%  %s" % (
            suite, model, st["rate"], b["rate"], 100 * d,
            "TOT" if d > 0 else "XAU"))'''
if old in s:
    s = s.replace(old, new)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da sua phan so sanh")
else:
    print("!! khong khop - can sua tay")
