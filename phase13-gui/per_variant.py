"""per_variant.py - tach win rate theo variant tu b15_result.json (de biet
variant nao "sach" (khong bi train) va baseline cua no)."""
import io
import json
import sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else 'phase13-gui/out_bench_v15/b15_result.json'
d = json.load(io.open(path, encoding='utf-8'))
eps = d.get('episodes') or []
by_var = defaultdict(lambda: [0, 0])
by_task = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for e in eps:
    v = e.get('variant')
    w = 1 if e.get('win') or e.get('success') else 0
    by_var[v][0] += w
    by_var[v][1] += 1
    by_task[e.get('task_id')][v][0] += w
    by_task[e.get('task_id')][v][1] += 1
tot_w = sum(x[0] for x in by_var.values())
tot_n = sum(x[1] for x in by_var.values())
print("%s: %d/%d = %.3f" % (path, tot_w, tot_n, tot_w / max(tot_n, 1)))
for v in sorted(by_var):
    w, n = by_var[v]
    print("  variant %s: %d/%d = %.3f" % (v, w, n, w / max(n, 1)))
print("  theo task:")
for t in sorted(by_task):
    s = "  %-14s" % t + " ".join(
        "v%s:%d/%d" % (v, by_task[t][v][0], by_task[t][v][1])
        for v in sorted(by_task[t]))
    print(s)
