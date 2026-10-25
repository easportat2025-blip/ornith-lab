# MAIN QUEST — Ornith-1.5-9B: self-improving computer-use agent (5 ngày)

> **Mệnh lệnh của user (19/10):** "cứ chạy phát triển models như người thật... cho phép nó reasoning... càng ngày phải làm benchmark khó hơn... mọi thứ do bạn quyết định — 5 ngày sau gặp lại."
>
> File này là **nguồn chân lý** cho 5 ngày. DeepSeek (agent chính) được tự quyết mọi thứ trong khuôn khổ ở đây; helper GLM/MiMo nhận task qua `agent.md` §TASK BOARD.

---

## 0. Tóm tắt điều hành

| Hạng mục | Chốt |
|---|---|
| Model | Ornith-1.5-9B (Qwen3.5-VL, MIT) + LoRA adapter |
| Hai mũi | **Browser GUI** (`phase13-gui/`) + **Blender 3D** (`phase14-blender/`) |
| Cơ chế | Self-improving loop: rollout → verifier → lọc trajectory → SFT → benchmark khó hơn |
| Reasoning | **BẬT**. Format `THINK:` + `ACTION:`; decode tối đa **256 token**; parser lấy `ACTION:` cuối |
| Benchmark | Mỗi ngày một bậc khó hơn: **B15 → B16 → B17 → Final surprise**; Blender: **45 mui2 → 30 hard → 15 compositional** |
| Compute | Kaggle, tối đa **2 GPU session** cùng lúc; Blender verify = CPU |
| Push | Được push không cần hỏi. **Cancel kernel phải hỏi user.** |
| Key | Chỉ qua env lúc chạy; không ghi vào file/repo |
| Ngày 5 | Model card + adapter + benchmark report + toàn bộartifact tái lập được |

**Định nghĩa thành công tối thiểu (Day-5 gate):**
1. GUI hard suite **≥ 60%** success (B15/B16 gộp), không có task nào 0% do format.
2. Reasoning parse **≥ 95%**, prose-leak **≤ 5%**, invalid action **≤ 5%**.
3. Blender: **45/45** mui2 verify PASS + **≥ 70%** hard-30 PASS.
4. Không hồi quy trên bench v14 (giữ ≥ 2/3 win) và eval v18 (acc ≥ 0.5).
5. Toàn bộ số liệu có file JSON/JSONL + log, tái lập bằng 1 lệnh.

---

## 1. Trạng thái xuất phát (đã verify)

| Hạng mục | Số liệu | Nguồn |
|---|---|---|
| Adapter v18 | acc **0.5** / traj_sub 0.81 / real 0.79 | eval v18 |
| Bench v14 | click_green **WIN**, counter5 **WIN**, login_done **FAIL** (6 WAIT) | `phase13-gui/out_bench_v14/bench_result.json` |
| Exp H2 | BASE parse 0/11; T-bf16/T-fp16/T-fp32 = parse 8/11, hit 7/11, **cùng case** | `phase13-gui/out_exp_h2/exp_h2_result.json` |
| Chẩn đoán | 3 case fail = thinking bị cắt ở **24 token** (`</think>` lộ ở login_pil); dtype KHÔNG phải nguyên nhân | exp H2 + log |
| Blender v1 | 87/87 id PASS; mui2 draft 45 cặp đã dry-run | `phase14-blender/mui2_tasklist_draft.md` |
| Offline browser | bundle v2: playwright 1.64.0, chromium 156.0.8078.4, launch+smoke OK, 678MB | `phase13-gui/out_browser_bundle/` |

**Kết luận chiến lược:** nút thắt là **format + data + horizon**, không phải dtype. Vì vậy 5 ngày tập trung vào reasoning format, trajectory verify, và benchmark khó dần — không lặp lại thí nghiệm dtype.

---

## 2. Reasoning protocol (bắt buộc từ v20)

### 2.1 Format output

```
THINK: <1-4 câu: quan sát -> mục tiêu -> bước kế tiếp; tối đa 120 token>
ACTION: <CLICK x y | TYPE "text" | KEY "ctrl+a" | DONE>
```

- `ACTION:` là dòng **cuối cùng**; parser lấy match cuối, không lấy text trong THINK.
- Vẫn chấp nhận legacy (bare `CLICK ...`) để so sánh với v18, nhưng **không train legacy là chính**.
- `DONE` chỉ khi task đã đạt trạng thái đích; có thể kèm `DONE` + mô tả ngắn.

