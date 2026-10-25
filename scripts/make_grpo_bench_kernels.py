# -*- coding: utf-8 -*-
"""
make_grpo_bench_kernels.py - tao kernel GATE cho adapter GRPO (acc B).

Dung 2 suite de so sanh nhanh (theo W4: sau moi lan RL -> full gate, nhung
neu thieu quota thi 2 suite nay la toi thieu):
  - B15,5 (18 ep)  : so voi v24 (9/18) va v22 (10/18)
  - B16-A (24 ep)  : so voi v24 (16/24) va v22 (13/24)
+ 1 kernel DESKTOP (30 ep) de check RL co lam suy thoai hanh vi desktop khong ✗
ASCII-only.
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
OLD_ADAPTER = "dieniw/ornith-gui-lora-v24"
NEW_ADAPTER = "dieniw/ornith-gui-lora-grpo1"

JOBS = [
    ("kernel_bench_v155_v24_B", "kernel_bench_v155_grpo_b",
     "dieniw/ornith-gui-bench-v155-grpo", "ornith-gui-bench-v155-grpo",
     "B15,5"),
    ("kernel_bench_v16_v24_B", "kernel_bench_v16_grpo_b",
     "dieniw/ornith-gui-bench-v16-grpo", "ornith-gui-bench-v16-grpo",
     "B16-A"),
]


def main():
    made = []
    for src_rel, dst_rel, kid, title, suite in JOBS:
        src = os.path.join(P13, src_rel)
        dst = os.path.join(P13, dst_rel)
        if not os.path.isdir(src):
            print("  !! thieu nguon: %s" % src_rel)
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        mp = os.path.join(dst, "kernel-metadata.json")
        m = json.load(io.open(mp, encoding="utf-8"))
        m["dataset_sources"] = [NEW_ADAPTER if d == OLD_ADAPTER else d
                                 for d in m.get("dataset_sources", [])]
        m["id"] = kid
        m["title"] = title
        json.dump(m, io.open(mp, "w", encoding="utf-8", newline="\n"),
                  ensure_ascii=False, indent=2)
        made.append((kid, dst_rel, suite))
        print("  %-8s %-26s -> %s" % (suite, src_rel, kid))

    if made:
        p = os.path.join(ROOT, "scripts", "gpu_queue_B.json")
        q = json.load(io.open(p, encoding="utf-8"))
        ids = {it.get("id") for it in q}
        for kid, dst_rel, suite in made:
            if kid in ids:
                continue
            q.append({"id": kid, "dir": "phase13-gui/" + dst_rel, "acc": "B",
                      "note": "GATE %s voi adapter GRPO v1" % suite})
            print("  -> them queue B: %s" % kid)
        json.dump(q, io.open(p, "w", encoding="utf-8", newline="\n"),
                  ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
