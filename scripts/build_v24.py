# -*- coding: utf-8 -*-
"""
build_v24.py - dung kernel 'ornith-gui-sft-v24' tu kernel_v23b voi recipe:

 1) traj: dataset R2 (972 row / 216 DONE) thay cho traj2 (816 row) va BO
    truncation [:400] (R2 row DONE nam o cuoi file -> truncate = mat het
    loi ich cua R2).
 2) targeted: done_rate 0.0 -> 0.75 + families="ALL" (S1-S8 + S9/S10).
    Do cua @GLM 22/10: P(DONE) buoc cuoi ep nhieu buoc
       v22 = 16,4% | v23a (dr0.75) = 68,9% | v23a + R2 = 83,6% (tot nhat)
 3) them du lieu loop-recovery cua @GLM (600 row tren app THAT, nham 2 vong
    lap that su: ghi lai cung 1 field / lap shortcut).
 4) loader: them buoc quet thu muc dataset goc (fix 816/816 row khong
    resolve duoc anh do anh nam o subdir traj_images/).
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "kernel_v23b")
DST = os.path.join(ROOT, "phase13-gui", "kernel_v24")

# ---- 1) copy code + metadata ----
os.makedirs(DST, exist_ok=True)
shutil.copy2(os.path.join(SRC, "gui_sft_v23.py"), os.path.join(DST, "gui_sft_v23.py"))
code_p = os.path.join(DST, "gui_sft_v23.py")
s = io.open(code_p, encoding="utf-8").read()


def sub(old, new, tag):
    global s
    if old not in s:
        raise SystemExit("KHONG khop: %s\n---\n%s" % (tag, old[:200]))
    if s.count(old) != 1:
        raise SystemExit("KHONG duy nhat (%d): %s" % (s.count(old), tag))
    s = s.replace(old, new, 1)
    print("  ok: " + tag)


# ---- a) targeted dr0.75 + tat ca 10 family ----
sub('    tgt_rows = build_targeted(N_TARGETED, SEED + 2, tdir, done_rate=0.0)\n'
    '    log(f"synth targeted: {len(tgt_rows)} row (S1-S8)")',
    '    tgt_rows = build_targeted(N_TARGETED, SEED + 2, tdir, done_rate=0.75,\n'
    '                            families="ALL")\n'
    '    log(f"synth targeted: {len(tgt_rows)} row (S1-S8+S9/S10, dr0.75)")',
    "targeted dr0.75 + ALL")

# ---- b) traj R2: bo truncation [:400] ----
sub('    traj_rows = traj_rows[:400]  # v23: giu phan nho hon',
    '    # v24: BO truncation [:400] - R2 co them 156 row DONE o CUOI file,\n'
    '    # truncate = mat het phan R2 dang gia nhat (P(DONE) 68,9% -> 83,6%).',
    "traj khong truncate")

# ---- c) them loop-recovery (synth-recipe cua @GLM) ----
sub('    # TASK-18: self-play (rollout -> curate) cap 30% tong du lieu\n'
    '    sp_rows = load_ds_rows("gui-selfplay", "traj.jsonl", required=True)',
    '    # v24: duLieu LOOP-RECOVERY tren app THAT (@GLM 22/10) - nham 2 vong\n'
    '    # lap that su: ghi lai cung 1 field / lap 1 shortcut.\n'
    '    rec_rows = load_ds_rows("ornith-gui-synth-recipe", "traj.jsonl",\n'
    '                           required=True)\n'
    '    log(f"loop-recovery (synth-recipe): {len(rec_rows)} row")\n'
    '    # TASK-18: self-play (rollout -> curate) cap 30% tong du lieu\n'
    '    sp_rows = load_ds_rows("gui-selfplay", "traj.jsonl", required=True)',
    "them loop-recovery rows")

# ---- d) dua rec_rows vao train_rows + base_n + log ----
sub('    base_n = (len(synth_rows) + len(real_train) + len(traj_rows)\n'
    '              + len(tgt_rows) + len(t3d_rows) + len(t3dh_rows)\n'
    '              + len(pr_rows))',
    '    base_n = (len(synth_rows) + len(real_train) + len(traj_rows)\n'
    '              + len(tgt_rows) + len(t3d_rows) + len(t3dh_rows)\n'
    '              + len(pr_rows) + len(rec_rows))',
    "base_n += rec_rows")

sub('    train_rows = (synth_rows + real_train + traj_rows + tgt_rows\n'
    '                  + t3d_rows + t3dh_rows + pr_rows + sp_rows)',
    '    train_rows = (synth_rows + real_train + traj_rows + tgt_rows\n'
    '                  + t3d_rows + t3dh_rows + pr_rows + rec_rows + sp_rows)',
    "train_rows += rec_rows")

sub('        f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"',
    '        f"targeted {len(tgt_rows)} + loop-recovery {len(rec_rows)}"\n'
    '        f" + train3d {len(t3d_rows)}"',
    "log co rec_rows")

# ---- e) nhan recipe ----
sub('"recipe": "v23: rebalance - synth 500 + targeted 800 + policy-replay x2 + '
    '3D 600 + traj 400 + selfplay"',
    '"recipe": "v24: dr0.75 + S1-S10 + R2 972 + loop-recovery 600 + '
    'policy-replay x2 + 3D 600 + selfplay"',
    "nhan recipe")

io.open(code_p, "w", encoding="utf-8", newline="\n").write(s)

# ---- 2) metadata ----
meta_p = os.path.join(SRC, "kernel-metadata.json")
m = json.load(io.open(meta_p, encoding="utf-8"))
ds = [d for d in m["dataset_sources"] if d != "khoadangnguye/ornith-gui-traj2"]
ds.insert(5, "khoadangnguye/ornith-gui-traj")
if "khoadangnguye/ornith-gui-synth-recipe" not in ds:
    ds.insert(6, "khoadangnguye/ornith-gui-synth-recipe")
m["dataset_sources"] = ds
m["id"] = "khoadangnguye/ornith-gui-sft-v24"
m["title"] = "ornith-gui-sft-v24"
json.dump(m, io.open(os.path.join(DST, "kernel-metadata.json"), "w",
                      encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
print("  ok: metadata (traj2 -> traj + synth-recipe)")
print("  code_file:", m["code_file"], "| ds:", len(ds))

# ---- 3) verify ----
py = os.path.join(DST, "gui_sft_v23.py")
import py_compile
try:
    py_compile.compile(py, doraise=True)
    print("  ok: py_compile")
except Exception as e:
    print("  !! py_compile loi:", e)
    sys.exit(1)
txt = io.open(py, encoding="utf-8").read()
checks = [
    ("done_rate=0.75", "done_rate=0.75" in txt),
    ('families="ALL"', 'families="ALL"' in txt),
    ("khong truncate traj", "traj_rows[:400]" not in txt),
    ("loop-recovery", "loop-recovery (synth-recipe)" in txt),
    ("rec_rows trong train_rows", "+ rec_rows + sp_rows" in txt),
    ("fix loader base-walk", "os.walk(base)" in txt),
    ("guard traj >=900", "len(traj_rows) < 900" in txt),
]
for name, ok in checks:
    print("   %-26s %s" % (name, "PASS" if ok else "FAIL"))
if not all(c[1] for c in checks):
    sys.exit(1)
print("\nSAN SANG PUSH:", os.path.join(DST))
