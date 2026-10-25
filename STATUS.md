# STATUS — Ornith-1.5-9B → agent GUI/3D/computer-use (cập nhật 21/10 08:50)

## 0. Tài khoản & GPU (21/10 08:50) — **2 ACC, ~41.7 GPU-GIỜ CÒN** (+60h reset 24/10)

| Acc | Quota GPU (còn) | Vai trò | Queue |
|---|---|---|---|
| **`khoadangnguye` (A)** | 19.2h/30h | **train v22** + gate v21 (B15.5/B16/3D) | `scripts/gpu_queue.json` |
| **`dieniw` (B)** | 22.5h/30h | **baseline v18** (B15.5/B16/3D/3D-hard) | `scripts/gpu_queue_B.json` |
| `hhjiji` | hết quota | giữ dataset gốc | — |

- **Key chỉ truyền qua env var** (`KAGGLE_USERNAME`/`KAGGLE_KEY`), **không ghi file** → đã lưu trong `HKCU:\Environment` (`KAGGLE_KEY_A/B`, `ACC_SRC_*`, `HF_TOKEN`) để pipeline **tự khởi động lại khi bật máy** ✓.
- **Tự bật pipeline khi login Windows**: `C:\Users\Admin\ornith_autostart.cmd` trong **Startup folder** → gọi `scripts/start_all.ps1` (đọc key từ registry ✓ → spawn watchdog A/B + space_sync + watcher agent.md ✓). Đã test ✓.
- Khởi động lại thủ công: `python scripts/restart_watchdogs.py` (cần env `KAGGLE_KEY_A`/`KAGGLE_KEY_B`).
- **Câu cứng duy nhất (PLAN.md §X)**: *"Mỗi lần train: seed mới, ma trận mới"* → code đã sửa (`SEED = random.randint` mỗi run ✓ + log + ghi result ✓).

## 1. Số liệu chuẩn (v21 vs v18 baseline)
| Suite | v21 | v18 | Chênh | parse v21 |
|---|---|---|---|---|
| B15 | 11/36 = 30.6% | 10/36 = 27.8% | **+2.8%** | 0.95 |
| B15.5 | 1/18 = 5.6% | 0/18 = 0% | **+5.6%** | **0.44** ⚠ |
| B16 | 7/24 = 29.2% | 6/24 = 25.0% | **+4.2%** | 0.96 |

- Ngưỡng gate: B15 ≥35% · holdout (variant 2) ≥35% · v14 ≥2/3.
- **Vấn đề chính**: parse_rate B15.5 = 0.44 → trên suite khó model **quay lại prose** ⇒ cần data **action-only sạch cho task khó**.
- **Model thua 0 ở**: signup 0/20 · pagecode 0/19 · errorfix 0/18 · login 0/16 · tabcode 0/7 ⇒ lỗi là **nhiều bước + gõ chữ + nhắc thứ tự**, không phải format.
- Self-play vòng 2: rollout win 25/72 → curate **118 row** → dataset `khoadangnguye/gui-selfplay` v2 READY ✓.

## 2. BUS TRAO ĐỔI TỨC THÌ (môi trường chat nhanh — 21/10)
| Thành phần | Vai trò |
|---|---|
| `scripts/bus.py` | bus tin nhắn localhost:8777 — `POST /post`, `GET /events` (SSE), `GET /since`, `GET /messages` ✓ |
| `scripts/bus_post.py` | **lệnh 1 dòng cho agent**: `python scripts/bus_post.py <Tên> "<tin>" --tag <tag>` ✓ (bus chưa chạy → ghi `bus_outbox.jsonl` ✓) |
| `scripts/watch_bus.py` | subscriber: nhận tin **~1s** → in log + **beep** + **POST thẳng vào session OpenCode** (`/api/session/<id>/prompt`) → agent bị *thức* ngay ✓ |
| `scripts/watchdog.py` | poll **60s** + **post bus** khi kernel COMPLETE/ERROR + khi push xong ✓ |
| `scripts/watch_agent_md.py` | post bus mỗi lần agent.md có dòng mới ✓ |

