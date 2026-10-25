"""make_bench_v14_v21.py - kernel v14 regression (3 task) cho adapter v21.

v14 = click_green / counter5 / login_done; adapter v18 dat 2/3 (gate Day 2:
v21 >= 2/3). Bo competition_sources de tranh loi 400 (GPU + competition +
internet=true bi Kaggle chan).
"""
import json
import os
import shutil

SRC = 'phase13-gui/bench_kernel'
DST = 'phase13-gui/kernel_bench_v14_v21'

os.makedirs(DST, exist_ok=True)
shutil.copy(os.path.join(SRC, 'bench_gui_kaggle.py'),
            os.path.join(DST, 'bench_gui_kaggle.py'))
md = json.load(open(os.path.join(SRC, 'kernel-metadata.json'), encoding='utf-8'))
md['competition_sources'] = []
md['dataset_sources'] = [
    ('hhjiji/ornith-gui-lora-v21' if d == 'hhjiji/ornith-gui-lora' else d)
    for d in md['dataset_sources']]
md['id'] = 'hhjiji/ornith-gui-bench-v14-v21'
md['title'] = 'ornith-gui-bench-v14-v21'
json.dump(md, open(os.path.join(DST, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('created', DST, '| id', md['id'], '| comp', md['competition_sources'],
      '| net', md['enable_internet'], '| gpu', md['enable_gpu'])
