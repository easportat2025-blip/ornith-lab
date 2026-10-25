# -*- coding: utf-8 -*-
"""
reset_push_state.py - bo co 'pushed' trong watchdog state de watchdog PUSH LAI
kernel da chay xong (ERROR/COMPLETE nhung can chay lai).

Vi du: 3 kernel bench-v22 da push nhung chet vi thieu adapter lora-v22.
Sau khi upload adapter, can push lai; state dang co "pushed": true nen
watchdog bo qua. Lenh nay xoa flag do (khong xoa trang thai khac).

Dung:
    python scripts/reset_push_state.py khoadangnguye/ornith-gui-bench-v22
    python scripts/reset_push_state.py --all-errors
    python scripts/reset_push_state.py --dry-run khoadangnguye/ornith-gui-bench-v22
"""
import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = [
    ("scripts/gpu_queue_state.json", "A"),
    ("scripts/gpu_queue_B_state.json", "B"),
]


def load(p):
    if not os.path.exists(p):
        return {}
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return {}


def save(p, d):
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kernels", nargs="*")
    ap.add_argument("--all-errors", action="store_true",
                    help="reset moi kernel co status ERROR")
    ap.add_argument("--pause", action="store_true",
                    help="them co 'paused' cho kernel (watchdog bo qua)")
    ap.add_argument("--unpause", action="store_true",
                    help="bo co 'paused' cho kernel")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.kernels and not a.all_errors:
        print("Dung: reset_push_state.py <kernel> [<kernel> ...] | --all-errors "
              "| --pause | --unpause")
        return 2
    if a.pause or a.unpause:
        for qf in ("scripts/gpu_queue.json", "scripts/gpu_queue_B.json"):
            qp = os.path.join(ROOT, qf.replace("/", os.sep))
            if not os.path.exists(qp):
                continue
            q = load(qp)
            ch = False
            for it in q:
                if isinstance(it, dict) and it.get("id") in a.kernels:
                    if a.pause:
                        it["paused"] = True
                    else:
                        it.pop("paused", None)
                    ch = True
                    print("  %-46s paused=%s" % (it.get("id"),
                                                 it.get("paused", False)))
            if ch and not a.dry_run:
                save(qp, q)
        return 0
    n = 0
    for rel, tag in STATES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        d = load(p)
        if not d:
            continue
        changed = False
        for k, v in list(d.items()):
            if not isinstance(v, dict):
                continue
            hit = k in a.kernels
            if a.all_errors and str(v.get("status", "")).upper() == "ERROR":
                hit = True
            if hit and v.get("pushed"):
                n += 1
                print("  [%s] %-46s pushed %s -> reset (status %s)"
                      % (tag, k, v.get("pushed_at"), v.get("status")))
                if not a.dry_run:
                    v["pushed"] = False
                    v["pushed_at"] = ""
                changed = True
        if changed and not a.dry_run:
            save(p, d)
    print("TONG reset: %d%s" % (n, " (DRY-RUN)" if a.dry_run else ""))
    if n and not a.dry_run:
        print("Watchdog se push lai cac kernel tren (neu adapter/du lieu da "
              "san, no se push; neu con thieu se BO QUA va bao bus)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