- **Luật mới**: agent.md = **sổ cái** (append-only: quyết định/số liệu/CLAIM/RELEASE) · **BUS = kênh trao đổi nhanh** (hỏi/đáp/báo kết quả) · không "ghi rồi ngủ" ✓.
- API OpenCode: `http://127.0.0.1:45278/api/...` + Basic auth (user `opencode`, password trong `~/.config/opencode/service.json`) ✓ · `POST /api/session/<id>/prompt` body `{"text":...}` ✓.

## 3. Đang chạy (21/10 11:30)
- **A**: `sft-v22` v2 (4700 row: synth 1200 + real-ui 792 + traj 816 + targeted **500** + 3D 1200 + **policy-replay 332 task-thật** + selfplay 123) · `bench-3d-v21` (đã vá `main()`)
- **B**: `bench-3d-b1` · `bench-3d-hard-b1` (baseline v18)

## 3. DESKTOP-ENV (computer-use thật) — **ĐÃ CHỨNG MINH**
- Xvfb 1280×720 + chromium headful (playwright) + **phím OS thật làm app đổi state** ✓ (kernel `khoadangnguye/ornith-desktop-proof`).
- 3 bẫy đã lộ & đã sửa: `chromium-browser` = wrapper **snap** (không chạy) · chromium **bundle không mở port remote-debugging** (dùng `playwright.launch(headless=False)`) · process phải có `os.environ['DISPLAY']`.
- **Lệch 86px** do thanh công cụ browser ⇒ `off_y = 720 - innerHeight` (chưa đúng vì playwright override innerHeight) → cần đo bằng marker đỏ hoặc crop ảnh theo viewport.
- Hạ tầng: `phase14-desktop/env.py` · `tasks/game_2048.html` (điểm = reward) · `harness.py` (GLM) · `TASK26_TASK27.md` (spec) · `dashboard_sync.py` + `push_space_static.py` (panel DESKTOP trên Space static ✓).

## 1. Pipeline hiện tại
```
ACC A: [bench-v21 ▸] [bench-v155-v21 ▸] → sft-v22 → bench-v14-v21 → bench-v16-v21
       → rollout-v21 → bench-3d-v21 → bench-3d-hard-v21 → think0
ACC B: [bench-v155-b1 ▸] → bench-v16-b1 → bench-3d-b1 → bench-3d-hard-b1
```
- **2 session GPU/acc** (`MAX_SESSIONS=2` trong `scripts/watchdog.py`), quota chỉ là điều kiện (cache 6h, refresh 24/10 00:00).
- **Tự động chấm gate**: `scripts/post_gate.py` + `scripts/post_gate.ps1` → watchdog tải output → `gate_report.py` → LOBBY + `phase13-gui/gate_results.jsonl` → dashboard Space. Gắn cho 7 mục (file `scripts/post_gates/*.ps1`).
- 2 watchdog chạy **độc lập** (A/B): `WATCH_TARGETS` / `WATCH_STATE` / `WATCH_LOG` / `GPU_QUEUE` theo env → `scripts/watchdog_targets.json` vs `watchdog_targets_B.json`.

## 2. Số liệu chuẩn (gate)
- **B15 baseline v18 = 10/36 = 27.8%** (v0 3/12, v1 3/12, **v2 4/12 = 33.3%** = holdout).
- Ngưỡng gate: B15 tổng ≥35% · holdout (variant 2) ≥35% · v14 ≥2/3.
- v20 (recipe think+action) = 8.3% → **recipe think bị loại**, dùng action-only của v18.

