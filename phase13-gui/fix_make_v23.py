# -*- coding: utf-8 -*-
"""fix_make_v23.py - sua pattern trong make_v23.py cho khop code v22 hien tai
(da them `required=True` + duong dan ENV) + giam 3D xuong 600 tong.
"""
import io

P = "phase13-gui/make_v23.py"
s = io.open(P, encoding="utf-8").read()

# 1) traj: them slicing
old = ('    traj_rows = load_ds_rows("ornith-gui-traj", "traj.jsonl", required=True)')
new = (old + "\n"
       '    traj_rows = traj_rows[:%d]  # v23: giu phan nho hon (it row prose)" % N_TRAJ')
if "traj_rows[:%d]" not in s:
    if old in s:
        s = s.replace(old, new)
        print("da them slicing cho traj")
    else:
        print("!! khong khop dong traj")
else:
    print("traj da co slicing")

# 2) 3D: 600 -> N_3D (300 moi bien the => 600 tong)
for var in ("t3d_rows", "t3dh_rows"):
    o = "    %s = %s[:600]" % (var, var)
    n = "    %s = %s[:N_3D]" % (var, var)
    if o in s:
        s = s.replace(o, n)
        print("da giam", var)

# 3) them N_3D vao danh sach thay the trong TPL (neu can)
s = s.replace('s = s.replace(\n    \'    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)\',\n'
              '    \'    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)\'\n'
              '    \'\\n    t3d_rows = t3d_rows[:%d]\' % N_3D)',
              's = s.replace(\n'
              '    \'    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)\',\n'
              '    \'    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)\'\n'
              '    \'\\n    t3d_rows = t3d_rows[:N_3D]\')')
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("OK")
