"""package_3d.py - dong goi dataset 3D (train hoac bench) len Kaggle.

Dung:
  python phase14-blender/package_3d.py --src <dir co blend3d/> --stage <dir> \
      --id hhjiji/... --kind train|bench --title "..."
Layout: <stage>/<kind>.jsonl + <stage>/shots.zip (anh TOP-LEVEL) +
        dataset-metadata.json
"""
import argparse
import io
import json
import os
import shutil
import zipfile

ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)
ap.add_argument('--stage', required=True)
ap.add_argument('--id', required=True)
ap.add_argument('--kind', default='train', choices=['train', 'bench'])
ap.add_argument('--title', required=True)
a = ap.parse_args()

base = os.path.join(a.src, 'blend3d')
# TEN FILE phai khop voi load_ds_rows trong kernel:
#   train -> "traj.jsonl" (gui-train3d / gui-train3d-hard)
#   bench -> "bench3d.jsonl" (gui-bench3d / gui-bench3d-hard)
jf = 'traj.jsonl' if a.kind == 'train' else 'bench3d.jsonl'
src_jf = 'train3d.jsonl' if a.kind == 'train' else 'bench3d.jsonl'
rows = [json.loads(l) for l in
        io.open(os.path.join(base, src_jf), encoding='utf-8') if l.strip()]
print('rows:', len(rows))

shutil.rmtree(a.stage, ignore_errors=True)
os.makedirs(a.stage, exist_ok=True)
n_shot = 0
with zipfile.ZipFile(os.path.join(a.stage, 'shots.zip'), 'w',
                     zipfile.ZIP_DEFLATED) as z:
    for r in rows:
        name = os.path.basename(r['image'])
        found = None
        for d in os.listdir(base):
            cand = os.path.join(base, d, name)
            if os.path.exists(cand):
                found = cand
                break
        if found:
            z.write(found, name)
            n_shot += 1
print('shots.zip: %d anh' % n_shot)

out = os.path.join(a.stage, jf)
with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
    for r in rows:
        rec = {'image': r['image'], 'instruction': r['instruction']}
        for k in ('bbox', 'color', 'shape', 'src'):
            if k in r:
                rec[k] = r[k]
        if a.kind == 'train':
            rec['action'] = r['action']
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
meta = {'title': a.title, 'id': a.id, 'licenses': [{'name': 'other'}]}
json.dump(meta, io.open(os.path.join(a.stage, 'dataset-metadata.json'), 'w',
                         encoding='utf-8'), ensure_ascii=False, indent=2)
print('stage', a.stage, '| title len', len(a.title), '| id', a.id)
for f in os.listdir(a.stage):
    print('   ', f, os.path.getsize(os.path.join(a.stage, f)))
