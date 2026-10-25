# -*- coding: utf-8 -*-
"""
make_kernel_old_suite.py - tao kernel bench_v155_v22_old: do "model v22 tren
task B15.5 CU" = O CON THIEU cua thu nghiem 2x2 ( tach phan sua loi sinh
voi phan sua 15 fix task).

Ly do: B15.5 v21 -> v22 tang +50 diem nhung do CHUNG 2 nguyen nhan:
  (a) sua loi sinh (buoc rong 55,8% -> 0%)
  (b) sua 15 fix task
=> khong tach duoc. Bang 2x2:
            task CU      task MOI
   v21      5,6% (co)    -
   v22      (THIEU)      55,6% (co)
=> can mot run: model v22 + task CU.

Co che: kernel `suite_load()` tim thu muc theo `tasks.json` (khong quan tam
ten slug) => chi can mount dataset ban CU (slug moi ...-bench-v155-old) va
doi dataset_sources cua kernel.
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
SRC = os.path.join(ROOT, "phase13-gui", "kernel_bench_v155_v22")
DST = os.path.join(ROOT, "phase13-gui", "kernel_bench_v155_v22_old")
OLD_DS = "khoadangnguye/ornith-gui-bench-v155-old"
NEW_DS = "khoadangnguye/ornith-gui-bench-v155"

if os.path.isdir(DST):
    shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST, exist_ok=True)
code = [f for f in os.listdir(SRC) if f.endswith(".py")]
for f in code:
    shutil.copy2(os.path.join(SRC, f), os.path.join(DST, f))
md = json.load(io.open(os.path.join(SRC, "kernel-metadata.json"), encoding="utf-8"))
ds = md.get("dataset_sources", [])
if NEW_DS not in ds:
    print("CANH BAO: khong thay %s trong dataset_sources" % NEW_DS)
md["dataset_sources"] = [OLD_DS if d == NEW_DS else d for d in ds]
md["id"] = "khoadangnguye/ornith-gui-bench-v155-v22-old"
md["title"] = "ornith-gui-bench-v155-v22-old"
with io.open(os.path.join(DST, "kernel-metadata.json"), "w",
             encoding="utf-8", newline="\n") as fh:
    json.dump(md, fh, ensure_ascii=False, indent=1)
print("da tao: %s" % os.path.relpath(DST, ROOT))
print("  id      : %s" % md["id"])
print("  dataset : %s (thay cho %s)" % (OLD_DS, NEW_DS))
print("  code    : %s" % code)
print()
print("=== 2 LENH (can key acc A) ===")
print('  1) kaggle datasets create -p "phase13-gui/old_bench_ds/'
      'khoadangnguye__ornith-gui-bench-v155-old"')
print("  2) kaggle kernels push -p phase13-gui/kernel_bench_v155_v22_old")
print("  => ket qua se ve phase13-gui/out_bench_v155_v22_old/ (theo watchdog)")
