# -*- coding: utf-8 -*-
"""make_v25b_bench_kernels.py - 4 kernel gate cho adapter v25b.

  B15  : dieniw/ornith-gui-bench-b15-v25b
  B15.5: dieniw/ornith-gui-bench-v155-v25b
  B16-A: dieniw/ornith-gui-bench-v16-v25b
  B17  : dieniw/ornith-gui-bench-b17-v25b

Adapter dich: dieniw/ornith-gui-lora-v25b (publish sau khi sft-v25b xong).
Cac kernel nay nam trong queue B voi `after` = sft-v25b, nen chi push sau
khi adapter da duoc publish.
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
LORA = "dieniw/ornith-gui-lora-v25b"

JOBS = [
    ("kernel_bench_v24_b", "kernel_bench_b15_v25b",
     "dieniw/ornith-gui-bench-b15-v25b"),
    ("kernel_bench_v155_v24_B", "kernel_bench_v155_v25b",
     "dieniw/ornith-gui-bench-v155-v25b"),
    ("kernel_bench_v16_v24_B", "kernel_bench_v16_v25b",
     "dieniw/ornith-gui-bench-v16-v25b"),
    ("kernel_bench_b17", "kernel_bench_b17_v25b",
     "dieniw/ornith-gui-bench-b17-v25b"),
]


def main():
    for src_name, dst_name, kid in JOBS:
        src = os.path.join(P13, src_name)
        dst = os.path.join(P13, dst_name)
        if not os.path.isdir(src):
            print("!! thieu kernel mau:", src_name)
            continue
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith((".py", ".json")):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        mp = os.path.join(dst, "kernel-metadata.json")
        md = json.load(io.open(mp, encoding="utf-8"))
        ds = []
        for d in md.get("dataset_sources", []):
            if d.endswith("ornith-gui-lora-v24") or \
                    d.endswith("ornith-gui-lora-v22"):
                d = LORA
            ds.append(d)
        if LORA not in ds:
            ds.append(LORA)
        md["dataset_sources"] = ds
        md["id"] = kid
        md["title"] = kid.split("/")[-1]
        md["expected_adapter"] = LORA
        with io.open(mp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(md, fh, ensure_ascii=False, indent=1)
        print("== %-28s -> %-28s %s" % (src_name, dst_name, kid))
        print("   adapter: %s" % LORA)
        print("   task   : %s" % (ds[-2] if ds[-1] == LORA else ds[-1]))
    print("=> sau khi sft-v25b xong: python scripts/publish_lora.py "
          "--kernel dieniw/ornith-gui-sft-v25b "
          "--slug dieniw/ornith-gui-lora-v25b --acc B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
