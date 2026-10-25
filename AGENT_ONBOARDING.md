# ONBOARDING CHO AGENT MỚI (đọc file này TRƯỚC, 5 phút)

> Bạn là **agent phụ** trong dự án **Ornith** (workspace `C:\Users\Admin\Desktop\New folder`).
> Tài liệu này đủ để bạn làm việc ngay mà không cần hỏi ai.

---

## 1. Dự án là gì

**Mục tiêu**: train model **Ornith-1.5-9B** (Qwen3.5-VL base) thành **agent điều khiển máy tính**
(GUI web / 3D Blender / computer-use thật), theo vòng lặp **tự cải thiện**: agent tự sinh dữ liệu
→ tự huấn luyện → tự đánh giá → lặp lại.

**Hiện tại**:
- Base model: `dieniw/ornbase-s1..s4` (4 shard) + adapter LoRA (`khoadangnguye/ornith-gui-lora-v21`).
- Huấn luyện chạy trên **Kaggle GPU** (2 acc × 30h/tuần). **Bạn KHÔNG cần GPU** — có thể làm việc CPU-only.
- Benchmark: **B15** (12 task web × 3 biến thể = 36 episode), **B15.5**, **B16**, **3D grounding**, **desktop-env**.

**Số liệu chuẩn (đọc để hiểu đâu là nút thắt)**:
| Suite | v21 (hiện tại) | v18 (baseline) | Ngưỡng |
|---|---|---|---|
| B15 | 11/36 = **30.6%** | 27.8% | ≥35% |
| B15.5 | 1/18 = 5.6% | 0% | (đang sửa lại) |
| B16 | 7/24 = 29.2% | 25.0% | ≥35% |

Model **thắng** ở task dễ (T09_coupon 18/18, T11_counter 8/8, T03_delayed 7/7, T10_canvas 5/5) và
**thua 0** ở task nhiều bước + gõ chữ: `signup 0/20 · pagecode 0/19 · errorfix 0/18 · login 0/16 · tabcode 0/7`.
⇒ **Kết luận quan trọng**: model **biết format** (parse_rate 0.95 ở B15) nhưng **không làm theo yêu cầu cụ thể**.
⇒ Việc cần làm: **sinh data dạng "nhiều bước + giá trị ngẫu nhiên trên trang"** (không phải thêm data dễ).

---

## 2. LUẬT CỨNG (vi phạm là hỏng việc)

1. **Câu cứng duy nhất (PLAN.md §X, user chốt 07/10/2026)**:
   > *"Mỗi lần train: seed mới, ma trận mới — không để một khúc tham số học quá nhiều."*
   → Trong code: `SEED = random.randint(1, 10**9)` mỗi run + log seed + ghi vào result json ✓
   (rank/steps/batch/LR thì linh hoạt, nhưng phải ghi lại).
2. **Key/token chỉ truyền qua env var lúc chạy — KHÔNG ghi vào file.** (Đã lưu trong `HKCU:\Environment` ✓
   để pipeline tự chạy; đọc bằng `Get-ItemProperty 'HKCU:\Environment'` ✓.)
3. **Không push Kaggle kernel** (đó là việc của tôi/DeepSeek) — trừ khi được giao rõ.
4. **Không tự cancel kernel** (hỏi trước; CLI không có lệnh cancel → `delete` xoá hẳn kernel).
5. **Không sửa file của agent khác** khi chưa CLAIM. Quy tắc file: đọc `agent.md` (mục **LUẬT CỨNG** +
   Danh bạ) → CLAIM file đích (ghi vào LOBBY) → làm → RELEASE.
6. `agent.md` là **append-only** (không sửa/xoá dòng cũ).
7. **Tiếng Việt không dấu** trong .py để tránh lỗi cp1252 (bài học ✓).

---

## 3. Trao đổi: BUS (tức thì) + agent.md (sổ cái)

```powershell
# GỬI TIN (đến trong ~1 giây, được đẩy thẳng vào session OpenCode của agent kia)
python scripts/bus_post.py TEN_BAN "nội dung" --tag bench|app|harness|question|done

# GỬI THẲNG VÀO 1 SESSION cụ thể
python scripts/session_send.py <session_id> "nội dung"
python scripts/session_send.py --title "LOBBY & TASK BOARD" "nội dung"
python scripts/session_send.py --list

# Đọc tin mới nhất
python -c "import io;print(''.join(io.open('scripts/bus.jsonl',encoding='utf-8').readlines()[-3:]))"
```

- **BUS = kênh trao đổi nhanh** (hỏi/đáp/báo kết quả/cần trợ giúp).
- **`agent.md` = sổ cái bền**: ghi quyết định, số liệu, CLAIM/RELEASE, kết luận (append-only).
- **Không "ghi rồi ngủ"** → post bus rồi làm việc khác; tin sẽ tới bạn.
- Watchdog poll **60s** và **post bus** khi kernel xong → bạn không cần tự `kaggle kernels output`.

---

## 4. Bản đồ dự án (file quan trọng)

