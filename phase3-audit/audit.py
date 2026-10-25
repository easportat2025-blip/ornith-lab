"""Audit bench_detail: fence rate, do dai gen, phan bo loi theo config."""
import json
import os
from collections import Counter

detail = None
for root, _, files in os.walk("/kaggle/input"):
    if "bench_detail.jsonl" in files:
        detail = os.path.join(root, "bench_detail.jsonl")
print(f"[audit] detail={detail}", flush=True)
if not detail:
    raise SystemExit("khong thay bench_detail")

rows = [json.loads(l) for l in open(detail, encoding="utf-8")]
print(f"[audit] n={len(rows)}", flush=True)
by_cfg = {}
for r in rows:
    by_cfg.setdefault(r["cfg"], []).append(r)
for cfg, rs in by_cfg.items():
    fenced = sum(1 for r in rs if "```" in r.get("gen", ""))
    empty = sum(1 for r in rs if len(r.get("gen", "").strip()) < 20)
    avglen = sum(len(r.get("gen", "")) for r in rs) / max(len(rs), 1)
    whys = Counter(r.get("why", "?") for r in rs)
    scores = Counter(r.get("score", -1) for r in rs)
    print(f"[audit] {cfg}: fence={fenced}/{len(rs)} empty={empty} "
          f"avglen={avglen:.0f}", flush=True)
    print(f"[audit] {cfg} why={dict(whys)}", flush=True)
    print(f"[audit] {cfg} scores={dict(sorted(scores.items()))}",
          flush=True)
print("[audit] DONE", flush=True)
