"""test_handoff2.py - kiem tra lai chuoi curate -> dataset -> _resolve voi layout
MOI (Kaggle auto-extract: zip 'shots.zip' top-level -> <ds>/shots/<ten>.png)."""
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, "tmp_handoff2")
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
        row("T10", 2, 0, 0, "CLICK 300 400", True, 0),
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
print(out.stdout.strip()[-400:])
assert out.returncode == 0, out.stderr

# zip phai chua anh o TOP-LEVEL
with zipfile.ZipFile(os.path.join(STAGE, "shots.zip")) as z:
    names = z.namelist()
assert names and not any(n.startswith("shots/") for n in names), names[:3]
print("shots.zip entries top-level OK:", len(names))

# mo phong KAGGLE: file zip bi STRIP, noi dung giai nen vao <ds>/shots/<ten>.png
kaggle_ds = os.path.join(TMP, "kaggle_input_gui-selfplay")
os.makedirs(kaggle_ds, exist_ok=True)
shutil.copy(os.path.join(STAGE, "traj.jsonl"), kaggle_ds)
with zipfile.ZipFile(os.path.join(STAGE, "shots.zip")) as z:
    z.extractall(os.path.join(kaggle_ds, "shots"))

traj = [json.loads(l) for l in
        io.open(os.path.join(kaggle_ds, "traj.jsonl"), encoding="utf-8")
        if l.strip()]
print("traj rows:", len(traj))


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
    for root, _dirs, files in os.walk(base):
        if name in files:
            return os.path.join(root, name)
    return None


n_ok = sum(1 for r in traj if resolve(r["image"], kaggle_ds, TMP))
print("resolve OK %d/%d" % (n_ok, len(traj)))
assert n_ok == len(traj), "FAIL resolve"
assert not [r for r in traj if r.get("variant") == 2], "variant 2 chua bi loai"
shutil.rmtree(TMP, ignore_errors=True)
shutil.rmtree(STAGE, ignore_errors=True)
shutil.rmtree(os.path.join(HERE, "selfplay"), ignore_errors=True)
print("HANDOFF2 TEST PASS (layout Kaggle that)")
