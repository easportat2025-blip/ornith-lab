"""read_b15_result.py — doc b15_result.json (kernel bench v15) va in bao cao gon.

Dung:
  python phase13-gui/read_b15_result.py <path> [--samples N] [--raw all|win|fail]

In: tong quan, by_task, agg, tung episode, phan tich fail, va (tuy chon) raw
output cua cac step (tu trace, da bi cat 300 chars trong kernel).
"""
import argparse
import io
import json
import re
import sys


def load(path):
    t = io.open(path, encoding="utf-8", errors="replace").read()
    return json.loads(t)


def classify_fail(eps):
    """Doan nhiem nhan fail tu trace: done_spam / no_action / wrong_action / stuck."""
    tags = []
    tr = eps.get("trace") or []
    if not tr:
        return "no_trace"
    modes = [s.get("mode") for s in tr]
    acts = [str(s.get("act") or "") for s in tr]
    if modes and modes[-1] == "none":
        tags.append("no_action_last")
    ndone = sum(1 for s in tr if s.get("act") in ("DONE", "done"))
    if ndone >= 2:
        tags.append("done_spam")
    if any(m == "none" for m in modes):
        tags.append("no_action_step")
    if len(set(acts)) <= max(1, len(acts) // 3):
        tags.append("stuck_repeat")
    return ",".join(tags) or "wrong_action"


def post_action_guess(raw):
    """True neu raw (<=300 chars) co dong khac rong SAU 'ACTION:' cuoi."""
    lines = [l.strip() for l in (raw or "").splitlines() if l.strip()]
    k = None
    for i, l in enumerate(lines):
        if re.match(r"^ACTION\s*:", l, re.I):
            k = i
    if k is None:
        return None
    return len(lines[k + 1:]) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--raw", default="none", choices=["all", "win", "fail", "none"])
    a = ap.parse_args()

    d = load(a.path)
    if "error" in d:
        print("!! KERNEL ERROR DUMP:", d.get("error"), "-", d.get("msg", "")[:300])
        print("   t_sec:", d.get("t_sec"))
        return 1

    print("=== TONG QUAN ===")
    for k in ("suite", "runner", "n", "wins", "win_rate", "adapter",
              "adapter_strategy", "reason_max", "t_sec"):
        print("  %-16s %s" % (k, d.get(k)))
    print("  by_task:")
    for t, v in sorted((d.get("by_task") or {}).items()):
        print("    %-14s %s" % (t, v))
    print("  agg:", json.dumps(d.get("agg") or {}, ensure_ascii=False))

    eps = d.get("episodes") or []
    print()
    print("=== EPISODES (%d) ===" % len(eps))
    for r in eps:
        tr = r.get("trace") or []
        npost = sum(1 for s in tr if post_action_guess(s.get("raw")))
        print("  %-14s v%s win=%-5s steps=%-3s mode=%s post=%s reason=%s"
              % (r.get("task_id"), r.get("variant"), r.get("win"),
                 len(tr),
                 ",".join(sorted({s.get("mode") or "?" for s in tr})),
                 npost, str(r.get("reason"))[:60]))
    fl = [r for r in eps if not r.get("win")]
    if fl:
        print()
        print("=== FAIL (%d) ===" % len(fl))
        for r in fl:
            print("  %-14s v%s -> %s" % (r.get("task_id"), r.get("variant"),
                                         classify_fail(r)))

    if a.samples or a.raw != "none":
        want = {"all": lambda r: True, "win": lambda r: r.get("win"),
                "fail": lambda r: not r.get("win"), "none": lambda r: False}[a.raw]
        print()
        print("=== RAW SAMPLES (mode=%s) ===" % a.raw)
        shown = 0
        for r in eps:
            if not want(r):
                continue
            for s in (r.get("trace") or []):
                if shown >= a.samples:
                    break
                print("  [%s v%s t%s] mode=%s act=%s ok=%s"
                      % (r.get("task_id"), r.get("variant"), s.get("t"),
                         s.get("mode"), s.get("act"), s.get("success")))
                print("      raw:", str(s.get("raw"))[:220].replace("\n", "\\n"))
                shown += 1
            if shown >= a.samples:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
