"""patch_v22_policy.py - them du lieu policy-replay (task THAT, action dung
format) vao mix cua v22 + acc B.

Dataset: khoadangnguye/ornith-policy-replay-data (tao boi post_policy_replay.ps1)
"""
import io
import json
import os

K = 'phase13-gui/kernel_v22/gui_sft_v22.py'
s = io.open(K, encoding='utf-8').read()

OLD = """    t3d_rows = load_ds_rows("gui-train3d", "traj.jsonl")"""
NEW = """    t3d_rows = load_ds_rows("gui-train3d", "traj.jsonl")
    # TASK-25: du lieu "task THAT" (policy-replay) - day model hoc task 0/3
    pr_rows = load_ds_rows("policy-replay-data", "traj.jsonl")
    log(f"policy-replay: {len(pr_rows)} row")"""
if OLD in s:
    s = s.replace(OLD, NEW, 1)
    s = s.replace("                  + t3d_rows + t3dh_rows + sp_rows)",
                  "                  + t3d_rows + t3dh_rows + pr_rows + sp_rows)", 1)
    s = s.replace("              + len(tgt_rows) + len(t3d_rows) + len(t3dh_rows))",
                  "              + len(tgt_rows) + len(t3d_rows) + len(t3dh_rows)\n"
                  "              + len(pr_rows))", 1)
    s = s.replace('f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"',
                  'f"targeted {len(tgt_rows)} + train3d {len(t3d_rows)}"\n'
                  '        f"(+hard {len(t3dh_rows)}) + policy-replay {len(pr_rows)}"', 1)
    s = s.replace('"n_train3d": len(t3d_rows) + len(t3dh_rows),',
                  '"n_train3d": len(t3d_rows) + len(t3dh_rows),\n'
                  '        "n_policy_replay": len(pr_rows),', 1)
    io.open(K, 'w', encoding='utf-8', newline='').write(s)
    print('patched v22 (them policy-replay)')
else:
    print('v21/v22: khong tim thay khoi de patch')

# --- metadata: them dataset + acc B namespace
for d in ('phase13-gui/kernel_v22', 'phase13-gui/kernel_v22_B'):
    mf = os.path.join(d, 'kernel-metadata.json')
    if not os.path.exists(mf):
        continue
    md = json.load(io.open(mf, encoding='utf-8'))
    ds = md.get('dataset_sources', [])
    for slug in ('khoadangnguye/ornith-policy-replay-data',
                 'dieniw/ornith-policy-replay-data'):
        if slug not in ds:
            ds.append(slug)
    md['dataset_sources'] = ds
    json.dump(md, io.open(mf, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(d, '->', md['dataset_sources'][-2:])
