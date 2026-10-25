text = ("- 20/10/2026 (tietp 44): **TRACK 3D chuyen sang co DU LIEU + co METRIC** (muc tieu user \"agent 3D\" + \"benchmark phai kho hon moi ngay\"). "
"**Data train 3D**: kernel CPU `hhjiji/ornith-blender-gen3d` (0 GPU-quota) render 300 scene Blender 4.2 (3-6 object, (mau,shape) duy nhat, CYCLES 16 samples, view transform Standard) -> target = **diem do chieu** (`world_to_camera_view`) chuan hoa 0..1000 -> action **`CLICK x y`** (GIONH action space GUI) -> dataset `hhjiji/ornith-gui-train3d` READY -> **da mix vao v22** (`load_ds_rows('gui-train3d','traj.jsonl')`, metadata da mount) => model 3D hoc chung ky nang \"nhin anh -> click target\" o ca 2D va 3D. "
"**Bench 3D (metric)**: kernel CPU `hhjiji/ornith-blender-bench3d` sinh 100 task eval (seed 999 held-out so voi train) + **bbox CHIEU** cua object target -> checker = click co nam trong bbox khong (giong `hit(point,bbox)` cua GUI) + per-mau + parse/prose. Validate: center trong bbox **100/100** (vo doi duoc), median bbox 6.9% anh. Dataset `hhjiji/ornith-gui-bench3d` READY + kernel GPU `ornith-gui-bench-3d` + `-v21` -> da them vao hang doi GPU. "
"**Bench 3D HARD (B16-3D)**: them che do `hard` (5-8 object, nho hon 0.28-0.45, sat nhau, camera xa hon) cho ca gen3d va bench3d -> 2 kernel CPU `ornith-blender-gen3d-hard` + `ornith-blender-bench3d-hard` (dang chay) de len tiep chuoi \"kho hon moi ngay\". "
"**Kinh nghiem them**: (a) `kaggle datasets upload` canh tao subdir theo component DAU cua stage path trong %TEMP%\\.kaggle\\uploads -> phai New-Item truoc (da co trong `scripts/upload_dataset.ps1`); "
"(b) kernel CPU (internet true, khong competition) la duong de sinh du lieu 3D **ton 0 GPU-quota** (~4-10 phut/300 render); (c) kernel chi upload code_file -> file phu phai inline (da lam cho gen_synth_targeted + gen_bench3d).")

with open('PLAN.md', 'a', encoding='utf-8') as f:
    f.write("\n" + text)
print('appended', len(text))
