"""make_bench_any.py - tao kernel bench cho (suite x adapter) bat ky.

Dung:
    python phase13-gui/make_bench_any.py <dir> <kernel_id> <title> <suite> <adapter>
  suite:   b15 | b155 | b16   (bo 'b' -> import module bench_v<suite>)
  adapter: v18 | v21 | v22   (dataset hhjiji/ornith-gui-lora[-v21|-v22])
"""
import json
import os
import re
import shutil

BENCH_SRC = 'phase13-gui/kernel_bench_v15'
SUITE_MODULE = {'b15': 'bench_v15', 'b155': 'bench_v155', 'b16': 'bench_v16'}
SUITE_DATASET = {
    'b15': 'hhjiji/ornith-gui-bench-v15',
    'b155': 'hhjiji/ornith-gui-bench-v155',
    'b16': 'hhjiji/ornith-gui-bench-v16',
}
ADAPTER_DATASET = {
    'v18': 'hhjiji/ornith-gui-lora',
    'v21': 'hhjiji/ornith-gui-lora-v21',
    'v22': 'hhjiji/ornith-gui-lora-v22',
}


def build(dst, kid, title, suite, adapter, think=False):
    os.makedirs(dst, exist_ok=True)
    code = open(os.path.join(BENCH_SRC, 'bench_v15_kernel.py'),
                encoding='utf-8').read()
    # import loop: dat suite truoc
    mods = ['"' + SUITE_MODULE[suite] + '"', '"bench_v155"', '"bench_v16"',
            '"bench_v15"', '"checker"']
    seen, uniq = set(), []
    for m in mods:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    new_import = '        for name in (%s):\n' % ', '.join(uniq)
    code, n = re.subn(r'        for name in \("bench[^)]*\):\n', new_import,
                      code, count=1)
    assert n == 1, 'khong thay import loop trong %s' % BENCH_SRC
    if not think:
        pass
    else:
        old = 'ENABLE_THINKING = os.environ.get("ORNI_THINK", "1") != "0"'
        assert old in code
        code = code.replace(old, 'ENABLE_THINKING = False  # think0 variant')
    open(os.path.join(dst, 'bench_v15_kernel.py'), 'w',
         encoding='utf-8').write(code)
    md = json.load(open(os.path.join(BENCH_SRC, 'kernel-metadata.json'),
                        encoding='utf-8'))
    ds = []
    for d in md['dataset_sources']:
        if d == 'hhjiji/ornith-gui-bench-v15':
            ds.append(SUITE_DATASET[suite])
        elif d == 'hhjiji/ornith-gui-lora':
            ds.append(ADAPTER_DATASET[adapter])
        else:
            ds.append(d)
    md['dataset_sources'] = ds
    md['id'] = kid
    md['title'] = title
    json.dump(md, open(os.path.join(dst, 'kernel-metadata.json'), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=2)
    print('kernel %-42s -> %s' % (dst, kid))
    print('   suite=%s adapter=%s | %s' % (suite, adapter,
          [x for x in ds if 'bench' in x or 'lora' in x]))


if __name__ == '__main__':
    import sys
    a = sys.argv[1:]
    build(a[0], a[1], a[2], a[3], a[4], think=(len(a) > 5 and a[5] == 'think0'))