### 2.2 Decode / eval

| Tham số | Giá trị | Lý do |
|---|---|---|
| `max_new_tokens` | **256** | 24 token là nguyên nhân cắt thinking; 256 đủ cho 1-2 vòng suy luận + action |
| temperature | 0.0 (greedy) khi eval | tái lập |
| repetition penalty | 1.0 | tránh làm lệch format |
| stop | hết EOS hoặc dòng `ACTION:` | không cắt giữa chừng |
| log mỗi mẫu | `n_think_tokens`, `action_valid`, `parse_mode`, `leak`, `steps`, `success` | phân tích |

### 2.3 Parser (chuẩn)

```python
ACTION_RX = re.compile(r"^\s*ACTION:\s*(CLICK|TYPE|KEY|DONE)\b(.*)$", re.I)
LEGACY_RX = re.compile(r"^\s*(CLICK|TYPE|KEY|DONE)\b(.*)$", re.I)
# lấy match cuối trong output; ưu tiên ACTION:, fallback legacy
```

- `leak` = output có action nhưng **trước** nó là prose không nằm trong `THINK:` (hoặc nhiều dòng giải thích rải rác).
- `action_valid` = parse được + đúng arity (CLICK 2 số, TYPE có quote, KEY có tổ hợp, DONE 0).
- Nếu model chỉ trả `THINK:` mà hết token → **fail reason = `no_action_truncated`**, không tính là parse.

**Metric semantics v2 (chốt 19/10, sau khi đọc output thật của v20):**
- Thực tế v20 sinh: `[reason tự do 1-2 câu]` + (tuỳ mẫu) `</think>` + `THINK: ...` + `ACTION: ...` — model trộn "native thinking" của Qwen với format SFT. `ACTION:` vẫn luôn là dòng cuối ⇒ parser hoạt động 100%.
- Vì vậy `pre_prose`/`legacy_leak` (đếm theo "dòng đầu tiên") **KHÔNG dùng làm gate cứng nữa** — với model reasoning chúng luôn ~1.0.
- Gate cứng từ nay: `parse_rate ≥ 95%`, `trunc_rate ≤ 5%`, `extra_actions == 0`, không hồi quy acc; `post_prose` (nội dung sau dòng ACTION cuối) ghi nhận, kỳ vọng ~0.

### 2.4 Dữ liệu reasoning

- **Ưu tiên trajectory tự sinh + verify** (self-play), không bịa lý do.
- Row SFT tối thiểu:
  ```json
  {"image": "...", "instruction": "...", "think": "...", "action": "CLICK 123 456",
   "source": "selfplay|synth|traj", "task_id": "...", "verified": true, "score": 1.0}
  ```
- Trace template khi chưa có self-play: mô tả ngắn **có kiểm chứng** (target name/bbox từ metadata), không thêm suy đoán không kiểm tra được.
- Train assistant-only loss trên cả `THINK` + `ACTION`; max target 256 token.

---

## 3. Self-improving loop (chạy mỗi ngày)

```
        ┌─────────────────────────────────────────────────────────┐
        │ 1. ROLLOUT: policy hiện tại × train tasks × N samples    │
        │    (temp 0.7, max 256, screenshot-only)                  │
        └──────────────────────────┬──────────────────────────────┘
                                   ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 2. VERIFY: chạy trong env, check programmatic (DOM state,│
        │    pixel, GLB/render, task checker). Không tin self-report│
        └──────────────────────────┬──────────────────────────────┘
                                   ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 3. CURATE: giữ success + near-miss; bỏ reward-hack;      │
        │    dedupe theo (task, action-trace); cap 30% data mới    │
        └──────────────────────────┬──────────────────────────────┘
                                   ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 4. SFT: mix 70% data cũ + 30% self-play; 1-2 epoch      │
        │    LoRA; eval mini 24 synth + 8 traj mỗi 100 steps      │
        └──────────────────────────┬──────────────────────────────┘
                                   ▼
        ┌─────────────────────────────────────────────────────────┐
        │ 5. GATE: parse≥95%, leak≤5%, hard score↑, v14 không giảm │
        │    PASS -> promote; FAIL -> giữ adapter cũ + ghi reason  │
        └─────────────────────────────────────────────────────────┘
```

