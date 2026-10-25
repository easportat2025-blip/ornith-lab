"""check_done_prediction.py - kiem chung DU DOAN "ky luat DONE" cua GLM tren ket qua bench.

Du doan (duoc do tren DATA, phase13-gui/done_discipline_report.md):
  mix v22 co P(DONE | cuoi episode nhieu buoc) = 16,4%  (targeted dr=0, 0% row DONE)
  => model IT khi emit DONE, nhat la tren task nhieu buoc
  => cluster C4 (khong ket thuc / no_submit) ky vong VAN CON.

Cong cu nay do tren KET QUA BENH (b15_result.json hoac desktop_result.json):
  - % episode co DONE / % episode KET THUC bang DONE
  - % episode "stuck" (lap cung 1 hanh dong >= 3 lan)
  - win rate, avg steps
  - phan tich rieng tren episode THAT (nhiều bước) - noi C4 xay ra

Dung: python phase13-gui/check_done_prediction.py <result.json> [...]
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def log(m):
    print("[donepred] %s" % m, flush=True)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())[:120]


def verb_of(a):
    a = (a or "").strip()
    if not a:
        return ""
    a = a.split()[0].upper()
    if a == "ACTION:":
        return ""
    return a


def act_str(t):
    """'act' co 2 dang: str ('CLICK 1 2') hoac list (['click',[1,2]])."""
    a = t.get("act")
    if isinstance(a, str):
        return a
    if isinstance(a, (list, tuple)) and a:
        head = str(a[0])
        rest = " ".join(str(y) for y in a[1:])
        return (head + " " + rest).strip()
    return ""


def episodes_of(d):
    """Lay episodes[] tu 2 format: bench B15 (trace) va desktop (actions)."""
    out = []
    for e in d.get("episodes") or []:
        tr = e.get("trace") or []
        acts = [x for x in (e.get("actions") or []) if x]
        raws = []
        if tr:
            acts = [act_str(t) for t in tr]
            raws = [t.get("raw") for t in tr]
        else:
            raws = [None] * len(acts)
        # dong trong "raw" co 'DONE' khong? (bench raw co 'ACTION: DONE')
        has_done = any(re.search(r"\bDONE\b", (r or ""), re.I) for r in raws) \
            or any(verb_of(a) == "DONE" for a in acts)
        end_done = bool(acts) and (verb_of(acts[-1]) == "DONE"
                                   or re.search(r"\bDONE\b", raws[-1] or "", re.I))
        steps = len(acts) or e.get("n_steps") or 0
        vs = [verb_of(a) for a in acts if a]
        max_same = max((vs.count(v) for v in set(vs)), default=0)
        stuck = 1 if (max_same >= 3 and steps >= 3) else 0
        out.append({"task": e.get("task_id"), "win": bool(e.get("win")),
                    "steps": steps, "any_done": 1 if has_done else 0,
                    "end_done": 1 if end_done else 0, "stuck": stuck,
                    "max_same": max_same, "score": e.get("score")})
    return out


def report(path):
    d = json.load(io.open(path, encoding="utf-8", errors="replace"))
    eps = episodes_of(d)
    if not eps:
        log("%s: khong co episodes[]" % path)
        return None
    by = {}
    for e in eps:
        by.setdefault(e["task"], []).append(e)
    print("\n=== %s ===" % os.path.basename(path))
    print("| task | ep | win_rate | %ep co DONE | %ep KET THUC bang DONE | %stuck | avg steps |")
    print("|---|---|---|---|---|---|---|")
    tot = {"n": 0, "win": 0, "any": 0, "end": 0, "stuck": 0, "steps": 0}
    for t, gg in sorted(by.items()):
        n = len(gg)
        w = sum(1 for x in gg if x["win"])
        a = sum(x["any_done"] for x in gg)
        e2 = sum(x["end_done"] for x in gg)
        st = sum(x["stuck"] for x in gg)
        sp = sum(x["steps"] for x in gg) / max(n, 1)
        print("| %s | %d | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f |" %
              (t, n, 100.0 * w / n, 100.0 * a / n, 100.0 * e2 / n,
               100.0 * st / n, sp))
        tot["n"] += n
        tot["win"] += w
        tot["any"] += a
        tot["end"] += e2
        tot["stuck"] += st
        tot["steps"] += sum(x["steps"] for x in gg)
    n = max(tot["n"], 1)
    print("| **TONG** | %d | %.1f%% | **%.1f%%** | **%.1f%%** | %.1f%% | %.1f |" %
          (tot["n"], 100.0 * tot["win"] / n, 100.0 * tot["any"] / n,
           100.0 * tot["end"] / n, 100.0 * tot["stuck"] / n,
           tot["steps"] / n))
    return tot


def main():
    paths = sys.argv[1:]
    if not paths:
        cands = []
        for d in ("out_bench_v22", "out_bench_v21", "out_bench_v15",
                  "out_bench_v155_v21", "out_bench_v155_B"):
            p = os.path.join(HERE, d, "b15_result.json")
            if os.path.exists(p):
                cands.append(p)
        paths = cands
    if not paths:
        log("khong co file ket qua nao de kiem")
        return 1
    for p in paths:
        try:
            report(p)
        except Exception as e:
            log("%s loi: %s" % (p, e))
    print("\nGHI CHU: du doan cua GLM: P(DONE | cuoi ep nhieu buoc) cua MIX v22 = 16,4%")
    print("  => neu %ep KET THUC bang DONE tren bench < 30% => du doan DUNG (C4 van con).")
    print("  => neu >= 40% => du doan SAI => can lai phan tich (model da hoc duoc DONE).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