| File | Vai trò |
|---|---|
| `agent.md` | LOBBY + LUẬT CỨNG + danh bạ task (đọc đầu file) |
| `PLAN.md` | kế hoạch dài hạn (**§X = câu cứng**) |
| `MAIN_QUEST.md` | nhiệm vụ gốc + rủi ro quota |
| `STATUS.md` | trạng thái hiện tại (đọc để vào việc nhanh) |
| `AGENT_BUS_GUIDE.md` | hướng dẫn bus (ngắn hơn file này) |
| `phase13-gui/kernel_v22/` `kernel_v23/` | **kernel train** (đừng sửa khi đang chạy) |
| `phase13-gui/bench_v15/` | task web B15 (12 trang) + checker |
| `phase13-gui/bench_v15/tasks_v15_5/` | task B15.5 (T13–T18) — **MiMo đã sửa T13** |
| `phase13-gui/bench_v15/tasks_v16_a/` | task B16 (T19–T26) — **đã bỏ lộ đáp án** |
| `phase13-gui/rollout_curate.py` | lọc dữ liệu self-play (có fix A2) |
| `phase13-gui/gate_report.py` | chấm gate (exit 0/1) |
| `phase14-desktop/env.py` | **môi trường computer-use thật**: Xvfb + chụp màn hình + xdotool |
| `phase14-desktop/harness.py` | vòng obs→model→action→env (đã chuyển sang **Playwright headful**) |
| `phase14-desktop/tasks/` | app cho desktop-env (game_2048.html ✓) |
| `scripts/watchdog.py` `scripts/bus.py` `scripts/post_gate.py` | hạ tầng vận hành |
| `phase14-space/` | Docker Space (OpenCode + dashboard) |

---

## 5. BẪY ĐÃ GẶP (đừng lặp lại)

| Bẫy | Sự thật |
|---|---|
| `kaggle datasets create` | **bỏ qua thư mục con** → ảnh trong `shots/` bị mất. Phải để **phẳng ở gốc** ✓ |
| Kaggle không giải nén zip lồng nhau | muốn `shots/x.png` phải giải nén local rồi upload ảnh phẳng ✓ |
| `kaggle kernels push` exit 0 dù lỗi | **kiểm chuỗi output**, đừng tin rc ✓ |
| Kernel chỉ upload `code_file` | mọi thư viện phải **inline** trong 1 file ✓ |
| Push 1 kernel cũ bị 409 | slug "ma" (Kaggle tạo rồi save fail) → **đổi slug mới** ✓ |
| Kernel 3D "chạy xong" nhưng rỗng | thiếu lệnh gọi `main()` → đã fix ✓ |
| Chromium bundle không mở port remote-debugging | dùng **`playwright.launch(headless=False)`** ✓ + `os.environ['DISPLAY']=':99'` ✓ (bắt buộc) |
| Tọa độ lệch 86px | do **thanh công cụ browser** → cắt ảnh theo viewport ✓ |
| B15.5/B16 cũ có lỗi | T13 tự mâu thuẫn ✗, B16 lộ đáp án ✗ → **đã sửa**, gate đang đo lại ✓ |
| 3D metric | "knife-edge", dễ hơn GUI → **ưu tiên GUI** ✓ |

---

## 6. Việc bạn có thể làm NGAY (CPU-only, không cần GPU, không cần hỏi)

Chọn 1 và **CLAIM** trong LOBBY (`agent.md`) trước khi viết code:

- **A. App computer-use mới** (`phase14-desktop/tasks/`): 1 app offline (`file://`) có **biến ngẫu nhiên**
  (mật khẩu/mã/số đổi mỗi lần chạy ✓) + **nhiều bước** ✓ + checker **đọc DOM** ✓ + success-policy
  **đọc biến từ DOM** ✓ + fail-policy ✓ + self-test ✓. (Đây là thứ thiếu nhất ✓)
- **B. Trace B15.5**: đọc `phase13-gui/out_bench_v155_v21/b15_result.json` (mỗi episode có `trace` ✓) +
  `out_bench_v155_B/` → tìm task (T14–T18) có **màn hình tự mâu thuẫn / thiếu phản hồi** → sửa + verify.
- **C. Kiểm tra chất lượng data** (`phase13-gui/out_traj/traj.jsonl`): đếm row prose/ sai format → đề xuất lọc.
- **D. Viết tài liệu/đo đạc**: ví dụ script tổng hợp kết quả nhiều suite (`scripts/collect_results.py` ✓ có sẵn).

---

## 7. Quy trình làm việc (theo thứ tự)

```
1. Đọc: STATUS.md + agent.md (đầu file: LUẬT CỨNG) + AGENT_BUS_GUIDE.md
2. Chọn 1 việc ở mục 6  →  CLAIM trong agent.md (ghi file đích + ghi rõ không sửa file của ai)
3. Làm (CPU-only)  →  tự kiểm chứng (self-test / checker --self-test / dummy replay)
4. Ghi LOBBY (agent.md): kết quả + số liệu + file đã tạo + RELEASE
5. Báo bus: python scripts/bus_post.py TEN_BAN "xong TASK-X: <kết quả>" --tag done
```

**Cứ làm**: sai thì sửa ✓ — nhưng **đừng sửa file người khác đang giữ** ✗, **đừng push kernel** ✗,
**đừng đụng key** ✗.
