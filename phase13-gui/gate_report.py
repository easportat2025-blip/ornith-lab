"""gate_report.py - cham gate GUI/B15 tu ket qua cac kernel bench.

Dung:
  python phase13-gui/gate_report.py --b15 out_bench_v21/b15_result.json \
      [--b155 ...] [--b16 ...] [--v14 ...] [--holdout-variant 2] [--label v21]

Nguyen (MAIN_QUEST Day 2):
  - B15 tong >= 35%
  - variant HELD-OUT (mac dinh 2, bi loai khoi self-play train) >= 35%
  - v14 >= 2/3
  - B15.5 / B16: so sanh voi baseline v18 (neu co --b155-base / --b16-base)
Exit 0 = PASS, 1 = FAIL (dung cho pipeline).
"""
import argparse
import io
import json
import os
import sys
from collections import defaultdict

THRESH_B15 = 0.35
THRESH_HOLDOUT = 0.35
THRESH_V14 = 2.0 / 3.0
# baseline v18 tren B15 (doc 20/10): tong 10/36, holdout variant2 4/12
BASE_V18 = {"total": 10 / 36.0, "holdout": 4 / 12.0, "v14": 2.0 / 3.0}


def load(path):
    if not path:
        return None
    if not os.path.exists(path):
        print("KHONG CO file: %s" % path)
        return None
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def suite_stats(d):
    """Tu b15_result.json lay n / wins / per-task / per-variant."""
    if not d:
        return None
    eps = d.get("episodes") or []
    if not eps:
        s = d.get("summary") or {}
        bt = d.get("by_task") or {}
        n = sum(v.get("n", 0) for v in bt.values())
        w = sum(v.get("win", 0) for v in bt.values())
        return {"n": n, "wins": w, "rate": (w / n if n else 0.0),
                "by_task": {k: "%d/%d" % (v.get("win", 0), v.get("n", 0))
                            for k, v in bt.items()},
                "by_variant": {}, "agg": d.get("agg") or {}}
    by_var = defaultdict(lambda: [0, 0])
    by_task = defaultdict(lambda: [0, 0])
    for e in eps:
        v = e.get("variant")
        t = e.get("task_id")
        w = 1 if (e.get("win") or e.get("success")) else 0
        by_var[v][0] += w
        by_var[v][1] += 1
        by_task[t][0] += w
        by_task[t][1] += 1
    n = len(eps)
    w = sum(1 for e in eps if (e.get("win") or e.get("success")))
    return {"n": n, "wins": w, "rate": (w / n if n else 0.0),
            "by_task": {k: "%d/%d" % (v[0], v[1]) for k, v in by_task.items()},
            "by_variant": {k: "%d/%d" % (v[0], v[1]) for k, v in by_var.items()},
            "agg": d.get("agg") or {}}


def v14_stats(d):
    if not d:
        return None
    r = d.get("results") or {}
    n = len(r)
    w = sum(1 for v in r.values() if v)
    return {"n": n, "wins": w, "rate": (w / n if n else 0.0),
            "by_task": {k: ("PASS" if v else "FAIL") for k, v in r.items()}}


def show(name, st, holdout_var=None):
    if not st:
        print("  %-8s (khong co ket qua)" % name)
        return None
    line = "  %-8s %d/%d = %.3f" % (name, st["wins"], st["n"], st["rate"])
    if st.get("by_variant"):
        line += " | per-variant: " + " ".join(
            "v%s:%s" % (k, v) for k, v in sorted(st["by_variant"].items()))
    print(line)
    if st.get("by_task"):
        print("           per-task: " + "  ".join(
            "%s %s" % (k, v) for k, v in sorted(st["by_task"].items())))
    if st.get("agg"):
        a = st["agg"]
        print("           agg: parse=%.3f prose=%.3f mean_new=%.1f steps=%s" % (
            a.get("parse_rate", -1), a.get("prose_leak_rate", -1),
            a.get("mean_new", -1), a.get("steps", "?")))
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b15")
    ap.add_argument("--b155")
    ap.add_argument("--b16")
    ap.add_argument("--v14")
    ap.add_argument("--b155-base")
    ap.add_argument("--b16-base")
    ap.add_argument("--holdout-variant", type=int, default=2)
    ap.add_argument("--label", default="model")
    a = ap.parse_args()

    print("=" * 72)
    print("GATE REPORT - %s (holdout variant = %d)" % (a.label, a.holdout_variant))
    print("=" * 72)

    b15 = suite_stats(load(a.b15))
    b155 = suite_stats(load(a.b155))
    b16 = suite_stats(load(a.b16))
    v14 = v14_stats(load(a.v14))
    b155b = suite_stats(load(a.b155_base))
    b16b = suite_stats(load(a.b16_base))

    show("B15", b15)
    show("B15.5", b155)
    show("B16", b16)
    show("v14", v14)
    if b155b:
        show("B15.5base", b155b)
    if b16b:
        show("B16base", b16b)

    # ---- holdout (chi B15 co bien variant) ----
    hold_rate = None
    if b15 and b15.get("by_variant"):
        key = str(a.holdout_variant)
        v = b15["by_variant"].get(key)
        if v and "/" in v:
            w, n = [int(x) for x in v.split("/")]
            hold_rate = w / n if n else 0.0
            print("  HOLDOUT  v%s: %d/%d = %.3f  (baseline v18 = %.3f)"
                  % (key, w, n, hold_rate, BASE_V18["holdout"]))

    checks = []
    if b15:
        checks.append(("B15 tong >= %.0f%%" % (THRESH_B15 * 100),
                       b15["rate"] >= THRESH_B15, "%.3f" % b15["rate"]))
        checks.append(("B15 >= baseline v18 (%.3f)" % BASE_V18["total"],
                       b15["rate"] >= BASE_V18["total"], "%.3f" % b15["rate"]))
    if hold_rate is not None:
        checks.append(("holdout v%d >= %.0f%%" %
                       (a.holdout_variant, THRESH_HOLDOUT * 100),
                       hold_rate >= THRESH_HOLDOUT, "%.3f" % hold_rate))
        checks.append(("holdout >= baseline v18 (%.3f)" % BASE_V18["holdout"],
                       hold_rate >= BASE_V18["holdout"], "%.3f" % hold_rate))
    if v14:
        checks.append(("v14 >= 2/3", v14["rate"] >= THRESH_V14,
                       "%.3f" % v14["rate"]))
    if b155 and b155b:
        checks.append(("B15.5 >= baseline v18", b155["rate"] >= b155b["rate"],
                       "%.3f vs %.3f" % (b155["rate"], b155b["rate"])))
    if b16 and b16b:
        checks.append(("B16 >= baseline v18", b16["rate"] >= b16b["rate"],
                       "%.3f vs %.3f" % (b16["rate"], b16b["rate"])))

    print("-" * 72)
    if not checks:
        print("KHONG co check nao (thieu file ket qua?)")
        return 1
    allok = True
    for name, ok, val in checks:
        allok = allok and ok
        print("  [%s] %-34s %s" % ("PASS" if ok else "FAIL", name, val))
    print("-" * 72)
    print("GATE %s (%d/%d)" % ("PASS" if allok else "FAIL",
                               sum(1 for _, o, _ in checks if o), len(checks)))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
