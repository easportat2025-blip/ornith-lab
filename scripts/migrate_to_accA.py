"""migrate_to_accA.py - chuyen toan bo kernel/dataset mount sang acc A
(khoadangnguye) de chay GPU NGAY (acc hhjiji het quota).

- doi "hhjiji/<slug>" -> "khoadangnguye/<slug>" trong dataset_sources
- doi kernel id "hhjiji/xxx" -> "khoadangnguye/xxx"
- doi trong scripts/gpu_queue.json + scripts/watchdog_targets.json
Giu nguyen: kernel co san tren hhjiji (khong xoa).
"""
import glob
import io
import json
import os

A = "khoadangnguye"
OLD = "hhjiji"
SKIP_DATASETS = set()      # dataset chua ferry -> giu "hhjiji/..." (se bi loi mount)


def patch_json(path):
    s = io.open(path, encoding="utf-8").read()
    o = s
    s = s.replace('"%s/' % OLD, '"%s/' % A)
    if s != o:
        io.open(path, 'w', encoding='utf-8', newline='').write(s)
        return True
    return False


def main():
    n = 0
    for mf in glob.glob('phase13-gui/kernel*/kernel-metadata.json') + \
            glob.glob('phase14-blender/*/kernel-metadata.json'):
        d = json.load(io.open(mf, encoding='utf-8'))
        changed = False
        if d.get('id', '').startswith(OLD + '/'):
            d['id'] = A + '/' + d['id'].split('/', 1)[1]
            changed = True
        ds = []
        for x in d.get('dataset_sources', []):
            if x.startswith(OLD + '/') and x.split('/', 1)[1] not in SKIP_DATASETS:
                x = A + '/' + x.split('/', 1)[1]
                changed = True
            ds.append(x)
        d['dataset_sources'] = ds
        if changed:
            json.dump(d, io.open(mf, 'w', encoding='utf-8'), ensure_ascii=False,
                      indent=2)
            print('meta:', d['id'], '|', [x for x in ds if 'ornith' in x])
            n += 1
    for p in ('scripts/gpu_queue.json', 'scripts/watchdog_targets.json'):
        if patch_json(p):
            print('patched', p)
            n += 1
    print('tong thay doi:', n)


if __name__ == "__main__":
    main()
