"""test_handoff.py - kiem tra chuoi curate -> dataset -> _resolve cua load_ds_rows.

Muc dich: v21 train se that 1 GPU-gio; neu anh "image" trong traj.jsonl khong
resolve duoc (hoac zip sai cau truc) thi mat that gio. Test nay mo phong lai
logic _resolve cua gui_sft.py tren dataset staged that.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, "tmp_handoff")
STAGE = os.path.join(HERE, "selfplay_dataset")
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP, exist_ok=True)


def row(task, var, rep, step, act, win, nfail):
    return {"task_id": task, "variant": var, "rep": rep, "step": step,
            "image": "shots/%s_v%d_r%d_s%02d.png" % (task, var, rep, step),
            "instruction": "do " + task, "target": "prose\nACTION: " + act,
            "action": act, "mode": "action", "prose_lines": 1,
            "extra_actions": 0, "n_new": 30, "win": win,
            "n_fail_checks": nfail, "n_checks": 3, "fail_reason": ""}


rows = [row("T10", 0, 0, 0, "CLICK 100 200", True, 0),
        row("T10", 0, 0, 1, "TYPE hi", True, 0),
        row("T10", 2, 0, 0, "CLICK 300 400", True, 0),   # variant 2 -> loai
        row("T01", 0, 0, 0, "CLICK 1 1", False, 1)]
bp = os.path.join(TMP, "bundle.zip")
with zipfile.ZipFile(bp, "w") as z:
    z.writestr("rollout_rows.jsonl", "\n".join(json.dumps(r) for r in rows))
    z.writestr("rollout_summary.json", json.dumps({"episodes": 3, "wins": 2}))
    for r in rows:
        z.writestr(r["image"], "PNGDATA")

shutil.rmtree(STAGE, ignore_errors=True)
out = subprocess.run([sys.executable, os.path.join(HERE, "rollout_curate.py"),
                      "--bundle", bp, "--cap", "100", "--max-fail", "2",
                      "--exclude-variants", "2"],
                     capture_output=True, text=True, encoding="utf-8")
print(out.stdout.strip())
assert out.returncode == 0, out.stderr

# --- mo phong _resolve cua load_ds_rows (gui_sft.py) ---
traj = os.path.join(STAGE, "traj.jsonl")
drows = [json.loads(l) for l in io.open(traj, encoding="utf-8") if l.strip()]
print("traj.jsonl rows:", len(drows))
ext = os.path.join(TMP, "ext")
os.makedirs(ext, exist_ok=True)
for f in os.listdir(STAGE):
    if f.endswith(".zip"):
        with zipfile.ZipFile(os.path.join(STAGE, f)) as z:
            z.extractall(ext)


def resolve(rel, base, ext):
    p = os.path.join(base, rel)
    if os.path.exists(p):
        return p
    cand = os.path.join(ext, rel)
    if os.path.exists(cand):
        return cand
    name = os.path.basename(rel)
    for root, _dirs, files in os.walk(ext):
        if name in files:
            return os.path.join(root, name)
    return None


n_ok = 0
for r in drows:
    p = resolve(r["image"], STAGE, ext)
    if p:
        n_ok += 1
    else:
        print("  KHONG RESOLVE:", r["image"])
assert n_ok == len(drows), "resolve %d/%d" % (n_ok, len(drows))
# variant 2 phai bi loai khoi train
assert not [r for r in drows if r.get("variant") == 2], "variant 2 chua bi loai"
# moi row phai co action + image + instruction
for r in drows:
    assert r.get("action") and r.get("instruction") and r.get("image"), r
print("resolve OK %d/%d | variant2 excluded OK | schema OK" % (n_ok, len(drows)))
shutil.rmtree(TMP, ignore_errors=True)
shutil.rmtree(STAGE, ignore_errors=True)
shutil.rmtree(os.path.join(HERE, "selfplay"), ignore_errors=True)
print("HANDOFF TEST PASS")
