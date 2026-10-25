"""make_bench_v21.py - tao kernel bench cho adapter v21 (copy kernel_bench_v15)."""
import json
import os
import shutil

SRC = 'phase13-gui/kernel_bench_v15'
DST = 'phase13-gui/kernel_bench_v21'

os.makedirs(DST, exist_ok=True)
shutil.copy(os.path.join(SRC, 'bench_v15_kernel.py'),
            os.path.join(DST, 'bench_v15_kernel.py'))
md = json.load(open(os.path.join(SRC, 'kernel-metadata.json'), encoding='utf-8'))
md['dataset_sources'] = [
    ('hhjiji/ornith-gui-lora-v21' if d == 'hhjiji/ornith-gui-lora' else d)
    for d in md['dataset_sources']]
md['id'] = 'hhjiji/ornith-gui-bench-v21'
md['title'] = 'ornith-gui-bench-v21'
json.dump(md, open(os.path.join(DST, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('created', DST)
print('id:', md['id'])
print('lora:', [x for x in md['dataset_sources'] if 'lora' in x])
