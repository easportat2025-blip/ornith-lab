"""patch_v22_3d.py - them data train 3D vao kernel v22 (grounding 3D, action
space giong GUI: CLICK x y 0..1000).

Data: dataset hhjiji/ornith-gui-train3d (traj.jsonl + shots.zip).
Vai tro: model 3D cua ta hoc CHUNG ky nang "nhin anh -> click target" o ca 2D/3D.
"""
import json
import os
import re

K = 'phase13-gui/kernel_v22/gui_sft_v22.py'
s = open(K, encoding='utf-8').read()

OLD = """    # TASK-19: synth TARGETED S1-S8 (module da INLINE o cuoi file nay)"""
NEW = """    # TASK-23: data train 3D (grounding 3D - action space giong GUI)
    t3d_rows = load_ds_rows("gui-train3d", "traj.jsonl")
    log(f"train3d: {len(t3d_rows)} row")
    # TASK-19: synth TARGETED S1-S8 (module da INLINE o cuoi file nay)"""
assert OLD in s
s = s.replace(OLD, NEW, 1)

OLD2 = """    train_rows = (synth_rows + real_train + traj_rows + tgt_rows + sp_rows)"""
NEW2 = """    train_rows = (synth_rows + real_train + traj_rows + tgt_rows
                  + t3d_rows + sp_rows)"""
assert OLD2 in s
s = s.replace(OLD2, NEW2, 1)

OLD3 = """        f"targeted {len(tgt_rows)} + selfplay {len(sp_rows)}) \""""
NEW3 = """        f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"
        f" + selfplay {len(sp_rows)}) \""""
assert OLD3 in s
s = s.replace(OLD3, NEW3, 1)

OLD4 = """        "n_targeted": len(tgt_rows),"""
NEW4 = """        "n_targeted": len(tgt_rows),
        "n_train3d": len(t3d_rows),"""
assert OLD4 in s
s = s.replace(OLD4, NEW4, 1)

# base_n phai tinh ca train3d de cap 30% selfplay dung
OLD5 = """    base_n = (len(synth_rows) + len(real_train) + len(traj_rows)
              + len(tgt_rows))"""
NEW5 = """    base_n = (len(synth_rows) + len(real_train) + len(traj_rows)
              + len(tgt_rows) + len(t3d_rows))"""
assert OLD5 in s
s = s.replace(OLD5, NEW5, 1)

open(K, 'w', encoding='utf-8').write(s)
print('patched', K)

# --- metadata: them dataset train3d
mf = 'phase13-gui/kernel_v22/kernel-metadata.json'
md = json.load(open(mf, encoding='utf-8'))
if 'hhjiji/ornith-gui-train3d' not in md['dataset_sources']:
    md['dataset_sources'].append('hhjiji/ornith-gui-train3d')
json.dump(md, open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('metadata datasets:', md['dataset_sources'])
