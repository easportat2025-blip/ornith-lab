"""make_b_variants.py - tao bien thep kernel cho acc B (dieniw): copy dir + doi
namespace trong metadata (id + dataset_sources) sang acc B.

Ly do: `kaggle kernels push` lay repo id TU metadata -> phai doi metadata
cho tung acc (khong push duoc vao namespace cua acc khac).
"""
import io
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
B = "dieniw"
A = "khoadangnguye"

# dir nguon -> ten moi
PAIRS = [
    ("phase13-gui/kernel_bench_v155", "phase13-gui/kernel_bench_v155_B"),
    ("phase13-gui/kernel_bench_v16", "phase13-gui/kernel_bench_v16_B"),
    ("phase13-gui/kernel_bench_3d", "phase13-gui/kernel_bench_3d_B"),
    ("phase13-gui/kernel_bench_3d_hard", "phase13-gui/kernel_bench_3d_hard_B"),
    ("phase13-gui/kernel_v22", "phase13-gui/kernel_v22_B"),
    ("phase13-gui/kernel_bench_v22", "phase13-gui/kernel_bench_v22_B"),
    ("phase13-gui/kernel_bench_v155_v22", "phase13-gui/kernel_bench_v155_v22_B"),
    ("phase13-gui/kernel_bench_v16_v22", "phase13-gui/kernel_bench_v16_v22_B"),
]
for src, dst in PAIRS:
    s = os.path.join(ROOT, src)
    if not os.path.isdir(s):
        print("skip (khong co)", src)
        continue
    d = os.path.join(ROOT, dst)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(s, d)
    mf = os.path.join(d, "kernel-metadata.json")
    md = json.load(io.open(mf, encoding="utf-8"))
    if md.get("id", "").startswith(A + "/"):
        md["id"] = B + "/" + md["id"].split("/", 1)[1]
    md["dataset_sources"] = [x.replace(A + "/", B + "/")
                             for x in md.get("dataset_sources", [])]
    json.dump(md, io.open(mf, "w", encoding="utf-8"), ensure_ascii=False,
              indent=2)
    print("%-40s -> %s" % (dst, md["id"]))
