"""make_v21.py - fork recipe v18 (gui_sft.py) -> kernel_v21/gui_sft_v21.py + self-play.

TASK-18: v20 (recipe reasoning THINK+ACTION) REGRESS tren B15 27.8% -> 8.3%.
v21 = recipe v18 (1 dong action, data synth+real-ui+gui-traj) + self-play rows,
self-play cap 30% tong du lieu, steps scale theo data.
"""
import os
import re
import shutil

SRC = 'phase13-gui/kernel/gui_sft.py'
DST = 'phase13-gui/kernel_v21/gui_sft_v21.py'

OLD_DATA = '''    real_rows = load_ds_rows("real-fixtures", "grounding.jsonl")
    real_train = load_ds_rows("real-ui", "grounding.jsonl")
    traj_rows = load_ds_rows("gui-traj", "traj.jsonl")
    train_rows = synth_rows + real_train + traj_rows
'''

NEW_DATA = '''    real_rows = load_ds_rows("real-fixtures", "grounding.jsonl")
    real_train = load_ds_rows("real-ui", "grounding.jsonl")
    traj_rows = load_ds_rows("gui-traj", "traj.jsonl")
    # TASK-18: self-play (rollout -> curate) cap 30% tong du lieu
    sp_rows = load_ds_rows("gui-selfplay", "traj.jsonl")
    base_n = len(synth_rows) + len(real_train) + len(traj_rows)
    cap_sp = int(0.30 * base_n / 0.70)
    if len(sp_rows) > cap_sp:
        log(f"selfplay {len(sp_rows)} -> cap {cap_sp} (30%)")
        sp_rows = sp_rows[:cap_sp]
    train_rows = synth_rows + real_train + traj_rows + sp_rows
    STEPS_V21 = max(200, int(STEPS * len(train_rows) / 2808))
    log(f"STEPS_V21 = max(200, {STEPS} * {len(train_rows)} / 2808) = {STEPS_V21}")
'''

OLD_LOG = '''    log(f"train={len(train_rows)} (synth {len(synth_rows)} + "
        f"real {len(real_train)} + traj {len(traj_rows)}) "
        f"eval={len(eval_rows)} t={time.time() - t0:.0f}s")
'''
NEW_LOG = '''    log(f"train={len(train_rows)} (synth {len(synth_rows)} + "
        f"real {len(real_train)} + traj {len(traj_rows)} + "
        f"selfplay {len(sp_rows)}) "
        f"eval={len(eval_rows)} t={time.time() - t0:.0f}s")
'''

s = open(SRC, encoding='utf-8').read()
assert OLD_DATA in s
assert OLD_LOG in s
s = s.replace(OLD_DATA, NEW_DATA)
s = s.replace(OLD_LOG, NEW_LOG)
assert s.count('        max_steps=STEPS,\n') == 1
s = s.replace('        max_steps=STEPS,\n', '        max_steps=STEPS_V21,\n')
assert s.count('"n_train": len(train_rows), "steps": STEPS,') == 1
s = s.replace('"n_train": len(train_rows), "steps": STEPS,',
              '"n_train": len(train_rows), "steps": STEPS_V21,\n'
              '        "n_selfplay": len(sp_rows),\n'
              '        "recipe": "v18-action-only + selfplay",')
os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, 'w', encoding='utf-8').write(s)
print('wrote', DST, len(s), 'bytes')
print('checks:', 'STEPS_V21' in s, 'selfplay' in s, 'max_steps=STEPS_V21' in s)
