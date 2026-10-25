# Báo cáo chất lượng data — `phase13-gui/out_traj/traj.jsonl`

- Tác giả: **GPT** (helper, 21/10) · Việc CPU-only theo onboarding mục 6C · Không push, không kernel, không key.
- Công cụ: `phase13-gui/audit_traj.py` (chạy lại được: `python phase13-gui/audit_traj.py`, py_compile OK, ASCII-only).
- Đối tượng: 816 row + 816 ảnh trong `out_traj/` — nguồn **gui-traj** (816 row) đang nằm trong mix train v22/v23.

## 1. Tổng quan

| chỉ số | giá trị |
|---|---|
| row parse OK | **816/816** (0 JSON hỏng) |
| hành động | CLICK 577 (70,7%) · TYPE 144 (17,6%) · DONE 60 (7,4%) · KEY 35 (4,3%) |
| episode (gộp theo template ảnh, bỏ `_s<n>`) | **216 ep** — 1..9 bước, trung bình 3,78 |
| gia đình app | click_button 72 ep · counter 72 ep · login_form 72 ep |
| resolution | 1280×720 (197 row) · 1440×900 (209) · 1024×768 (195) · 800×600 (215) |
| instruction duy nhất | **95** (instruction lặp nhiều nhất ×35) |

## 2. Điểm ĐẠT (kiểm chứng bằng số, không suy đoán)

1. **Schema sạch**: mọi row đều có `image`/`instruction`/`action`. 239 row (TYPE+KEY+DONE) thiếu `point`/`bbox`/`label` — **đúng thiết kế**; loader dùng `.get()` (`gui_sft_v19.py` dòng 288/435) nên không vỡ.
2. **Họạ học chính xác tuyệt đối**: 0 tọa độ ngoài màn hình (0..1280 × 0..720); **0/577** điểm CLICK nằm ngoài bbox của nó; **0/577** dòng `CLICK x y` lệch với trường `point`.
3. **Ảnh khớp 1:1**: 816 file ảnh ↔ 816 row, 0 ảnh thiếu, 0 ảnh mồ côi.
4. **DONE không bao giờ giữa chừng**: 0/60 DONE xuất hiện không phải bước cuối của episode.
5. **Không trùng (image, action)**: 0 cặp.

## 3. VẤN ĐỀ (xếp theo mức độ)

### P1 — Rò rỉ giá trị vào instruction (nghiêm trọng nhất, đúng "nút thắt" đang chẩn đoán)
- **657/816 row (80,5%)** instruction chứa chữ số (vd `Increment the counter to 8.`, `Log in with username admin and password 1234.`).
- Tập giá trị cực hẹp: chỉ **4 cặp (user, pass)** — admin/1234, user1/pass123, maria/s3cret, tom/qwerty; **6 giá trị counter** (3–8); **8 giá trị TYPE** (`user1`, `pass123`, `maria`, `s3cret`, `admin`…); KEY chỉ đúng **`enter` ×35**.
- Hệ quả: với nguồn này model **không buộc phải đọc màn hình** — chỉ cần chép instruction. Đây chính là anti-pattern mà @MiMo đã diệt ở synth/targeted (pool giá trị procedural, instruction không được chứa giá trị); nguồn traj cũ này **vẫn nguyên** lỗi đó và chiếm ~17% mix v22 (816/4700).
- **Không sửa được bằng cách viết lại instruction** (giá trị gõ phải khớp ảnh) → muốn hết phải **sinh lại app + state với giá trị ngẫu nhiên** — trùng hướng với TASK-26 của @MiMo.

### P2 — P(DONE) rất thấp (thiếu "finish/commit" đúng như metric P(DONE) 10,7% đã nêu)
- Chỉ **60 DONE row = 7,4%** row; **156/216 ep (72%) kết thúc không có DONE**.
- Theo app: click_button 25/72 ep có DONE (35%) · counter 17/72 (24%) · login_form 18/72 (25%).
- Đây là mảng data trực tiếp nuôi lỗi "model làm xong không commit / không emit DONE" trên chuỗi dài (B15.5 0/18, B16-A 0/24 với baseline).

### P3 — Đa dạng task thấp
- Chỉ **3 app** (click_button, counter, login_form). Bench B15.5/B16 (T13–T26) có wizard/validation, alerts+scroll, clipboard, reorder, count+submit, filter/chọn list → **gần như không có train coverage tương ứng** trong nguồn này. (Đúng hướng bàn giao TASK-26/28.)

### P4 — Trùng nội dung ảnh (nhỏ)
- 3 cặp ảnh **giống hệt về md5**: `counter_1440x900_v05_s0..s2` ≡ `v16_s0..s2` (cùng `CLICK 544 283`, chỉ khác cách diễn đạt instruction: "Make the counter show 3." vs "Use the + button until the counter reaches 3."). Không hại (vốn là paraphrase), nhưng ~3 row dư.

## 4. Đề xuất (cần người quyết — mình không tự làm nếu đụng mix train)

- **R1 (không tốn gì)**: với v23, coi `gui-traj 816` là nguồn **legacy** — chỉ tin ở phần CLICK-grounding (mục 2 chứng minh nó sạch); **không** dùng nó để dạy value-discipline hay finish-discipline.
- **R2 (offline, 1 dòng code, không đụng file gốc)**: sinh file mới `out_traj/traj_done_aug.jsonl` = 816 row cũ **+ 156 row DONE** (dùng lại ảnh bước cuối của 156 ep thiếu DONE, action `DONE`) → P(DONE) của nguồn này 7,4% → **~23%**, khớp cách @MiMo đã làm cho synth (10,7%→80,2%). Nếu anh chị duyệt thì mình chạy ngay (file mới, không sửa bản gốc, không push).
- **R3**: các giá trị trong P1 nên được thay bằng pool ngẫu nhiên khi TASK-26 render app — data traj cũ không cần đụng lại.

## 5. Cách tái kiểm chứng
```
python phase13-gui/audit_traj.py
```
Mọi con số trong báo cáo đều là output trực tiếp của script (có đối chiếu tay vài dòng mẫu bằng JSON thô).

— GPT, 21/10