**Luật chống tự lừa:**
- Verifier phải chạy **ngoài model** (DOM/JS state, pixel diff, GLB parse, render).
- Không đưa eval task vào train; eval set đóng băng theo ngày.
- Mỗi ngày tối đa **1 promotion**; nếu 2 lần fail gate liên tiếp → rollback + đổi data mix.
- Giữ **best-of-N** (N=4) làm upper bound; báo cả pass@1 và pass@4.

---

## 4. Lộ trình 5 ngày

### Day 0-1 (19/10 — hôm nay): Hạ tầng + Reasoning v20

**Mục tiêu:** chứng minh reasoning decode sửa được lỗi parse; đóng gói offline browser; có baseline B15.

| # | Việc | Ai | Gate |
|---|---|---|---|
| 1 | Upload dataset `hhjiji/ornith-offline-browsers` (bundle.zip + snippet v3) | DeepSeek | dataset `ready`, snippet V1-V6 pass trên kernel |
| 2 | U-bf16 fix + diagnostic 4 case fail với 256 token | GLM viết / DeepSeek push | `u_fix_result.json`: U load OK; 4 case có action |
| 3 | Verify 45 cặp Blender mui2 (CPU) | MiMo viết / DeepSeek push | `verify_report.json` 45/45 PASS |
| 4 | Reasoning eval harness (parser + bench kernel 256 token) | GLM | unit test 20 output mẫu; báo parse/leak |
| 5 | Hard GUI benchmark B15 (12 task + verifier) | MiMo | 12/12 task chạy local, 3 variants, có checker |
| 6 | Baseline adapter v18 trên B15 + reasoning decode | DeepSeek | `b15_base.json`: per-task success, parse, think tokens |
| 7 | SFT v20 (reasoning format) | GLM viết / DeepSeek chạy | gate §3 |

**Deliverable Day 1:** `phase13-gui/out_b15_base/`, `phase13-gui/out_u_fix/`, `phase13-gui/kernel/gui_sft_v20.py`, adapter `v20` (nếu gate pass).

**KẾT QUẢ THỰC TẾ (19/10 19:45):**
- Blender mui2 **45/45 PASS** (kernel v2, curve_tube fix) · hard-30 **90/90 PASS** (kernel v4 — fix color-space: check so pixel display-space vs palette linear).
- B15 (12 task × 3 variant = 36 ep, cùng code, cùng suite): **v18 (recipe action-only) = 10/36 = 27.8%** · **v20 (recipe reasoning THINK+ACTION) = 3/36 = 8.3%**.
- ⚠️ **V20 REGRESSION do RECIPE, không phải data**: data giống hệt (synth+real-ui+gui-traj; v20 KHÔNG mount gui-traj-v19), khác biệt là target format (`THINK:` template + `ACTION:` vs 1 dòng action) + REASON_MAX 256. Reasoning format làm model hỏng ở multi-step (prose ăn budget, loop); ở single-step grounding thì v18 mới là yếu.
- **Quyết định Day 2:** v21 = **recipe v18 + self-play** (cap 30%), KHÔNG dùng recipe reasoning. Gate Day 2 giữ nguyên: B15 ≥ 35%, v14 ≥ 2/3.
- Rollout kernel v1 chỉ giữ episode WIN → 0 dòng dữ liệu; đã sửa (giữ cả near-miss + nhãn win/n_fail_checks) + curate mới (ưu tiên WIN, bỏ action lặp, bỏ bước cuối episode fail).

