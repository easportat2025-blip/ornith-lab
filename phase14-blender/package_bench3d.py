"""package_bench3d.py - dong goi bench 3D (eval) thanh dataset Kaggle.

Dataset: hhjiji/ornith-gui-bench3d
  bench3d.jsonl : {"image","instruction","bbox":[x0,y0,x1,y1],...}
  shots.zip     : anh (ten o TOP-LEVEL -> Kaggle giai nen ra <ds>/shots/<ten>.png
                  -> khop voi "image": "shots/<ten>.png")
"""
import io
import json
import os
import shutil
import zipfile

SRC = 'phase14-blender/out_bench3d/blend3d'
STAGE = 'phase14-blender/bench3d_dataset'
DATASET_ID = 'hhjiji/ornith-gui-bench3d'

rows = [json.loads(l) for l in
        io.open(os.path.join(SRC, 'bench3d.jsonl'), encoding='utf-8')
        if l.strip()]
print('rows:', len(rows))

shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
n_shot = 0
with zipfile.ZipFile(os.path.join(STAGE, 'shots.zip'), 'w',
                     zipfile.ZIP_DEFLATED) as z:
    for r in rows:
        name = os.path.basename(r['image'])
        found = None
        for d in os.listdir(SRC):
            cand = os.path.join(SRC, d, name)
            if os.path.exists(cand):
                found = cand
                break
        if found:
            z.write(found, name)
            n_shot += 1
print('shots.zip: %d anh' % n_shot)

with io.open(os.path.join(STAGE, 'bench3d.jsonl'), 'w', encoding='utf-8',
             newline='\n') as fh:
    for r in rows:
        fh.write(json.dumps({
            'image': r['image'], 'instruction': r['instruction'],
            'bbox': r['bbox'], 'color': r.get('color'),
            'shape': r.get('shape'), 'src': r.get('src', 'bench3d-d1'),
        }, ensure_ascii=False) + '\n')
meta = {'title': 'Ornith bench 3D grounding', 'id': DATASET_ID,
        'licenses': [{'name': 'other'}]}
json.dump(meta, io.open(os.path.join(STAGE, 'dataset-metadata.json'), 'w',
                         encoding='utf-8'), ensure_ascii=False, indent=2)
print('stage', STAGE, '| title len', len(meta['title']))
for f in os.listdir(STAGE):
    print('   ', f, os.path.getsize(os.path.join(STAGE, f)))
