"""check_bench_failure_modes.py - do CO CHE THAT BAI cua model tren ket qua
bench (GLM, 22/10).

Doc 1 file ket qua (b15_result.json / desktop_result.json) va tach 5 co che:
  1) WIN / FAIL
  2) DONE discipline: %ep co DONE / %ep KET THUC bang DONE
  3) LOOP (stuck): ep lap >= 3 lan cung 1 hanh dong (va khong win)
  4) TRUNCATE: buoc sinh het token (n_new >= cap) => action rong => lap
  5) EMPTY ACTION: buoc khong parse ra hanh dong (mode=none)

Ket luan in ra:
  - %ep co DONE nhung FAIL  => model bi LOOP truoc khi kip ket thuc
  - %ep co DONE va WIN      => DONE la hieu qua cua giai, khong phai nguyen nhan
  - buoc rong/truncate      => can them token / train suc tich gon hon

Dung:
  python phase13-gui/check_bench_failure_modes.py phase13-gui/out_bench_v22/b15_result.json
  python phase13-gui/check_bench_failure_modes.py <result.json> --cap 256
"""
import argparse
import collections
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(m):
    print("[fm] %s" % m, flush=True)


def trace_of(e):
    """trace (B15) hoac trajectory (desktop) -> list step."""
    tr = e.get("trace") or []
    if tr:
        return tr
    traj = e.get("trajectory") or []
    return [{"act": s.get("action"), "step": s.get("step")} for s in traj]


