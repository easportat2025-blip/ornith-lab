"""test_curate.py - unit test logic chon row cua rollout_curate.py (bundle gia)."""
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, "tmp_curate_test")
os.makedirs(TMP, exist_ok=True)


def row(task, var, rep, step, act, win, nfail, ncheck, mode="action"):
    return {"task_id": task, "variant": var, "rep": rep, "step": step,
            "image": "shots/%s_v%d_r%d_s%02d.png" % (task, var, rep, step),
            "instruction": "do " + task, "target": "prose here\nACTION: " + act,
            "action": act, "mode": mode, "prose_lines": 1, "extra_actions": 0,
            "n_new": 30, "win": win, "n_fail_checks": nfail, "n_checks": ncheck,
            "fail_reason": "failed: x"}


rows = []
# episode WIN 3 step (co 1 action lap) -> giu 2
rows += [row("T10", 0, 0, 0, "CLICK 10 20", True, 0, 2),
         row("T10", 0, 0, 1, "TYPE hi", True, 0, 2),
         row("T10", 0, 0, 2, "TYPE hi", True, 0, 2)]
# episode FAIL 1 check, 2 step -> bo step cuoi, giu step 0
rows += [row("T01", 0, 0, 0, "CLICK 1 1", False, 1, 3),
         row("T01", 0, 0, 1, "CLICK 2 2", False, 1, 3)]
# episode FAIL 5 check -> bo het
rows += [row("T02", 0, 0, 0, "CLICK 3 3", False, 5, 6),
         row("T02", 0, 0, 1, "CLICK 4 4", False, 5, 6)]
# episode mode=legacy -> giu
rows += [row("T03", 0, 0, 0, "TYPE legacy", True, 0, 1, mode="legacy")]

bp = os.path.join(TMP, "bundle.zip")
with zipfile.ZipFile(bp, "w") as z:
    z.writestr("rollout_rows.jsonl",
               "\n".join(json.dumps(r) for r in rows))
    z.writestr("rollout_summary.json", json.dumps({"episodes": 4, "wins": 2,
                                                    "win_rate": 0.5,
                                                    "n_rows": len(rows)}))
    for r in rows:
        z.writestr(r["image"], "PNGDATA")

out = subprocess.run([sys.executable, os.path.join(HERE, "rollout_curate.py"),
                      "--bundle", bp, "--cap", "100"],
                     capture_output=True, text=True, encoding="utf-8")
print(out.stdout)
if out.returncode != 0:
    print("STDERR:", out.stderr)
    sys.exit(1)

p = os.path.join(HERE, "selfplay_dataset", "traj.jsonl")
kept = [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]
print("KEPT:", len(kept))
for k in kept:
    print("  ", k["task_id"], "step", k["step"], k["action"], "win", k["win"])
# ky vong: T10 step0, T10 step1 (step2 lap bi bo), T01 step0 (step1 bi bo),
# T02 bo het, T03 step0 -> 4 dong
assert len(kept) == 4, "FAIL: %d" % len(kept)
assert [k["step"] for k in kept if k["task_id"] == "T10"] == [0, 1]
assert [k["step"] for k in kept if k["task_id"] == "T01"] == [0]
assert not [k for k in kept if k["task_id"] == "T02"]
assert not [k for k in kept if k["task_id"] == "T03" and k["action"] == "legacy"
            and k["win"] is False]
p2 = os.path.join(HERE, "selfplay_dataset", "traj_reason.jsonl")
assert len([l for l in io.open(p2, encoding="utf-8") if l.strip()]) == 4
sz = os.path.getsize(os.path.join(HERE, "selfplay_dataset", "shots.zip"))
print("shots.zip bytes:", sz)
print("TEST PASS")
