# -*- coding: utf-8 -*-
"""
make_bench_kernels_b.py - tao kernel BENCH phia ACC B cho 2 phep do (acc A het
quota GPU 22/10):
  1) o 2x2   : model v22 tren task B15.5 CU   (dieniw/ornith-gui-bench-v155-old)
  2) B16-A moi: model v22 tren task B16-A DA SUA (dieniw/ornith-gui-bench-v16b)
=> ca 2 deu mount adapter v22 cua acc B (dieniw/ornith-gui-lora-v22).

Copy code tu kernel acc A (giong logic) + doi dataset slug sang acc B + doi id.
Dung:
    python phase13-gui/make_bench_kernels_b.py
ASCII-only source.
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

JOBS = [
    # (ten thu muc moi, kernel mau, id moi, slug dataset bench moi)
    ("kernel_bench_v155_v22old_B", "kernel_bench_v155_v22_old",
     "dieniw/ornith-gui-bench-v155-v22old",
     "dieniw/ornith-gui-bench-v155-old"),
    ("kernel_bench_v16_v22_B2", "kernel_bench_v16_v22",
     "dieniw/ornith-gui-bench-v16-v22b",
     "dieniw/ornith-gui-bench-v16b"),
]
# slug can doi (acc A -> acc B)
SWAP = {
    "khoadangnguye/gemma12b-wheels": "dieniw/gemma12b-wheels",
    "khoadangnguye/ornith-gui-lora-v22": "dieniw/ornith-gui-lora-v22",
    "khoadangnguye/ornith-offline-browsers": "dieniw/ornith-offline-browsers",
}


def main():
    for dst_name, src_name, new_id, new_bench in JOBS:
        src = os.path.join(HERE, src_name)
        dst = os.path.join(HERE, dst_name)
        if not os.path.isdir(src):
            print("KHONG TIM THAY kernel mau:", src_name)
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith(".py"):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        md = json.load(io.open(os.path.join(src, "kernel-metadata.json"),
                              encoding="utf-8"))
        ds = []
        for d in md.get("dataset_sources", []):
            if d.endswith("ornith-gui-bench-v155-old") or \
                    d.endswith("ornith-gui-bench-v16b"):
                d = new_bench
            else:
                d = SWAP.get(d, d)
            ds.append(d)
        md["dataset_sources"] = ds
        md["id"] = new_id
        md["title"] = new_id.split("/")[-1]
        with io.open(os.path.join(dst, "kernel-metadata.json"), "w",
                     encoding="utf-8", newline="\n") as fh:
            json.dump(md, fh, ensure_ascii=False, indent=1)
        print("da tao %-32s id=%s" % (dst_name, new_id))
        for d in ds:
            print("      ", d)
    print()
    print("=== KIEM TRA (gate + dataset tren Kaggle) ===")
    print("  python scripts/prepush_gate.py phase13-gui/<ten thu muc moi>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
