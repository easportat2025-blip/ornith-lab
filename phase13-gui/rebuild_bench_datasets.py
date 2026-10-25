# -*- coding: utf-8 -*-
"""rebuild_bench_datasets.py - dong goi LAI dataset bench (B15.5 / B16) sau khi
MiMo sua trang (T13: validate lai khi goi/blur; B16: bo "expected <dap an>").

Chi rebuild phan ZIP + dataset-metadata (khong touching kernel).
Upload:  kaggle datasets version -p <DST>
"""
import io
import json
import os
import shutil
import zipfile

JOBS = [
    ("phase13-gui/bench_v15/tasks_v15_5", "phase13-gui/bench_v155_dataset",
     "bench_v155", "bench_v155_bundle.zip",
     "khoadangnguye/ornith-gui-bench-v155",
     "Ornith GUI bench B15.5 (T13-T18)"),
    ("phase13-gui/bench_v15/tasks_v16_a", "phase13-gui/bench_v16_dataset",
     "bench_v16", "bench_v16_bundle.zip",
     "khoadangnguye/ornith-gui-bench-v16",
     "Ornith GUI bench B16-A (T19-T26)"),
]


def build(src, dst, top, zipname, dsid, title):
    os.makedirs(dst, exist_ok=True)
    zp = os.path.join(dst, zipname)
    n = 0
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in ("bench_v155.py", "bench_v16.py", "checker.py",
                    "checker_v16.py", "self_test_report.json",
                    "dummy_actions_v155.json", "dummy_actions_v16.json",
                    "dummy_run_result.json", "dummy_run_result_v16.json"):
            p = os.path.join(src, rel)
            if os.path.exists(p):
                z.write(p, top + "/" + rel)
                n += 1
        tdir = os.path.join(src, "tasks")
        for f in sorted(os.listdir(tdir)):
            z.write(os.path.join(tdir, f), top + "/tasks/" + f)
            n += 1
    with zipfile.ZipFile(zp) as z:
        names = set(z.namelist())
    assert top + "/tasks/tasks.json" in names, "thieu tasks.json"
    assert (top + "/checker.py" in names or
            top + "/checker_v16.py" in names), "thieu checker"
    meta = {"title": title, "id": dsid, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(dst, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("  %s: %d file, %.1f KB -> %s" % (top, n,
                                           os.path.getsize(zp) / 1024, dsid))


print("=== rebuild dataset bench (voi trang da fix) ===")
for job in JOBS:
    build(*job)
print("Xong. Bay: kaggle datasets version -p <DST>")
