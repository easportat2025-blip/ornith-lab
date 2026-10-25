# -*- coding: utf-8 -*-
"""
make_bench_kernels.py - tao cac kernel BENCH cho cac model moi (v23 / v23a /
v23b ...), copy tu kernel bench hien tai va doi:
  - dataset_sources: doi slug ADAPTER (khoadangnguye/ornith-gui-lora-vXX)
  - id / title: doi slug kernel

Vi sao can: de so 3 kernel (v23 vs v23b vs v23a) thi can 3 run bench tren
CUNG mot bo task, va moi adapter la MOT dataset rieng (adapter duoc xuat ra
tu kernel SFT) => 3 kernel bench rieng. Khong sua tay 3 file metadata.

Dung:
    python scripts/make_bench_kernels.py --from kernel_bench_v16_v22 \
        --spec "v23=khoadangnguye/ornith-gui-lora-v23" \
        --spec "v23a=khoadangnguye/ornith-gui-lora-v23a" \
        --spec "v23b=khoadangnguye/ornith-gui-lora-v23b"
    python scripts/make_bench_kernels.py --from kernel_bench_v16_v22 --spec "v23=..." --dry-run
ASCII-only source.
"""
import argparse
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True,
                    help="ten kernel bench mau (vd kernel_bench_v16_v22)")
    ap.add_argument("--spec", action="append", default=[],
                    help="<nhan>=<slug adapter> (nhieu lan)")
    ap.add_argument("--out-prefix", default="kernel_bench_v16_",
                    help="tien to ten thu muc kernel moi")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = os.path.join(P13, a.src)
    if not os.path.isdir(src):
        print("KHONG TIM THAY thu muc mau:", a.src)
        return 2
    md = json.load(io.open(os.path.join(src, "kernel-metadata.json"),
                           encoding="utf-8"))
    base_ds = list(md.get("dataset_sources", []))
    old_adapter = None
    for d in base_ds:
        if "lora" in d or "adapter" in d:
            old_adapter = d
            break
    if not old_adapter:
        print("KHONG tim thay slug adapter trong dataset_sources cua %s" % a.src)
        return 3
    print("mau: %s | adapter cu: %s" % (a.src, old_adapter))
    made = []
    for spec in a.spec:
        if "=" not in spec:
            print("spec sai dinh dang (can <nhan>=<slug>):", spec)
            return 2
        tag, new_adapter = spec.split("=", 1)
        tag = tag.strip()
        new_adapter = new_adapter.strip()
        dst = os.path.join(P13, "%s%s" % (a.out_prefix, tag))
        if not a.dry_run:
            if os.path.isdir(dst):
                shutil.rmtree(dst, ignore_errors=True)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(src):
                if f.endswith(".py"):
                    shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        nmd = dict(md)
        nmd["dataset_sources"] = [new_adapter if d == old_adapter else d
                                  for d in base_ds]
        nmd["id"] = "khoadangnguye/ornith-gui-bench-v16-%s" % tag
        nmd["title"] = "ornith-gui-bench-v16-%s" % tag
        if not a.dry_run:
            with io.open(os.path.join(dst, "kernel-metadata.json"), "w",
                         encoding="utf-8", newline="\n") as fh:
                json.dump(nmd, fh, ensure_ascii=False, indent=1)
        print("  %-10s -> %-38s id=%s" % (tag, os.path.relpath(dst, ROOT),
                                           nmd["id"]))
        made.append(dst)
    if a.dry_run:
        print("(DRY-RUN: chua ghi file)")
        return 0
    print()
    print("=== KIEM TRA GATE (bat buoc truoc khi push) ===")
    for d in made:
        print("  python scripts/prepush_gate.py %s" % os.path.relpath(d, ROOT))
    print()
    print("=== LENH PUSH (can key acc A) ===")
    for d in made:
        print("  kaggle kernels push -p %s" % os.path.relpath(d, ROOT))
    print("  (dien kernel can ADAPTER da upload: xem 'dataset check' cua watchdog)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
