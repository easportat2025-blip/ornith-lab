"""make_v23.py - sinh kernel v23 (recipe v22 + rebalance du lieu theo bang chung).

LY DO (sau gate v21 + rollout v21 + review MiMo):
  - model THANG 3/3 o task de (canvas/counter/delayed/coupon) → synth tong hop
    (1200) + 3D (1200) = 51% data nhung lai "de" → chuyen tieu hoa.
  - model THUA 0 o task nhieu buoc + go chuoi (signup 0/20, pagecode 0/19,
    errorfix 0/18, login 0/16, tabcode 0/7) → tang manh "targeted S1-S8"
    (dung loai task nay) + "policy-replay" (task THAT) ×2.
  - 3D giữ 600 (muc tieu rieng, khong phai nut thot hien tai).
  - van giu: cung giu YEU CAU CUNG (seed moi moi run) ✓.

Tham so (sua o day roi chay):
  N_SYNTH   = 500    # thay cho 1200
  N_TARGETED= 800    # thay cho 500 (bo sinh ~4 row/episode -> ~3100 row)
  PR_REPEAT = 2      # nhan ×2 policy-replay
  N_3D      = 300    # moi bien the (3D 600 -> 600 tong)
  N_TRAJ    = 400    # thay cho 816
"""
import io
import os
import re
import shutil

SRC = "phase13-gui/kernel_v22"
DST = "phase13-gui/kernel_v23"
N_SYNTH = 500
N_TARGETED = 800
PR_REPEAT = 2
N_3D = 600
N_TRAJ = 400

os.makedirs(DST, exist_ok=True)
s = io.open(os.path.join(SRC, "gui_sft_v22.py"), encoding="utf-8").read()

# 1) so luong synth tong hop
s = re.sub(r"^N_TRAIN = \d+", "N_TRAIN = %d" % N_SYNTH, s, count=1,
           flags=re.M)
# 2) targeted S1-S8
s = re.sub(r"^N_TARGETED = \d+", "N_TARGETED = %d" % N_TARGETED, s,
           count=1, flags=re.M)
# 3) traj: cat con lai
s = s.replace(
    '    traj_rows = load_ds_rows("ornith-gui-traj", "traj.jsonl")',
    '    traj_rows = load_ds_rows("ornith-gui-traj", "traj.jsonl")\n'
    '    traj_rows = traj_rows[:%d]  # v23: giu phan nho hon (it row prose)' % N_TRAJ)
# 4) 3D: cat con lai (ca 2 bien the)
s = s.replace(
    '    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)',
    '    t3d_rows = load_ds_rows("ornith-gui-train3d", "traj.jsonl", required=True)'
    '\n    t3d_rows = t3d_rows[:N_3D]')
s = s.replace(
    '    t3dh_rows = load_ds_rows("ornith-gui-train3d-hard", "traj.jsonl",\n'
    '                              required=True)',
    '    t3dh_rows = load_ds_rows("ornith-gui-train3d-hard", "traj.jsonl",\n'
    '                              required=True)\n'
    '    t3dh_rows = t3dh_rows[:%d]' % N_3D)
# 5) policy-replay ×N (nhan them ban goc, khong sua action)
s = s.replace(
    '    log(f"policy-replay: {len(pr_rows)} row")',
    '    pr_rows = pr_rows * %d  # v23: nhan ×%d (task THAT la nut thot)\n'
    '    log(f"policy-replay: {len(pr_rows)} row (x%d)")' % (PR_REPEAT, PR_REPEAT,
                                                            PR_REPEAT))
# 6) nhan dinh recipe trong log/result
s = s.replace('"recipe": "v18-action-only + synth-targeted S1-S8 + selfplay"',
              '"recipe": "v23: rebalance - synth %d + targeted %d + policy-replay x%d '
              '+ 3D %d + traj %d + selfplay"'
              % (N_SYNTH, N_TARGETED, PR_REPEAT, N_3D, N_TRAJ))
io.open(os.path.join(DST, "gui_sft_v23.py"), "w", encoding="utf-8",
        newline="\n").write(s)

# metadata: doi slug + giu dataset
md = io.open(os.path.join(SRC, "kernel-metadata.json"), encoding="utf-8").read()
md = md.replace('"code_file": "gui_sft_v22.py"', '"code_file": "gui_sft_v23.py"')
md = md.replace('"khoadangnguye/ornith-gui-sft-v22"',
                '"khoadangnguye/ornith-gui-sft-v23"')
md = md.replace('"title": "ornith gui sft v22"', '"title": "ornith gui sft v23"')
io.open(os.path.join(DST, "kernel-metadata.json"), "w", encoding="utf-8",
        newline="\n").write(md)

print("da tao", DST)

# --- buoc hau ky: cat cac bien the (gia tri cuoi co the lech do code v22 da doi)
out_p = os.path.join(DST, "gui_sft_v23.py")
t = io.open(out_p, encoding="utf-8").read()
if "traj_rows = traj_rows[:%d]" % N_TRAJ not in t:
    anchor = '    traj_rows = load_ds_rows("ornith-gui-traj", "traj.jsonl", required=True)'
    if anchor in t:
        t = t.replace(anchor, anchor + "\n    traj_rows = traj_rows[:%d]  # v23: giu phan nho hon" % N_TRAJ)
        print("   + traj slicing")
if "t3dh_rows = t3dh_rows[:N_3D]" not in t:
    t = t.replace("    t3dh_rows = t3dh_rows[:600]",
                  "    t3dh_rows = t3dh_rows[:N_3D]")
    print("   + t3dh slicing")
io.open(out_p, "w", encoding="utf-8", newline="\n").write(t)

for k in ("N_TRAIN = ", "N_TARGETED = ", "pr_rows = pr_rows *",
          "t3d_rows = t3d_rows[:", "t3dh_rows = t3dh_rows[:",
          "traj_rows = traj_rows[:", '"recipe"'):
    for l in s.splitlines():
        if k in l:
            print("   ", l.strip()[:110])
            break
