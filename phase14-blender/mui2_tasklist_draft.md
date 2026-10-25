# mui2_tasklist_draft.md — TASK-3: đề xuất mở rộng Blender data-gen (mũi 2)

> **Tác giả:** MiMo (helper) · 19/10 · trạng thái: **DRAFT — chỉ đọc + viết**.
> **KHÔNG** sửa `gen_kernel/blender_gen.py`, **KHÔNG** sửa dataset, **KHÔNG** push kernel (chờ **user GO**).
> File đích duy nhất của TASK-3 = file này.

---

## 0. Tóm tắt 5 dòng

1. Đề xuất **15 task mới × 3 variants = 45 cặp (instruction → bpy script)**, chia **Gói A (8 task composition, rủi ro THẤP)** + **Gói B1 (5 modifier, TB)** + **Gói B2 (2 task convert FONT/CURVE, TB-CAO)**.
2. Mọi task **verify được theo đúng bộ gate cũ**: `rc=0` + `VERIFY_OK` + parse GLB (`meshes>0`, `glb_tris>0`) + `render.png > 2000B` — vì mỗi task đều tạo ≥1 object MESH, có polygon thật, đặt trong khung camera.
3. **Chống trùng**: 15 id mới khác hoàn toàn 29 id cũ; `(instruction, script)` **45/45 unique** (bài học `gold`/`traffic_light`: mọi variant phải khác **tham số cấu trúc**, không chỉ màu).
4. **Đã kiểm chứng local** bằng script dry-run (compile + dedupe + id clash + bounds + material-var): **45/45 PASS** — máy này **không có Blender binary chạy được** (chỉ có bản Linux) nên phần bpy-runtime **chưa chạy thật**, cần 1 lần verify trên Kaggle (CPU kernel, ~2–4').
5. Tích hợp gợi ý: **tạo file MỚI `blender_gen_v2.py`** (copy + thêm 15 task) thay vì sửa file cũ; output 45 rows merge vào 83 rows hiện có — chờ `@DeepSeek` + user chốt.

---

## 1. Nguồn đã đọc (evidence)

| Nguồn | Dòng/chỗ | Lấy được gì |
|---|---|---|
| `phase14-blender/gen_kernel/blender_gen.py` (647 dòng) | `TASKS` dòng 511–523 | **29 task cũ**: cube, sphere, cylinder, cone, torus, plane, moved, rotated, scaled, stack3, row5, pyramid, ring8, gold, emissive, matte, two_color, house, snowman, table, traffic_light, rocket, robot_head, tree, car, bevel, solidify, array, subsurf |
|同 file | `VARIANTS = 3` (dòng 41), `gen_rows()` (530) | palette quay `(ti*5+v*3)%10`, `rng = Random(1000+ti*97+v)` → variant số học có deterministic seed |
|同 file | `run_one()` (564–600) | **Bộ gate verify**: `rc==0`, `"VERIFY_OK" in stdout`, `glb_stats` parse được (`meshes>0`, `glb_tris>0`), `png_bytes > 2000`; timeout 240s/task |
|同 file | `TAIL` (108–155) | Camera cố định `(9.5,-9.5,6.5)` → target `(0,0,1.6)`; world `(0.85,0.87,0.92)`; Sun energy 4; Cycles 16 samples, **320×320, không denoise**; xuất GLB rồi render rồi print `VERIFY_*` |
|同 file | `PREFIX` (84–106) + `mdef/add/rotz/fmt` (173–211) | `mat()` có sẵn `metallic/rough/emit`; `add()` hỗ trợ `cube/sphere(UV)/cylinder/cone/torus/plane` + `rot=` + `scale=` + `depth=` — **khối building duy nhất đã 87/87 PASS** |
| `PLAN.md` | dòng 207 | v1: **87/87 PASS, 138s (~1.2s/task)**; dedupe `gold`+`traffic_light` (màu hardcode) → **83 unique**; dataset `hhjiji/ornith-blender-gen-data` |
| `LONGMEMORY.md` | dòng 81–83 | Blender 4.2.23 portable (mirror NLUUG + UA); `blender --background --factory-startup --python x.py`; Cycles CPU ≈0.56s/scene; **"task màu hardcode → variants trùng: dedupe theo (instruction, script)"** |
| `phase14-blender/out_gen1/` | `blend_gen/rows.jsonl` 87 dòng, `ds_upload/rows.jsonl` **83 dòng**, `failures.jsonl` 0B, renders 81–117KB, glb 1.2KB–361KB | Số liệu thật để đặt kỳ vọng đầu ra |

---

## 2. Bộ gate verify (bám nguyên xi `run_one()`) + ràng buộc thiết kế

**Gate (không được sửa):** `rc = 0` ∧ `VERIFY_OK` ∈ stdout ∧ GLB parse được với `meshes > 0` ∧ `glb_tris > 0` ∧ `png_bytes > 2000` (mỗi task 1 tiến trình Blender riêng, timeout 240s).

**Ràng buộc thiết kế → mọi task trong draft đều thoả:**

| # | Ràng buộc | Vì sao | Draft đã làm gì |
|---|---|---|---|
| 1 | Tạo ≥1 object `MESH` có polygon | `meshes>0` + `glb_tris>0` | 15/15 task đều có primitive mesh; 2 task FONT/CURVE **convert sang MESH trước khi TAIL export** |
| 2 | Object nằm trong khung camera | ra khỏi khung → nền phẳng → PNG dễ < 2KB | giới hạn `|x|,|y| ≤ 4.6` và `-1 ≤ z ≤ 6.5` (camera bán kính ~5.4 ở mặt phẳng target) — **đã check bằng script** |
| 3 | Variant phải khác nhau về **cấu trúc** | bài học `gold`/`traffic_light` → dedupe mất 4 rows | mọi task chọn tham số bằng `rng.choice` (số bậc, kích thước, bán kính, góc…) → **instruction cũng như script đều unique** |
| 4 | Không đổi PREFIX/TAIL/gate | giữ proven harness, `pass_rate 1.0` | chỉ thêm hàm emitter kiểu `t_*` mới |
| 5 | Ngôn ngữ instruction = tiếng Anh như 83 rows cũ | nhất quán dataset | 15 template tiếng Anh (có số liệu tham số trong câu) |

---

## 3. Bảng 15 task mới + variants

**Biến thể dùng chung:** mỗi task có 3 variants; màu quay theo `rotate_palette` **(mặc định của kernel)** + tham số cấu trúc do `rng.choice` sinh (seed `1000+ti*97+v` với `ti` tiếp tục từ 29 → không lệch seed cũ).

### GÓI A — composition bằng helper cũ (`mdef` + `add`) · rủi ro **THẤP**

| # | id | Cấu trúc (bpy) | Tham số variant (`rng.choice`) | Instruction mẫu (`_v0`) |
|---|---|---|---|---|
| A1 | `staircase` | 4–6 cube bậc thang, lệch x + cao dần, scale `(step*0.9, 1.6, rise)` | `n`∈{4,5,6}, `step`∈{1.0,1.2}, `rise`∈{0.6,0.8} | *Create a staircase with 4 orange steps rising along X (steps 1.0 apart, each step 0.8 taller).* |
| A2 | `arch` | 2 trụ cube + 1 đòn beam cube (2 material) | `span`∈{3.0,3.6,4.2}, `ph`∈{2.6,3.0}, `pw`∈{0.6,0.8} | *Build an arch gateway: two red pillars 3.0 apart topped by a blue beam (pillar height 3.0).* |
| A3 | `helix_tower` | trục cylinder + 6–10 sphere xoắn ốc quanh trục | `cnt`∈{6,8,10}, `rad`∈{1.2,1.4,1.6}, `rise`∈{0.4,0.45,0.55}, `sdeg`∈{45,60} | *Create a helix of 6 orange spheres (radius 0.35, orbit radius 1.4, rising 0.4 per 45 degree step) winding around a brown pole.* |
| A4 | `bookshelf` | 2 vách + (shelves+1) kệ + 4–12 sách cube mỏng, **mỗi sách 1 material riêng** | `w`∈{2.4,3.0}, `h`∈{3.0,3.6}, `shelves`∈{2,3}, `per`∈{3,4} | *Build a 2.4 wide red bookshelf 3.6 tall with 2 shelves holding 6 upright books.* |
| A5 | `desk_lamp` | đế cylinder + cánh tay cylinder nghiêng (rot X) + đèn cone + bóng sphere `emit=5` | `br`∈{0.8,1.0}, `arm`∈{1.8,2.1}, `tilt`∈{30,35,40} | *Build a desk lamp: a dark base of radius 1.0, an arm tilted 35 degrees, an orange cone shade and a glowing bulb.* |
| A6 | `windmill` | tháp cone + trục ngang (rot X 90) + hub sphere + **4 cánh cube quay `rot=(0,β,0)`, β∈{0,90,180,270}`** tạo chữ thập phía trước | `th`∈{2.6,3.0}, `bl`∈{1.3,1.6,1.9}, `bw`∈{0.3,0.4} | *Build a windmill: a red tapered tower 3.0 tall with a front hub and four blue blades in a cross (blade length 1.6).* |
| A7 | `fountain` | bồn cylinder + cột cylinder + bồn nhỏ + quả sphere | `br`∈{1.8,2.2}, `ch`∈{1.2,1.6} | *Build a fountain: an orange basin of radius 1.8 with a cyan column (1.2 tall), a small upper basin and a ball on top.* |
| A8 | `dominoes` | 3–5 cube mỏng đứng + **1 cube ngã** (rot Y 75°/90°, z tính theo chiếu cao thật) | `n`∈{4,5,6}, `gap`∈{0.7,0.85}, `dh`∈{1.2,1.5}, `tip`∈{75,90} | *Create 5 red dominoes 1.2 tall standing 0.85 apart, the last one blue tipped over at 90 degrees.* |

### GÓI B1 — modifier mới (cùng pattern `modifiers.new` + `modifier_apply` đã PASS với bevel/solidify/array/subsurf) · rủi ro **TRUNG BÌNH-THẤP**

| # | id | Modifier + thủ thuật | Tham số variant | Instruction mẫu (`_v0`) |
|---|---|---|---|---|
| B1-1 | `boolean_hole` | `BOOLEAN/DIFFERENCE` cube ← cylinder (rot X 90, dài hơn cube 1 đơn vị) → **xoá cutter** bằng `bpy.data.objects.remove(..., do_unlink=True)` | `size`∈{2.4,3.0}, `hole`∈{0.7,0.9} | *Create an orange 2.4 cube with a round hole of radius 0.7 cut clean through its center (boolean difference with a cylinder).* |
| B1-2 | `mirror_pair` | **shift vertex** `v.co.x += off` (mirror sẽ vô nghĩa nếu geometry nằm đúng tâm) rồi `MIRROR`, `use_axis=(True,False,False)` | `cs`∈{1.6,2.0}, `off`∈{1.6,2.0,2.4} | *Create a red cube of size 2.0 shifted 1.6 units right of center and mirror it across the middle plane to make a symmetric pair.* |
| B1-3 | `twist_column` | `SIMPLE_DEFORM`, `deform_method="TWIST"`, `deform_axis="Z"`, `angle=radians(...)` trên cylinder 32 cạnh | `h`∈{2.6,3.0}, `rad`∈{0.5,0.65}, `ang`∈{60,90,120} | *Create an orange column of radius 0.5 and height 2.6 twisted 120 degrees along its vertical axis.* |
| B1-4 | `wireframe_globe` | `WIREFRAME`, `thickness` nhỏ, `use_replace=True` trên UV sphere (metallic để cáp nổi) | `rad`∈{1.4,1.6,1.8}, `th`∈{0.05,0.07,0.1} | *Turn a red sphere of radius 1.8 into a hollow wireframe globe with wire thickness 0.1.* |
| B1-5 | `decimate_rock` | **`primitive_ico_sphere_add`** (primitive mới, chưa từng dùng) + scale lệch + `DECIMATE/ratio` | `rad`∈{1.1,1.3}, `squash`∈{(1.5,1,0.7),(1.3,1.1,0.8)}, `ratio`∈{0.2,0.3,0.4} | *Create a low-poly orange rock: a squashed icosphere (radius 1.3, scaled 1.5 x 1.0 x 0.7) decimated to 0.4 of its triangles.* |

### GÓI B2 — capability mới FONT/CURVE → MESH · rủi ro **TRUNG BÌNH-CAO** (verify riêng từng cái)

| # | id | Thủ thuật | Tham số variant | Instruction mẫu (`_v0`) |
|---|---|---|---|---|
| B2-1 | `text_3d` | `bpy.ops.object.text_add` (rot X 90 + Z 45 để dựng đứng & quay mặt về camera) → `body/size/extrude/align CENTER` → **`bpy.ops.object.convert(target="MESH")`** → material | `word`∈{ORNITH,BLENDER,MESH,GLTF}, `size`∈{0.9,1.1}, `ext`∈{0.05,0.08} | *Create the red 3D word "GLTF" standing upright and centered, text size 1.1 and extruded 0.05.* |
| B2-2 | `curve_tube` | `primitive_bezier_curve_add` → 2 điểm `co`, handle `AUTO` → `bevel_depth` + `use_fill_caps` → **convert sang MESH** | `tr`∈{0.12,0.16}, `dz`∈{0.5,0.8} | *Create a smooth orange arc tube from a beveled bezier curve, running along X and rising from z=-0.8 to z=0.8 at height 1.5 (wire radius 0.16).* |

> **Vì sao B2 cần chú ý extra:** `convert(target="MESH")` chưa từng dùng trong kernel (mọi task cũ đi thẳng primitive → mesh). Nếu font/curve fail thì `rc≠0` hoặc `meshes=0` → **fail sạch, không phá batch** (verify là per-task, `failures.jsonl` tách riêng như v1).

---

## 4. Bảng đối chiếu chống trùng (15 task mới vs 29 task cũ)

| Task mới | Task cũ gần nhất | Trùng? | Vì sao KHÔNG trùng |
|---|---|---|---|
| `staircase` | `stack3`, `pyramid` | ❌ | bậc thang **lệch trục X + cao dần**, không xếp chồng thẳng hàng (stack3) cũng không tháp tam giác (pyramid) |
| `arch` | `house`, `table` | ❌ | 2 trụ rỗng + đòn ngang (không có khối đặc kiểu tường/nóc hay mặt bàn + 4 chân) |
| `helix_tower` | `ring8`, `row5` | ❌ | `ring8` = 8 cube **nằm phẳng** 1 vòng trên nền; helix = trục đứng + **xoắn ốc lên cao** bằng sphere |
| `bookshelf` | `table` | ❌ | cấu trúc khung + kệ + nhiều cube mỏng nhiều material (bàn = mặt + 4 chân cylinder) |
| `desk_lamp` | `traffic_light`, `rocket` | ❌ | đế + cánh tay nghiêng + đèn cone + bóng emissive (cột đèn = cột + hộp + 3 bóng; rocket = thân + nắp + lửa) |
| `windmill` | `tree`, `rocket` | ❌ | 4 cánh chữ thập **xoay quanh trục ngang** ở mặt trước tháp (cây = thân + vòm; rocket = thẳng đứng) |
| `fountain` | `snowman`, `stack3` | ❌ | bồn rộng + cột + bồn con + quả (khối chồng cầu/box đơn thuần) |
| `dominoes` | `array`, `row5` | ❌ | cube **mỏng-dọc** đặt sát + **1 viên ngã nghiêng** (array = modifier 5 cube đều nhau spacing 1.5; row5 = sphere) |
| `boolean_hole` | `bevel` (modifier khác) | ❌ | modifier BOOLEAN = lỗ thủng xuyên qua; chưa có task nào tạo lỗ |
| `mirror_pair` | `array` (modifier khác) | ❌ | MIRROR = đối xứng trục; array = nhân bản theo hệ số lệch |
| `twist_column` | `rotated` (khác hoàn toàn) | ❌ | SIMPLE_DEFORM TWIST = vặn **dọc trục** theo góc (rotated chỉ xoay object cứng 30/45/60°) |
| `wireframe_globe` | `sphere`, `subsurf` | ❌ | WIREFRAME biến đặc → lưới rỗng; sphere là khối đặc, subsurf làm trơn bề mặt |
| `decimate_rock` | `sphere` | ❌ | dùng **icosphere** (primitive mới) + nén tam giác (DECIMATE), không phải UV sphere |
| `text_3d` | *không có task nào* | ❌ | FONT → MESH: capability mới hoàn toàn |
| `curve_tube` | `torus` | ❌ | đường cong bezier có caps → ống cung (torus = vòng kín tạo sẵn bằng primitive) |

**Kết quả đối chiếu id:** 15 id mới ⊄ 29 id cũ → **0 trùng** với 87 id hiện có (đã check bằng script).

---

## 5. Kết quả kiểm chứng local (đã chạy thật)

Script: `%TEMP%\opencode\mui2_draft_check.py` (chỉ **đọc** `blender_gen.py` qua `importlib`, không ghi gì vào workspace; tái dùng nguyên `PREFIX/TAIL/mdef/add/rotate_palette` của kernel → mọi script sinh ra = đúng cấu trúc sẽ chạy trên Kaggle).

```
task moi: 15 | rows: 45 (cu: 29 task / 87 rows / 83 unique)
id duy nhat vs 87 id cu: OK
dedupe (instruction,script): 45/45 unique
compile + material + bounds: OK
```

Check cụ thể từng dòng (45 rows):

| Check | Nghĩa | Kết quả |
|---|---|---|
| `compile(PREFIX+code+TAIL)` | script hợp lệ Python (không lỗi syntax khi chạy `--python`) | 45/45 ✅ |
| `material var ⊆ mdef(...)` | mọi `o.data.materials.append(mN)` đều có `mN = mat(...)` trước đó | 45/45 ✅ |
| **bounds** | mọi `location=(x,y,z)`: `|x|,|y| ≤ 4.6`, `-1 ≤ z ≤ 6.5` (trong khung camera) | 45/45 ✅ |
| **id clash** | 45 id mới không chạm 87 id cũ | 0 trùng ✅ |
| **dedupe** | `(instruction, script)` unique (đúng kiểu dedupe `gold`/`traffic_light`) | 45/45 ✅ |
| có primitive | mỗi script có ≥1 lệnh tạo object (`primitive_*` / `text_add` / `curve.primitive`) | 45/45 ✅ |

**Chưa kiểm chứng (trung thực):** runtime bpy — Blender binary trong repo chỉ là bản **Linux** (`phase12-bagent/out_v3/blender/blender-5.2.0-linux-x64`), máy Win này không chạy được → **15 emitter chưa từng chạy Blender thật**. Rủi ro tập trung ở Gói B2 (convert) và tên property modifier của Blender **4.2.23** (khớp `BVER` trong kernel). → cần **1 run verify trên Kaggle CPU** (không tốn quota GPU).

---

## 6. Cách tích hợp (đề xuất — chờ chốt, mình KHÔNG tự sửa)

**Khuyến nghị: tạo file MỚI `phase14-blender/gen_kernel/blender_gen_v2.py`** (copy `blender_gen.py` nguyên vẹn + thêm 15 task) — đúng tinh thần "không sửa file đã có", và `rows.jsonl` v2 sẽ tự chứa cả 132 rows (87 cũ + 45 mới) nếu gộp.

Các bước (ai làm cũng được, **push thì phải qua user GO**):

1. Copy `blender_gen.py` → `blender_gen_v2.py`.
2. Nối `TASKS += [...]` cho 15 task mới (id tiếp tục dải name thuần, không có tiền tố → nhất quán với 29 task cũ; `gen_rows()` tự tính `ti` += 29 nên seed/palette **không đụng** lượt cũ).
3. Thêm helper 4 dòng (chỉ trong file v2):
   ```python
   def art(w):
       """a/an dung truoc ten mau."""
       return "an" if w[:1].lower() in "aeiou" else "a"
   ```
4. (Gợi ý, tuỳ @DeepSeek) in thêm 2 dòng summary: `n_unique` theo cặp `(instruction, script)` và danh sách id bị dedupe → khỏi phải nhớ bài học `gold`/`traffic_light`.
5. Dry-run local (đã có sẵn script ở mục 5): compile + id clash + dedupe trước khi push.
6. Push kernel **chờ user GO**; CPU kernel, không đụng quota GPU.

**Ước lượng:** 45 rows × ~1.2s ≈ **55s** chạy thật (theo rate 138s/87 của v1) + tải Blender portable ~1–3' nếu `/tmp` trống → **~2–4' tổng**, output `rows.jsonl` 45 dòng (hoặc ~132 nếu gộp) + `renders/`, `glb/`, `failures.jsonl`, `summary.json`.

**Merge dataset:** hiện `hhjiji/ornith-blender-gen-data` = 83 rows. Hai phương án:
- **(a)** upload batch mới với slug khác (vd `ornith-blender-gen-data-mui2`), concat 83+45 = **128 rows** local trước khi push dataset; hoặc
- **(b)** ghi đè dataset cũ bằng 132 rows (87 gốc + 45) — phải chắc file cũ không ai đang dùng.
→ thuộc về quyết định của `@DeepSeek` + user.

---

## 7. Câu hỏi cho @DeepSeek

1. **Q1 — Tên file:** đồng ý phương án `blender_gen_v2.py` (file MỚI), hay bạn muốn chính mình append 15 task vào `blender_gen.py` (vì chỉ DeepSeek được quyền sửa file chủ lực của mũi)?
2. **Q2 — Gói chạy trước:** mình đề xuất chạy **Gói A (8 task, 24 rows) trước** để xác nhận pass_rate 1.0 với emitter mới, rồi mới Gói B1/B2 — hay chạy thẳng **15 task / 45 rows** 1 lần cho nhanh? (v1 chỉ 138s nên 1 lần cũng rẻ)
3. **Q3 — Capability mới FONT/CURVE (B2):** nếu bạn muốn **bảo hiểm tối đa** cho dataset, mình có thể bỏ 2 task này và thay bằng 2 task composition thuần (đề xuất: `picket_fence` — 5 hàng rào + 2 thanh ngang; `stairs_rail`/`swing_set`) → giữ đúng 15 task nhưng 100% helper cũ. Bạn chọn?
4. **Q4 — Merge dataset** (phương án a hay b ở mục 6) — và ai là người push sau user GO?
5. **Q5 — Tham số variant:** mình đang `rng.choice` cấu trúc theo bảng ở mục 3 (bài học gold/traffic_light). Bạn có muốn thêm biến "màu ngữ nghĩa" (vd flame luôn cam phát sáng) giữ nguyên — mình đã để `emit` hardcode ở `desk_lamp` bulb, nhưng **các tham số cấu trúc vẫn đổi** nên instruction/script vẫn unique (đã check 45/45).

---
*Hết draft — MiMo · RELEASE file này khi `DONE TASK-3` được ghi ở LOBBY.*

---

## Appendix A — 15 hàm emitter (code đã qua check ở mục 5, dán thẳng vào file v2)

> Dùng nguyên helper có sẵn của `blender_gen.py` (`mdef`, `add`, `PALETTE`) + `math` (đã import sẵn) + helper mới `art()`.
> Thứ tự trong `NEW_TASKS` = thứ tự bảng mục 3 (Gói A → B1 → B2).

```python
def art(w):
    """a/an dung truoc ten mau/color."""
    return "an" if w[:1].lower() in "aeiou" else "a"


# ---------------- GOI A (composition)
def t_staircase(pal, rng):
    c = pal[0]
    n = rng.choice([4, 5, 6])
    step = rng.choice([1.0, 1.2])
    rise = rng.choice([0.6, 0.8])
    code = mdef("m0", c[1]) + "\n"
    x0 = -((n - 1) * step) / 2
    for i in range(n):
        code += add("cube", 1.0, (x0 + i * step, 0.0, rise / 2 + i * rise), "m0",
                    f"S{i}", scale=(step * 0.9, 1.6, rise))
    return (f"Create a staircase with {n} {c[0]} steps rising along X (steps {step} "
            f"apart, each step {rise} taller)."), code


def t_arch(pal, rng):
    a, b = pal[0], pal[1]
    span = rng.choice([3.0, 3.6, 4.2])
    ph = rng.choice([2.6, 3.0])
    pw = rng.choice([0.6, 0.8])
    code = mdef("m0", a[1]) + "\n" + mdef("m1", b[1]) + "\n"
    code += add("cube", 1.0, (-span / 2, 0.0, ph / 2), "m0", "PillarL",
                scale=(pw, pw, ph))
    code += add("cube", 1.0, (span / 2, 0.0, ph / 2), "m0", "PillarR",
                scale=(pw, pw, ph))
    code += add("cube", 1.0, (0.0, 0.0, ph + 0.35), "m1", "Beam",
                scale=(span + pw, 1.0, 0.7))
    return (f"Build an arch gateway: two {a[0]} pillars {span} apart topped by "
            f"{art(b[0])} {b[0]} beam (pillar height {ph})."), code


def t_helix_tower(pal, rng):
    ball, po = pal[0], PALETTE[8]
    cnt = rng.choice([6, 8, 10])
    rad = rng.choice([1.2, 1.4, 1.6])
    rise = rng.choice([0.4, 0.45, 0.55])
    sdeg = rng.choice([45, 60])
    code = mdef("m0", po[1], rough=0.8) + "\n" + mdef("m1", ball[1]) + "\n"
    pole_h = 0.3 + cnt * rise
    code += add("cylinder", 0.12, (0.0, 0.0, pole_h / 2), "m0", "Pole", depth=pole_h)
    for i in range(cnt):
        ang = math.radians(i * sdeg)
        x = round(rad * math.cos(ang), 3)
        y = round(rad * math.sin(ang), 3)
        z = round(0.4 + i * rise, 3)
        code += add("sphere", 0.35, (x, y, z), "m1", f"B{i}")
    return (f"Create a helix of {cnt} {ball[0]} spheres (radius 0.35, orbit radius "
            f"{rad}, rising {rise} per {sdeg} degree step) winding around a brown "
            f"pole."), code


def t_bookshelf(pal, rng):
    frame, sh = pal[0], pal[1]
    w = rng.choice([2.4, 3.0])
    h = rng.choice([3.0, 3.6])
    shelves = rng.choice([2, 3])
    per = rng.choice([3, 4])
    code = mdef("m0", frame[1], rough=0.7) + "\n" + mdef("m1", sh[1], rough=0.7) + "\n"
    code += add("cube", 1.0, (-w / 2, 0.0, h / 2), "m0", "SideL", scale=(0.14, 0.5, h))
    code += add("cube", 1.0, (w / 2, 0.0, h / 2), "m0", "SideR", scale=(0.14, 0.5, h))
    for i in range(shelves + 1):
        code += add("cube", 1.0, (0.0, 0.0, i * (h / shelves)), "m1", f"Sh{i}",
                    scale=(w, 0.5, 0.1))
    bh = h / shelves - 0.3
    nb = 0
    for i in range(shelves):
        base_z = i * (h / shelves) + 0.05
        for j in range(per):
            x = round(-(per - 1) * 0.17 + j * 0.34, 3)
            col = pal[(i + j) % 4]
            code += mdef(f"mB{i}{j}", col[1], rough=0.6) + "\n"
            code += add("cube", 1.0, (x, 0.0, round(base_z + bh / 2, 3)),
                        f"mB{i}{j}", f"B{i}{j}", scale=(0.16, 0.4, round(bh, 3)))
            nb += 1
    return (f"Build a {w} wide {frame[0]} bookshelf {h} tall with {shelves} shelves "
            f"holding {nb} upright books."), code


def t_desk_lamp(pal, rng):
    shade, base_c = pal[0], (0.2, 0.2, 0.22)
    br = rng.choice([0.8, 1.0])
    arm = rng.choice([1.8, 2.1])
    tilt = rng.choice([30, 35, 40])
    s = math.sin(math.radians(tilt))
    ct = math.cos(math.radians(tilt))
    ay = round(arm / 2 * s, 3)
    az = round(0.26 + arm / 2 * ct, 3)
    ty = round(arm * s, 3)
    tz = round(0.26 + arm * ct, 3)
    code = mdef("m0", base_c, rough=0.6) + "\n"
    code += mdef("m1", shade[1], rough=0.45) + "\n"
    code += mdef("m2", (1.0, 0.95, 0.75), emit=5.0) + "\n"
    code += add("cylinder", br, (0.0, 0.0, 0.13), "m0", "Base", depth=0.26)
    code += add("cylinder", 0.09, (0.0, -ay, az), "m0", "Arm", depth=arm,
                rot=f"(math.radians({tilt}), 0.0, 0.0)")
    code += add("cone", 0.5, (0.0, -ty, round(tz + 0.15, 3)), "m1", "Shade", depth=0.8)
    code += add("sphere", 0.17, (0.0, -ty, round(tz - 0.05, 3)), "m2", "Bulb")
    return (f"Build a desk lamp: a dark base of radius {br}, an arm tilted {tilt} "
            f"degrees, {art(shade[0])} {shade[0]} cone shade and a glowing bulb."), code


def t_windmill(pal, rng):
    tw, bl_c = pal[0], pal[1]
    th = rng.choice([2.6, 3.0])
    bl = rng.choice([1.3, 1.6, 1.9])
    bw = rng.choice([0.3, 0.4])
    hz = round(th - 0.4, 3)
    code = mdef("m0", tw[1], rough=0.7) + "\n" + mdef("m1", bl_c[1], rough=0.5) + "\n"
    code += mdef("m2", (0.25, 0.25, 0.28), rough=0.6) + "\n"
    code += add("cone", 1.1, (0.0, 0.0, th / 2), "m0", "Tower", depth=th)
    code += add("cylinder", 0.1, (0.0, -0.38, hz), "m2", "Axle", depth=0.76,
                rot="(math.radians(90), 0.0, 0.0)")
    code += add("sphere", 0.3, (0.0, -0.75, hz), "m2", "Hub")
    reach = round(0.35 + bl / 2, 3)
    for i, beta in enumerate([0, 90, 180, 270]):
        r = math.radians(beta)
        x = round(math.cos(r) * reach, 3)
        z = round(hz - math.sin(r) * reach, 3)
        code += add("cube", 1.0, (x, -0.75, z), "m1", f"Blade{i}",
                    rot=f"(0.0, math.radians({beta}), 0.0)",
                    scale=(bl, 0.16, bw))
    return (f"Build a windmill: {art(tw[0])} {tw[0]} tapered tower {th} tall with a "
            f"front hub and four {bl_c[0]} blades in a cross (blade length {bl})."), code


def t_fountain(pal, rng):
    a, b = pal[0], pal[1]
    br = rng.choice([1.8, 2.2])
    ch = rng.choice([1.2, 1.6])
    code = mdef("m0", a[1], rough=0.6) + "\n" + mdef("m1", b[1], rough=0.5) + "\n"
    code += add("cylinder", br, (0.0, 0.0, 0.3), "m0", "Basin", depth=0.6)
    code += add("cylinder", 0.3, (0.0, 0.0, round(0.6 + ch / 2, 3)), "m1", "Column",
                depth=ch)
    code += add("cylinder", round(br * 0.45, 3), (0.0, 0.0, round(0.6 + ch + 0.15, 3)),
                "m0", "Top", depth=0.3)
    code += add("sphere", 0.35, (0.0, 0.0, round(0.6 + ch + 0.65, 3)), "m1", "Ball")
    return (f"Build a fountain: {art(a[0])} {a[0]} basin of radius {br} with "
            f"{art(b[0])} {b[0]} column ({ch} tall), a small upper basin and a ball "
            f"on top."), code


def t_dominoes(pal, rng):
    c0, c1 = pal[0], pal[1]
    n = rng.choice([4, 5, 6])
    gap = rng.choice([0.7, 0.85])
    dh = rng.choice([1.2, 1.5])
    tip = rng.choice([75, 90])
    t = 0.22
    code = mdef("m0", c0[1], rough=0.5) + "\n" + mdef("m1", c1[1], rough=0.5) + "\n"
    x_last = 0.0
    for i in range(n - 1):
        x = round((i - (n - 1) / 2) * gap, 3)
        code += add("cube", 1.0, (x, 0.0, dh / 2), "m0", f"D{i}", scale=(t, 0.6, dh))
        x_last = x
    r = math.radians(tip)
    half_x = (dh * math.cos(r) + t * math.sin(r)) / 2
    cz = (dh * abs(math.sin(r)) + t * abs(math.cos(r))) / 2
    fx = round(x_last + gap * 0.5 + half_x * 0.9, 3)
    code += add("cube", 1.0, (fx, 0.0, round(cz, 3)), "m1", "Fallen",
                rot=f"(0.0, math.radians({tip}), 0.0)", scale=(t, 0.6, dh))
    return (f"Create {n} {c0[0]} dominoes {dh} tall standing {gap} apart, the last "
            f"one {c1[0]} tipped over at {tip} degrees."), code


# ---------------- GOI B1 (modifier)
def t_boolean_hole(pal, rng):
    c = pal[0]
    size = rng.choice([2.4, 3.0])
    hole = rng.choice([0.7, 0.9])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", size, (0.0, 0.0, size / 2 + 0.01), "m0", "Block")
    code += add("cylinder", hole, (0.0, 0.0, size / 2 + 0.01), "m0", "Cutter",
                depth=size + 1.0, rot="(math.radians(90), 0.0, 0.0)")
    code += ('base = bpy.data.objects["Block"]\n'
             'cut = bpy.data.objects["Cutter"]\n'
             'mod = base.modifiers.new("Cut", "BOOLEAN")\n'
             'mod.operation = "DIFFERENCE"\n'
             'mod.object = cut\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'base.select_set(True)\n'
             'bpy.context.view_layer.objects.active = base\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n'
             'bpy.data.objects.remove(cut, do_unlink=True)\n')
    return (f"Create {art(c[0])} {c[0]} {size} cube with a round hole of radius "
            f"{hole} cut clean through its center (boolean difference with a "
            f"cylinder)."), code


def t_mirror_pair(pal, rng):
    c = pal[0]
    cs = rng.choice([1.6, 2.0])
    off = rng.choice([1.6, 2.0, 2.4])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", cs, (0.0, 0.0, cs / 2 + 0.01), "m0", "Twin")
    code += (f'for v in bpy.data.objects["Twin"].data.vertices:\n'
             f'    v.co.x += {fmt(off)}\n'
             'o = bpy.data.objects["Twin"]\n'
             'mod = o.modifiers.new("Mir", "MIRROR")\n'
             'mod.use_axis = (True, False, False)\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create {art(c[0])} {c[0]} cube of size {cs} shifted {off} units right "
            f"of center and mirror it across the middle plane to make a symmetric "
            f"pair."), code


def t_twist_column(pal, rng):
    c = pal[0]
    h = rng.choice([2.6, 3.0])
    rad = rng.choice([0.5, 0.65])
    ang = rng.choice([60, 90, 120])
    code = mdef("m0", c[1], rough=0.4) + "\n"
    code += add("cylinder", rad, (0.0, 0.0, h / 2), "m0", "Col", depth=h)
    code += ('mod = o.modifiers.new("Tw", "SIMPLE_DEFORM")\n'
             'mod.deform_method = "TWIST"\n'
             'mod.deform_axis = "Z"\n'
             f'mod.angle = math.radians({ang})\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create {art(c[0])} {c[0]} column of radius {rad} and height {h} "
            f"twisted {ang} degrees along its vertical axis."), code


def t_wireframe_globe(pal, rng):
    c = pal[0]
    rad = rng.choice([1.4, 1.6, 1.8])
    th = rng.choice([0.05, 0.07, 0.1])
    code = mdef("m0", c[1], metallic=0.6, rough=0.35) + "\n"
    code += add("sphere", rad, (0.0, 0.0, rad), "m0", "Globe")
    code += ('mod = o.modifiers.new("Wire", "WIREFRAME")\n'
             f'mod.thickness = {th}\n'
             'mod.use_replace = True\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Turn {art(c[0])} {c[0]} sphere of radius {rad} into a hollow wireframe "
            f"globe with wire thickness {th}."), code


def t_decimate_rock(pal, rng):
    c = pal[0]
    rad = rng.choice([1.1, 1.3])
    squash = rng.choice([(1.5, 1.0, 0.7), (1.3, 1.1, 0.8)])
    ratio = rng.choice([0.2, 0.3, 0.4])
    code = mdef("m0", c[1], rough=0.9) + "\n"
    code += (f'bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius={rad}, '
             'location=(0.0, 0.0, 1.0))\n'
             'o = bpy.context.active_object\n'
             'o.name = "Rock"\n'
             f'o.scale = {fmt(squash)}\n'
             'o.data.materials.append(m0)\n'
             'mod = o.modifiers.new("Dec", "DECIMATE")\n'
             f'mod.ratio = {ratio}\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create a low-poly {c[0]} rock: a squashed icosphere (radius {rad}, "
            f"scaled {squash[0]} x {squash[1]} x {squash[2]}) decimated to {ratio} "
            f"of its triangles."), code


# ---------------- GOI B2 (FONT/CURVE -> MESH)
def t_text_3d(pal, rng):
    c = pal[0]
    word = rng.choice(["ORNITH", "BLENDER", "MESH", "GLTF"])
    size = rng.choice([0.9, 1.1])
    ext = rng.choice([0.05, 0.08])
    code = mdef("m0", c[1], metallic=0.2, rough=0.4) + "\n"
    code += ('bpy.ops.object.text_add(location=(0.0, 0.0, 1.5), '
             'rotation=(math.radians(90), 0.0, math.radians(45)))\n'
             'o = bpy.context.active_object\n'
             'o.name = "Label"\n'
             f'o.data.body = "{word}"\n'
             f'o.data.size = {size}\n'
             f'o.data.extrude = {ext}\n'
             'o.data.align_x = "CENTER"\n'
             'o.data.align_y = "CENTER"\n'
             'bpy.ops.object.convert(target="MESH")\n'
             'o = bpy.context.active_object\n'
             'o.data.materials.append(m0)\n')
    return (f"Create the {c[0]} 3D word \"{word}\" standing upright and centered, "
            f"text size {size} and extruded {ext}."), code


def t_curve_tube(pal, rng):
    c = pal[0]
    tr = rng.choice([0.12, 0.16])
    dz = rng.choice([0.5, 0.8])
    code = mdef("m0", c[1], metallic=0.7, rough=0.3) + "\n"
    code += ('bpy.ops.curve.primitive_bezier_curve_add(location=(0.0, 0.0, 1.5))\n'
             'o = bpy.context.active_object\n'
             'o.name = "Tube"\n'
             'sp = o.data.splines[0]\n'
             'bp = sp.bezier_points\n'
             f'bp[0].co = (-2.2, 0.0, -{dz})\n'
             f'bp[1].co = (2.2, 0.0, {dz})\n'
             'for p in bp:\n'
             '    p.handle_left_type = "AUTO"\n'
             '    p.handle_right_type = "AUTO"\n'
             f'o.data.bevel_depth = {tr}\n'
             'o.data.bevel_resolution = 4\n'
             'o.data.use_fill_caps = True\n'
             'bpy.ops.object.convert(target="MESH")\n'
             'o = bpy.context.active_object\n'
             'o.data.materials.append(m0)\n')
    return (f"Create a smooth {c[0]} arc tube from a beveled bezier curve, running "
            f"along X and rising from z=-{dz} to z={dz} at height 1.5 (wire radius "
            f"{tr})."), code


NEW_TASKS_MUI2 = [
    ("staircase", t_staircase), ("arch", t_arch), ("helix_tower", t_helix_tower),
    ("bookshelf", t_bookshelf), ("desk_lamp", t_desk_lamp),
    ("windmill", t_windmill), ("fountain", t_fountain), ("dominoes", t_dominoes),
    ("boolean_hole", t_boolean_hole), ("mirror_pair", t_mirror_pair),
    ("twist_column", t_twist_column), ("wireframe_globe", t_wireframe_globe),
    ("decimate_rock", t_decimate_rock), ("text_3d", t_text_3d),
    ("curve_tube", t_curve_tube),
]
# Goi vao file v2 (KHONG sua file cu):  TASKS = TASKS + NEW_TASKS_MUI2
```

**Lưu ý kỹ thuật khi dán vào Blender 4.2.23:**
- `bpy.ops.object.select_all(action="DESELECT")` + `select_set(True)` + `view_layer.objects.active = o` trước `modifier_apply` — **lặp đúng pattern** mà `bevel/solidify/array/subsurf` của kernel đang dùng (đã 87/87 PASS), thêm bước deselect cho chắc khi scene có nhiều object.
- `boolean_hole`: cutter **bị xoá** → `VERIFY_N_MESH` = 1; `mirror_pair`: 1 object chứa 2 khối → `VERIFY_N_MESH` = 1 (verify **không** gate con số này, chỉ gate `VERIFY_OK` + `meshes>0` + `tris>0` + `png>2KB`) → vẫn PASS.
- `text_3d`/`curve_tube`: **convert sang MESH trước khi TAIL export GLB** — nếu `convert` lỗi thì `rc≠0` → vào `failures.jsonl`, không làm hỏng các row khác.
