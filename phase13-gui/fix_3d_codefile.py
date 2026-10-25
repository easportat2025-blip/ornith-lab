"""fix_3d_codefile.py - sua code_file cua 4 kernel bench 3D (metadata tro
'bench_v15_kernel.py' nhung file thuc la 'bench3d_kernel.py' -> push se hong).
"""
import json
import os

DIRS = ['phase13-gui/kernel_bench_3d', 'phase13-gui/kernel_bench_3d_v21',
        'phase13-gui/kernel_bench_3d_hard', 'phase13-gui/kernel_bench_3d_hard_v21']
for d in DIRS:
    mf = os.path.join(d, 'kernel-metadata.json')
    if not os.path.exists(mf):
        print('skip', d)
        continue
    md = json.load(open(mf, encoding='utf-8'))
    files = [f for f in os.listdir(d) if f.endswith('.py')]
    if md.get('code_file') not in files:
        md['code_file'] = 'bench3d_kernel.py'
        json.dump(md, open(mf, 'w', encoding='utf-8'), ensure_ascii=False,
                  indent=2)
        print('fixed', d, '-> code_file', md['code_file'])
    else:
        print('ok', d, md['code_file'])
