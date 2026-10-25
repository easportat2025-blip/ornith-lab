# TASK-26 / TASK-27 — DESKTOP-ENV (môi trường computer-use thật)

> File này là **bản spec đầy đủ** cho 2 helper. Nếu bạn chỉ thấy tin trong LOBBY khi ai đó sửa `agent.md`, đọc file này là đủ.

## Bối cảnh
Ornith (model 9B) hiện mới giỏi "click vào DOM HTML" (B15 = 27.8%). Muốn tiến lên **computer-use thật**:
agent nhìn **ảnh chụp màn hình** và thao tác **chuột/bàn phím thật** trên desktop.

## Hạ tầng đã có (KHÔNG cần làm lại, KHÔNG sửa)
| File | Vai trò |
|---|---|
| `phase14-desktop/env.py` | Xvfb 1280×720 + chụp màn hình (`import -window root`) + **xdotool** (move/click/drag/scroll/type/key) + mở app + đọc state app qua Chrome DevTools Protocol (`dom_state()`) |
| `phase14-desktop/tasks/game_2048.html` | game 2048 tự viết, điểm số nằm ở `#s` và `window.__score` (reward = điểm) |
| `phase14-desktop/kernel_selftest2/selftest_desktop.py` | kernel CPU self-contained, đã push: `khoadangnguye/ornith-desktop-selftest` |

**Giao diện policy (giống hệt B15 → model/code cũ chạy lại được):**
```
"CLICK 322 440"   (x,y normalized 0..1000)
"TYPE user@example.com"
"KEY up" / "KEY ctrl+a" / "KEY enter" ...
"MOVE 500 500" · "DRAG 300 300 700 500" · "SCROLL 3"
```

## TASK-26 (MiMo) — bộ task computer-use thật
Viết trong `phase14-desktop/tasks/` (file MỚI, **không sửa `env.py`**):

Mỗi task gồm: **1 app web tự viết** (HTML+JS, chạy được từ `file://`, offline) + **checker đọc trạng thái app từ DOM** (không tin self-report) + **success-policy** (dùng để sinh data SFT kiểu policy-replay) + **fail-policy** (phải bị reject) + self-test.

| Task | App | Reward (checker đọc) |
|---|---|---|
| `T20_2048` | game 2048 (đã có) | điểm số ≥ ngưỡng (vd 40) |
| `T21_form_desktop` | form đăng ký | giá trị field + cờ submit |
| `T22_calc` | app máy tính | đáp án đúng |
| `T23_table_sort` | bảng dữ liệu | thứ tự hàng + dòng đã chọn |
| `T24_text_edit` | editor text | nội dung sau khi lưu |

Yêu cầu: mỗi task **ghi rõ toạ độ các phần tử** (để người khác viết success-policy) + mô tả task trong `TASKS.md`; self-test report JSON.
Ưu tiên: T20 → T21 → T22 → rồi T23/T24.

## TASK-27 (GLM) — harness dùng chung
Viết `phase14-desktop/harness.py` (file MỚI):
1. obs = screenshot của env (`env.screenshot`) + instruction của task
2. model = **PolicyV2** (copy nguyên file từ `phase13-gui/kernel_bench_v15/bench_v15_kernel.py` — **không sửa file cũ**)
3. action = `env.do_action(action_str)` — **sự kiện chuột/phím thật**
4. ghi: `obs/<ep>_<step>.png` + `actions.jsonl` (action + mô tả + reward) + `reward.json`
5. **chạy được trong container Docker của Space** (`kkouadn-dual-orchtractor.hf.space`) để user **xem agent thao tác thật** (thêm noVNC nếu được).

Ràng buộc: action space phải khớp 1-1 format model ở trên; mỗi task 1 reward từ checker; **chưa cần model thật** — chạy được bằng policy giả lập để chứng minh harness đúng.

## Ranh giới
- Không push kernel (DeepSeek push). Không cần GPU/Key.
- CLAIM file đích trước khi viết (ghi vào LOBBY).
- Mọi app phải **offline** (`file://`) và **không cần mạng** lúc chạy.
