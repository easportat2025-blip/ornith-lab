"""build_hard_kernels.py - 2 kernel CPU 'hard' (B16-3D):
  - gen3d-hard  : them 300 row 3D kho (nhieu object, nho, sat) -> dataset train
  - bench3d-hard: 100 task eval 3D kho -> dataset bench (metric kho hon)
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def make(src_file, dst_dir, kid, title, edits, extra_files=()):
    dst_dir = os.path.join(HERE, dst_dir)
    os.makedirs(dst_dir, exist_ok=True)
    s = open(os.path.join(HERE, src_file), encoding='utf-8').read()
    for old, new in edits:
        assert old in s, (src_file, old[:50])
        s = s.replace(old, new, 1)
    open(os.path.join(dst_dir, os.path.basename(src_file)), 'w',
         encoding='utf-8').write(s)
    for f in extra_files:
        shutil.copy(os.path.join(HERE, f), os.path.join(dst_dir, f))
    md = {
        "id": kid, "title": title,
        "code_file": os.path.basename(src_file),
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": False, "enable_internet": True, "enable_tpu": False,
        "dataset_sources": [], "competition_sources": [],
        "kernel_sources": [], "model_sources": [],
    }
    json.dump(md, open(os.path.join(dst_dir, 'kernel-metadata.json'), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=2)
    print('created', dst_dir, '->', kid)


# --- gen3d hard: hard=True + seed 17
make('generate_3d.py', 'gen3d_hard_kernel', 'hhjiji/ornith-blender-gen3d-hard',
     'ornith-blender-gen3d-hard',
     [('    ap.add_argument("--hard", action="store_true",',
       '    ap.add_argument("--hard", action="store_true", default=True,')])

# --- bench3d hard: hard=True + seed 1999 (dung ban SELF-CONTAINED da build)
make('gen_bench3d_kernel/gen_bench3d.py', 'gen_bench3d_hard_kernel',
     'hhjiji/ornith-blender-bench3d-hard', 'ornith-blender-bench3d-hard',
     [('    ap.add_argument("--hard", action="store_true",',
       '    ap.add_argument("--hard", action="store_true", default=True,'),
      ('ap.add_argument("--seed", type=int, default=999)',
       'ap.add_argument("--seed", type=int, default=1999)')])
