"""analyze_desktop_result.py - phan tich ket qua DESKTOP-BENCH (GLM, 21/10).

Doc: 1 hoac NHIEU ket qua (desktop_result.json) -> gop lai de so sanh
split A/B (2 kernel chay song song tren 2 acc).
Cu phap:
    python phase13-gui/analyze_desktop_result.py                       # mac dinh
    python phase13-gui/analyze_desktop_result.py <result.json|dir> ... # tu chon
    python phase13-gui/analyze_desktop_result.py --out <file.md>
In: bang theo task (win rate, mean score, parse_rate, stuck_rate, buoc/ep),
    cum episode theo kieu that, va VI DU trajectory cho tung task.
Chi doc, khong GPU/key/mang.
"""
import io
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "phase13-gui", "out_desktop_bench")
DEFAULT_RES = os.path.join(OUT_DIR, "desktop_result.json")


def log(m):
    print("[desk] %s" % m, flush=True)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())[:120]


def verb_of(a):
    a = (a or "").strip()
    return a.split()[0].upper() if a else ""


def find_result(p):
    """-> (result_path, actions_path|None) cho 1 arg (file hoac thu muc)."""
    p = os.path.abspath(p)
    if os.path.isdir(p):
        for cand in ("desktop_result.json", "desktop_bench/desktop_result.json",
                     "result.json"):
            q = os.path.join(p, cand)
            if os.path.isfile(q):
                act = os.path.join(os.path.dirname(q), "actions.jsonl")
                return q, (act if os.path.isfile(act) else None)
        return None, None
    if os.path.isfile(p):
        act = os.path.join(os.path.dirname(p), "actions.jsonl")
        return p, (act if os.path.isfile(act) else None)
    return None, None


