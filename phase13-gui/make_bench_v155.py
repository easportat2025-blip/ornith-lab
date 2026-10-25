"""make_bench_v155.py - dong goi B15.5 (MiMo TASK-15) thanh dataset + tao kernel.

Dataset: hhjiji/ornith-gui-bench-v155  (zip bench_v155_bundle.zip -> top 'bench_v155/')
Kernels: hhjiji/ornith-gui-bench-v155 (adapter v18 = baseline)
         hhjiji/ornith-gui-bench-v155-v21 (adapter v21 = gate)
"""
import json
import os
import shutil
import zipfile

SRC = 'phase13-gui/bench_v15/tasks_v15_5'
DST = 'phase13-gui/bench_v155_dataset'
TOP = 'bench_v155'
ZIP_NAME = 'bench_v155_bundle.zip'
DATASET_ID = 'hhjiji/ornith-gui-bench-v155'

# ---------------------------------------------------------------- dataset
os.makedirs(DST, exist_ok=True)
zp = os.path.join(DST, ZIP_NAME)
n = 0
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for rel in ['bench_v155.py', 'checker.py', 'self_test_report.json']:
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
assert TOP + '/tasks/tasks.json' in names, 'thieu tasks.json'
assert TOP + '/bench_v155.py' in names, 'thieu bench_v155.py'
assert TOP + '/checker.py' in names, 'thieu checker.py'
meta = {"title": "Ornith GUI bench B15.5 (T13-T18)",
        "id": DATASET_ID, "licenses": [{"name": "other"}]}
json.dump(meta, open(os.path.join(DST, 'dataset-metadata.json'), 'w',
                     encoding='utf-8'), ensure_ascii=False, indent=2)
print('zip %s: %d files, %.1f KB' % (zp, n, os.path.getsize(zp) / 1024))

# ---------------------------------------------------------------- kernels
BENCH_SRC = 'phase13-gui/kernel_bench_v15'
OLD_IMPORT = '        for name in ("bench_v15", "checker"):\n'
NEW_IMPORT = '        for name in ("bench_v155", "bench_v15", "checker"):\n'
OLD_MODE = '            SUITE.mode = "B15"\n'
NEW_MODE = '            SUITE.mode = meta.get("suite") or "B15"\n'
OLD_MIMO = '    use_mimo = (SUITE.mode == "B15" and SUITE.mod is not None\n'
NEW_MIMO = '    use_mimo = (str(SUITE.mode).startswith("B15") and SUITE.mod is not None\n'


def make_kernel(dst, kid, title, lora):
    os.makedirs(dst, exist_ok=True)
    code = open(os.path.join(BENCH_SRC, 'bench_v15_kernel.py'),
                encoding='utf-8').read()
    for old, new in ((OLD_IMPORT, NEW_IMPORT), (OLD_MODE, NEW_MODE),
                     (OLD_MIMO, NEW_MIMO)):
        assert old in code, 'NOT FOUND: %s' % old[:50]
        code = code.replace(old, new)
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
    print('kernel', dst, '->', kid)
    print('   datasets:', [x for x in md['dataset_sources']
                           if 'bench' in x or 'lora' in x])


make_kernel('phase13-gui/kernel_bench_v155', 'hhjiji/ornith-gui-bench-v155',
            'ornith-gui-bench-v155', 'v18')
make_kernel('phase13-gui/kernel_bench_v155_v21',
            'hhjiji/ornith-gui-bench-v155-v21', 'ornith-gui-bench-v155-v21',
            'v21')
