# -*- coding: utf-8 -*-
"""cleanup_keep_adapters.py - don dia, GIU:
  - adapter da tai: phase13-gui/out_sft_v21, out_sft_v22 (v18/v20 giu nho)
  - bundle browser offline (can cho RTX offline + local env)
  - dataset 3D + traj R2 (can cho train)
  - code, ket qua (result.json), log
XAO: staging da upload, output cu, temp, pycache, anh cua bench.
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

# --- 1) XOA: staging da upload + output cu (phase12) ---
DELETE_DIRS = [
    r"phase12-bagent\out_v5", r"phase12-bagent\out_v10", r"phase12-bagent\out_v3",
    r"phase12-bagent\ds_b5", r"phase12-bagent\ds_b10",
    r"data\ferry",
    r"phase13-gui\acc_b_staging",
    r"phase13-gui\out_deps_collect",
    r"phase13-gui\_dd_tmp_long", r"phase13-gui\_dd_tmp_imgs",
    r"phase13-gui\_mix_tmp_imgs",
    r"phase14-blender\out_gen3d", r"phase14-blender\out_gen3d_v3",
    r"phase14-blender\out_gen3d_hard",
    r"phase14-blender\train3d_hard_dataset",
    r"phase14-blender\train3d_hard_dataset_accA",
    r"phase13-gui\out_traj_test", r"phase13-gui\tmp_pull", r"phase13-gui\tmp_pull8",
    r"phase13-gui\policy_replay_dataset",
    r"phase13-gui\selfplay_dataset", r"phase13-gui\selfplay_dataset_v21",
    r"phase13-gui\lora_v20_dataset", r"phase13-gui\lora_v21_dataset",
    r"phase13-gui\lora_v22_dataset",
]
freed = 0
for d in DELETE_DIRS:
    p = os.path.join(R, d)
    if os.path.isdir(p):
        s = du(p)
        shutil.rmtree(p, ignore_errors=True)
        freed += s
        print("  xoa %-46s %8.1f MB" % (d, s / 1e6))

# --- 2) XOA: __pycache__ + anh cu trong out_bench_* (giu result.json + log) ---
n = 0
for root, dirs, _files in os.walk(R):
    for dn in list(dirs):
        if dn == "__pycache__":
            p = os.path.join(root, dn)
            freed += du(p)
            shutil.rmtree(p, ignore_errors=True)
            n += 1
print("  xoa %d __pycache__" % n)

for root, dirs, files in os.walk(R):
    base = os.path.basename(root)
    if base.startswith("out_bench") or base.startswith("out_desktop"):
        for f in files:
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".zip")):
                p = os.path.join(root, f)
                try:
                    freed += os.path.getsize(p)
                    os.remove(p)
                except OSError:
                    pass

# --- 3) BAO VE: adapter + dataset can dung (kiem tra con) ---
KEEP = ["phase13-gui/out_sft_v21", "phase13-gui/out_sft_v22",
        "phase13-gui/out_sft_v18", "phase13-gui/out_v20",
        "phase13-gui/offline_browsers_dataset",
        "phase13-gui/synth_recipe_ds_staging",
        "phase14-blender/train3d_dataset"]
print("--- kiem tra muc BAO GIU ---")
for k in KEEP:
    p = os.path.join(R, k)
    print("  %-46s %s" % (k, ("OK %.1f MB" % (du(p) / 1e6)) if os.path.isdir(p)
                          else "MAT!"))
print("sau:   %.2f GB (giai phong %.2f GB)" % (free(), freed / 1e9))
