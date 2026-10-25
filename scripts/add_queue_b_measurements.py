# -*- coding: utf-8 -*-
"""
add_queue_b_measurements.py - them 2 kernel BENCH phia ACC B vao queue + targets
(acc A het quota GPU 22/10 => 2 phep do chuyen sang acc B):
  1) o 2x2     : dieniw/ornith-gui-bench-v155-v22old (v22 tren task B15.5 CU)
  2) B16-A moi : dieniw/ornith-gui-bench-v16-v22b     (v22 tren task B16-A DA SUA)

Targets: de watchdog tai ket qua ve (outdir khop voi scripts/report_fixed_suite.py).
Dung: python scripts/add_queue_b_measurements.py
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"

# FIX 22/10 (MiMo): cac muc KHONG duoc them lai (trung nghiem vu / het y nghia):
#   dieniw/ornith-gui-bench-v155-v22old  -> trung kernel 2x2 cua @DeepSeek
#                                          (dieniw/ornith-gui-bench-v155-v22-old
#                                           da push va dang chay) => 1 slot B
#   dieniw/ornith-gui-bench-v155-v22-b   -> trung phep do da co tren acc A
#                                          (out_bench_v155_v22 = 55,6%)
#   dieniw/ornith-gui-desktop-bench-b2   -> source CU (thieu 4 app) => bi
#                                          thay bang b3 (co guard)
SKIP_IDS = {
    "dieniw/ornith-gui-bench-v155-v22old",
    "dieniw/ornith-gui-bench-v155-v22-b",
    "dieniw/ornith-gui-desktop-bench-b2",
}
QUEUE = "scripts/gpu_queue_B.json"
TARGETS = "scripts/watchdog_targets_B.json"
JOBS = [
    {
        "id": "dieniw/ornith-gui-bench-v155-v22old",
        "dir": "phase13-gui/kernel_bench_v155_v22old_B",
        "note": "O 2X2: model v22 tren task B15.5 CU (acc A het quota => chuyen sang B)",
        "label": "bench-v155-v22old-B",
        "outdir": "phase13-gui/out_bench_v155_v22old_B",
        "pattern": "b15_result\\.json|.*\\.log",
    },
    {
        "id": "dieniw/ornith-gui-bench-v16-v22b",
        "dir": "phase13-gui/kernel_bench_v16_v22_B2",
        "note": "B16-A tren task DA SUA (acc A het quota => chuyen sang B)",
        "label": "bench-v16-v22b-B",
        "outdir": "phase13-gui/out_bench_v16_v22b_B",
        "pattern": "b15_result\\.json|.*\\.log",
    },
    {
        # FIX 22/10 (MiMo): O THIEU that cua 2x2 = (v21, task MOI).
        # Adapter: dieniw/ornith-gui-lora-v21 (da so TRONG SO voi acc A:
        # 256/256 tensor giong het, max|diff|=0).
        # Task: dieniw/ornith-gui-bench-v155 (da verify 11/11 file = ban MOI).
        "id": "dieniw/ornith-gui-bench-v155-v21new",
        "dir": "phase13-gui/kernel_bench_v155_v21new_B",
        "note": "O THIEU 2x2: (v21, task MOI) - tach 'sua task' vs 'sua data'",
        "label": "bench-v155-v21new-B",
        "outdir": "phase13-gui/out_bench_v155_v21new_B",
        "pattern": "b15_result\\.json|.*\\.log",
    },
    {
        # FIX 22/10 (MiMo): b2 co app thieu => anh den => 40/120 ep bi tinh
        # nham la model that. b3 = source moi (guard fail-loud) + adapter v22.
        "id": "dieniw/ornith-gui-desktop-bench-b3",
        "dir": "phase13-gui/kernel_desktop_bench_b3",
        "note": "DESKTOP-BENCH b3 (app day du + guard + v22) - sua loi anh den",
        "label": "desktop-bench-b3",
        "outdir": "phase13-gui/out_desktop_bench_b3",
        "pattern": ("desktop_result\\.json|actions\\.jsonl|reward\\.json|"
                    "infra_errors\\.json|.*\\.log"),
    },
]


def load(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return []


def save(p, d):
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)


def main():
    qp = os.path.join(ROOT, QUEUE.replace("/", os.sep))
    tp = os.path.join(ROOT, TARGETS.replace("/", os.sep))
    q = load(qp)
    t = load(tp)
    qids = {x.get("id") for x in q if isinstance(x, dict)}
    tids = {x.get("kernel") for x in t if isinstance(x, dict)}
    for j in JOBS:
        if j["id"] in SKIP_IDS:
            print("- BO QUA (trung/het y nghia):", j["id"])
            continue
        if j["id"] not in qids:
            q.append({"id": j["id"], "dir": j["dir"], "note": j["note"]})
            print("+ queue B:", j["id"])
        else:
            print("= queue B da co:", j["id"])
        if j["id"] not in tids:
            t.append({"kernel": j["id"], "label": j["label"],
                      "outdir": j["outdir"], "pattern": j["pattern"]})
            print("+ target B:", j["label"], "->", j["outdir"])
        else:
            print("= target B da co:", j["id"])
    save(qp, q)
    save(tp, t)
    print("queue B: %d muc | targets B: %d muc" % (len(q), len(t)))
    print("=> watchdog B se push 2 kernel nay khi co slot GPU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
