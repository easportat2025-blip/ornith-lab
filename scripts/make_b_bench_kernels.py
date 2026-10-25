# -*- coding: utf-8 -*-
"""
make_b_bench_kernels.py - tao kernel bench tren ACC B (dieniw) cho o 2x2.

Ly do: acc A het quota GPU (reset 24/10) -> pho do phai chay tren B.
2 kernel (cung harness, cung adapter v22, chi khac dataset task):
  B1) v22 tren task B15.5 CU   (dieniw/ornith-gui-bench-v155-old)
  B2) v22 tren task B15.5 MOI  (dieniw/ornith-gui-bench-v155)
=> chay CA HAI tren B = cap nhat + dung harness -> so sanh cong bang.
ASCII-only.
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")

SWAP = {
    "khoadangnguye/ornith-gui-lora-v22": "dieniw/ornith-gui-lora-v22",
    "khoadangnguye/ornith-gui-bench-v155-old":
        "dieniw/ornith-gui-bench-v155-old",
    "khoadangnguye/ornith-gui-bench-v155": "dieniw/ornith-gui-bench-v155",
    "khoadangnguye/ornith-gui-bench-v16b": "dieniw/ornith-gui-bench-v16b",
    "khoadangnguye/ornith-gui-bench-v16": "dieniw/ornith-gui-bench-v16",
    "khoadangnguye/ornith-offline-browsers":
        "dieniw/ornith-offline-browsers",
    "khoadangnguye/gemma12b-wheels": "dieniw/gemma12b-wheels",
    "khoadangnguye/gemma12b-tools": "dieniw/gemma12b-tools",
}

JOBS = [
    ("kernel_bench_v155_v22_old", "kernel_bench_v155_v22_old_b",
     "dieniw/ornith-gui-bench-v155-v22-old", "ornith-gui-bench-v155-v22-old-b"),
    ("kernel_bench_v155_v22", "kernel_bench_v155_v22_b",
     "dieniw/ornith-gui-bench-v155-v22-b", "ornith-gui-bench-v155-v22-b"),
]


def main():
    for src_rel, dst_rel, kid, title in JOBS:
        src = os.path.join(P13, src_rel)
        dst = os.path.join(P13, dst_rel)
        if not os.path.isdir(src):
            print("  !! thieu:", src)
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        mp = os.path.join(dst, "kernel-metadata.json")
        m = json.load(io.open(mp, encoding="utf-8"))
        m["id"] = kid
        m["title"] = title
        m["dataset_sources"] = [SWAP.get(d, d) for d in m.get("dataset_sources", [])]
        json.dump(m, io.open(mp, "w", encoding="utf-8", newline="\n"),
                  ensure_ascii=False, indent=2)
        print("  %-28s -> %s" % (src_rel, kid))
        for d in m["dataset_sources"]:
            print("      " + d)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