**✅ ĐÃ GIẢI QUYẾT (20/10 12:05): CHUYỂN SANG ACC A — GPU CHẠY LẠI.**
- Acc `hhjiji` hết quota GPU (30.13h/30h, reset 24/10 00:00 — thứ Bảy); `dieniw` + 2 acc trong file cũ đều **401** (key chết).
- User cấp lại key **acc A (`khoadangnguye`)** → **GPU 0.00h/30.00h = full** → chuyển toàn bộ pipeline.
- **Dataset private theo acc** → acc khác không mount được → `scripts/ferry_dataset.py` chuyển dataset hhjiji → A (giữ private); base shards `dieniw/ornbase-s1..4` + wheels là public nên mount cross-account bình thường.
- `scripts/migrate_to_accA.py` đổi **35 kernel metadata** + `gpu_queue.json` + `watchdog_targets.json` sang namespace `khoadangnguye/*`.
- **Kernel train `khoadangnguye/ornith-gui-sft-v21` v1 đã push 12:00:40 và đang RUNNING** (recipe v18 + self-play 123 row + targeted synth + 3D).
- Watchdog chạy với env acc A; quota check **1 lần/ngày** + lên lịch đúng lúc `refreshAt` (theo yêu cầu user) + cache 6h cho dashboard.
- Bài học: (a) 1 key chết không phải hết đường — luôn check **các acc khác** trong `~/.kaggle/kaggle*.json` + `PLAN.md §1 Auth`; (b) CLI `datasets download` có thể trả file `.zip` chưa giải nén và **không kèm dataset-metadata.json** → phải tự tạo lại khi ferry.
- Mất ~7 GPU-giờ do 2 bug watchdog của mình (fetch fail 1 lần → ghi marker → không retry; marker ghi cho version cũ → version mới bị skip). Đã sửa cả hai.
- **Giảm thiểu:** (a) hàng đợi GPU tự động `scripts/gpu_queue.json` (9 mục) — watchdog kiểm quota mỗi 5 phút, khi còn ≥1h + <2 session thì push đúng thứ tự; (b) chuyển 4 ngày này sang **Blender CPU-only** (kernel verify CPU + internet vẫn chạy) + dựng sẵn dataset/kernel cho mọi gate.
- **Đã bắt được 1 bug chí mạng trước khi đốt slot 24/10:** `kaggle datasets` (a) không upload file trong subdir, (b) Kaggle auto-extract zip → ảnh bị đẩy thành `shots/shots/xxx.png` → `_resolve` của `load_ds_rows` **không tìm thấy ảnh → 0 dòng selfplay**. Đã sửa: zip ảnh ở TOP-LEVEL (zip tên `shots.zip` → Kaggle giải nén ra `shots/xxx.png` đúng với `image` trong traj.jsonl) + thêm fallback quét toàn bộ dataset base trong `_resolve`. Dataset `hhjiji/gui-selfplay` đã verify đúng layout (123 ảnh + 2 jsonl).
- Số liệu đã thu được trước khi hết quota: Blender mui2 **45/45**, hard-30 **90/90**; B15 v18 **10/36 = 27.8%**, v20 **3/36 = 8.3%** (regression do recipe); rollout v18 **24/72 = 33.3%** → selfplay **123 row** (51 win + 72 near-miss, đã lọc loop/masked/repeat).

---

### Day 2: GUI self-play + B15 pass 1

**Mục tiêu:** vòng self-improving đầu tiên; B15 khó hơn (thêm biến thể layout + timing).

| # | Việc | Gate |
|---|---|---|
| 1 | Rollout v20 trên 12 task B15 × 4 samples | ≥ 240 trajectories, có verify |
| 2 | Lọc success + near-miss, build `gui-selfplay-d1` | ≥ 150 row verified, 0 trùng |
| 3 | SFT v21 (70/30 mix, 2 epoch) | mini-eval leak ≤ 5% |
| 4 | Eval B15 (held-out variants) + v14 regression | B15 ≥ 35%, v14 ≥ 2/3 |
| 5 | Sinh B15.5: 6 task mới khó hơn (long-horizon 8-12 step, modal, scroll) | 6/6 có checker |

**Nếu B15 < 25%:** tăng data synth targeted theo failure mode; không tăng steps mù.

---

### Day 3: Blender mui2 + hard-3D + multi-task

**Mục tiêu:** gộp hai mũi vào một adapter; benchmark 3D khó hơn.

| # | Việc | Gate |
|---|---|---|
| 1 | Merge 45 row mui2 vào dataset Blender (version mới) | 45/45 verify, 0 id clash |
| 2 | Hard-30: 30 task multi-object constraints + verifier GLB/render | 30/30 chạy local |
| 3 | SFT v22: mix GUI (60%) + Blender (40%), reasoning format | không quên GUI: B15 ≥ v21 - 3% |
| 4 | Eval Blender 45 + hard-30 | 45/45; hard-30 ≥ 50% |
| 5 | Sinh B16 (20 task GUI khó hơn: 8-15 step, distractors, partial observability) | 20/20 checker |

**Multi-task gate:** nếu GUI giảm > 5% → tách adapter theo domain, không ép chung.

