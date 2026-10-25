# SCORING — Bench game 60 task (base vs r1 vs r2) + computer 20 task

> fair = strip fence + base-chat + greedy. Sampling cũ (temp 0.3) chỉ tham khảo.
> Tổng mới: 400 (game/unity/bpy 300 + computer 100). Bench cũ giữ thang 300.

## 4. Track điều khiển máy tính (20 task × 5đ = 100)

- Model xuất lệnh bash (mỗi dòng 1 lệnh), harness chạy trong sandbox
  (reset mỗi task, timeout 15s/lệnh, cấm lệnh nguy hiểm).
- Verify bằng code kiểm tra trạng thái filesystem (deterministic).
- Đúng = 5, sai/crash/lệnh cấm = 0. Không chấm từng phần.

> File này là luật chấm DUY NHẤT. Model nào cũng chấm y hệt. Tổng 300 điểm.

## 1. Cấu trúc: 60 task × 5 điểm = 300 điểm

| Track | Số task | Chạy trên |
|---|---|---|
| Pygame (game 2D chạy thật) | 20 | `SDL_VIDEODRIVER=dummy`, timeout 60s |
| Unity-pattern (C# MonoBehaviour) | 20 | check tĩnh (không có Unity engine trên Kaggle) |
| bpy Blender (model 3D) | 20 | Blender 5.2 headless thật, fallback check tĩnh nếu Blender lỗi |

## 2. Thang điểm từng task (0–5)

**Pygame:**
- Chạy không lỗi (exit 0): **2**
- Sống đủ 10s không crash: **1**
- Có game-loop đủ: `pygame.init` + `display.set_mode` + `event.get` + `Clock/tick` + `flip/update` (đủ ≥4/5): **1**
- Có state game (`score`/`lives`/`level`/`health`): **1**

**Unity-pattern:**
- Có class kế thừa `MonoBehaviour`: **1**
- Có `Start` và `Update`: **1**
- Brace `{}` cân bằng: **1**
- Dùng ≥5 Unity API (`transform, GetComponent, Instantiate, Rigidbody, Collider, Input, Time, Debug, GameObject, Vector3, Camera, AudioSource, Animator`): **2** (≥3 API: 1)

**bpy Blender:**
- Blender exit 0: **2**
- Render ra PNG không rỗng (std pixel > 5): **2**
- Dùng ≥2 primitive `bpy.ops.mesh`: **1**
- Nếu Blender lỗi môi trường: thay bằng `ast.parse` OK (2) + keywords (2) + non-empty (1) — ghi rõ mode vào log

## 3. Cách tính

- Mỗi config generate 1 mẫu/task (GREEDY deterministic: do_sample=False, max 256 tokens, eval seed cố định 123). Đổi từ temp 0.3 sang greedy vì variance ±30 làm điểm vô nghĩa.
- **Strip markdown fence trước khi chấm** (lấy code trong ```...```, bỏ dòng ```). Áp dụng như nhau cho mọi config — chấm code thật, không chấm thói quen format.
- Base chấm 2 kiểu: `base-alpaca` (prompt thô như lúc train) và `base-chat` (chat template chuẩn của model) để thấy năng lực thật của base. r1/r2 chấm bằng prompt Alpaca (đúng phân phối lúc train).
- Điểm model = tổng 60 task. Báo thêm điểm từng track (Pygame /100, Unity /100, bpy /100).
- Hòa điểm → so số task pass 5/5, rồi so loss train.
