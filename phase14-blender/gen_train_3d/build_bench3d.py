"""build_bench3d.py - tao file kernel self-contained cho bench 3D.

Kaggle chi upload code_file -> gen_bench3d.py phai chua het phan download
Blender + make_specs (tu generate_3d.py) + script Blender eval (co bbox).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
gen = open(os.path.join(HERE, 'generate_3d.py'), encoding='utf-8').read()
b3 = open(os.path.join(HERE, 'gen_bench3d.py'), encoding='utf-8').read()

head = gen.split('def main(')[0]
# phan BLENDER_EVAL + main cua gen_bench3d.py (bo import tu generate_3d)
tail = b3.split("BLENDER_EVAL = r'''", 1)[1]
tail = "BLENDER_EVAL = r'''" + tail
# bo dong import generate_3d (da nam trong head)
out = head + "\n\n" + tail
out = out.replace('sys.path.insert(0, HERE)\n', '')
if 'import zipfile' not in out.split('def make_specs')[0]:
    out = out.replace('import json\n', 'import json\nimport zipfile\n', 1)
os.makedirs(os.path.join(HERE, 'gen_bench3d_kernel'), exist_ok=True)
dst = os.path.join(HERE, 'gen_bench3d_kernel', 'gen_bench3d.py')
open(dst, 'w', encoding='utf-8').write(out)
print('wrote', dst, len(out), 'bytes')
import json
meta = {
    "id": "hhjiji/ornith-blender-bench3d",
    "title": "ornith-blender-bench3d",
    "code_file": "gen_bench3d.py",
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": False,
    "enable_internet": True,
    "enable_tpu": False,
    "dataset_sources": [],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
}
json.dump(meta, open(os.path.join(HERE, 'gen_bench3d_kernel',
                                 'kernel-metadata.json'), 'w',
                     encoding='utf-8'), ensure_ascii=False, indent=2)
print('kernel id:', meta['id'])
