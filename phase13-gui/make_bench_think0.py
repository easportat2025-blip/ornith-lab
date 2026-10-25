"""make_bench_think0.py - bien thep bench voi enable_thinking=False (prompt co
think RONG) de do tac dong cua failure mode C1 (prose/no-action).

Giu nguyen protocol goc (thinking ON) cho gate chinh; bien thep nay la
THI NGHIEM so luong: neu v18 think0 >> 27.8% thi day la lever lon nhat.
"""
import json
import os
import shutil

SRC = 'phase13-gui/kernel_bench_v15'
DST = 'phase13-gui/kernel_bench_v18_think0'

os.makedirs(DST, exist_ok=True)
code = open(os.path.join(SRC, 'bench_v15_kernel.py'), encoding='utf-8').read()
OLD = 'ENABLE_THINKING = os.environ.get("ORNI_THINK", "1") != "0"'
NEW = 'ENABLE_THINKING = False  # variant think0: prompt render think rong'
assert OLD in code
code = code.replace(OLD, NEW)
open(os.path.join(DST, 'bench_v15_kernel.py'), 'w', encoding='utf-8').write(code)
md = json.load(open(os.path.join(SRC, 'kernel-metadata.json'), encoding='utf-8'))
md['id'] = 'hhjiji/ornith-gui-bench-v15-think0'
md['title'] = 'ornith-gui-bench-v15-think0'
json.dump(md, open(os.path.join(DST, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('created', DST, '| id', md['id'], '| lora',
      [x for x in md['dataset_sources'] if 'lora' in x])
