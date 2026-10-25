"""fix_meta_scopes.py - moi kernel chi mount dataset cua acc no (A/B) + rebuild
bien thep acc B tu bien thep acc A (nen metadata B khong con slug cua A).
"""
import io
import json
import os

A = "khoadangnguye"
B = "dieniw"

# 1) kernel_v22 (acc A): chi dataset A
mf = 'phase13-gui/kernel_v22/kernel-metadata.json'
md = json.load(io.open(mf, encoding='utf-8'))
md['dataset_sources'] = [x for x in md['dataset_sources']
                         if not x.startswith(B + "/")]
json.dump(md, io.open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('v22 (A) datasets:', md['dataset_sources'])

# 2) rebuild bien thep B tu A (copy code + doi namespace)
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
import shutil
for src, dst in PAIRS:
    s = os.path.join(src)
    if not os.path.isdir(s):
        continue
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(s, dst)
    m = os.path.join(dst, "kernel-metadata.json")
    md = json.load(io.open(m, encoding='utf-8'))
    if md.get("id", "").startswith(A + "/"):
        md["id"] = B + "/" + md["id"].split("/", 1)[1]
    md["dataset_sources"] = [x.replace(A + "/", B + "/")
                             for x in md.get("dataset_sources", [])]
    json.dump(md, io.open(m, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("%-44s -> %s" % (dst, md["id"]))
