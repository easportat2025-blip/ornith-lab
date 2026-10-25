"""package_train3d.py - dong goi data train 3D thanh dataset Kaggle.

Kaggle CLI KHONG upload file trong subdir + auto-extract zip -> dung
shots.zip (anh o TOP-LEVEL) + traj.jsonl (image = "shots/<ten>.png") ->
Kaggle giai nen ra <ds>/shots/<ten>.png -> khop voi traj.jsonl.
"""
import io
import json
import os
import shutil
import zipfile

SRC = 'phase14-blender/out_gen3d_v3/blend3d'
STAGE = 'phase14-blender/train3d_dataset'
DATASET_ID = 'hhjiji/ornith-gui-train3d'

rows = [json.loads(l) for l in
        io.open(os.path.join(SRC, 'train3d.jsonl'), encoding='utf-8')
        if l.strip()]
shots = os.path.join(SRC, 'shots')
print('rows:', len(rows))

shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
n_shot = 0
with zipfile.ZipFile(os.path.join(STAGE, 'shots.zip'), 'w',
                     zipfile.ZIP_DEFLATED) as z:
    for r in rows:
        p = os.path.join(shots, os.path.basename(r['image']))
        if not os.path.exists(p):
            continue
        z.writestr(os.path.basename(r['image']),
                   open(p, 'rb').read())
        n_shot += 1
print('shots.zip: %d anh (top-level)' % n_shot)

with io.open(os.path.join(STAGE, 'traj.jsonl'), 'w', encoding='utf-8',
             newline='\n') as fh:
    for r in rows:
        fh.write(json.dumps({
            'image': r['image'], 'instruction': r['instruction'],
            'action': r['action'], 'family': r.get('family'),
            'color': r.get('color'), 'shape': r.get('shape'),
            'src': r.get('src', 'blend3d-d1'),
        }, ensure_ascii=False) + '\n')
meta = {'title': 'Ornith GUI train3D grounding', 'id': DATASET_ID,
        'licenses': [{'name': 'other'}]}
json.dump(meta, io.open(os.path.join(STAGE, 'dataset-metadata.json'), 'w',
                         encoding='utf-8'), ensure_ascii=False, indent=2)
print('stage', STAGE, '| title len', len(meta['title']))
for f in os.listdir(STAGE):
    print('   ', f, os.path.getsize(os.path.join(STAGE, f)))
