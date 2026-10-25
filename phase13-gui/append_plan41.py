text = ("- 20/10/2026 (tietp 41): **QUOTA GPU HET (30.13h/30h) -> 24/10 00:00 moi co GPU**; key thu hai `dieniw` da het hieu luc (401) -> khong co account thu 2. "
"**Mat ~7 GPU-gio do bug watchdog cu** (fetch fail 1 lan -> ghi marker -> khong retry; marker ghi cho version cu -> version moi bi skip). Da fix ca hai: marker luu `lastRunTime` (tu `kaggle kernels list --mine`) va fetch FAIL -> giu marker cu de thu lai. "
"**Hang doi GPU tu dong moi** (`scripts/gpu_queue.json`, 9 muc): watchdog kiem quota moi 5 phong, con >=1h + <2 session -> push dung thu tu: sft-v21 -> bench-v18-think0 -> bench-v155 -> (sau v21: adapter upload -> bench-v21 + bench-v14-v21 + bench-v155-v21) -> sft-v22 -> bench-v16 -> bench-v16-v21. "
"**Rollout-base (v18, 72 ep x 2 reps, temp 0.7): 24/72 win = 33.3%** (cao hon greedy 27.8%), 511 rows (121 win + 390 near-miss), modes action 449 / legacy 16 / none 46, prose leak 99%. "
"**Curate + loc chat luong (da kiem bang mat):** bo episode LOOP (<=2 o toa do) 6 ep, bo `TYPE` giu chu che 4 row, cap action lap >2 lan/ep, bo step cuoi ep fail, dedupe, loai variant 2 khoi TRAIN -> **123 row (51 win + 72 near-miss)**; dataset `hhjiji/gui-selfplay` **READY**. "
"**B16-A (MiMo TASK-20) verify 24/24 + 24/24** -> dataset `hhjiji/ornith-gui-bench-v16` (18.7KB) + 2 kernel staged. "
"**4 ngay khong GPU -> chuyen sang Blender (CPU kernel van chay):** TASK-22 (MiMo) Blender compositional-15, TASK-23 (GLM) sinh data train 3D tu render that. "
"Bai hoc them: `kaggle datasets create` fail neu **title > 50 ky tu** (dung 54 -> 37); `kaggle datasets create -p` phai dung **duong dan tuong doi** (absolute -> CLI mung path hong); PS1 phai ASCII-only.")

with open('PLAN.md', 'a', encoding='utf-8') as f:
    f.write("\n" + text)
print('appended', len(text))
