# -*- coding: utf-8 -*-
"""
fix_3d_b_adapter.py - sua 2 kernel 3D phia acc B dang mount adapter BAI
('dieniw/ornith-gui-lora' = weights khac v21) -> 'dieniw/ornith-gui-lora-v21'
(trong so giong het acc A, da do bang fingerprint tensor).

Do gate G11 phat hien (22/10, @MiMo): 2 kernel nay se do SAI MODEL ma khong
ai biet => sua truoc khi watchdog push.

Dung: python scripts/fix_3d_b_adapter.py
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P13 = os.path.join(ROOT, "phase13-gui")
TRAP = "dieniw/ornith-gui-lora"
GOOD = "dieniw/ornith-gui-lora-v21"
KERNELS = ["kernel_bench_3d_B", "kernel_bench_3d_hard_B"]


def main():
    for k in KERNELS:
        mp = os.path.join(P13, k, "kernel-metadata.json")
        if not os.path.exists(mp):
            print("   thieu:", k)
            continue
        md = json.load(io.open(mp, encoding="utf-8"))
        ds = md.get("dataset_sources") or []
        if TRAP not in ds:
            print("   %-24s khong can sua" % k)
            continue
        md["dataset_sources"] = [GOOD if d == TRAP else d for d in ds]
        with io.open(mp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(md, fh, ensure_ascii=False, indent=1)
        print("   %-24s %s -> %s" % (k, TRAP, GOOD))
    print("=> chay lai: python scripts/gate_all_queue.py B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
