# -*- coding: utf-8 -*-
"""cleanup_local_keep_needed.py - local CHI GIU thu can thiet:
  - adapter da tai (out_sft_v2X/gui_lora, out_v20) ✓
  - ket qua + log (out_bench_*, out_rollout_*, result.json) ✓
  - code ✓
XOA: moi ban sao dataset (da co tren Kaggle / tren USB roi):
  - offline_browsers_dataset (USB da co) ✓
  - synth_recipe_ds_staging, traj_ds_staging, bench_v155_dataset, bench_v16_dataset,
    policy_replay_dataset, selfplay_dataset... ✓
  - blender: train3d_dataset, bench3d_dataset, out_bench3d* (uploaded roi) ✓
"""
import os
import shutil
import ctypes

R = r"C:\Users\Admin\Desktop\New folder"


def free():
    f = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW("C:\\", ctypes.byref(f), None, None)
    return f.value / 1e9


def du(p):
    t = 0
    for root, _d, files in os.walk(p):
        for f in files:
            try:
                t += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return t


before = free()
print("truoc: %.2f GB" % before)

DELETE = [
    r"phase13-gui\offline_browsers_dataset",
    r"phase13-gui\synth_recipe_ds_staging",
    r"phase13-gui\traj_ds_staging",
    r"phase13-gui\bench_v155_dataset",
    r"phase13-gui\bench_v16_dataset",
    r"phase13-gui\bench_dataset",
    r"phase13-gui\out_real",
    r"phase13-gui\out_traj",
    r"phase14-blender\train3d_dataset",
    r"phase14-blender\bench3d_dataset",
    r"phase14-blender\out_bench3d",
    r"phase14-blender\out_bench3d_hard",
    r"phase14-blender\out_gen1",
    r"phase14-blender\out_gen3d",
    r"phase14-blender\out_gen3d_hard",
    r"phase14-blender\out_gen3d_v3",
    r"phase13-gui\out_sft_v18",
    r"phase13-gui\out_v20",
]
freed = 0
for d in DELETE:
    p = os.path.join(R, d)
    if os.path.isdir(p):
        s = du(p)
        shutil.rmtree(p, ignore_errors=True)
        freed += s
        print("  xoa %-44s %8.1f MB" % (d, s / 1e6))

print("--- GIU LAI (can thiet) ---")
KEEP = ["phase13-gui/out_sft_v21", "phase13-gui/out_sft_v22",
        "phase13-gui/out_rollout_v21", "phase13-gui/out_rollout_base",
        "phase13-gui/out_bench_v22", "phase13-gui/out_bench_v155_v22",
        "phase13-gui/out_bench_v16_v22", "phase13-gui/out_bench_v21"]
for k in KEEP:
    p = os.path.join(R, k)
    print("  %-40s %s" % (k, ("OK %.1f MB" % (du(p) / 1e6)) if os.path.isdir(p)
                          else "khong co"))
print("sau:   %.2f GB (giai phong %.2f GB)" % (free(), freed / 1e9))
