"""post_gate.py - cham gate tu ket qua bench da tai ve + ghi LOBBY + log jsonl.

Dung:
    python scripts/post_gate.py --out phase13-gui/out_bench_v21 --label v21 \
        [--kernel khoadangnguye/ornith-gui-bench-v21] [--holdout-variant 2]
"""
import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE = os.path.join(ROOT, "phase13-gui", "gate_report.py")
LOBBY = os.path.join(ROOT, "agent.md")
JSONL = os.path.join(ROOT, "phase13-gui", "gate_results.jsonl")

# ten file ket qua theo suite
CAND = {
    "b15": ["b15_result.json"],
    "b155": ["b155_result.json", "b15_5_result.json"],
    "b16": ["b16_result.json"],
    "v14": ["v14_result.json", "bench_result.json"],
    "b3d": ["bench3d_result.json", "b3d_result.json"],
}


def find(out, suite):
    hits = []
    for nm in CAND[suite]:
        hits += glob.glob(os.path.join(out, "**", nm), recursive=True)
    # uu tien file lon nhat (thuong la ban day du)
    hits = [h for h in hits if os.path.getsize(h) > 20]
    if not hits:
        return None
    return max(hits, key=lambda p: os.path.getsize(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--kernel", default="")
    ap.add_argument("--holdout-variant", type=int, default=2)
    ap.add_argument("--no-lobby", action="store_true")
    a = ap.parse_args()

    args = []
    found = {}
    for suite in ("b15", "b155", "b16", "v14", "b3d"):
        p = find(a.out, suite)
        if p:
            found[suite] = p
    # bench 3D: khong qua gate_report (metric khac: bbox-hit) -> tom tat rieng
    if found.get("b3d") and not (found.get("b15") or found.get("b155")
                                 or found.get("b16") or found.get("v14")):
        try:
            d = json.load(io.open(found["b3d"], encoding="utf-8"))
        except Exception as e:
            print("3D doc loi:", e)
            return 2
        s = d.get("summary") if isinstance(d.get("summary"), dict) else d
        keys = ("n_tasks", "hit_rate", "bbox_hit", "median_pct", "median",
                "mean_pct", "mean")
        info = {k: s.get(k) for k in keys if k in s}
        if not info:
            info = {k: v for k, v in list(d.items())[:8]
                    if isinstance(v, (int, float, str))}
        rec = {"ts": time.time(), "label": a.label, "kernel": a.kernel,
               "verdict": "3D", "summary_3d": info, "files": found}
        with io.open(JSONL, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        line = "  3D       %s" % json.dumps(info, ensure_ascii=False)[:200]
        print(line)
        if not a.no_lobby:
            head = ("### [DeepSeek] %s - **BENCH 3D %s: %s**" % (
                time.strftime("%d/%m %H:%M"), a.label,
                json.dumps(info, ensure_ascii=False)[:160]))
            with io.open(LOBBY, "a", encoding="utf-8") as fh:
                fh.write("\n" + head + "\n")
            print("LOBBY updated")
        return 0
    for suite in ("b15", "b155", "b16", "v14"):
        if found.get(suite):
            args += ["--" + suite, found[suite]]
    if not args:
        print("KHONG tim thay file ket qua trong %s" % a.out)
        return 2
    args += ["--holdout-variant", str(a.holdout_variant), "--label", a.label]

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    p = subprocess.run([sys.executable, GATE] + args, capture_output=True,
                       env=env, cwd=ROOT, timeout=3600)
    rep = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    print(rep)
    if err.strip():
        print("STDERR:", err[-800:])
    rc = p.returncode

    m = re.search(r"GATE\s+(\w+)\s+\((\d+)/(\d+)\)", rep)
    verdict = m.group(1) if m else "?"
    npass = int(m.group(2)) if m else 0
    ntot = int(m.group(3)) if m else 0
    key_lines = [l.strip() for l in rep.splitlines()
                 if l.strip().startswith("[PASS]") or l.strip().startswith("[FAIL]")]
    suite_lines = [l.strip() for l in rep.splitlines()
                   if re.match(r"^\s{2}(B15|B15\.5|B16|v14|HOLDOUT)", l)]

    rec = {"ts": time.time(), "label": a.label, "kernel": a.kernel,
           "verdict": verdict, "npass": npass, "ntot": ntot, "rc": rc,
           "files": found, "summary": suite_lines, "checks": key_lines}
    with io.open(JSONL, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if not a.no_lobby:
        head = ("### [DeepSeek] \u2022 20/10 %s \u2014 **GATE %s: %s (%d/%d)**"
                % (time.strftime("%H:%M"), a.label, verdict, npass, ntot))
        body = ""
        if a.kernel:
            body += "- kernel: `%s`\n" % a.kernel
        for l in suite_lines:
            body += "- %s\n" % l
        for l in key_lines:
            body += "- %s\n" % l
        body += ("- baseline v18 tren B15 = 27.8% (holdout v2 = 33.3%) \u2014 "
                 "gate FAIL = can doi recipe; PASS = tie/duoc, tiep tuc v22\n")
        with io.open(LOBBY, "a", encoding="utf-8") as fh:
            fh.write("\n" + head + "\n\n" + body)
        print("LOBBY updated")
    return rc


if __name__ == "__main__":
    sys.exit(main())
