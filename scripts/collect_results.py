"""collect_results.py - gom TAT CA ket qua bench (gate + baseline) vao 1 bang.

Dung: python scripts/collect_results.py
"""
import glob
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (nhan, file ket qua, loai)
ITEMS = [
    ("v21", "phase13-gui/out_bench_v21/b15_result.json", "B15"),
    ("v22", "phase13-gui/out_bench_v22/b15_result.json", "B15"),
    ("v22", "phase13-gui/out_bench_v155_v22/b15_result.json", "B15.5"),
    ("v22", "phase13-gui/out_bench_v16_v22/b15_result.json", "B16"),
    ("v21", "phase13-gui/out_bench_v155_v21/b15_result.json", "B15.5"),
    ("v21", "phase13-gui/out_bench_v16_v21/b15_result.json", "B16"),
    ("v21", "phase13-gui/out_bench_3d_v21/bench3d_result.json", "3D"),
    ("v21", "phase13-gui/out_bench_3d_hard_v21/bench3d_result.json", "3D-HARD"),
    ("v18", "phase13-gui/out_bench_v155_B/b15_result.json", "B15.5"),
    ("v18", "phase13-gui/out_bench_v16_B/b15_result.json", "B16"),
    ("v18", "phase13-gui/out_bench_3d_B/bench3d_result.json", "3D"),
    ("v18", "phase13-gui/out_bench_3d_hard_B/bench3d_result.json", "3D-HARD"),
    ("v18", "phase13-gui/out_bench_v15/b15_result.json", "B15"),
]


def stats(path):
    try:
        d = json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return None
    eps = d.get("episodes") or []
    if eps:
        n = len(eps)
        w = sum(1 for e in eps if e.get("win") or e.get("success")
                or e.get("hit"))
        by_var = {}
        for e in eps:
            v = str(e.get("variant"))
            a = by_var.setdefault(v, [0, 0])
            a[0] += 1
            a[1] += 1 if (e.get("win") or e.get("success")
                          or e.get("hit")) else 0
        agg = d.get("agg") or {}
        return {"n": n, "w": w, "rate": w / n if n else 0,
                "var": {k: "%d/%d" % (v[1], v[0]) for k, v in sorted(by_var.items())},
                "parse": agg.get("parse_rate"), "prose": agg.get("prose_leak_rate")}
    r = d.get("results") or {}
    if r:
        n = len(r)
        w = sum(1 for v in r.values() if v)
        return {"n": n, "w": w, "rate": w / n if n else 0}
    # 3D: bbox-hit
    s = d.get("summary") or d
    if isinstance(s, dict) and ("hit_rate" in s or "median" in s
                                or "n_tasks" in s):
        return {"raw": {k: s.get(k) for k in
                        ("n_tasks", "hit_rate", "median_pct", "median",
                         "mean_pct", "bbox_hit") if k in s}}
    return None


rows = []
for model, path, suite in ITEMS:
    st = stats(os.path.join(ROOT, path))
    if not st:
        continue
    rows.append((model, suite, path, st))

print("%-6s %-8s %-34s %s" % ("model", "suite", "file", "ket qua"))
print("-" * 100)
for model, suite, path, st in rows:
    if "raw" in st:
        print("%-6s %-8s %-34s %s" % (model, suite, os.path.basename(path),
                                      json.dumps(st["raw"], ensure_ascii=False)))
    else:
        extra = ""
        if st.get("var"):
            extra += " per-var " + " ".join("v%s:%s" % (k, v)
                                           for k, v in st["var"].items())
        if st.get("parse") is not None:
            extra += " parse=%.2f" % st["parse"]
        print("%-6s %-8s %-34s %d/%d = %.3f%s" % (
            model, suite, os.path.basename(path), st["w"], st["n"],
            st["rate"], extra))

# so sanh v21 vs v18
print("-" * 100)
base = {(m, s): st for m, s, _p, st in rows if m == "v18"}
for model in ("v22", "v21"):
    for suite in ("B15", "B15.5", "B16", "3D"):
        st = next((r[3] for r in rows if r[0] == model and r[1] == suite
                   and "raw" not in r[3]), None)
        b = base.get(("v18", suite))
        if not st or not b or "raw" in b:
            continue
        d = st["rate"] - b["rate"]
        print("SO SANH %-8s %s %.3f vs v18 %.3f  => %+.1f%%  %s" % (
            suite, model, st["rate"], b["rate"], 100 * d,
            "TOT" if d > 0 else "XAU"))
