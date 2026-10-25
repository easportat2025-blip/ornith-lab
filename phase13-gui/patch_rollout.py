"""patch_rollout.py - fix rollout: giu near-miss rows, /tmp cho lora_fixed, full-run config.

TASK-17: rollout v1 chi giu rows cua episode WIN -> model chua win task nao thi
0 dong -> khong co du lieu self-play. Sua: giu TAT CA step, gan nhan win /
n_fail_checks / n_checks de curation chon.
"""
import json
import os
import shutil

SRC = 'phase13-gui/kernel_rollout_v20/rollout_kernel.py'
DST_DIR = 'phase13-gui/kernel_rollout_base'

OLD_CFG = '''N_REPS = 4
MAX_ROWS = 480
SMOKE_TASKS = ["T01_signup", "T05_shortcut", "T11_counter"]  # smoke truoc (v1)
SMOKE_REPS = 1            # smoke: 1 rep/task; full run se dat [] / None
'''

NEW_CFG = '''N_REPS = 2                # TASK-17: 12 task x 3 variant x 2 reps = 72 episode
MAX_ROWS = 1200           # full run: giu het (row nho, anh ~20KB)
SMOKE_TASKS = []          # full run (v2+): khong con smoke
SMOKE_REPS = None         # -> dung N_REPS
'''

OLD_KEEP = '''    win = bool(st.get("success"))
    if win:
        rows.extend(steps)
'''

NEW_KEEP = '''    win = bool(st.get("success"))
    # TASK-17: giu CA episode fail (near-miss) de curation chon; giu nhan de
    # curation biet episode nao WIN. Khong giu -> 0 dong khi model chua win
    # task nao (rollout v1: 0/9 win => 0 dong).
    tests = ((st.get("state") or {}).get("tests") or {})
    n_fail = sum(1 for v in tests.values() if not v)
    n_check = len(tests)
    for row in steps:
        row["win"] = win
        row["n_fail_checks"] = n_fail
        row["n_checks"] = n_check
        row["fail_reason"] = str(st.get("reason", ""))[:160]
    rows.extend(steps)
'''

OLD_FIXED = '    fixed = os.path.join(WORK or "/tmp", "lora_fixed")\n'
NEW_FIXED = ('    # /tmp de khong lam nganh 465MB adapter vao OUTPUT (disk local 10GB)\n'
             '    fixed = os.path.join("/tmp", "lora_fixed")\n')

OLD_CAP = '    rows = rows[:MAX_ROWS]\n'
NEW_CAP = ('    rows = rows[:MAX_ROWS]\n'
           '    n_row_win = sum(1 for r in rows if r.get("win"))\n'
           '    n_row_fail = len(rows) - n_row_win\n')

OLD_SUM = '''    summary = {"episodes": len(stats), "wins": wins, "win_rate": wins / n,
               "n_rows": len(rows), "n_reps": reps, "temp": ROLL_TEMP,
'''
NEW_SUM = '''    summary = {"episodes": len(stats), "wins": wins, "win_rate": wins / n,
               "n_rows": len(rows), "n_rows_win": n_row_win,
               "n_rows_fail": n_row_fail, "n_reps": reps, "temp": ROLL_TEMP,
'''


def patch(text, name, old, new):
    assert old in text, "NOT FOUND in %s: %s" % (name, old[:60])
    assert text.count(old) == 1, "AMBIGUOUS in %s" % name
    return text.replace(old, new)


s = open(SRC, encoding='utf-8').read()
s = patch(s, 'CFG', OLD_CFG, NEW_CFG)
s = patch(s, 'KEEP', OLD_KEEP, NEW_KEEP)
s = patch(s, 'FIXED', OLD_FIXED, NEW_FIXED)
s = patch(s, 'CAP', OLD_CAP, NEW_CAP)
s = patch(s, 'SUM', OLD_SUM, NEW_SUM)
open(SRC, 'w', encoding='utf-8').write(s)
print('patched', SRC)

# --- ban base: adapter v18 (tot nghiep hon) thay vi v20
os.makedirs(DST_DIR, exist_ok=True)
shutil.copy(SRC, os.path.join(DST_DIR, 'rollout_kernel.py'))
md = json.load(open('phase13-gui/kernel_rollout_v20/kernel-metadata.json',
                    encoding='utf-8'))
md['dataset_sources'] = [
    d if d != 'hhjiji/ornith-gui-lora-v20' else 'hhjiji/ornith-gui-lora'
    for d in md['dataset_sources']]
md['id'] = 'hhjiji/ornith-gui-rollout-base'
md['title'] = 'ornith-gui-rollout-base'
json.dump(md, open(os.path.join(DST_DIR, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('created', DST_DIR, '-> id', md['id'])
print('datasets:', md['dataset_sources'])