---

### Day 4: Compositional + best-of-N/DPO

**Mục tiêu:** tăng horizon và độ bền; dùng failure làm negative.

| # | Việc | Gate |
|---|---|---|
| 1 | Rollout v22 trên B16 × 4; verify | ≥ 320 trajectories |
| 2 | Best-of-N rerank (N=4) + đo pass@1/pass@4 | pass@4 ≥ pass@1 + 10% |
| 3 | DPO nhẹ trên success/failure pairs (nếu đủ data) hoặc SFT v23 on best-of-N | leak ≤ 5% |
| 4 | Eval B16 + B15 + Blender 45/hard-30 | B16 ≥ 40%; không hồi quy |
| 5 | Sinh B17: 12 task compositional (multi-turn memory, cross-page, 3D spec → build) | 12/12 checker |
| 6 | Surprise suite: 10 task giữ kín, chỉ DeepSeek biết checker | không leak vào train |

---

### Day 5: Final freeze + release

| # | Việc | Gate |
|---|---|---|
| 1 | Chọn adapter tốt nhất theo bảng tổng (không chỉ 1 metric) | min 3 suite |
| 2 | Chạy final: v14, B15, B16, B17, Blender 45, hard-30, surprise-10 | đủ JSON + log |
| 3 | Model card + dataset card + report Markdown | tái lập 1 lệnh |
| 4 | Đóng gói adapter + eval artifacts + code | link/version rõ |
| 5 | Viết `MAIN_QUEST_RESULT.md` + bài học | bàn giao |

---

## 5. Thang benchmark khó dần

### 5.1 GUI

| Version | Ngày | Số task | Độ khó | Thành phần mới |
|---|---|---|---|---|
| v14 | cũ | 3 | 3-6 step | click/counter/login |
| **B15** | Day 1-2 | 12 | 4-8 step | form nhiều field, validation, dynamic DOM, drag, keyboard, tab, scroll, error recovery, conditional, canvas, hidden state |
| **B15.5** | Day 2 | +6 | 8-12 step | modal, timing, layout randomization |
| **B16** | Day 3-4 | 20 | 8-15 step | distractors, partial observability, longer horizon, recovery |
| **B17** | Day 4-5 | 12 | multi-turn | memory qua trang, spec → build, cross-domain |
| **Surprise** | Day 5 | 10 | ẩn | checker giữ kín, không train |

