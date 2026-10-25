"""make_rollout_v21.py - kernel rollout vong 2: model v21 tu rollout tren B15.

Vong self-play tiep theo: model v21 (sau khi train) -> rollout temp 0.7 tren
B15 variant 0/1 -> curate -> data cho v23. Giu nguyen adapter v21 de khong
contaminate them bien variant (variant 2 van la held-out).
"""
import json
import os
import shutil

SRC = 'phase13-gui/kernel_rollout_base'
DST = 'phase13-gui/kernel_rollout_v21'

os.makedirs(DST, exist_ok=True)
code = open(os.path.join(SRC, 'rollout_kernel.py'), encoding='utf-8').read()
old = 'N_REPS = 2                # TASK-17: 12 task x 3 variant x 2 reps = 72 episode'
new = 'N_REPS = 2                # vong 2: 12 task x 3 variant x 2 reps = 72 episode'
assert old in code
code = code.replace(old, new)
open(os.path.join(DST, 'rollout_kernel.py'), 'w', encoding='utf-8').write(code)
md = json.load(open(os.path.join(SRC, 'kernel-metadata.json'), encoding='utf-8'))
md['dataset_sources'] = [
    ('hhjiji/ornith-gui-lora-v21' if d == 'hhjiji/ornith-gui-lora' else d)
    for d in md['dataset_sources']]
md['id'] = 'hhjiji/ornith-gui-rollout-v21'
md['title'] = 'ornith-gui-rollout-v21'
json.dump(md, open(os.path.join(DST, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('created', DST, '| id', md['id'])
print('datasets:', md['dataset_sources'])
