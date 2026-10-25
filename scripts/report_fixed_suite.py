# -*- coding: utf-8 -*-
"""
report_fixed_suite.py - BAO CAO CUOI cho 2 suite DA SUA (B15.5 + B16-A).

Khi ket qua v22 (task da sua) ve, lenh nay in day du:
  1) VERDICT task: run dung ban CU hay ban MOI (detect_task_fixes.py)
  2) SO DO voi baseline cung suite (v21) - cung 18/24 ep, cung task
  3) SO DO voi suite B15 (cung model, suite KHONG doi) - tach "do kho task"
     khoi "nang luc model"
  4) CLUSTER delta (C2 loop / C3 misread / C4 no_submit...)

Dung:
    python scripts/report_fixed_suite.py
    python scripts/report_fixed_suite.py --suite B15.5
ASCII-only source.
"""
import argparse
import importlib.util
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

SUITES = {
    "B15.5": {
        # acc A het quota GPU (22/10) => cac phep do chuyen sang acc B;
        # doc ca 2 duong (A neu co, B uu tien) de khong bo so.
        "result": ["phase13-gui/out_bench_v155_v22old_B/b15_result.json",
                   "phase13-gui/out_bench_v155_v22_old/b15_result.json",
                   "phase13-gui/out_bench_v155_v22/b15_result.json"],
        "baseline": "phase13-gui/out_bench_v155_v21/b15_result.json",
        "fixed": 18,
    },
    "B16-A": {
        "result": ["phase13-gui/out_bench_v16_v22b_B/b15_result.json",
                   "phase13-gui/out_bench_v16_v22/b15_result.json"],
        "baseline": "phase13-gui/out_bench_v16_v21/b15_result.json",
        "fixed": 24,
    },
}
# suite B15 (KHONG sua task) - cung model v22, dung de tach do kho task
B15_V22 = "phase13-gui/out_bench_v22/b15_result.json"
B15_V21 = "phase13-gui/out_bench_v21/b15_result.json"