def load_inputs(paths):
    """-> (episodes, rows, sources) gop tu nhieu file ket qua."""
    eps_all, rows_all, srcs = [], [], []
    for p in paths:
        rp, ap = find_result(p)
        if not rp:
            log("BO QUA (khong thay desktop_result.json): %s" % p)
            continue
        d = json.load(io.open(rp, encoding="utf-8"))
        eps = d.get("episodes") or []
        tag = os.path.basename(os.path.dirname(rp)) or os.path.basename(rp)
        for e in eps:
            e = dict(e)
            e["_src"] = tag
            eps_all.append(e)
        rows = []
        if ap:
            for line in io.open(ap, encoding="utf-8", errors="replace"):
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        r["_src"] = tag
                        rows.append(r)
                    except Exception:
                        pass
        rows_all += rows
        srcs.append((rp, len(eps), len(rows)))
    return eps_all, rows_all, srcs


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    out_md = None
    paths = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--out":
            i += 1
            out_md = argv[i] if i < len(argv) else None
        elif a.startswith("-"):
            log("bo qua option khong biet: %s" % a)
        else:
            paths.append(a)
        i += 1
    if not paths:
        paths = [DEFAULT_RES]
    md = out_md or os.path.join(OUT_DIR, "desktop_analysis.md")

    eps, rows, srcs = load_inputs(paths)
    if not eps:
        log("khong co episode nao trong %s (kernel chua xong?)" % paths)
        return 1
    log("doc %d episode / %d dong actions tu %d file" %
        (len(eps), len(rows), len(srcs)))
    for rp, ne, nr in srcs:
        log("  - %s (%d ep, %d actions)" % (rp, ne, nr))

    by_task = {}
    for e in eps:
        by_task.setdefault(e.get("task_id"), []).append(e)

    out = []
    out.append("# Phan tich DESKTOP-BENCH (%s)\n" %
               time.strftime("%Y-%m-%d %H:%M"))
    # tong hop theo nguon (split A/B la 2 kernel KHAC nhau - khong cong gon nham)
    if len(srcs) > 1:
        out.append("**Nguon (moi kernel 1 dong - KHONG cong gon):**\n")
        for rp, ne, nr in srcs:
            out.append("- `%s`: %d episode, %d action" %
                       (os.path.basename(os.path.dirname(rp)), ne, nr))
        out.append("")
    # summary: gop cac summary (khong gia dinh cung mau so)
    sums = []
    for p in paths:
        rp, _ = find_result(p)
        if not rp:
            continue
        try:
            d = json.load(io.open(rp, encoding="utf-8"))
            s = d.get("summary") or {}
            if s:
                sums.append((os.path.basename(os.path.dirname(rp)), s))
        except Exception:
            pass
    if sums:
        out.append("**Summary (theo nguon):**\n")
        for name, s in sums:
            out.append("- **%s**: %s" % (name, json.dumps(s, ensure_ascii=False)))
        out.append("")

    # BANG NANG LUC (W2) - doc tu result (by_capability)
    cap = d.get("by_capability")
    if cap:
        out.append("**Bang nang luc (W2):**\n")
        out.append("| nang luc | so task | so ep | win | win_rate |")
        out.append("|---|---|---|---|---|")
        for k in sorted(cap):
            c = cap[k]
            out.append("| %s | %d | %d | %d | %.1f%% |" %
                       (k, c.get("n_tasks", 0), c.get("ep", 0),
                        c.get("win", 0), 100.0 * c.get("win_rate", 0)))
        out.append("")

    out.append("| task | episodes | win | win_rate | mean_score | stuck | avg steps |")
    out.append("|---|---|---|---|---|---|---|")
    for t, gg in sorted(by_task.items()):
        n = len(gg)
        win = sum(1 for e in gg if e.get("win"))
        sc = [e.get("score") for e in gg if isinstance(e.get("score"), (int, float))]
        stuck = sum(1 for e in gg if e.get("stuck"))
        st = [e.get("n_steps") or 0 for e in gg]
        out.append("| %s | %d | %d | %.1f%% | %.2f | %d | %.1f |" %
                   (t, n, win, 100.0 * win / max(n, 1),
                    (sum(sc) / len(sc)) if sc else -1, stuck,
                    sum(st) / max(n, 1)))

    kinds = {"khong co action (mode none)": 0, "lap cung 1 hanh dong (stuck)": 0,
             "co action nhung FAIL": 0, "WIN": 0, "thieu du lieu": 0}
    for e in eps:
        tr = e.get("trace") or []
        acts = [x for x in (e.get("actions") or []) if x]
        if not acts and tr:
            acts = [x for x in (t.get("action") for t in tr) if x]
        if not acts and not tr:
            kinds["thieu du lieu"] += 1
        elif e.get("win"):
            kinds["WIN"] += 1
        elif e.get("stuck") or (acts and max(
                acts.count(a) for a in set(acts)) >= 3):
            kinds["lap cung 1 hanh dong (stuck)"] += 1
        elif not acts:
            kinds["khong co action (mode none)"] += 1
        else:
            kinds["co action nhung FAIL"] += 1
    out.append("\n**Cum failure (theo episode):**\n")
    for k, v in kinds.items():
        if v:
            out.append("- %s: %d" % (k, v))

    out.append("\n**Vi du trajectory theo task:**\n")
    for t, gg in sorted(by_task.items()):
        e = gg[0]
        out.append("- **%s** (win=%s score=%s): %s" %
                   (t, e.get("win"), e.get("score"),
                    " -> ".join((e.get("actions") or [])[:14])))

    if rows:
        out.append("\n**Raw model (3 vi du):**\n")
        seen = set()
        c = 0
        for r in rows:
            tid = r.get("task_id")
            if tid in seen or not (r.get("raw") or "").strip():
                continue
            seen.add(tid)
            c += 1
            out.append("- [%s step%s] %s" % (tid, r.get("step"),
                                              repr((r.get("raw") or "")[:260])))
            if c >= 3:
                break
    os.makedirs(os.path.dirname(os.path.abspath(md)), exist_ok=True)
    with io.open(md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    log("ghi %s" % md)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