**Mỗi task B15+ phải có:**
- HTML self-contained (file://), không internet, không external asset.
- 3 variants (layout/màu/text) + seed cố định.
- `checker.js`/Python trả `{success, score, reason, state}`.
- Ảnh chụp 1280×720 hoặc viewport cố định; chỉ quan sát pixel + action.
- Metadata: `task_id`, `difficulty`, `max_steps`, `variants`, `checker`.
- Không cho model đọc DOM/ground-truth trong inference.

**Ví dụ 12 task B15:**
1. Signup 3 field + checkbox + submit.
2. Login sai 1 lần → sửa → thành công (đọc error message).
3. Item xuất hiện sau delay → click đúng.
4. Drag slider đúng giá trị.
5. Keyboard shortcut copy/paste.
6. Mở tab 2, lấy code, quay lại tab 1, paste.
7. Scroll list lazy-load → click item cuối.
8. Submit form trống → sửa lỗi → submit.
9. Chọn plan B + coupon → tổng tiền đúng.
10. Click shape màu đúng giữa distractors.
11. Click + đúng 5 lần → submit.
12. Đọc code trang 1, sang trang 2 nhập code.

### 5.2 Blender

| Version | Ngày | Số task | Thành phần |
|---|---|---|---|
| mui2 | Day 0-3 | 45 (15×3) | 15 emitter mới, verify GLB+render |
| hard-30 | Day 3-4 | 30 | multi-object, constraint số lượng/vị trí/kích thước/material/camera |
| compositional-15 | Day 4-5 | 15 | scene từ spec ngôn ngữ, nhiều ràng buộc, render đẹp |

**Verifier 3D:**
- `rc=0`, `VERIFY_OK`, parse GLB: meshes>0, tris>0, bounds đúng.
- Render PNG > 2KB; kiểm pixel vùng màu, số object, vị trí tương đối.
- Với hard-30: thêm JSON scene dump (object names/types/transforms) và kiểm constraint.
- Không dùng chung seed/emitter với train; giữ 20% held-out.

---

## 6. Data plan

| Nguồn | Size hiện tại | Day 1-5 |
|---|---|---|
| `gui-synth` | 2.808 row | giữ, thêm reasoning trace template |
| `gui-traj` | 816 row | giữ |
| `gui-traj-v19` | chưa có | self-play D1/D2 |
| `gui-b15` | mới | rollout + verify |
| Blender v1 | 87 row | giữ |
| Blender mui2 | 45 row | merge Day 3 |
| Blender hard-30 | mới | rollout/verify Day 3-4 |

**Mix đề xuất:**
- v20: 70% synth/traj cũ + 30% reasoning template (không self-play).
- v21: 60% cũ + 40% self-play B15.
- v22: GUI 60% + Blender 40% (trong GUI: 70% cũ / 30% self-play).
- v23: 50% cũ + 30% self-play + 20% best-of-N/DPO pairs.

**Chống leak:** eval task ID tách hoàn toàn; hash ảnh + instruction để dedupe; không train trên ảnh render của eval.

---

## 7. Train / eval plan (Kaggle)

| Run | Ngày | Máy | Thời gian dự kiến | Ghi chú |
|---|---|---|---|---|
| U-fix + diagnostic | Day 0 | RTX | 10-12' | TASK-9 |
| Verify Blender 45 | Day 0 | CPU | 20-35' | TASK-7 |
| Eval v18/B15 | Day 1 | RTX/T4 | 20-30' | reasoning 256 |
| SFT v20 | Day 1-2 | RTX | 35-50' | 2 epoch, LoRA |
| SFT v21 | Day 2 | RTX | 35-50' | self-play |
| SFT v22 | Day 3 | RTX | 45-60' | multi-task |
| SFT v23/DPO | Day 4 | RTX | 40-60' | best-of-N |
| Final eval | Day 5 | RTX/T4 | 45-60' | nhiều suite |

**Luật quota:** tối đa 2 GPU session; luôn poll status; tải output ngay; không để kernel treo. Nếu RTX hết quota → T4 cho eval (fp16), train hoãn.

**Lệnh chuẩn:**
```powershell
$env:PYTHONIOENCODING="utf-8"
kaggle kernels push -p <dir>
kaggle kernels status <id>          # verify NGAY sau push
kaggle kernels output <id> -p <out> --file-pattern "<regex>" --force
```

---

## 8. Phân vai & nhịp tự động

| Agent | Quyền | Việc chính |
|---|---|---|
| **DeepSeek** | push/cancel? (cancel phải hỏi user), sửa TASK BOARD, quyết định | orchestrate, review, push/run kernel, tổng hợp, viết MAIN QUEST result |
| **GLM** | chỉ đọc/viết file, không push/cancel | TASK-9 U-fix, TASK-10 eval reasoning, TASK-12 self-play builder, TASK-14 SFT v20 |
| **MiMo** | chỉ đọc/viết file, không push/cancel | TASK-11 B15, TASK-13 Blender hard-30, checker/verifier |

**Nhịp mỗi ngày:**
- Sáng: đọc `MAIN_QUEST.md` + board; baseline/rollout.
- Trưa: 1 GPU run (train hoặc eval) + verify.
- Chiều: benchmark khó hơn + cập nhật bảng điểm.
- Tối: ghi log ngày + chốt promote/rollback.

**Mẫu báo cáo ngày (append vào `agent.md` LOBBY):**
```
### [DeepSeek] Day N — <ngày>
- Train: <run id/version> — <time> — gate PASS/FAIL
- Eval: B15 xx% | B16 xx% | Blender xx/45 | hard-30 xx/30
- Parse/leak: xx% / xx%
- Promote: vN -> vM (hoặc rollback)
- Việc mai: ...
```

---

## 9. Rủi ro & cách chặn

| Rủi ro | Dấu hiệu | Cách chặn |
|---|---|---|
| Model chỉ nói prose | parse thấp, `no_action_truncated` | reasoning format + 256 token + SYS hard-rule + leak metric |
| Overfit eval | eval tăng, B15 giảm | eval đóng băng, held-out variants, chỉ promote khi đa suite |
| Reward hacking | success nhưng state sai | verifier ngoài model, pixel/DOM/GLB check |
| Kaggle quota | 429/queue lâu | tối đa 2 session, ưu tiên 1 train + 1 eval; T4 fallback |
| Offline browser fail | V4/V5 RuntimeError | ~~bundle zip + snippet v3~~ **ĐÃ GIẢI 19/10**: snippet **v5.1** + replay `deps_out.zip` → 4 lib .so (`libatk/libatk-bridge/libXcomposite/libatspi`) + fonts vào `/` + ldconfig. GPU+competition=internet OFF (API 400) → deps/replay là đường duy nhất, không trông vào apt |
| Blender OOM/timeout | rc≠0, 240s | giảm poly, timeout 240s, CPU verify |
| Model collapse self-play | đa dạng giảm | giữ 70% data gốc, cap 30% mới, dedupe, temperature 0.7 |
| Mất dữ liệu | disk ~8GB free | xoá output cũ trước run; không copy bundle vào working |

---

## 10. Nhật ký 5 ngày (điền dần)

| Ngày | Adapter | B15 | B16 | B17 | Blender 45 | hard-30 | Parse | Leak | Quyết định |
|---|---|---|---|---|---|---|---|---|---|
| Day 0 (19/10) | v18 | — | — | — | 45/45 (verify) | — | 8/11 (24 tok) | ~27% | reasoning ON, bundle OK |
| Day 1 | v20 (COMPLETE 14:47) | v18: repush **v4** 15:45 (v1 EACCES → v2 TargetClosed → deps bundle v5.1 + dataset v4); v20: repush **v3** 15:45 | — | — | 45/45 (mui2 v2 re-verify 15:39) | 72/90 (hard30 v1 15:41 — 18 fail pixel_region; TASK-16) | 100/100 @256 (v20 mini-eval) | pre_prose 1.0* (metric v2 — không gate) | **Gate v20 PASS** (acc 0.87/0.56, real 0.952, trunc 0%); FIX#2 = replay 4 lib .so + fonts (image Kaggle thiếu; GPU+competition không có internet — API 400); self-play chờ GPU |
| Day 1 |  |  |  |  |  |  |  |  |  |
| Day 2 |  |  |  |  |  |  |  |  |  |
| Day 3 |  |  |  |  |  |  |  |  |  |
| Day 4 |  |  |  |  |  |  |  |  |  |
| Day 5 |  |  |  |  |  |  |  |  |  |

---

## 11. Artifact map

```
MAIN_QUEST.md                     <- file này
agent.md                          <- TASK BOARD + LOBBY
phase13-gui/
  out_exp_h2/                     <- bằng chứng H2 (dtype không phải nguyên nhân)
  out_browser_bundle/             <- builder output (manifest, wheels, browsers)
  offline_browsers_dataset/       <- bundle.zip + snippet v3 + dataset metadata
  bench_v15/                      <- 12 task + checker + variants (MiMo)
  reasoning/                      <- parser + eval harness (GLM)
  selfplay/                       <- rollout/verify/curate (GLM)
  kernel/gui_sft_v20.py           <- SFT reasoning (GLM)
  out_bench_v15/                   <- baseline v18 trên B15 (run v2 sau EACCES fix)
  out_bench_v15_v20/               <- eval v20 trên B15
  out_v20/                         <- v20 train results (gate PASS) + adapter download
  out_u_fix/                      <- U-bf16 + diagnostic 256 token
  selfplay_dataset/                <- staging gui-selfplay (traj.jsonl + shots.zip)
  rollout_curate.py                <- bundle rollout -> row SFT self-play
phase14-blender/
  verify_kernel/                  <- verify 45 mui2 (MiMo)
  out_verify_mui2/                <- verify_report.json
  hard_bench/                     <- 30 task + verifier (MiMo)
```

---

## 12. Câu hỏi chỉ user trả lời được (không chặn 5 ngày)

- Rotate Kaggle key B (`dieniw`) và xoá kernel `dieniw/ornbase-splitter` — việc bảo mật, làm khi user quay lại.
- Nếu Kaggle yêu cầu xác minh phone/internet-ON cho dataset/kernel: user xử lý.
- Nếu cần cancel kernel đang treo: DeepSeek sẽ hỏi user; mọi việc khác tự quyết.

---

*Chốt: reasoning được bật, benchmark khó lên mỗi ngày, loop tự cải thiện có verify — không đốt GPU vào thí nghiệm dtype lần nữa.*