def load(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def run(args):
    p = subprocess.run([PY] + args, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    return p.stdout or ""


def metrics(path):
    """-> dict metric gon (khong goi subprocess) cho 1 file result."""
    d = load(path, {})
    eps = d.get("episodes") or []
    n = len(eps)
    wins = sum(1 for e in eps if e.get("win"))
    steps = 0
    none = 0
    stuck = 0
    stuck_fail = 0
    multi_n = multi_w = 0
    for e in eps:
        tr = e.get("trace") or []
        acts = [str(s.get("act") or "") for s in tr]
        steps += len(acts)
        none += sum(1 for a in acts if a.upper() in ("", "NONE"))
        is_stuck = (len(acts) >= 3 and
                    len(set(a for a in acts if a)) <= max(1, len(acts) // 3))
        if is_stuck:
            stuck += 1
            if not e.get("win"):
                stuck_fail += 1
        if e.get("task_id", "").startswith(("T13", "T14", "T15", "T16", "T17",
                                            "T18", "T19", "T20", "T21", "T22",
                                            "T23", "T24", "T25", "T26")):
            multi_n += 1
            if e.get("win"):
                multi_w += 1
    return {"n": n, "wins": wins, "win_rate": 100.0 * wins / max(1, n),
            "commit": 100.0 * (steps - none) / max(1, steps),
            "stuck": 100.0 * stuck / max(1, n),
            "stuck_fail": stuck, "stuck_fail_eps": sum(1 for e in eps
                                                        if not e.get("win")),
            "multi": "%d/%d" % (multi_w, multi_n)}


def line(tag, m, n):
    print("   %-14s n=%-3d win=%-10s commit=%5.1f%%  stuck=%5.1f%%  "
          "stuck(FAIL)=%d/%d" % (tag, m["n"], "%d (%.1f%%)" % (m["wins"],
                                                                m["win_rate"]),
                                  m["commit"], m["stuck"], m["stuck_fail"],
                                  m["stuck_fail_eps"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default=None)
    a = ap.parse_args()
    names = [a.suite] if a.suite else list(SUITES)
    for name in names:
        cfg = SUITES.get(name)
        if not cfg:
            print("khong biet suite %r" % name)
            continue
        print("=" * 78)
        print("SUITE %s (task DA SUA - %d ep ky vong)" % (name, cfg["fixed"]))
        print("=" * 78)
        rp = None
        for c in cfg["result"]:
            fp = os.path.join(ROOT, c.replace("/", os.sep))
            if os.path.exists(fp):
                rp = fp
                break
        if not rp:
            print("   (chua co ket qua o: %s)" % ", ".join(cfg["result"]))
            print("   -> khi kernel xong, watchdog tai log+result ve day; "
                  "chay lai lenh nay")
            continue
        # 1) verdict task
        print("   [1] VERDICT TASK (cu hay moi?)")
        out = run([os.path.join(ROOT, "scripts", "detect_task_fixes.py"),
                   os.path.relpath(rp, ROOT).replace("\\", "/")])
        for l in out.splitlines():
            if ("PROOF_" in l or "UNKNOWN" in l or "TONG:" in l or
                    "KET LUAN" in l):
                print("      " + l.strip())
        # 2) so do cung suite
        print("   [2] SO DO CUNG SUITE (v21 -> v22, cung task, cung so ep)")
        bm = metrics(os.path.join(ROOT, cfg["baseline"].replace("/", os.sep)))
        nm = metrics(rp)
        line("v21 (cu)", bm, 0)
        line("v22 (moi)", nm, 0)
        if bm["n"] and nm["n"]:
            print("      DELTA: win %+.1f diem | commit %+.1f | stuck %+.1f"
                  % (nm["win_rate"] - bm["win_rate"],
                     nm["commit"] - bm["commit"],
                     nm["stuck"] - bm["stuck"]))
        # 3) so do voi B15 (cung model, suite khong doi)
        print("   [3] SO DO VOI SUITE B15 (cung model v22, suite KHONG doi)")
        b15 = os.path.join(ROOT, B15_V22.replace("/", os.sep))
        if os.path.exists(b15):
            m15 = metrics(b15)
            line("B15 v22", m15, 0)
            if m15["n"]:
                print("      (cung model, khac do kho task: B15 %d/36 vs %s %d/%d)"
                      % (m15["wins"], name, nm["wins"], nm["n"]))
        # 4) cluster delta
        print("   [4] CLUSTER DELTA (chi lay tu analyzer de chuan hoa)")
        out = run([os.path.join(ROOT, "scripts", "analyze_bench_result.py"),
                   os.path.relpath(rp, ROOT).replace("\\", "/"),
                   "--baseline", cfg["baseline"]])
        for l in out.splitlines():
            ls = l.strip()
            if (ls.startswith("clusters") or
                    (ls.startswith("C") and "_" in ls[:14]) or
                    "điểm" in ls or "delta" in ls.lower()):
                print("      " + ls)
    print("=" * 78)
    print("BANG 2x2 (tach 'sua loi sinh' voi 'sua task'):")
    print("   %-26s %-16s %-16s" % ("", "task CU", "task MOI"))
    grid = [
        # (nhan model, ket qua [task CU], ket qua [task MOI])
        # O THIEU that cua 2x2 = (v21, task MOI) -> kernel
        # dieniw/ornith-gui-bench-v155-v21new (adapter v21 + task MOI).
        ("v21 (buoc rong cao)",
         # KHONG dung out_bench_v155_B: run do mount 'dieniw/ornith-gui-lora'
         # (adapter CU, KHONG phai v21 - so trong so max|diff|=0.11) => invalid.
         ["phase13-gui/out_bench_v155_v21/b15_result.json"],
         ["phase13-gui/out_bench_v155_v21new_B/b15_result.json"]),
        ("v22 (buoc rong 0%)",
         ["phase13-gui/out_bench_v155_v22_old_B/b15_result.json",
          "phase13-gui/out_bench_v155_v22old_B/b15_result.json",
          "phase13-gui/out_bench_v155_v22_old/b15_result.json"],
         ["phase13-gui/out_bench_v155_v22/b15_result.json"]),
    ]

    def pick(cands):
        for c in cands or []:
            fp = os.path.join(ROOT, c.replace("/", os.sep))
            if os.path.exists(fp):
                return fp
        return None

    for lbl, oldc, newc in grid:
        cells = []
        for cands in (oldc, newc):
            if cands is None:
                cells.append("       -       ")
                continue
            fp = pick(cands)
            if not fp:
                cells.append("(chua co)    ")
                continue
            m = metrics(fp)
            cells.append("%d/%d = %5.1f%%" % (m["wins"], m["n"], m["win_rate"]))
        print("   %-26s %-16s %-16s" % (lbl, cells[0], cells[1]))
    print("   => o 'v22 tren task CU' = kernel acc B 'ornith-gui-bench-v155-v22-old'")
    print("   => o 'v21 tren task MOI' = kernel acc B "
          "'ornith-gui-bench-v155-v21new' (da them vao queue B)")
    print("   !! out_bench_v155_B / out_bench_v16_B KHONG hop le: adapter "
          "'dieniw/ornith-gui-lora' khong phai v21 (max|diff|=0.11) -> "
          "khong dung lam baseline")
    print("      (da them vao queue B + targets B; watchdog B se push khi co slot)")
    print("   => de doc them: python scripts/report_fixed_suite.py")
    print("=" * 78)
    print("=" * 78)
    print("DO LAP LAI (CUNG 1 CELL, 2 ACC) - so PAIRED theo task:")
    _pairs = [
        ("B15.5 (v22, task MOI)",
         ["phase13-gui/out_bench_v155_v22/b15_result.json",
          "phase13-gui/out_bench_v155_v22_b/b15_result.json"]),
        ("B16-A (v22, task MOI)",
         ["phase13-gui/out_bench_v16_v22/b15_result.json",
          "phase13-gui/out_bench_v16_v22b_B/b15_result.json"]),
    ]
    for _lbl, _fs in _pairs:
        _fs = [os.path.join(ROOT, f.replace("/", os.sep)) for f in _fs]
        _fs = [f for f in _fs if os.path.exists(f)]
        if len(_fs) < 2:
            print("   %-22s (chua co 2 lan chay de so sanh)" % _lbl)
            continue
        print("   --- %s" % _lbl)
        _o = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
        for _l in _o.splitlines():
            if ("FLAKY" in _l or "TASK FLAKY" in _l or "cell" in _l
                    or "out_bench" in _l):
                print("      " + _l.rstrip())
    # ---- PHAN RA HIEU UNG (cua bang 2x2) : Δ task / Δ data / tuong tac
    try:
        _g = {}
        for _lbl, _oldc, _newc in grid:
            for _k, _c in (("old", _oldc), ("new", _newc)):
                _fp = pick(_c)
                if _fp:
                    _g[(_lbl.split()[0], _k)] = metrics(_fp)["win_rate"]
        if len(_g) == 4:
            print("=" * 78)
            print("PHAN RA HIEU UNG (bang 2x2, %d ep/o):" % 18)
            _r = sorted(set(k[0] for k in _g))
            _c = sorted(set(k[1] for k in _g))
            for _m in _r:
                for _t in _c:
                    if (_m, _t) in _g:
                        print("   %-8s %-5s %5.1f%%" % (_m, _t, _g[(_m, _t)]))
            _dt = {m: _g[(m, "new")] - _g[(m, "old")] for m in _r
                   if (m, "new") in _g and (m, "old") in _g}
            _dd = {t: _g[(_r[-1], t)] - _g[(_r[0], t)] for t in _c
                   if (_r[-1], t) in _g and (_r[0], t) in _g}
            print("   Δ TASK (CŨ->MỚI): %s"
                  % ", ".join("%s %+.1f" % (m, v) for m, v in _dt.items()))
            print("   Δ DATA (v21->v22): %s"
                  % ", ".join("%s %+.1f" % (t, v) for t, v in _dd.items()))
            _base = _g.get((_r[0], "old"))
            _sum = _base + list(_dt.values())[0] + list(_dd.values())[0]
            _real = _g.get((_r[-1], "new"))
            if _base is not None and _real is not None:
                print("   KIEM TRA CONG GIAO: %0.1f + %+.1f + %+.1f = %0.1f"
                      " (thuc te %0.1f) => TUONG TAC %+.1f điểm"
                      % (_base, list(_dt.values())[0], list(_dd.values())[0],
                         _sum, _real, _real - _sum))
                if abs(_real - _sum) < 3.0:
                    print("   => HIEU UNG CONG GIAO (interaction ~ 0)")
                else:
                    print("   => co TUONG TAC giua task va data (can nhac khi "
                          "ket luan)")
    except Exception as _e:
        print("   (phan ra hieu ung loi: %s)" % _e)

    # ---- SO SANH RECIPE tren cung bo task (paired theo task)
    _rc = [
        ("B15.5 task MOI",
         "phase13-gui/out_bench_v155_v21new_B/b15_result.json",
         "phase13-gui/out_bench_v155_v22/b15_result.json",
         "phase13-gui/out_bench_v155_v24_B/b15_result.json"),
        ("B15.5 task CU",
         "phase13-gui/out_bench_v155_v21/b15_result.json",
         "phase13-gui/out_bench_v155_v22_old_B/b15_result.json",
         None),
        ("B16-A task MOI",
         "phase13-gui/out_bench_v16_v21/b15_result.json",
         "phase13-gui/out_bench_v16_v22b_B/b15_result.json",
         "phase13-gui/out_bench_v16_v24_B/b15_result.json"),
    ]
    for _lbl, _a, _b, _c in _rc:
        _fs = [os.path.join(ROOT, f.replace("/", os.sep))
               for f in (_a, _b, _c) if f]
        _fs = [f for f in _fs if os.path.exists(f)]
        if len(_fs) < 2:
            continue
        print("=" * 78)
        print("SO SANH RECIPE - %s (paired theo task)" % _lbl)
        _o = run([os.path.join(ROOT, "scripts", "cmp_cells.py")] + _fs)
        for _l in _o.splitlines():
            _ls = _l.strip()
            if ("TASK FLAKY" in _ls or "cell" in _ls or "out_bench" in _ls
                    or (_ls.startswith("T") and "/" in _ls)):
                print("      " + _ls)

    print("LUU Y: chi so so sanh duoc giua CUNG mot suite. Task B15.5/B16-A da"
          " sua nen KHONG so truc tiep voi B15 (chi tham khao de tach 'do kho"
          " task' khoi 'nang luc model').")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
