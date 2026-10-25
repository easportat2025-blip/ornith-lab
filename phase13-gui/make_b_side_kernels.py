import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

JOBS = [
    ("kernel_bench_v155_v22_old", "kernel_bench_v155_v22_old_B",
     "dieniw/ornith-gui-bench-v155-v22-old", "ornith-gui-bench-v155-v22-old",
     "O 2x2: v22 tren task B15.5 CU (dieniw/ornith-gui-bench-v155-old)"),
    ("kernel_bench_v16_v22", "kernel_bench_v16_v22_new_B",
     "dieniw/ornith-gui-bench-v16-v22-b", "ornith-gui-bench-v16-v22-b",
     "B16-A tren TASK MOI (dieniw/ornith-gui-bench-v16b)"),
    ("kernel_v24", "kernel_v24_B",
     "dieniw/ornith-gui-sft-v24-b", "ornith-gui-sft-v24-b",
     "SFT v24 tren acc B (dr0.75 + S1-S10 + R2 972 + loop-recovery 600 + ...)"),
]

OWNER_MAP = {"khoadangnguye": "dieniw"}

# dataset B-side: them synth-s11 (truoc day thieu) + sua slug (acc B)
EXTRA_DS = {"khoadangnguye/ornith-gui-synth-s11": "dieniw/ornith-gui-synth-s11"}


def main():
    ok_all = True
    for src_name, dst_name, new_id, new_title, note in JOBS:
        src = os.path.join(HERE, src_name)
        dst = os.path.join(HERE, dst_name)
        if not os.path.isdir(src):
            print("!! thieu %s (bo qua)" % src_name)
            ok_all = False
            continue
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith(".py") or f.endswith(".json"):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        mp = os.path.join(dst, "kernel-metadata.json")
        meta = json.load(io.open(mp, encoding="utf-8"))
        old_ds = list(meta.get("dataset_sources") or [])
        new_ds = []
        for d in old_ds:
            if "/" in d:
                owner, slug = d.split("/", 1)
                new_ds.append("%s/%s" % (OWNER_MAP.get(owner, owner), slug))
            else:
                new_ds.append(d)
        # them synth-s11 (thieu) cho kernel SFT
        if src_name == "kernel_v24" and not any("synth-s11" in x for x in new_ds):
            new_ds.append("dieniw/ornith-gui-synth-s11")
        meta["dataset_sources"] = new_ds
        meta["id"] = new_id
        meta["title"] = new_title
        io.open(mp, "w", encoding="utf-8", newline="\n").write(
            json.dumps(meta, indent=1))
        print("== %s -> %s" % (src_name, dst_name))
        print("   id: %s" % new_id)
        print("   note: %s" % note)
        for o, n in zip(old_ds, new_ds):
            if o != n:
                print("      %-46s -> %s" % (o, n))
        if src_name == "kernel_v24":
            print("   + them dieniw/ornith-gui-synth-s11 (thieu truoc day)")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
