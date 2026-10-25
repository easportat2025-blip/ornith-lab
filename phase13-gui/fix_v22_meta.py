"""fix_v22_meta.py - them lai base shards + wheels vao metadata v22 (A va B).
Lam: 2 acc deu can 'dieniw/ornbase-s1..4' (model) + 'dieniw/stack-wheels'.
"""
import json
import os

NEED = ["dieniw/ornbase-s1", "dieniw/ornbase-s2", "dieniw/ornbase-s3",
        "dieniw/ornbase-s4", "dieniw/stack-wheels"]
for d in ("phase13-gui/kernel_v22", "phase13-gui/kernel_v22_B"):
    mf = os.path.join(d, "kernel-metadata.json")
    if not os.path.exists(mf):
        print("skip", d)
        continue
    md = json.load(open(mf, encoding="utf-8"))
    ds = md.get("dataset_sources", [])
    for x in NEED:
        if x not in ds:
            ds.append(x)
    # thu tu: model shards truoc, wheels sau
    md["dataset_sources"] = ds
    json.dump(md, open(mf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(d, "->", len(ds), "datasets")
    print("   ", ds)
