"""check_all_kernels.py - tom tat kernel: id + dataset mount (suite x adapter)."""
import glob
import json
import os

rows = []
for mf in sorted(glob.glob('phase13-gui/kernel*/kernel-metadata.json') +
                 glob.glob('phase14-blender/*/kernel-metadata.json')):
    try:
        d = json.load(open(mf, encoding='utf-8'))
    except Exception as e:
        print('ERR', mf, e)
        continue
    ds = d.get('dataset_sources', [])
    suite = [x for x in ds if 'bench' in x]
    ad = [x for x in ds if 'lora' in x]
    extra = [x for x in ds if 'offline' in x or 'selfplay' in x]
    rows.append((d.get('id'), mf, suite, ad, extra,
                 'GPU' if d.get('enable_gpu') else
                 ('TPU' if d.get('enable_tpu') else 'CPU'),
                 d.get('enable_internet'), len(d.get('competition_sources') or [])))
for r in sorted(rows):
    print("%-46s %-4s net=%-5s comp=%d" % (r[0], r[5], r[6], r[7]))
    print("      suite=%s adapter=%s" % (r[2] or '-', r[3] or '-'))
    if r[4]:
        print("      extra=%s" % r[4])
print("total kernels:", len(rows))
