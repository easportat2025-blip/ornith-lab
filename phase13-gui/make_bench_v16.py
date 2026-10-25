"""make_bench_v16.py - dong goi B16-A (MiMo TASK-20, T19-T26) + 2 kernel bench.

Dataset: hhjiji/ornith-gui-bench-v16 (zip bench_v16_bundle.zip -> top 'bench_v16/')
Kernels: hhjiji/ornith-gui-bench-v16      (adapter v18 = baseline)
         hhjiji/ornith-gui-bench-v16-v21  (adapter v21 = gate)
"""
import json
import os
import shutil
import zipfile

SRC = 'phase13-gui/bench_v15/tasks_v16_a'
DST = 'phase13-gui/bench_v16_dataset'
TOP = 'bench_v16'
ZIP_NAME = 'bench_v16_bundle.zip'
DATASET_ID = 'hhjiji/ornith-gui-bench-v16'

os.makedirs(DST, exist_ok=True)
zp = os.path.join(DST, ZIP_NAME)
n = 0
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for rel in ['bench_v16.py', 'checker_v16.py', 'self_test_report.json']:
        p = os.path.join(SRC, rel)
        if os.path.exists(p):
            z.write(p, TOP + '/' + rel)
            n += 1
    tdir = os.path.join(SRC, 'tasks')
    for f in sorted(os.listdir(tdir)):
        z.write(os.path.join(tdir, f), TOP + '/tasks/' + f)
        n += 1
with zipfile.ZipFile(zp) as z:
    names = set(z.namelist())
for must in (TOP + '/tasks/tasks.json', TOP + '/bench_v16.py',
             TOP + '/checker_v16.py'):
    assert must in names, 'thieu ' + must
meta = {"title": "Ornith GUI bench B16-A (T19-T26)", "id": DATASET_ID,
        "licenses": [{"name": "other"}]}
json.dump(meta, open(os.path.join(DST, 'dataset-metadata.json'), 'w',
                     encoding='utf-8'), ensure_ascii=False, indent=2)
print('zip %s: %d files, %.1f KB' % (zp, n, os.path.getsize(zp) / 1024))

BENCH_SRC = 'phase13-gui/kernel_bench_v15'
import re
OLD_IMPORT = re.compile(r'        for name in \("bench[^)]*\):\n')
NEW_IMPORT = '        for name in ("bench_v16", "bench_v155", "bench_v15", "checker"):\n'
OLD_MODE = '            SUITE.mode = meta.get("suite") or "B15"\n'
NEW_MODE = '            SUITE.mode = meta.get("suite") or "B15"\n'


def make_kernel(dst, kid, title, lora):
    os.makedirs(dst, exist_ok=True)
    code = open(os.path.join(BENCH_SRC, 'bench_v15_kernel.py'),
                encoding='utf-8').read()
    assert OLD_IMPORT.search(code), 'khong thay import loop'
    code = OLD_IMPORT.sub(NEW_IMPORT, code, count=1)
    open(os.path.join(dst, 'bench_v15_kernel.py'), 'w',
         encoding='utf-8').write(code)
    md = json.load(open(os.path.join(BENCH_SRC, 'kernel-metadata.json'),
                        encoding='utf-8'))
    md['dataset_sources'] = [
        (DATASET_ID if d == 'hhjiji/ornith-gui-bench-v15' else
         ('hhjiji/ornith-gui-lora-v21' if d == 'hhjiji/ornith-gui-lora' and
          lora == 'v21' else
          ('hhjiji/ornith-gui-lora' if d == 'hhjiji/ornith-gui-lora' else d)))
        for d in md['dataset_sources']]
    md['id'] = kid
    md['title'] = title
    json.dump(md, open(os.path.join(dst, 'kernel-metadata.json'), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=2)
    print('kernel', dst, '->', kid, '|',
          [x for x in md['dataset_sources'] if 'bench' in x or 'lora' in x])


make_kernel('phase13-gui/kernel_bench_v16', 'hhjiji/ornith-gui-bench-v16',
            'ornith-gui-bench-v16', 'v18')
make_kernel('phase13-gui/kernel_bench_v16_v21',
            'hhjiji/ornith-gui-bench-v16-v21', 'ornith-gui-bench-v16-v21',
            'v21')
