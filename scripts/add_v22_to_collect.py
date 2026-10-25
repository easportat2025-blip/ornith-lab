# -*- coding: utf-8 -*-
"""add_v22_to_collect.py - them ket qua v22 (B15/B15.5/B16) vao collect_results.py
de result.md + bang so sanh co day du cac vong."""
import io

P = "scripts/collect_results.py"
s = io.open(P, encoding="utf-8").read()
anchor = '    ("v21", "phase13-gui/out_bench_v155_v21/b15_result.json", "B15.5"),'
add = ('    ("v22", "phase13-gui/out_bench_v22/b15_result.json", "B15"),\n'
       '    ("v22", "phase13-gui/out_bench_v155_v22/b15_result.json", "B15.5"),\n'
       '    ("v22", "phase13-gui/out_bench_v16_v22/b15_result.json", "B16"),\n')
if '"v22"' not in s:
    if anchor in s:
        s = s.replace(anchor, add + anchor)
        io.open(P, "w", encoding="utf-8", newline="\n").write(s)
        print("da them 3 muc v22 vao collect")
    else:
        print("!! khong tim thay anchor")
else:
    print("da co san muc v22")
