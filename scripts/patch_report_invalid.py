# -*- coding: utf-8 -*-
"""
patch_report_invalid.py - loai khoi bang 2x2 cac run acc B da chay adapter
SAI (dieniw/ornith-gui-lora = adapter CU, khong phai v21):
  out_bench_v155_B (0/18) va out_bench_v16_B (6/24)
Bang ket qua: khong duoc dung lam baseline v21.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "report_fixed_suite.py")

OLD = '''        ("v21 (buoc rong cao)",
         ["phase13-gui/out_bench_v155_v21/b15_result.json",
          "phase13-gui/out_bench_v155_B/b15_result.json"],
         ["phase13-gui/out_bench_v155_v21new_B/b15_result.json"]),
'''
NEW = '''        ("v21 (buoc rong cao)",
         # KHONG dung out_bench_v155_B: run do mount 'dieniw/ornith-gui-lora'
         # (adapter CU, KHONG phai v21 - so trong so max|diff|=0.11) => invalid.
         ["phase13-gui/out_bench_v155_v21/b15_result.json"],
         ["phase13-gui/out_bench_v155_v21new_B/b15_result.json"]),
'''

OLD2 = '''    print("   => o 'v22 tren task CU' = kernel acc B 'ornith-gui-bench-v155-v22old'")
'''
NEW2 = '''    print("   => o 'v22 tren task CU' = kernel acc B 'ornith-gui-bench-v155-v22-old'")
    print("   => o 'v21 tren task MOI' = kernel acc B "
          "'ornith-gui-bench-v155-v21new' (da them vao queue B)")
    print("   !! out_bench_v155_B / out_bench_v16_B KHONG hop le: adapter "
          "'dieniw/ornith-gui-lora' khong phai v21 (max|diff|=0.11) -> "
          "khong dung lam baseline")
'''

s = io.open(P, encoding="utf-8", newline="").read()
if "out_bench_v155_B/b15_result.json" not in s:
    print("da sua roi (hoac khong can sua)")
    sys.exit(0)
if OLD not in s:
    print("FAIL: khong tim thay khoi grid")
    sys.exit(1)
s = s.replace(OLD, NEW, 1)
if OLD2 in s:
    s = s.replace(OLD2, NEW2, 1)
else:
    print("WARN: khong tim thay dong note (van sua grid)")
with io.open(P, "w", encoding="utf-8", newline="") as fh:
    fh.write(s)
print("da sua:", P)
