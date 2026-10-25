"""finalize_3d.py - (1) patch v22 them data train3d-hard, (2) tao kernel GPU
bench 3D hard (baseline v18 + gate v21), (3) validate data hard."""
import json
import os
import shutil

# ---------- (1) v22: them dataset train3d-hard ----------
K = 'phase13-gui/kernel_v22/gui_sft_v22.py'
s = open(K, encoding='utf-8').read()
OLD = """    t3d_rows = load_ds_rows("gui-train3d", "traj.jsonl")
    log(f"train3d: {len(t3d_rows)} row")"""
NEW = """    t3d_rows = load_ds_rows("gui-train3d", "traj.jsonl")
    t3dh_rows = load_ds_rows("gui-train3d-hard", "traj.jsonl")
    log(f"train3d: {len(t3d_rows)} row (+hard {len(t3dh_rows)})")"""
if OLD in s:
    s = s.replace(OLD, NEW, 1)
    s = s.replace("                  + t3d_rows + sp_rows)",
                  "                  + t3d_rows + t3dh_rows + sp_rows)", 1)
    s = s.replace("+ len(tgt_rows) + len(t3d_rows))",
                  "+ len(tgt_rows) + len(t3d_rows) + len(t3dh_rows))", 1)
    s = s.replace('f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"',
                  'f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"\n'
                  '        f"(+hard {len(t3dh_rows)})"', 1)
    s = s.replace('"n_train3d": len(t3d_rows),',
                  '"n_train3d": len(t3d_rows) + len(t3dh_rows),', 1)
    open(K, 'w', encoding='utf-8').write(s)
    print('patched v22 (them train3d-hard)')
else:
    print('v22 da co train3d-hard? bo qua')

mf = 'phase13-gui/kernel_v22/kernel-metadata.json'
md = json.load(open(mf, encoding='utf-8'))
if 'hhjiji/ornith-gui-train3d-hard' not in md['dataset_sources']:
    md['dataset_sources'].append('hhjiji/ornith-gui-train3d-hard')
json.dump(md, open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('v22 datasets:', md['dataset_sources'][-2:])

# ---------- (2) kernel GPU bench 3D hard ----------
SRC = 'phase13-gui/kernel_bench_3d'
for dst, kid, title, adapter in [
        ('phase13-gui/kernel_bench_3d_hard', 'hhjiji/ornith-gui-bench-3d-hard',
         'ornith-gui-bench-3d-hard', 'v18'),
        ('phase13-gui/kernel_bench_3d_hard_v21',
         'hhjiji/ornith-gui-bench-3d-hard-v21', 'ornith-gui-bench-3d-hard-v21',
         'v21')]:
    shutil.copytree(SRC, dst, dirs_exist_ok=True)
    m = json.load(open(os.path.join(dst, 'kernel-metadata.json'),
                      encoding='utf-8'))
    m['dataset_sources'] = [
        ('hhjiji/ornith-gui-bench3d-hard'
         if d == 'hhjiji/ornith-gui-bench3d' else
         ('hhjiji/ornith-gui-lora-v21' if d == 'hhjiji/ornith-gui-lora' and
          adapter == 'v21' else
          ('hhjiji/ornith-gui-lora' if d == 'hhjiji/ornith-gui-lora' else d)))
        for d in m['dataset_sources']]
    m['id'] = kid
    m['title'] = title
    json.dump(m, open(os.path.join(dst, 'kernel-metadata.json'), 'w',
                       encoding='utf-8'), ensure_ascii=False, indent=2)
    print('kernel', dst, '->', kid)

# ---------- (3) validate data hard ----------
import io
P = 'phase14-blender/bench3d_hard_dataset/bench3d.jsonl'
rows = [json.loads(l) for l in io.open(P, encoding='utf-8') if l.strip()]
areas = []
for r in rows:
    b = r['bbox']
    w, h = b[2] - b[0], b[3] - b[1]
    areas.append(w * h / 1e6)
    assert b[0] <= b[2] and b[1] <= b[3], r
areas.sort()
print('bench3d HARD: %d task | bbox median %.2f%% | min %.2f%% max %.2f%%' % (
    len(rows), areas[len(areas) // 2] * 100, areas[0] * 100, areas[-1] * 100))
print('=> HARD kho hon DANG (median 6.91%%) bang %.2fx' %
      (areas[len(areas) // 2] / 0.0691))
