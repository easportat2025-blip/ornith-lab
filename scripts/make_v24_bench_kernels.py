# -*- coding: utf-8 -*-
"""
make_v24_bench_kernels.py - chuan bi 2 kernel BENCH cho adapter v24 (san
sang khi sft-v24 train xong + publish_lora.py xong):

  1) dieniw/ornith-gui-bench-v155-v24  : v24 tren task B15.5 MOI
  2) dieniw/ornith-gui-bench-v16-v24   : v24 tren task B16-A MOI

Adapter: dieniw/ornith-gui-lora-v24 (se ton tai sau khi publish_lora.py).
=> gate se FAIL G9 "dataset chua ton tai" TRUOC khi adapter duoc publish
   (dung: khong the bench adapter chua co). Sau khi publish -> gate PASS.

Dung: python scripts/make_v24_bench_kernels.py
ASCII-only source.
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P13 = os.path.join(ROOT, "phase13-gui")

V24_LORA = "dieniw/ornith-gui-lora-v24"
JOBS = [
    # (src dir, dst dir, id moi, slug task dataset)
    ("kernel_bench_v155_v22", "kernel_bench_v155_v24_B",
     "dieniw/ornith-gui-bench-v155-v24", "dieniw/ornith-gui-bench-v155"),
    ("kernel_bench_v16_v22", "kernel_bench_v16_v24_B",
     "dieniw/ornith-gui-bench-v16-v24", "dieniw/ornith-gui-bench-v16b"),
]
SWAP = {
    "khoadangnguye/gemma12b-wheels": "dieniw/gemma12b-wheels",
    "khoadangnguye/ornith-gui-lora-v22": V24_LORA,
    "khoadangnguye/ornith-offline-browsers":
        "dieniw/ornith-offline-browsers",
    "khoadangnguye/ornith-gui-bench-v155": "dieniw/ornith-gui-bench-v155",
    "khoadangnguye/ornith-gui-bench-v16b": "dieniw/ornith-gui-bench-v16b",
}


def main():
    for src_name, dst_name, kid, task_ds in JOBS:
        src = os.path.join(P13, src_name)
        dst = os.path.join(P13, dst_name)
        if not os.path.isdir(src):
            print("!! thieu kernel mau:", src_name)
            continue
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith(".py") or f.endswith(".json"):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        mp = os.path.join(dst, "kernel-metadata.json")
        md = json.load(io.open(mp, encoding="utf-8"))
        ds = [SWAP.get(d, d) for d in md.get("dataset_sources", [])]
        ds = [task_ds if d.endswith("ornith-gui-bench-v155")
              or d.endswith("ornith-gui-bench-v16b") else d for d in ds]
        md["dataset_sources"] = ds
        md["id"] = kid
        md["title"] = kid.split("/")[-1]
        md["expected_adapter"] = V24_LORA
        with io.open(mp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(md, fh, ensure_ascii=False, indent=1)
        print("== %s -> %s" % (src_name, dst_name))
        print("   id  : %s" % kid)
        print("   task: %s" % task_ds)
        print("   adapter: %s" % V24_LORA)
        for d in ds:
            print("      %s" % d)
    print("=> sau khi sft-v24 xong: python scripts/publish_lora.py --kernel "
          "dieniw/ornith-gui-sft-v24 --slug dieniw/ornith-gui-lora-v24 --acc B")
    print("=> roi: python scripts/lora_fingerprint.py --slug "
          "dieniw/ornith-gui-lora-v24 --register")
    print("=> roi: python scripts/prepush_gate.py phase13-gui/"
          "kernel_bench_v155_v24_B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
