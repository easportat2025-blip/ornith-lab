"""cmp_v18_v21.py - so sanh ket qua train v18 vs v21 + doc think0/3D neu co."""
import io
import json
import os


def load(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


print("=== TRAIN: v18 vs v21 ===")
rows = []
for tag, p in (("v18", "phase13-gui/out_sft_v18/gui_result.json"),
               ("v21 v1 (data rong)", "phase13-gui/out_sft_v21/gui_result.json")):
    d = load(p)
    if not d:
        print("  %-18s (khong co)" % tag)
        continue
    print("  %-18s n_train=%-5s steps=%-4s acc=%-6s train_sub=%-6s traj_sub=%-6s real=%-6s" %
          (tag, d.get("n_train"), d.get("steps"), d.get("acc_after"),
           d.get("acc_train_sub"), d.get("acc_traj_sub"), d.get("acc_real_after")))
    rows.append((tag, d))

print()
print("=== THINK0 (v18 + enable_thinking=False) tren B15 ===")
d = load("phase13-gui/out_bench_v18_think0/b15_result.json")
if d:
    s = d.get("summary") or {}
    agg = s.get("agg") or {}
    print("  n=%s wins=%s rate=%.3f | parse=%s prose=%s mean_new=%s" %
          (s.get("n"), s.get("wins"), s.get("win_rate", 0), agg.get("parse_rate"),
           agg.get("prose_leak_rate"), agg.get("mean_new")))
    print("  by_task:", json.dumps(s.get("by_task") or {}, ensure_ascii=False))
else:
    print("  (chua co)")

print()
print("=== 3D bench (v18 baseline) ===")
for d in ("phase13-gui/out_ornith-gui-bench-3d/bench3d_result.json",
          "phase13-gui/out_ornith-gui-bench-3d-hard/bench3d_result.json"):
    r = load(d)
    if not r:
        print("  %-52s (chua co)" % os.path.basename(os.path.dirname(d)))
        continue
    s = r.get("summary") or {}
    print("  %-24s n=%s hit=%s rate=%s parse=%s" %
          (os.path.basename(os.path.dirname(d)), s.get("n"), s.get("n_hit"),
           s.get("hit_rate"), s.get("parse_rate")))
    print("     by_color:", json.dumps(s.get("by_color") or {}, ensure_ascii=False))