def act_of(s):
    for k in ("act", "action"):
        if s.get(k):
            return str(s[k]).strip()
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--cap", type=int, default=256,
                    help="n_new toi da xem la TRUNCATE (mac dinh 256)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    p = os.path.abspath(a.result)
    if not os.path.isfile(p):
        log("khong thay %s" % p)
        return 1
    d = json.load(io.open(p, encoding="utf-8"))
    eps = d.get("episodes") or []
    log("%s | %d episode | suite=%s" % (os.path.basename(p), len(eps),
                                        d.get("suite") or d.get("suite_name") or "?"))
    if not eps:
        return 1

    by = collections.defaultdict(list)
    for e in eps:
        by[e.get("task_id")].append(e)

    tot = collections.Counter()
    rows = []
    for t, gg in sorted(by.items()):
        c = collections.Counter()
        for e in gg:
            c["ep"] += 1
            if e.get("win"):
                c["win"] += 1
            acts = [act_of(s) for s in trace_of(e)]
            acts = [x for x in acts if x]
            if any(x.upper().startswith("DONE") for x in acts):
                c["co_done"] += 1
            if acts and acts[-1].upper().startswith("DONE"):
                c["end_done"] += 1
            if acts:
                top = collections.Counter(acts).most_common(1)[0][1]
                if top >= 3:
                    c["stuck_raw"] += 1
                    if e.get("win"):
                        # loop VO HAI: action lap idempotent => trang thai van
                        # dung => loop khong ngay chan (nhe hon loop that bai)
                        c["stuck_win"] += 1
                    else:
                        c["stuck_fail"] += 1
            for s in trace_of(e):
                c["steps"] += 1
                if not act_of(s):
                    c["empty"] += 1
                try:
                    if int(s.get("n_new") or 0) >= a.cap:
                        c["trunc"] += 1
                except Exception:
                    pass
        rows.append((t, c))
        for k in c:
            tot[k] += c[k]

    n = tot["ep"]
    log("")
    log("TONG: %d ep | win %d (%.1f%%) | co DONE %d (%.1f%%) | KET THUC bang DONE %d (%.1f%%)"
        % (n, tot["win"], 100.0 * tot["win"] / max(n, 1),
           tot["co_done"], 100.0 * tot["co_done"] / max(n, 1),
           tot["end_done"], 100.0 * tot["end_done"] / max(n, 1)))
    log("LOOP (lap >=3 cung hanh dong): %d ep (%.1f%%) | trong do ep FAIL: %d (%.1f%%) | "
        "ep WIN (loop VO HAI - action lap idempotent): %d (%.1f%%)"
        % (tot["stuck_raw"], 100.0 * tot["stuck_raw"] / max(n, 1),
           tot["stuck_fail"], 100.0 * tot["stuck_fail"] / max(n, 1),
           tot["stuck_win"], 100.0 * tot["stuck_win"] / max(n, 1)))
    log("buoc RONG (khong parse ra hanh dong): %d/%d (%.1f%%) | buoc TRUNCATE (n_new>=%d): %d (%.1f%%)"
        % (tot["empty"], max(tot["steps"], 1),
           100.0 * tot["empty"] / max(tot["steps"], 1), a.cap,
           tot["trunc"], 100.0 * tot["trunc"] / max(tot["steps"], 1)))
    win_and_done = sum(1 for e in eps if e.get("win") and any(
        act_of(s).upper().startswith("DONE") for s in trace_of(e)))
    fail_and_done = sum(1 for e in eps if not e.get("win") and any(
        act_of(s).upper().startswith("DONE") for s in trace_of(e)))
    log("ep WIN+co DONE: %d | ep FAIL+co DONE: %d" % (win_and_done, fail_and_done))

    print()
    print("| task | ep | win | %DONE | %end-DONE | %loop | %loop-fail | %loop-win(vo hai) | empty | trunc |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for t, c in rows:
        e_ = max(c["ep"], 1)
        print("| %s | %d | %d | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %d | %d |" %
              (t, c["ep"], c["win"], 100.0 * c["co_done"] / e_,
               100.0 * c["end_done"] / e_, 100.0 * c["stuck_raw"] / e_,
               100.0 * c["stuck_fail"] / e_, 100.0 * c["stuck_win"] / e_,
               c["empty"], c["trunc"]))

    print()
    if win_and_done and win_and_done == tot["win"] and tot["stuck_fail"]:
        log("KET LUAN A: **MOI ep THANG deu co DONE** (%d/%d) => model DA HOC emit DONE; "
            "nut that la **LOOP** (%d ep FAIL lap >=3 cung hanh dong) + ky nang task, "
            "KHONG phai thieu mau DONE" % (win_and_done, tot["win"], tot["stuck_fail"]))
    elif tot["stuck_fail"] >= 0.5 * n and tot["co_done"] >= 0.5 * n:
        log("KET LUAN A: model PHAI loop truoc khi kip DONE => can DUY HOC 'doi chien lua khi hanh dong lap'")
    elif tot["end_done"] >= 0.4 * n:
        log("KET LUAN B: model KET THUC bang DONE o %.0f%% ep => co lenh DONE trong du; "
            "van con: %d ep FAIL co DONE (loop)" % (100.0 * tot["end_done"] / max(n, 1),
                                                    fail_and_done))
    else:
        log("KET LUAN C: %%ep ket thuc bang DONE thap (%.0f%%) => can them mau DONE (R2)"
            % (100.0 * tot["end_done"] / max(n, 1)))
    if tot["trunc"]:
        log("CANH BAO: %d buoc TRUNCATE (het %d token) => action rong => lap; "
            "fix: them token khi eval hoac train suc tich gon hon"
            % (tot["trunc"], a.cap))
    if tot["stuck_win"]:
        log("LUU Y: %d ep LOOP nhung VAN WIN (action lap idempotent) => "
            "'loop' o day KHONG phai loi that => **win_rate KHONG phan anh 'hieu "
            "qua'** (win do bang trang thai app CUOI, khong phai reward tung buoc) "
            "=> luon bao cao CA win_rate VA loop/stuck_rate"
            % tot["stuck_win"])
    if fail_and_done:
        log("CANH BAO: %d ep FAIL nhung van co DONE => DONE khong du de ket thuc dung" %
            fail_and_done)
    if out := a.out:
        with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("| task | ep | win | %%DONE | %%end-DONE | %%loop | %%loop-fail | empty | trunc |\n")
            for t, c in rows:
                e_ = max(c["ep"], 1)
                fh.write("| %s | %d | %d | %.0f%% | %.0f%% | %.0f%% | %.0f%% | %d | %d |\n" %
                         (t, c["ep"], c["win"], 100.0 * c["co_done"] / e_,
                          100.0 * c["end_done"] / e_, 100.0 * c["stuck_raw"] / e_,
                          100.0 * c["stuck_fail"] / e_, c["empty"], c["trunc"]))
        log("ghi %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
