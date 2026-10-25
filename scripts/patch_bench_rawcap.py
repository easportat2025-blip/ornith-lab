# -*- coding: utf-8 -*-
"""
patch_bench_rawcap.py - sua gioi han 300 ky tu trong vie luu 'raw' cua bench
kernel (2 cho: trace + episode state).

LY DO (22/10, @MiMo): analyzer (analyze_bench_result.py) PARSE LAI raw de tinh
mode/cluster/commit. raw bi cat con 300 ky tu => khi model viet prosE dai
(cong > 300 ky tu) thi dong ACTION bi cat mat => analyzer thay "mode=none"
=> COMMIT RATE giam + C1_no_action tang => PHANTOM (khong phai model that).
Vi du do duoc: v24 raw len=300 dung o 28 step, action thuc thi VAN DUNG
(action parse tu `ans` day du) => chi metric sai.
FIX: luu 4000 ky tu (khong ton GPU, chi them ~1KB/row).

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P13 = os.path.join(ROOT, "phase13-gui")
TARGETS = [
    "kernel_bench_v155_v22", "kernel_bench_v155_v21", "kernel_bench_v16_v22",
    "kernel_bench_v155_v22_old", "kernel_bench_v155_v21new_B",
    "kernel_bench_v155_v24_B", "kernel_bench_v16_v24_B", "kernel_bench_v22",
    "kernel_bench_v16_v21", "kernel_bench_v155_v22_old_b",
]
n_files = 0
n_repl = 0
for k in TARGETS:
    d = os.path.join(P13, k)
    for f in os.listdir(d) if os.path.isdir(d) else []:
        if not f.endswith(".py"):
            continue
        p = os.path.join(d, f)
        s = io.open(p, encoding="utf-8", errors="replace").read()
        if '"raw": ans[:300]' not in s:
            continue
        s2 = s.replace('"raw": ans[:300]', '"raw": ans[:4000]')
        with io.open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(s2)
        n_files += 1
        n_repl += s.count('"raw": ans[:300]')
        print("   sua %s/%s" % (k, f))
print("=> %d file, %d cho da doi 300 -> 4000" % (n_files, n_repl))
if n_files == 0:
    print("!! khong sua gi - can kiem tra lai")
    sys.exit(1)
