"""make_v22.py - fork recipe v18 -> kernel_v22: + self-play + synth TARGETED (S1-S8).

TASK-19 (MiMo): phase13-gui/gen_synth_targeted.py -> build_targeted(n, seed, img_dir)
Dong vao data train de va 3 cum loi lon nhat cua v18:
  C1 prose/no-action, C2 stuck-repeat, C3 khong doc text hien thi.
"""
import json
import os
import shutil

SRC = 'phase13-gui/kernel/gui_sft.py'
DST = 'phase13-gui/kernel_v22/gui_sft_v22.py'
GENDIR = 'phase13-gui/kernel_v22'
N_TARGETED = 250           # ~940 row (3.75 row/ep) ~ 24% cua mix 3860 row

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
    # TASK-19: synth TARGETED S1-S8 (3 cum loi lon cua v18)
    import gen_synth_targeted as GST
    tdir = os.path.join(WORK, "gui_imgs_targeted")
    os.makedirs(tdir, exist_ok=True)
    tgt_rows = GST.build_targeted(N_TARGETED, 303, tdir)
    log(f"synth targeted: {len(tgt_rows)} row (S1-S8)")
    base_n = (len(synth_rows) + len(real_train) + len(traj_rows)
              + len(tgt_rows))
    cap_sp = int(0.30 * base_n / 0.70)
    if len(sp_rows) > cap_sp:
        log(f"selfplay {len(sp_rows)} -> cap {cap_sp} (30%)")
        sp_rows = sp_rows[:cap_sp]
    train_rows = (synth_rows + real_train + traj_rows + tgt_rows + sp_rows)
    STEPS_V22 = max(200, int(STEPS * len(train_rows) / 2808))
    log(f"STEPS_V22 = max(200, {STEPS} * {len(train_rows)} / 2808) = {STEPS_V22}")
'''

OLD_LOG = '''    log(f"train={len(train_rows)} (synth {len(synth_rows)} + "
        f"real {len(real_train)} + traj {len(traj_rows)}) "
        f"eval={len(eval_rows)} t={time.time() - t0:.0f}s")
'''
NEW_LOG = '''    log(f"train={len(train_rows)} (synth {len(synth_rows)} + "
        f"real {len(real_train)} + traj {len(traj_rows)} + "
        f"targeted {len(tgt_rows)} + selfplay {len(sp_rows)}) "
        f"eval={len(eval_rows)} t={time.time() - t0:.0f}s")
'''

s = open(SRC, encoding='utf-8').read()
assert OLD_DATA in s and OLD_LOG in s
s = s.replace(OLD_DATA, NEW_DATA)
s = s.replace(OLD_LOG, NEW_LOG)
# --- TASK-22: Kaggle CHI upload code_file, file phu trong kernel dir bi BO.
# -> gen_synth_targeted.py phai INLINE vao script (khong dung import file).
GST_SRC = open('phase13-gui/gen_synth_targeted.py', encoding='utf-8').read()
cut = GST_SRC.find('if __name__ ==')
if cut > 0:
    GST_SRC = GST_SRC[:cut]
import re as _re
NEW_DATA2 = _re.sub(
    r"    # TASK-19: synth TARGETED.*?tgt_rows = GST\.build_targeted\(N_TARGETED, 303, tdir\)",
    "    # TASK-19: synth TARGETED S1-S8 (module da INLINE o cuoi file nay)\n"
    "    tdir = os.path.join(WORK, \"gui_imgs_targeted\")\n"
    "    os.makedirs(tdir, exist_ok=True)\n"
    "    tgt_rows = build_targeted(N_TARGETED, 303, tdir)",
    NEW_DATA, flags=_re.S)
assert "GST.build_targeted" not in NEW_DATA2, 'thay the loader that bai'
s = s.replace(NEW_DATA, NEW_DATA2)
# insert module source truoc khoi __main__
MAIN = 'if __name__ == "__main__":\n'
assert MAIN in s
s = s.replace(MAIN, '# ==== gen_synth_targeted.py (INLINE: Kaggle chi upload code_file) ====\n'
              + GST_SRC + '\n\n' + MAIN, 1)
assert s.count('        max_steps=STEPS,\n') == 1
s = s.replace('        max_steps=STEPS,\n', '        max_steps=STEPS_V22,\n')
assert s.count('"n_train": len(train_rows), "steps": STEPS,') == 1
s = s.replace('"n_train": len(train_rows), "steps": STEPS,',
              '"n_train": len(train_rows), "steps": STEPS_V22,\n'
              '        "n_selfplay": len(sp_rows),\n'
              '        "n_targeted": len(tgt_rows),\n'
              '        "recipe": "v18-action-only + synth-targeted S1-S8 + selfplay",')
# hang constant
s = s.replace('N_TRAIN = 1200\n',
              'N_TRAIN = 1200\nN_TARGETED = %d\n' % N_TARGETED)
os.makedirs(GENDIR, exist_ok=True)
open(DST, 'w', encoding='utf-8').write(s)
shutil.copy('phase13-gui/gen_synth_targeted.py',
            os.path.join(GENDIR, 'gen_synth_targeted.py'))
md = json.load(open('phase13-gui/kernel_v21/kernel-metadata.json',
                    encoding='utf-8'))
md['id'] = 'hhjiji/ornith-gui-sft-v22'
md['title'] = 'ornith-gui-sft-v22'
md['code_file'] = 'gui_sft_v22.py'
json.dump(md, open(os.path.join(GENDIR, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('wrote', DST, len(s), 'bytes')
print('kernel v22 id:', md['id'])
print('datasets:', md['dataset_sources'])