## 3. DESKTOP-ENV (môi trường computer-use THẬT) — mới 20/10
- Quan sát = **ảnh chụp màn hình X11**; hành động = **xdotool** (move/click/drag/scroll/type/key) → sự kiện OS thật.
- Giao diện policy **giống hệt B15** (`CLICK x y` 0..1000 / `TYPE` / `KEY`) → model + code cũ chạy lại được.
- Hạ tầng: `phase14-desktop/env.py` · `phase14-desktop/tasks/game_2048.html` (điểm = reward) · `phase14-desktop/harness.py` (GLM: vòng obs→model→action→env, ghi `actions.jsonl`+`reward.json`+ảnh) · `phase14-desktop/TASK26_TASK27.md` (spec cho helper).
- **Đã verify trên Kaggle CPU**: Xvfb OK, `import -window root` OK, xdotool OK, app thật (xeyes) hiện trên ảnh.
- Kernel: `khoadangnguye/ornith-desktop-selftest` (self-test) · `khoadangnguye/ornith-desktop-harness-check` (chromium + CDP + điểm game).
- Ưu tiên: env này **để sinh data SFT task thật** + **demo cho user xem trên Space (noVNC)** — chưa phải để model tự chơi (model 9B còn yếu).

## 4. Data train (v22)
`1200 synth + 792 real-ui + 816 traj + 250 targeted(S1-S8) + 600 3D + 600 3D-hard + 332 policy-replay + selfplay ≤30%` ≈ 4200 row.
- **332 row policy-replay = task THẬT** (sinh bằng success-policy trên app thật) → dataset `khoadangnguye/ornith-policy-replay-data` v2 (đã giữ `shots/*.png`).
- 3D train data: `ornith-gui-train3d` + `-hard` (action `CLICK x y` giống GUI).

## 5. 4 bài học Kaggle CLI (đã tốn GPU-giờ)
1. `datasets create/version` **bỏ qua thư mục** → dataset có `deps_out/`, `shots/`, `images/` bị mất → phải để file ở **cấp gốc** hoặc tự giải nén.
2. CLI trả **exit code 0 kể cả khi API lỗi (403/404)** → phải kiểm **CHUỖI output**, không tin rc.
3. `datasets download` trả 1 file `.zip` chưa giải nén → upload **NGUYÊN file zip**; nhưng **Kaggle KHÔNG giải nén zip lồng nhau** → muốn `shots/x.png` phải giải nén ở local rồi upload thư mục ảnh.
4. `kernels list` phân trang 20 dòng → quét hết dataset phải `--page-size 200` + `--page-token`.
5. *(thêm)* Kaggle kernel **chỉ upload `code_file`** → mọi thư viện phải **inline** trong 1 file.
6. *(thêm)* `kaggle kernels output` lỗi charmap → dùng `scripts/kq.ps1` hoặc `PYTHONUTF8=1` + `chcp 65001`.

## 6. Vận hành khi user đóng session (QUAN TRỌNG)
- 4 process **tách rời** (Windows DETACHED_PROCESS) chạy 24/24, không bị kill khi đóng OpenCode:
  - `watchdog` A → `scripts/logs/watchdog.log` (queue `gpu_queue.json`)
  - `watchdog` B → `scripts/logs/watchdog_B.log` (queue `gpu_queue_B.json`)
  - `space_sync` → `scripts/logs/space_sync.log` (đẩy state lên Space mỗi 3′)
  - `agent_md_watch` → `scripts/logs/agent_md_watch.log` + `scripts/agent_md_changes.log`
- Khởi động lại: `python scripts/restart_watchdogs.py` (cần env `KAGGLE_KEY_A`/`KAGGLE_KEY_B`).
- Space Docker (private): `https://kkouadn-dual-orchtractor.hf.space` → `/health` `/status` `/lobby`; **request cần header `Authorization: Bearer <HF_TOKEN>`** (private → không token thì 404).
- Space static: `https://himagayem-ornith-agent.static.hf.space`.

## 7. Việc còn tồn (cần user)
1. **Mistral + Gemini key** (đặt trong Space secrets) → bật chat LLM trên Space.
2. **Rotate key acc B** (`dieniw`) + **xoá kernel `dieniw/ornith-splitter`** (đã lỗi 401).
3. HF PRO (tuỳ chọn) → bản Docker đầy đủ + `RUN_WATCHDOG=1` + noVNC.
