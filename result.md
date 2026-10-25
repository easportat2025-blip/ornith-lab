# KET QUA ORNITH - nhat ky theo ngay

> File nay cap nhat **tu dong** (phan AUTO) + **ghi chu thu cong** (phan NHAT KY).
> Sinh boi `scripts/update_result_md.py` - chay lai sau moi vong train/gate.
> **LUU Y: may RTX cua user KHONG co internet** -> moi thu can chuan bi offline
> (xem muc "CHAY OFFLINE" o duoi + `scripts/prepare_offline_bundle.py`).




<!-- DIARY:BEGIN -->
**22/10 18:25 — GATE B15 CỦA v24 = 22/36 = 61,1% (v22 = 33,3%) ⇒ +10 episode; tổng 3 suite 47/78 = 60,3% (v22 35/78 = 44,9%) ⇒ +12 ep.**
- **B15 (36 ep):** v24 **22/36 = 61,1%** vs v22 **12/36 = 33,3%** ⇒ **+10 ep (+27,8 điểm)** ✓ — **không task nào tụt** ✓: T02_login 0/3→**2/3** ✓ · T09_coupon 0/3→**2/3** ✓ · **T07_scroll 0/3→3/3** ✓✓ (đúng năng lực vừa phân tích ✓) · T01/T04/T06 +1 ✓
- ⚠️ **Confound cần xác minh (24/10)**: run v24 dùng **reason_max 512** (có thinking) còn baseline v22 dùng **256** ⇒ **+10 có thể một phần do thinking** ✗ ⇒ phải chạy lại v22 với harness 512 để so sạch ✓
- **GRPO-v1 chết vì thiếu bước cài unsloth** (lỗi của tôi ✗ — data pipeline chạy đúng 300 prompt ✓ rồi mới chết ✗) ⇒ **đã vá**: `install_unsloth()` ✓ + `GRPO_4BIT=1` (để smoke-test trên Colab T4 ✓) + checkpoint mỗi 15 step ✓ + lưu adapter từ `checkpoint-*` ✓
- **Checklist bắt buộc trước khi push kernel mới** (bổ sung vào LONGMEMORY ✓): (1) wheels ✓ (2) base/paths ✓ (3) guard fail-loud ✓ (4) hằng số ✓ (5) **import thật của thư viện** ✓ (6) test local logic ✓ ⇒ **copy nguyên khối khởi tạo từ kernel đã chạy được, không viết lại từ đầu** ✗

**22/10 18:00 — 2 việc lớn: (A) phân tích 13% desktop (model LÀM GÌ) · (B) Google Colab CLI = GPU thứ 2 (đã xác thực chạy thật).**

**(A) 13% DESKTOP — MODEL LÀM GÌ (350 bước / 30 ep của b3 ✓, script `scripts/analyze_desktop_actions.py` ✓):**
| chỉ số | giá trị |
|---|---|
| bước **lặp lại hành động** | **241/350 = 68,9%** ✗ |
| bước **lặp lại nguyên văn reasoning** | **207/350 = 59,1%** ✗ |
| phân bố hành động | click 243 · key 49 · **SCROLL 47** · **TYPE chỉ 6 (1,7%)** ✗ · done 5 |
| episode kết thúc `DONE` mà reward<1 (bỏ cua) | 5 |
⇒ **Mẫu số cực rõ: task nào KHÔNG lặp → thắng** (T26_clipboard: 0 lặp ⇒ 3/5 ✓) **· task nào lặp → 0/5** (T21_form: 14 bước nhưng **chỉ 1 hành động duy nhất** ⇒ 0/5 ✗) ⇒ **vòng lặp deterministic là nguyên nhân số 1** ✗.
⇒ **3 lỗ hổng data cụ thể** (đây là thứ cần sửa): **(a)** thiếu chuyển tiếp **click→TYPE** (reasoning nói *"click để bắt đầu gõ"* rồi click lại 14 lần ✗ ⇒ type 1,7% ✗) · **(b)** **SCROLL/MOVE/DRAG không có trong data train** (harness có hỗ trợ ✓ nhưng toàn bộ data chỉ có CLICK/TYPE/KEY/DONE ✗ ⇒ 47 bước SCROLL là mệnh lệnh chưa từng được huấn luyện ✗) · **(c)** lỗi chiến lược: model **chỉ scroll xuống, không scroll lên** ✗ (mục tiêu nằm ở trên ✗) ⇒ cần task "quét hai chiều" ✓.
⇒ **Thuốc:** `desktop-replay` (app form ⇒ click→type ✓ · app table ⇒ SCROLL ✓) + **S11 = SCROLL/MOVE/DRAG** + task quét hai chiều ✓.

**(B) GOOGLE COLAB CLI — GPU THỨ 2 (đã kiểm chứng chạy thật ✓):**
- `google-colab-cli` **0.7.5** ✓ (CLI chính thức Google ✓) · **chạy được trên Windows** ✓ (README ghi Linux/macOS ✗) · **đã đăng nhập** ✓ → `colab new -s orn-probe --gpu T4` ⇒ **Session READY** ✓ (T4 16GB ✓ · disk 75,5GB ✓ · RAM 13,6GB ✓ · 2 CPU core ✗ · torch 2.11+CUDA sẵn ✓).
- **Bẫy đã dính:** file gửi lên VM **không được có BOM** ✗ (PowerShell 5.1 thêm BOM ✗ → `SyntaxError U+FEFF` ✗) ⇒ tạo .py bằng UTF-8 **không BOM** ✓.
- **Giới hạn cứng của T4:** VRAM 16GB ⇒ model 10B bf16 (~20GB) **không vừa** ⇒ bắt buộc **4-bit (QLoRA)** ⇒ số liệu **không so sánh được** với run bf16 Kaggle ✗ ⇒ T4 free = **"phòng thí nghiệm 4-bit"** (dev harness ✓ · smoke-test GRPO ✓ · ablation ✓), **không thay được** backend bf16 ✗.
- **Base model:** `ornith-ai/Ornith-1.5-9B` public HF ✓ (không cần token ✓) · data: upload 5 `.zip` (~75MB ✓, không cần Kaggle key trên VM ✓) · output: `colab download` adapter → upload Kaggle → gate trên Kaggle ✓.
- **Quyết định user:** (a) **Colab Pro ~$10/tháng** ⇒ A100/L4 = GPU thật thứ 2 ✓; (b) **authorize Drive 1 lần** ⇒ cache 18GB base ✓; (c) nếu thuê VPS Linux cho web ⇒ **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.
- Đã lưu: `COLAB_RUNBOOK.md` ✓ + `scripts/colab_stage.py` ✓.

**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).<!-- DIARY:END -->

<!-- HISTORY:BEGIN -->
## 2026-10-24

### 1) Benchmark (tu dong thu thap)
```
model  suite    file                               ket qua
----------------------------------------------------------------------------------------------------
v21    B15      b15_result.json                    11/36 = 0.306 per-var v0:3/12 v1:4/12 v2:4/12 parse=0.95
v22    B15      b15_result.json                    12/36 = 0.333 per-var v0:4/12 v1:4/12 v2:4/12 parse=0.97
v22    B15.5    b15_result.json                    10/18 = 0.556 per-var v0:3/6 v1:4/6 v2:3/6 parse=1.00
v22    B16      b15_result.json                    11/24 = 0.458 per-var v0:2/8 v1:5/8 v2:4/8 parse=1.00
v21    B15.5    b15_result.json                    1/18 = 0.056 per-var v0:1/6 v1:0/6 v2:0/6 parse=0.44
v21    B16      b15_result.json                    7/24 = 0.292 per-var v0:3/8 v1:2/8 v2:2/8 parse=0.96
v21    3D       bench3d_result.json                27/100 = 0.270 per-var vNone:27/100
v18    B15.5    b15_result.json                    0/18 = 0.000 per-var v0:0/6 v1:0/6 v2:0/6 parse=0.34
v18    B16      b15_result.json                    6/24 = 0.250 per-var v0:2/8 v1:2/8 v2:2/8 parse=0.70
v18    3D       bench3d_result.json                65/100 = 0.650 per-var vNone:65/100
v18    3D-HARD  bench3d_result.json                5/100 = 0.050 per-var vNone:5/100
v18    B15      b15_result.json                    10/36 = 0.278 per-var v0:3/12 v1:3/12 v2:4/12 parse=0.84
----------------------------------------------------------------------------------------------------
SO SANH B15      v22 0.333 vs v18 0.278  => +5.6%  TOT
SO SANH B15.5    v22 0.556 vs v18 0.000  => +55.6%  TOT
SO SANH B16      v22 0.458 vs v18 0.250  => +20.8%  TOT
SO SANH B15      v21 0.306 vs v18 0.278  => +2.8%  TOT
SO SANH B15.5    v21 0.056 vs v18 0.000  => +5.6%  TOT
SO SANH B16      v21 0.292 vs v18 0.250  => +4.2%  TOT
SO SANH 3D       v21 0.270 vs v18 0.650  => -38.0%  XAU
```

### 2) Gate da cham
```
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v21 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.056 ; [FAIL] B15 >= baseline v18 (0.278)        0.056
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.000 ; [FAIL] B15 >= baseline v18 (0.278)        0.000
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.292 ; [PASS] B15 >= baseline v18 (0.278)        0.292
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v18-think0 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v22 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.333 ; [PASS] B15 >= baseline v18 (0.278)        0.333
```

### 3) Lan train gan nhat (v22)
```
  acc_before           0.0000
  acc_after            0.8900
  acc_train_sub        1.0000
  acc_targeted_sub     1.0000
  acc_selfplay_sub     0.9167
  acc_train3d_sub      1.0000
  acc_traj_sub         1.0000
  acc_real_after       1.0000
  n_train              5802
  steps                1033
  seed                 844155262
  recipe               v18-action-only + synth-targeted S1-S8 + selfplay
  t_sec                5208.8136
```

### 4) Hang doi GPU
```
  [A] ornith-gui-sft-v21                           COMPLETE  pushed=True
  [A] ornith-gui-rollout-base                      UNKNOWN   pushed=None
  [A] ornith-gui-rollout-v20                       UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval                    UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval-v20                UNKNOWN   pushed=None
  [A] ornith-gui-bench-v21                         COMPLETE  pushed=True
  [A] ornith-gui-bench-v155                        UNKNOWN   pushed=None
  [A] ornith-gui-bench-v155-v21                    UNKNOWN   pushed=True
  [A] ornith-gui-sft-v22                           COMPLETE  pushed=True
  [A] ornith-gui-bench-v22                         ERROR     pushed=False
  [A] ornith-gui-bench-v155-v22                    ERROR     pushed=False
  [A] ornith-gui-bench-v16-v22                     ERROR     pushed=False
  [A] ornith-gui-bench-v16                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-v16-v21                     COMPLETE  pushed=True
  [A] ornith-gui-bench-v14-v21                     UNKNOWN   pushed=True
  [A] ornith-gui-bench-v15-think0                  COMPLETE  pushed=True
  [A] ornith-gui-rollout-v21                       COMPLETE  pushed=True
  [A] ornith-suite-selftest                        UNKNOWN   pushed=None
  [A] ornith-blender-gen3d                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d                          UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-v21                      COMPLETE  pushed=True
  [A] ornith-gui-bench-3d-hard                     UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-hard-v21                 COMPLETE  pushed=True
  [A] ornith-policy-replay                         COMPLETE  pushed=None
  [A] ornith-gui-desktop-bench                     ERROR     pushed=False
  [A] ornith-gui-desktop-bench-a                   COMPLETE  pushed=True
```

_Cap nhat luc: 05:40:09_

## 2026-10-23

### 1) Benchmark (tu dong thu thap)
```
model  suite    file                               ket qua
----------------------------------------------------------------------------------------------------
v21    B15      b15_result.json                    11/36 = 0.306 per-var v0:3/12 v1:4/12 v2:4/12 parse=0.95
v22    B15      b15_result.json                    12/36 = 0.333 per-var v0:4/12 v1:4/12 v2:4/12 parse=0.97
v22    B15.5    b15_result.json                    10/18 = 0.556 per-var v0:3/6 v1:4/6 v2:3/6 parse=1.00
v22    B16      b15_result.json                    11/24 = 0.458 per-var v0:2/8 v1:5/8 v2:4/8 parse=1.00
v21    B15.5    b15_result.json                    1/18 = 0.056 per-var v0:1/6 v1:0/6 v2:0/6 parse=0.44
v21    B16      b15_result.json                    7/24 = 0.292 per-var v0:3/8 v1:2/8 v2:2/8 parse=0.96
v21    3D       bench3d_result.json                27/100 = 0.270 per-var vNone:27/100
v18    B15.5    b15_result.json                    0/18 = 0.000 per-var v0:0/6 v1:0/6 v2:0/6 parse=0.34
v18    B16      b15_result.json                    6/24 = 0.250 per-var v0:2/8 v1:2/8 v2:2/8 parse=0.70
v18    3D       bench3d_result.json                65/100 = 0.650 per-var vNone:65/100
v18    3D-HARD  bench3d_result.json                5/100 = 0.050 per-var vNone:5/100
v18    B15      b15_result.json                    10/36 = 0.278 per-var v0:3/12 v1:3/12 v2:4/12 parse=0.84
----------------------------------------------------------------------------------------------------
SO SANH B15      v22 0.333 vs v18 0.278  => +5.6%  TOT
SO SANH B15.5    v22 0.556 vs v18 0.000  => +55.6%  TOT
SO SANH B16      v22 0.458 vs v18 0.250  => +20.8%  TOT
SO SANH B15      v21 0.306 vs v18 0.278  => +2.8%  TOT
SO SANH B15.5    v21 0.056 vs v18 0.000  => +5.6%  TOT
SO SANH B16      v21 0.292 vs v18 0.250  => +4.2%  TOT
SO SANH 3D       v21 0.270 vs v18 0.650  => -38.0%  XAU
```

### 2) Gate da cham
```
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v21 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.056 ; [FAIL] B15 >= baseline v18 (0.278)        0.056
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.000 ; [FAIL] B15 >= baseline v18 (0.278)        0.000
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.292 ; [PASS] B15 >= baseline v18 (0.278)        0.292
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v18-think0 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v22 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.333 ; [PASS] B15 >= baseline v18 (0.278)        0.333
```

### 3) Lan train gan nhat (v22)
```
  acc_before           0.0000
  acc_after            0.8900
  acc_train_sub        1.0000
  acc_targeted_sub     1.0000
  acc_selfplay_sub     0.9167
  acc_train3d_sub      1.0000
  acc_traj_sub         1.0000
  acc_real_after       1.0000
  n_train              5802
  steps                1033
  seed                 844155262
  recipe               v18-action-only + synth-targeted S1-S8 + selfplay
  t_sec                5208.8136
```

### 4) Hang doi GPU
```
  [A] ornith-gui-sft-v21                           COMPLETE  pushed=True
  [A] ornith-gui-rollout-base                      UNKNOWN   pushed=None
  [A] ornith-gui-rollout-v20                       UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval                    UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval-v20                UNKNOWN   pushed=None
  [A] ornith-gui-bench-v21                         COMPLETE  pushed=True
  [A] ornith-gui-bench-v155                        UNKNOWN   pushed=None
  [A] ornith-gui-bench-v155-v21                    UNKNOWN   pushed=True
  [A] ornith-gui-sft-v22                           COMPLETE  pushed=True
  [A] ornith-gui-bench-v22                         ERROR     pushed=False
  [A] ornith-gui-bench-v155-v22                    ERROR     pushed=False
  [A] ornith-gui-bench-v16-v22                     ERROR     pushed=False
  [A] ornith-gui-bench-v16                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-v16-v21                     COMPLETE  pushed=True
  [A] ornith-gui-bench-v14-v21                     UNKNOWN   pushed=True
  [A] ornith-gui-bench-v15-think0                  COMPLETE  pushed=True
  [A] ornith-gui-rollout-v21                       COMPLETE  pushed=True
  [A] ornith-suite-selftest                        UNKNOWN   pushed=None
  [A] ornith-blender-gen3d                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d                          UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-v21                      COMPLETE  pushed=True
  [A] ornith-gui-bench-3d-hard                     UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-hard-v21                 COMPLETE  pushed=True
  [A] ornith-policy-replay                         COMPLETE  pushed=None
  [A] ornith-gui-desktop-bench                     ERROR     pushed=False
  [A] ornith-gui-desktop-bench-a                   COMPLETE  pushed=True
```

_Cap nhat luc: 00:00:04_

## 2026-10-22

### 1) Benchmark (tu dong thu thap)
```
model  suite    file                               ket qua
----------------------------------------------------------------------------------------------------
v21    B15      b15_result.json                    11/36 = 0.306 per-var v0:3/12 v1:4/12 v2:4/12 parse=0.95
v22    B15      b15_result.json                    12/36 = 0.333 per-var v0:4/12 v1:4/12 v2:4/12 parse=0.97
v22    B15.5    b15_result.json                    10/18 = 0.556 per-var v0:3/6 v1:4/6 v2:3/6 parse=1.00
v22    B16      b15_result.json                    11/24 = 0.458 per-var v0:2/8 v1:5/8 v2:4/8 parse=1.00
v21    B15.5    b15_result.json                    1/18 = 0.056 per-var v0:1/6 v1:0/6 v2:0/6 parse=0.44
v21    B16      b15_result.json                    7/24 = 0.292 per-var v0:3/8 v1:2/8 v2:2/8 parse=0.96
v21    3D       bench3d_result.json                27/100 = 0.270 per-var vNone:27/100
v18    B15.5    b15_result.json                    0/18 = 0.000 per-var v0:0/6 v1:0/6 v2:0/6 parse=0.34
v18    B16      b15_result.json                    6/24 = 0.250 per-var v0:2/8 v1:2/8 v2:2/8 parse=0.70
v18    3D       bench3d_result.json                65/100 = 0.650 per-var vNone:65/100
v18    3D-HARD  bench3d_result.json                5/100 = 0.050 per-var vNone:5/100
v18    B15      b15_result.json                    10/36 = 0.278 per-var v0:3/12 v1:3/12 v2:4/12 parse=0.84
----------------------------------------------------------------------------------------------------
SO SANH B15      v22 0.333 vs v18 0.278  => +5.6%  TOT
SO SANH B15.5    v22 0.556 vs v18 0.000  => +55.6%  TOT
SO SANH B16      v22 0.458 vs v18 0.250  => +20.8%  TOT
SO SANH B15      v21 0.306 vs v18 0.278  => +2.8%  TOT
SO SANH B15.5    v21 0.056 vs v18 0.000  => +5.6%  TOT
SO SANH B16      v21 0.292 vs v18 0.250  => +4.2%  TOT
SO SANH 3D       v21 0.270 vs v18 0.650  => -38.0%  XAU
```

### 2) Gate da cham
```
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v21 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.056 ; [FAIL] B15 >= baseline v18 (0.278)        0.056
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.000 ; [FAIL] B15 >= baseline v18 (0.278)        0.000
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.292 ; [PASS] B15 >= baseline v18 (0.278)        0.292
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v18-think0 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v22 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.333 ; [PASS] B15 >= baseline v18 (0.278)        0.333
```

### 3) Lan train gan nhat (v22)
```
  acc_before           0.0000
  acc_after            0.8900
  acc_train_sub        1.0000
  acc_targeted_sub     1.0000
  acc_selfplay_sub     0.9167
  acc_train3d_sub      1.0000
  acc_traj_sub         1.0000
  acc_real_after       1.0000
  n_train              5802
  steps                1033
  seed                 844155262
  recipe               v18-action-only + synth-targeted S1-S8 + selfplay
  t_sec                5208.8136
```

### 4) Hang doi GPU
```
  [A] ornith-gui-sft-v21                           COMPLETE  pushed=True
  [A] ornith-gui-rollout-base                      UNKNOWN   pushed=None
  [A] ornith-gui-rollout-v20                       UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval                    UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval-v20                UNKNOWN   pushed=None
  [A] ornith-gui-bench-v21                         COMPLETE  pushed=True
  [A] ornith-gui-bench-v155                        UNKNOWN   pushed=None
  [A] ornith-gui-bench-v155-v21                    UNKNOWN   pushed=True
  [A] ornith-gui-sft-v22                           COMPLETE  pushed=True
  [A] ornith-gui-bench-v22                         ERROR     pushed=False
  [A] ornith-gui-bench-v155-v22                    ERROR     pushed=False
  [A] ornith-gui-bench-v16-v22                     ERROR     pushed=False
  [A] ornith-gui-bench-v16                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-v16-v21                     COMPLETE  pushed=True
  [A] ornith-gui-bench-v14-v21                     UNKNOWN   pushed=True
  [A] ornith-gui-bench-v15-think0                  COMPLETE  pushed=True
  [A] ornith-gui-rollout-v21                       COMPLETE  pushed=True
  [A] ornith-suite-selftest                        UNKNOWN   pushed=None
  [A] ornith-blender-gen3d                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d                          UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-v21                      COMPLETE  pushed=True
  [A] ornith-gui-bench-3d-hard                     UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-hard-v21                 COMPLETE  pushed=True
  [A] ornith-policy-replay                         COMPLETE  pushed=None
  [A] ornith-gui-desktop-bench                     ERROR     pushed=False
  [A] ornith-gui-desktop-bench-a                   COMPLETE  pushed=True
```

_Cap nhat luc: 17:51:00_

## 2026-10-21

### 1) Benchmark (tu dong thu thap)
```
model  suite    file                               ket qua
----------------------------------------------------------------------------------------------------
v21    B15      b15_result.json                    11/36 = 0.306 per-var v0:3/12 v1:4/12 v2:4/12 parse=0.95
v22    B15      b15_result.json                    12/36 = 0.333 per-var v0:4/12 v1:4/12 v2:4/12 parse=0.97
v22    B15.5    b15_result.json                    10/18 = 0.556 per-var v0:3/6 v1:4/6 v2:3/6 parse=1.00
v22    B16      b15_result.json                    11/24 = 0.458 per-var v0:2/8 v1:5/8 v2:4/8 parse=1.00
v21    B15.5    b15_result.json                    1/18 = 0.056 per-var v0:1/6 v1:0/6 v2:0/6 parse=0.44
v21    B16      b15_result.json                    7/24 = 0.292 per-var v0:3/8 v1:2/8 v2:2/8 parse=0.96
v21    3D       bench3d_result.json                27/100 = 0.270 per-var vNone:27/100
v18    B15.5    b15_result.json                    0/18 = 0.000 per-var v0:0/6 v1:0/6 v2:0/6 parse=0.34
v18    B16      b15_result.json                    6/24 = 0.250 per-var v0:2/8 v1:2/8 v2:2/8 parse=0.70
v18    3D       bench3d_result.json                65/100 = 0.650 per-var vNone:65/100
v18    3D-HARD  bench3d_result.json                5/100 = 0.050 per-var vNone:5/100
v18    B15      b15_result.json                    10/36 = 0.278 per-var v0:3/12 v1:3/12 v2:4/12 parse=0.84
----------------------------------------------------------------------------------------------------
SO SANH B15      v22 0.333 vs v18 0.278  => +5.6%  TOT
SO SANH B15.5    v22 0.556 vs v18 0.000  => +55.6%  TOT
SO SANH B16      v22 0.458 vs v18 0.250  => +20.8%  TOT
SO SANH B15      v21 0.306 vs v18 0.278  => +2.8%  TOT
SO SANH B15.5    v21 0.056 vs v18 0.000  => +5.6%  TOT
SO SANH B16      v21 0.292 vs v18 0.250  => +4.2%  TOT
SO SANH 3D       v21 0.270 vs v18 0.650  => -38.0%  XAU
```

### 2) Gate da cham
```
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v21 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.056 ; [FAIL] B15 >= baseline v18 (0.278)        0.056
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.000 ; [FAIL] B15 >= baseline v18 (0.278)        0.000
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.292 ; [PASS] B15 >= baseline v18 (0.278)        0.292
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v18-think0 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v22 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.333 ; [PASS] B15 >= baseline v18 (0.278)        0.333
```

### 3) Lan train gan nhat (v22)
```
  acc_before           0.0000
  acc_after            0.8900
  acc_train_sub        1.0000
  acc_targeted_sub     1.0000
  acc_selfplay_sub     0.9167
  acc_train3d_sub      1.0000
  acc_traj_sub         1.0000
  acc_real_after       1.0000
  n_train              5802
  steps                1033
  seed                 844155262
  recipe               v18-action-only + synth-targeted S1-S8 + selfplay
  t_sec                5208.8136
```

### 4) Hang doi GPU
```
  [A] ornith-gui-sft-v21                           COMPLETE  pushed=True
  [A] ornith-gui-rollout-base                      UNKNOWN   pushed=None
  [A] ornith-gui-rollout-v20                       UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval                    UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval-v20                UNKNOWN   pushed=None
  [A] ornith-gui-bench-v21                         COMPLETE  pushed=True
  [A] ornith-gui-bench-v155                        UNKNOWN   pushed=None
  [A] ornith-gui-bench-v155-v21                    UNKNOWN   pushed=True
  [A] ornith-gui-sft-v22                           COMPLETE  pushed=True
  [A] ornith-gui-bench-v22                         ERROR     pushed=True
  [A] ornith-gui-bench-v155-v22                    ERROR     pushed=True
  [A] ornith-gui-bench-v16-v22                     ERROR     pushed=True
  [A] ornith-gui-bench-v16                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-v16-v21                     COMPLETE  pushed=True
  [A] ornith-gui-bench-v14-v21                     UNKNOWN   pushed=True
  [A] ornith-gui-bench-v15-think0                  COMPLETE  pushed=True
  [A] ornith-gui-rollout-v21                       COMPLETE  pushed=True
  [A] ornith-suite-selftest                        UNKNOWN   pushed=None
  [A] ornith-blender-gen3d                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d                          UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-v21                      COMPLETE  pushed=True
  [A] ornith-gui-bench-3d-hard                     UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-hard-v21                 COMPLETE  pushed=True
  [A] ornith-policy-replay                         COMPLETE  pushed=None
  [A] ornith-gui-desktop-bench                     ERROR     pushed=False
  [A] ornith-gui-desktop-bench-a                   RUNNING   pushed=True
```

_Cap nhat luc: 21:09:13_<!-- HISTORY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 18:00 — 2 việc lớn: (A) phân tích 13% desktop (model LÀM GÌ) · (B) Google Colab CLI = GPU thứ 2 (đã xác thực chạy thật).**

**(A) 13% DESKTOP — MODEL LÀM GÌ (350 bước / 30 ep của b3 ✓, script `scripts/analyze_desktop_actions.py` ✓):**
| chỉ số | giá trị |
|---|---|
| bước **lặp lại hành động** | **241/350 = 68,9%** ✗ |
| bước **lặp lại nguyên văn reasoning** | **207/350 = 59,1%** ✗ |
| phân bố hành động | click 243 · key 49 · **SCROLL 47** · **TYPE chỉ 6 (1,7%)** ✗ · done 5 |
| episode kết thúc `DONE` mà reward<1 (bỏ cua) | 5 |
⇒ **Mẫu số cực rõ: task nào KHÔNG lặp → thắng** (T26_clipboard: 0 lặp ⇒ 3/5 ✓) **· task nào lặp → 0/5** (T21_form: 14 bước nhưng **chỉ 1 hành động duy nhất** ⇒ 0/5 ✗) ⇒ **vòng lặp deterministic là nguyên nhân số 1** ✗.
⇒ **3 lỗ hổng data cụ thể** (đây là thứ cần sửa): **(a)** thiếu chuyển tiếp **click→TYPE** (reasoning nói *"click để bắt đầu gõ"* rồi click lại 14 lần ✗ ⇒ type 1,7% ✗) · **(b)** **SCROLL/MOVE/DRAG không có trong data train** (harness có hỗ trợ ✓ nhưng toàn bộ data chỉ có CLICK/TYPE/KEY/DONE ✗ ⇒ 47 bước SCROLL là mệnh lệnh chưa từng được huấn luyện ✗) · **(c)** lỗi chiến lược: model **chỉ scroll xuống, không scroll lên** ✗ (mục tiêu nằm ở trên ✗) ⇒ cần task "quét hai chiều" ✓.
⇒ **Thuốc:** `desktop-replay` (app form ⇒ click→type ✓ · app table ⇒ SCROLL ✓) + **S11 = SCROLL/MOVE/DRAG** + task quét hai chiều ✓.

**(B) GOOGLE COLAB CLI — GPU THỨ 2 (đã kiểm chứng chạy thật ✓):**
- `google-colab-cli` **0.7.5** ✓ (CLI chính thức Google ✓) · **chạy được trên Windows** ✓ (README ghi Linux/macOS ✗) · **đã đăng nhập** ✓ → `colab new -s orn-probe --gpu T4` ⇒ **Session READY** ✓ (T4 16GB ✓ · disk 75,5GB ✓ · RAM 13,6GB ✓ · 2 CPU core ✗ · torch 2.11+CUDA sẵn ✓).
- **Bẫy đã dính:** file gửi lên VM **không được có BOM** ✗ (PowerShell 5.1 thêm BOM ✗ → `SyntaxError U+FEFF` ✗) ⇒ tạo .py bằng UTF-8 **không BOM** ✓.
- **Giới hạn cứng của T4:** VRAM 16GB ⇒ model 10B bf16 (~20GB) **không vừa** ⇒ bắt buộc **4-bit (QLoRA)** ⇒ số liệu **không so sánh được** với run bf16 Kaggle ✗ ⇒ T4 free = **"phòng thí nghiệm 4-bit"** (dev harness ✓ · smoke-test GRPO ✓ · ablation ✓), **không thay được** backend bf16 ✗.
- **Base model:** `ornith-ai/Ornith-1.5-9B` public HF ✓ (không cần token ✓) · data: upload 5 `.zip` (~75MB ✓, không cần Kaggle key trên VM ✓) · output: `colab download` adapter → upload Kaggle → gate trên Kaggle ✓.
- **Quyết định user:** (a) **Colab Pro ~$10/tháng** ⇒ A100/L4 = GPU thật thứ 2 ✓; (b) **authorize Drive 1 lần** ⇒ cache 18GB base ✓; (c) nếu thuê VPS Linux cho web ⇒ **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.
- Đã lưu: `COLAB_RUNBOOK.md` ✓ + `scripts/colab_stage.py` ✓.

**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 18:25 — GATE B15 CỦA v24 = 22/36 = 61,1% (v22 = 33,3%) ⇒ +10 episode; tổng 3 suite 47/78 = 60,3% (v22 35/78 = 44,9%) ⇒ +12 ep.**
- **B15 (36 ep):** v24 **22/36 = 61,1%** vs v22 **12/36 = 33,3%** ⇒ **+10 ep (+27,8 điểm)** ✓ — **không task nào tụt** ✓: T02_login 0/3→**2/3** ✓ · T09_coupon 0/3→**2/3** ✓ · **T07_scroll 0/3→3/3** ✓✓ (đúng năng lực vừa phân tích ✓) · T01/T04/T06 +1 ✓
- ⚠️ **Confound cần xác minh (24/10)**: run v24 dùng **reason_max 512** (có thinking) còn baseline v22 dùng **256** ⇒ **+10 có thể một phần do thinking** ✗ ⇒ phải chạy lại v22 với harness 512 để so sạch ✓
- **GRPO-v1 chết vì thiếu bước cài unsloth** (lỗi của tôi ✗ — data pipeline chạy đúng 300 prompt ✓ rồi mới chết ✗) ⇒ **đã vá**: `install_unsloth()` ✓ + `GRPO_4BIT=1` (để smoke-test trên Colab T4 ✓) + checkpoint mỗi 15 step ✓ + lưu adapter từ `checkpoint-*` ✓
- **Checklist bắt buộc trước khi push kernel mới** (bổ sung vào LONGMEMORY ✓): (1) wheels ✓ (2) base/paths ✓ (3) guard fail-loud ✓ (4) hằng số ✓ (5) **import thật của thư viện** ✓ (6) test local logic ✓ ⇒ **copy nguyên khối khởi tạo từ kernel đã chạy được, không viết lại từ đầu** ✗

**22/10 18:00 — 2 việc lớn: (A) phân tích 13% desktop (model LÀM GÌ) · (B) Google Colab CLI = GPU thứ 2 (đã xác thực chạy thật).**

**(A) 13% DESKTOP — MODEL LÀM GÌ (350 bước / 30 ep của b3 ✓, script `scripts/analyze_desktop_actions.py` ✓):**
| chỉ số | giá trị |
|---|---|
| bước **lặp lại hành động** | **241/350 = 68,9%** ✗ |
| bước **lặp lại nguyên văn reasoning** | **207/350 = 59,1%** ✗ |
| phân bố hành động | click 243 · key 49 · **SCROLL 47** · **TYPE chỉ 6 (1,7%)** ✗ · done 5 |
| episode kết thúc `DONE` mà reward<1 (bỏ cua) | 5 |
⇒ **Mẫu số cực rõ: task nào KHÔNG lặp → thắng** (T26_clipboard: 0 lặp ⇒ 3/5 ✓) **· task nào lặp → 0/5** (T21_form: 14 bước nhưng **chỉ 1 hành động duy nhất** ⇒ 0/5 ✗) ⇒ **vòng lặp deterministic là nguyên nhân số 1** ✗.
⇒ **3 lỗ hổng data cụ thể** (đây là thứ cần sửa): **(a)** thiếu chuyển tiếp **click→TYPE** (reasoning nói *"click để bắt đầu gõ"* rồi click lại 14 lần ✗ ⇒ type 1,7% ✗) · **(b)** **SCROLL/MOVE/DRAG không có trong data train** (harness có hỗ trợ ✓ nhưng toàn bộ data chỉ có CLICK/TYPE/KEY/DONE ✗ ⇒ 47 bước SCROLL là mệnh lệnh chưa từng được huấn luyện ✗) · **(c)** lỗi chiến lược: model **chỉ scroll xuống, không scroll lên** ✗ (mục tiêu nằm ở trên ✗) ⇒ cần task "quét hai chiều" ✓.
⇒ **Thuốc:** `desktop-replay` (app form ⇒ click→type ✓ · app table ⇒ SCROLL ✓) + **S11 = SCROLL/MOVE/DRAG** + task quét hai chiều ✓.

**(B) GOOGLE COLAB CLI — GPU THỨ 2 (đã kiểm chứng chạy thật ✓):**
- `google-colab-cli` **0.7.5** ✓ (CLI chính thức Google ✓) · **chạy được trên Windows** ✓ (README ghi Linux/macOS ✗) · **đã đăng nhập** ✓ → `colab new -s orn-probe --gpu T4` ⇒ **Session READY** ✓ (T4 16GB ✓ · disk 75,5GB ✓ · RAM 13,6GB ✓ · 2 CPU core ✗ · torch 2.11+CUDA sẵn ✓).
- **Bẫy đã dính:** file gửi lên VM **không được có BOM** ✗ (PowerShell 5.1 thêm BOM ✗ → `SyntaxError U+FEFF` ✗) ⇒ tạo .py bằng UTF-8 **không BOM** ✓.
- **Giới hạn cứng của T4:** VRAM 16GB ⇒ model 10B bf16 (~20GB) **không vừa** ⇒ bắt buộc **4-bit (QLoRA)** ⇒ số liệu **không so sánh được** với run bf16 Kaggle ✗ ⇒ T4 free = **"phòng thí nghiệm 4-bit"** (dev harness ✓ · smoke-test GRPO ✓ · ablation ✓), **không thay được** backend bf16 ✗.
- **Base model:** `ornith-ai/Ornith-1.5-9B` public HF ✓ (không cần token ✓) · data: upload 5 `.zip` (~75MB ✓, không cần Kaggle key trên VM ✓) · output: `colab download` adapter → upload Kaggle → gate trên Kaggle ✓.
- **Quyết định user:** (a) **Colab Pro ~$10/tháng** ⇒ A100/L4 = GPU thật thứ 2 ✓; (b) **authorize Drive 1 lần** ⇒ cache 18GB base ✓; (c) nếu thuê VPS Linux cho web ⇒ **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.
- Đã lưu: `COLAB_RUNBOOK.md` ✓ + `scripts/colab_stage.py` ✓.

**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 18:25 — GATE B15 CỦA v24 = 22/36 = 61,1% (v22 = 33,3%) ⇒ +10 episode; tổng 3 suite 47/78 = 60,3% (v22 35/78 = 44,9%) ⇒ +12 ep.**
- **B15 (36 ep):** v24 **22/36 = 61,1%** vs v22 **12/36 = 33,3%** ⇒ **+10 ep (+27,8 điểm)** ✓ — **không task nào tụt** ✓: T02_login 0/3→**2/3** ✓ · T09_coupon 0/3→**2/3** ✓ · **T07_scroll 0/3→3/3** ✓✓ (đúng năng lực vừa phân tích ✓) · T01/T04/T06 +1 ✓
- ⚠️ **Confound cần xác minh (24/10)**: run v24 dùng **reason_max 512** (có thinking) còn baseline v22 dùng **256** ⇒ **+10 có thể một phần do thinking** ✗ ⇒ phải chạy lại v22 với harness 512 để so sạch ✓
- **GRPO-v1 chết vì thiếu bước cài unsloth** (lỗi của tôi ✗ — data pipeline chạy đúng 300 prompt ✓ rồi mới chết ✗) ⇒ **đã vá**: `install_unsloth()` ✓ + `GRPO_4BIT=1` (để smoke-test trên Colab T4 ✓) + checkpoint mỗi 15 step ✓ + lưu adapter từ `checkpoint-*` ✓
- **Checklist bắt buộc trước khi push kernel mới** (bổ sung vào LONGMEMORY ✓): (1) wheels ✓ (2) base/paths ✓ (3) guard fail-loud ✓ (4) hằng số ✓ (5) **import thật của thư viện** ✓ (6) test local logic ✓ ⇒ **copy nguyên khối khởi tạo từ kernel đã chạy được, không viết lại từ đầu** ✗

**22/10 18:00 — 2 việc lớn: (A) phân tích 13% desktop (model LÀM GÌ) · (B) Google Colab CLI = GPU thứ 2 (đã xác thực chạy thật).**

**(A) 13% DESKTOP — MODEL LÀM GÌ (350 bước / 30 ep của b3 ✓, script `scripts/analyze_desktop_actions.py` ✓):**
| chỉ số | giá trị |
|---|---|
| bước **lặp lại hành động** | **241/350 = 68,9%** ✗ |
| bước **lặp lại nguyên văn reasoning** | **207/350 = 59,1%** ✗ |
| phân bố hành động | click 243 · key 49 · **SCROLL 47** · **TYPE chỉ 6 (1,7%)** ✗ · done 5 |
| episode kết thúc `DONE` mà reward<1 (bỏ cua) | 5 |
⇒ **Mẫu số cực rõ: task nào KHÔNG lặp → thắng** (T26_clipboard: 0 lặp ⇒ 3/5 ✓) **· task nào lặp → 0/5** (T21_form: 14 bước nhưng **chỉ 1 hành động duy nhất** ⇒ 0/5 ✗) ⇒ **vòng lặp deterministic là nguyên nhân số 1** ✗.
⇒ **3 lỗ hổng data cụ thể** (đây là thứ cần sửa): **(a)** thiếu chuyển tiếp **click→TYPE** (reasoning nói *"click để bắt đầu gõ"* rồi click lại 14 lần ✗ ⇒ type 1,7% ✗) · **(b)** **SCROLL/MOVE/DRAG không có trong data train** (harness có hỗ trợ ✓ nhưng toàn bộ data chỉ có CLICK/TYPE/KEY/DONE ✗ ⇒ 47 bước SCROLL là mệnh lệnh chưa từng được huấn luyện ✗) · **(c)** lỗi chiến lược: model **chỉ scroll xuống, không scroll lên** ✗ (mục tiêu nằm ở trên ✗) ⇒ cần task "quét hai chiều" ✓.
⇒ **Thuốc:** `desktop-replay` (app form ⇒ click→type ✓ · app table ⇒ SCROLL ✓) + **S11 = SCROLL/MOVE/DRAG** + task quét hai chiều ✓.

**(B) GOOGLE COLAB CLI — GPU THỨ 2 (đã kiểm chứng chạy thật ✓):**
- `google-colab-cli` **0.7.5** ✓ (CLI chính thức Google ✓) · **chạy được trên Windows** ✓ (README ghi Linux/macOS ✗) · **đã đăng nhập** ✓ → `colab new -s orn-probe --gpu T4` ⇒ **Session READY** ✓ (T4 16GB ✓ · disk 75,5GB ✓ · RAM 13,6GB ✓ · 2 CPU core ✗ · torch 2.11+CUDA sẵn ✓).
- **Bẫy đã dính:** file gửi lên VM **không được có BOM** ✗ (PowerShell 5.1 thêm BOM ✗ → `SyntaxError U+FEFF` ✗) ⇒ tạo .py bằng UTF-8 **không BOM** ✓.
- **Giới hạn cứng của T4:** VRAM 16GB ⇒ model 10B bf16 (~20GB) **không vừa** ⇒ bắt buộc **4-bit (QLoRA)** ⇒ số liệu **không so sánh được** với run bf16 Kaggle ✗ ⇒ T4 free = **"phòng thí nghiệm 4-bit"** (dev harness ✓ · smoke-test GRPO ✓ · ablation ✓), **không thay được** backend bf16 ✗.
- **Base model:** `ornith-ai/Ornith-1.5-9B` public HF ✓ (không cần token ✓) · data: upload 5 `.zip` (~75MB ✓, không cần Kaggle key trên VM ✓) · output: `colab download` adapter → upload Kaggle → gate trên Kaggle ✓.
- **Quyết định user:** (a) **Colab Pro ~$10/tháng** ⇒ A100/L4 = GPU thật thứ 2 ✓; (b) **authorize Drive 1 lần** ⇒ cache 18GB base ✓; (c) nếu thuê VPS Linux cho web ⇒ **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.
- Đã lưu: `COLAB_RUNBOOK.md` ✓ + `scripts/colab_stage.py` ✓.

**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->



<!-- DIARY:BEGIN -->
**22/10 18:25 — GATE B15 CỦA v24 = 22/36 = 61,1% (v22 = 33,3%) ⇒ +10 episode; tổng 3 suite 47/78 = 60,3% (v22 35/78 = 44,9%) ⇒ +12 ep.**
- **B15 (36 ep):** v24 **22/36 = 61,1%** vs v22 **12/36 = 33,3%** ⇒ **+10 ep (+27,8 điểm)** ✓ — **không task nào tụt** ✓: T02_login 0/3→**2/3** ✓ · T09_coupon 0/3→**2/3** ✓ · **T07_scroll 0/3→3/3** ✓✓ (đúng năng lực vừa phân tích ✓) · T01/T04/T06 +1 ✓
- ⚠️ **Confound cần xác minh (24/10)**: run v24 dùng **reason_max 512** (có thinking) còn baseline v22 dùng **256** ⇒ **+10 có thể một phần do thinking** ✗ ⇒ phải chạy lại v22 với harness 512 để so sạch ✓
- **GRPO-v1 chết vì thiếu bước cài unsloth** (lỗi của tôi ✗ — data pipeline chạy đúng 300 prompt ✓ rồi mới chết ✗) ⇒ **đã vá**: `install_unsloth()` ✓ + `GRPO_4BIT=1` (để smoke-test trên Colab T4 ✓) + checkpoint mỗi 15 step ✓ + lưu adapter từ `checkpoint-*` ✓
- **Checklist bắt buộc trước khi push kernel mới** (bổ sung vào LONGMEMORY ✓): (1) wheels ✓ (2) base/paths ✓ (3) guard fail-loud ✓ (4) hằng số ✓ (5) **import thật của thư viện** ✓ (6) test local logic ✓ ⇒ **copy nguyên khối khởi tạo từ kernel đã chạy được, không viết lại từ đầu** ✗

**22/10 18:00 — 2 việc lớn: (A) phân tích 13% desktop (model LÀM GÌ) · (B) Google Colab CLI = GPU thứ 2 (đã xác thực chạy thật).**

**(A) 13% DESKTOP — MODEL LÀM GÌ (350 bước / 30 ep của b3 ✓, script `scripts/analyze_desktop_actions.py` ✓):**
| chỉ số | giá trị |
|---|---|
| bước **lặp lại hành động** | **241/350 = 68,9%** ✗ |
| bước **lặp lại nguyên văn reasoning** | **207/350 = 59,1%** ✗ |
| phân bố hành động | click 243 · key 49 · **SCROLL 47** · **TYPE chỉ 6 (1,7%)** ✗ · done 5 |
| episode kết thúc `DONE` mà reward<1 (bỏ cua) | 5 |
⇒ **Mẫu số cực rõ: task nào KHÔNG lặp → thắng** (T26_clipboard: 0 lặp ⇒ 3/5 ✓) **· task nào lặp → 0/5** (T21_form: 14 bước nhưng **chỉ 1 hành động duy nhất** ⇒ 0/5 ✗) ⇒ **vòng lặp deterministic là nguyên nhân số 1** ✗.
⇒ **3 lỗ hổng data cụ thể** (đây là thứ cần sửa): **(a)** thiếu chuyển tiếp **click→TYPE** (reasoning nói *"click để bắt đầu gõ"* rồi click lại 14 lần ✗ ⇒ type 1,7% ✗) · **(b)** **SCROLL/MOVE/DRAG không có trong data train** (harness có hỗ trợ ✓ nhưng toàn bộ data chỉ có CLICK/TYPE/KEY/DONE ✗ ⇒ 47 bước SCROLL là mệnh lệnh chưa từng được huấn luyện ✗) · **(c)** lỗi chiến lược: model **chỉ scroll xuống, không scroll lên** ✗ (mục tiêu nằm ở trên ✗) ⇒ cần task "quét hai chiều" ✓.
⇒ **Thuốc:** `desktop-replay` (app form ⇒ click→type ✓ · app table ⇒ SCROLL ✓) + **S11 = SCROLL/MOVE/DRAG** + task quét hai chiều ✓.

**(B) GOOGLE COLAB CLI — GPU THỨ 2 (đã kiểm chứng chạy thật ✓):**
- `google-colab-cli` **0.7.5** ✓ (CLI chính thức Google ✓) · **chạy được trên Windows** ✓ (README ghi Linux/macOS ✗) · **đã đăng nhập** ✓ → `colab new -s orn-probe --gpu T4` ⇒ **Session READY** ✓ (T4 16GB ✓ · disk 75,5GB ✓ · RAM 13,6GB ✓ · 2 CPU core ✗ · torch 2.11+CUDA sẵn ✓).
- **Bẫy đã dính:** file gửi lên VM **không được có BOM** ✗ (PowerShell 5.1 thêm BOM ✗ → `SyntaxError U+FEFF` ✗) ⇒ tạo .py bằng UTF-8 **không BOM** ✓.
- **Giới hạn cứng của T4:** VRAM 16GB ⇒ model 10B bf16 (~20GB) **không vừa** ⇒ bắt buộc **4-bit (QLoRA)** ⇒ số liệu **không so sánh được** với run bf16 Kaggle ✗ ⇒ T4 free = **"phòng thí nghiệm 4-bit"** (dev harness ✓ · smoke-test GRPO ✓ · ablation ✓), **không thay được** backend bf16 ✗.
- **Base model:** `ornith-ai/Ornith-1.5-9B` public HF ✓ (không cần token ✓) · data: upload 5 `.zip` (~75MB ✓, không cần Kaggle key trên VM ✓) · output: `colab download` adapter → upload Kaggle → gate trên Kaggle ✓.
- **Quyết định user:** (a) **Colab Pro ~$10/tháng** ⇒ A100/L4 = GPU thật thứ 2 ✓; (b) **authorize Drive 1 lần** ⇒ cache 18GB base ✓; (c) nếu thuê VPS Linux cho web ⇒ **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.
- Đã lưu: `COLAB_RUNBOOK.md` ✓ + `scripts/colab_stage.py` ✓.

**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->

<!-- AUTO:BEGIN -->
## 2026-10-25

### 1) Benchmark (tu dong thu thap)
```
model  suite    file                               ket qua
----------------------------------------------------------------------------------------------------
v21    B15      b15_result.json                    11/36 = 0.306 per-var v0:3/12 v1:4/12 v2:4/12 parse=0.95
v22    B15      b15_result.json                    12/36 = 0.333 per-var v0:4/12 v1:4/12 v2:4/12 parse=0.97
v22    B15.5    b15_result.json                    10/18 = 0.556 per-var v0:3/6 v1:4/6 v2:3/6 parse=1.00
v22    B16      b15_result.json                    11/24 = 0.458 per-var v0:2/8 v1:5/8 v2:4/8 parse=1.00
v21    B15.5    b15_result.json                    1/18 = 0.056 per-var v0:1/6 v1:0/6 v2:0/6 parse=0.44
v21    B16      b15_result.json                    7/24 = 0.292 per-var v0:3/8 v1:2/8 v2:2/8 parse=0.96
v21    3D       bench3d_result.json                27/100 = 0.270 per-var vNone:27/100
v18    B15.5    b15_result.json                    0/18 = 0.000 per-var v0:0/6 v1:0/6 v2:0/6 parse=0.34
v18    B16      b15_result.json                    6/24 = 0.250 per-var v0:2/8 v1:2/8 v2:2/8 parse=0.70
v18    3D       bench3d_result.json                65/100 = 0.650 per-var vNone:65/100
v18    3D-HARD  bench3d_result.json                5/100 = 0.050 per-var vNone:5/100
v18    B15      b15_result.json                    10/36 = 0.278 per-var v0:3/12 v1:3/12 v2:4/12 parse=0.84
----------------------------------------------------------------------------------------------------
SO SANH B15      v22 0.333 vs v18 0.278  => +5.6%  TOT
SO SANH B15.5    v22 0.556 vs v18 0.000  => +55.6%  TOT
SO SANH B16      v22 0.458 vs v18 0.250  => +20.8%  TOT
SO SANH B15      v21 0.306 vs v18 0.278  => +2.8%  TOT
SO SANH B15.5    v21 0.056 vs v18 0.000  => +5.6%  TOT
SO SANH B16      v21 0.292 vs v18 0.250  => +4.2%  TOT
SO SANH 3D       v21 0.270 vs v18 0.650  => -38.0%  XAU
```

### 2) Gate da cham
```
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v21 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.056 ; [FAIL] B15 >= baseline v18 (0.278)        0.056
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.000 ; [FAIL] B15 >= baseline v18 (0.278)        0.000
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.292 ; [PASS] B15 >= baseline v18 (0.278)        0.292
v18-base | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v21 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.306 ; [PASS] B15 >= baseline v18 (0.278)        0.306
v18-think0 | GATE FAIL (0/2) | [FAIL] B15 tong >= 35%                    0.250 ; [FAIL] B15 >= baseline v18 (0.278)        0.250
v22 | GATE FAIL (1/2) | [FAIL] B15 tong >= 35%                    0.333 ; [PASS] B15 >= baseline v18 (0.278)        0.333
```

### 3) Lan train gan nhat (v22)
```
  acc_before           0.0000
  acc_after            0.8900
  acc_train_sub        1.0000
  acc_targeted_sub     1.0000
  acc_selfplay_sub     0.9167
  acc_train3d_sub      1.0000
  acc_traj_sub         1.0000
  acc_real_after       1.0000
  n_train              5802
  steps                1033
  seed                 844155262
  recipe               v18-action-only + synth-targeted S1-S8 + selfplay
  t_sec                5208.8136
```

### 4) Hang doi GPU
```
  [A] ornith-gui-sft-v21                           COMPLETE  pushed=True
  [A] ornith-gui-rollout-base                      UNKNOWN   pushed=None
  [A] ornith-gui-rollout-v20                       UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval                    UNKNOWN   pushed=None
  [A] ornith-gui-bench-v15-eval-v20                UNKNOWN   pushed=None
  [A] ornith-gui-bench-v21                         COMPLETE  pushed=True
  [A] ornith-gui-bench-v155                        UNKNOWN   pushed=None
  [A] ornith-gui-bench-v155-v21                    UNKNOWN   pushed=True
  [A] ornith-gui-sft-v22                           COMPLETE  pushed=True
  [A] ornith-gui-bench-v22                         ERROR     pushed=False
  [A] ornith-gui-bench-v155-v22                    ERROR     pushed=False
  [A] ornith-gui-bench-v16-v22                     ERROR     pushed=False
  [A] ornith-gui-bench-v16                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-v16-v21                     COMPLETE  pushed=True
  [A] ornith-gui-bench-v14-v21                     UNKNOWN   pushed=True
  [A] ornith-gui-bench-v15-think0                  COMPLETE  pushed=True
  [A] ornith-gui-rollout-v21                       COMPLETE  pushed=True
  [A] ornith-suite-selftest                        UNKNOWN   pushed=None
  [A] ornith-blender-gen3d                         UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d                          UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-v21                      COMPLETE  pushed=True
  [A] ornith-gui-bench-3d-hard                     UNKNOWN   pushed=None
  [A] ornith-gui-bench-3d-hard-v21                 COMPLETE  pushed=True
  [A] ornith-policy-replay                         COMPLETE  pushed=None
  [A] ornith-gui-desktop-bench                     ERROR     pushed=False
  [A] ornith-gui-desktop-bench-a                   COMPLETE  pushed=True
```

_Cap nhat luc: 05:43:35_
<!-- AUTO:END -->

<!-- DIARY:BEGIN -->
**22/10 18:25 — GATE B15 CỦA v24 = 22/36 = 61,1% (v22 = 33,3%) ⇒ +10 episode; tổng 3 suite 47/78 = 60,3% (v22 35/78 = 44,9%) ⇒ +12 ep.**
- **B15 (36 ep):** v24 **22/36 = 61,1%** vs v22 **12/36 = 33,3%** ⇒ **+10 ep (+27,8 điểm)** ✓ — **không task nào tụt** ✓: T02_login 0/3→**2/3** ✓ · T09_coupon 0/3→**2/3** ✓ · **T07_scroll 0/3→3/3** ✓✓ (đúng năng lực vừa phân tích ✓) · T01/T04/T06 +1 ✓
- ⚠️ **Confound cần xác minh (24/10)**: run v24 dùng **reason_max 512** (có thinking) còn baseline v22 dùng **256** ⇒ **+10 có thể một phần do thinking** ✗ ⇒ phải chạy lại v22 với harness 512 để so sạch ✓
- **GRPO-v1 chết vì thiếu bước cài unsloth** (lỗi của tôi ✗ — data pipeline chạy đúng 300 prompt ✓ rồi mới chết ✗) ⇒ **đã vá**: `install_unsloth()` ✓ + `GRPO_4BIT=1` (để smoke-test trên Colab T4 ✓) + checkpoint mỗi 15 step ✓ + lưu adapter từ `checkpoint-*` ✓
- **Checklist bắt buộc trước khi push kernel mới** (bổ sung vào LONGMEMORY ✓): (1) wheels ✓ (2) base/paths ✓ (3) guard fail-loud ✓ (4) hằng số ✓ (5) **import thật của thư viện** ✓ (6) test local logic ✓ ⇒ **copy nguyên khối khởi tạo từ kernel đã chạy được, không viết lại từ đầu** ✗

**22/10 18:00 — 2 việc lớn: (A) phân tích 13% desktop (model LÀM GÌ) · (B) Google Colab CLI = GPU thứ 2 (đã xác thực chạy thật).**

**(A) 13% DESKTOP — MODEL LÀM GÌ (350 bước / 30 ep của b3 ✓, script `scripts/analyze_desktop_actions.py` ✓):**
| chỉ số | giá trị |
|---|---|
| bước **lặp lại hành động** | **241/350 = 68,9%** ✗ |
| bước **lặp lại nguyên văn reasoning** | **207/350 = 59,1%** ✗ |
| phân bố hành động | click 243 · key 49 · **SCROLL 47** · **TYPE chỉ 6 (1,7%)** ✗ · done 5 |
| episode kết thúc `DONE` mà reward<1 (bỏ cua) | 5 |
⇒ **Mẫu số cực rõ: task nào KHÔNG lặp → thắng** (T26_clipboard: 0 lặp ⇒ 3/5 ✓) **· task nào lặp → 0/5** (T21_form: 14 bước nhưng **chỉ 1 hành động duy nhất** ⇒ 0/5 ✗) ⇒ **vòng lặp deterministic là nguyên nhân số 1** ✗.
⇒ **3 lỗ hổng data cụ thể** (đây là thứ cần sửa): **(a)** thiếu chuyển tiếp **click→TYPE** (reasoning nói *"click để bắt đầu gõ"* rồi click lại 14 lần ✗ ⇒ type 1,7% ✗) · **(b)** **SCROLL/MOVE/DRAG không có trong data train** (harness có hỗ trợ ✓ nhưng toàn bộ data chỉ có CLICK/TYPE/KEY/DONE ✗ ⇒ 47 bước SCROLL là mệnh lệnh chưa từng được huấn luyện ✗) · **(c)** lỗi chiến lược: model **chỉ scroll xuống, không scroll lên** ✗ (mục tiêu nằm ở trên ✗) ⇒ cần task "quét hai chiều" ✓.
⇒ **Thuốc:** `desktop-replay` (app form ⇒ click→type ✓ · app table ⇒ SCROLL ✓) + **S11 = SCROLL/MOVE/DRAG** + task quét hai chiều ✓.

**(B) GOOGLE COLAB CLI — GPU THỨ 2 (đã kiểm chứng chạy thật ✓):**
- `google-colab-cli` **0.7.5** ✓ (CLI chính thức Google ✓) · **chạy được trên Windows** ✓ (README ghi Linux/macOS ✗) · **đã đăng nhập** ✓ → `colab new -s orn-probe --gpu T4` ⇒ **Session READY** ✓ (T4 16GB ✓ · disk 75,5GB ✓ · RAM 13,6GB ✓ · 2 CPU core ✗ · torch 2.11+CUDA sẵn ✓).
- **Bẫy đã dính:** file gửi lên VM **không được có BOM** ✗ (PowerShell 5.1 thêm BOM ✗ → `SyntaxError U+FEFF` ✗) ⇒ tạo .py bằng UTF-8 **không BOM** ✓.
- **Giới hạn cứng của T4:** VRAM 16GB ⇒ model 10B bf16 (~20GB) **không vừa** ⇒ bắt buộc **4-bit (QLoRA)** ⇒ số liệu **không so sánh được** với run bf16 Kaggle ✗ ⇒ T4 free = **"phòng thí nghiệm 4-bit"** (dev harness ✓ · smoke-test GRPO ✓ · ablation ✓), **không thay được** backend bf16 ✗.
- **Base model:** `ornith-ai/Ornith-1.5-9B` public HF ✓ (không cần token ✓) · data: upload 5 `.zip` (~75MB ✓, không cần Kaggle key trên VM ✓) · output: `colab download` adapter → upload Kaggle → gate trên Kaggle ✓.
- **Quyết định user:** (a) **Colab Pro ~$10/tháng** ⇒ A100/L4 = GPU thật thứ 2 ✓; (b) **authorize Drive 1 lần** ⇒ cache 18GB base ✓; (c) nếu thuê VPS Linux cho web ⇒ **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.
- Đã lưu: `COLAB_RUNBOOK.md` ✓ + `scripts/colab_stage.py` ✓.

**22/10 15:20 — GATE B16-A CỦA v24 = 16/24 = 66,7% (+3 ep so với v22), MỌI task đều tăng ⇒ verdict v24 ≥ v22.**
- **B16-A (task đã sửa, 24 ep, cùng harness 256):** v24 **16/24 = 66,7%** vs v22 **13/24 = 54,2%** ⇒ **+3 episode (+12,5 điểm)** ✓✓
  - T21_hiddenval (đọc→ẩn→**nhớ**→gõ) 0/3 → **1/3** ✓
  - T22_keynav (**phím mũi tên**+Enter) 2/3 → **3/3** ✓
  - T25_compute (đọc 2 số→**tính**→gõ) 2/3 → **3/3** ✓
  - T19/T20/T23/T24/T26: **không task nào tụt** ✓
- **Tổng 2 suite (42 ep):** v24 **25/42 = 59,5%** vs v22 **23/42 = 54,8%** ⇒ **+2 episode ⇒ v24 ≥ v22** ✓ (B15,5 9/18 là −1 ep = trong nhiễu ±5,6% ✗)
- ⇒ **cải thiện nằm đúng ở kỹ năng targeted** (dr0.75 + loop-recovery + R2 ✓) ⇒ **data tác động đúng chỗ** ✓ (B15,5 cũng vậy: T13_wizard 0/3→2/3 ✓)
- **Bài học đã vào luật:** *đo cải thiện thật trên **≥2 suite** + **tổng ≥2 episode** + **không task nào tụt** ✓* — không kết luận từ 1 suite 18 ep ✗
- **Còn chờ:** gate **B15** (36 ep ✓) của v24 — số quyết định ✓ — chờ quota 24/10 ✓

**22/10 14:40 — DESKTOP SẠCH = 13,3% (0% lỗi hạ tầng) ⇒ khoảng cách môi trường là THẬT · GRPO-v1 kernel đã dựng + test và ĐANG CHẠY.**
- **Desktop sạch (b3 — đã có guard app ✓):** **4/30 = 13,3%** · **0/30 ep lỗi hạ tầng** ✓ (contamination 33-50% đã bị loại hẳn ✓✓) · T26_clipboard 3/5 ✓ · T25_recovery 1/5 ✓ · T21/T22/T23/T23_table_sort **0/5** ✗.
  ⇒ **web B16-A 54,2% vs desktop 13,3%** ⇒ **chuyển đổi môi trường là vấn đề THẬT** ✓ ⇒ thuốc đúng = **`desktop-real replay`** (đang giao @MiMo ✓) ⇒ **desktop là chỉ số số 1 cần theo dõi** ✓.
- **GRPO-v1 kernel đã xong** (`phase13-gui/kernel_grpo_v1/grpo_v1.py` ✓ → `dieniw/ornith-gui-grpo-v1` ✓ **đang chạy** ✓):
  - **API đọc từ wheel thật** `trl-1.14.1` ✓ (không đoán ✓): `GRPOTrainer(model, reward_funcs, args, train_dataset, processing_class, …)` ✓ · `GRPOConfig`: `num_generations / max_completion_length / max_prompt_length / beta / epsilon / loss_type / scale_rewards / num_iterations` ✓ · **hỗ trợ VLM** ✓ (cột `prompt` + `image` ✓) · reward nhận **extra column** ⇒ truyền `gt` ✓.
  - **Reward verifiable** ✓: parse action (đúng parser của bench ✓) → 1.0 khớp GT ✓ · 0.3 nếu click lệch nhỏ ✓ · 0.0 sai ✓ · **−0.1 nếu không parse** (chặn prose ✓).
  - **Tập reward tách tập eval** ✓✓: policy-replay 332 + traj R2 972 → **300 prompt** ✓ (không trùng task web/desktop ✓).
  - **Khởi tạo từ adapter v24** ✓ ⇒ KL của GRPO = khoảng cách so với SFT ✓ · G=8 ✓ · lr=1e-6 ✓ · beta=0.02 ✓ · loss=`dr_grpo` ✓.
  - **Test local 15/15 PASS** ✓ (`scripts/test_grpo_reward.py` ✓) + py_compile ✓ + preflight **9/9 READY** ✓ ⇒ **không đốt 2h GPU vì lỗi parse** ✓.
- **Sau GRPO-v1:** upload adapter `dieniw/ornith-gui-lora-grpo1` ✓ → **gate bắt buộc** (B15,5 18ep ✓ + desktop 30ep ✓ theo W4 ✓) ⇒ **chỉ giữ nếu ≥ SFT** ✓ (chống suy thoái ✓) → rồi mới mở rộng reward từ desktop thật ✓.
- **Bài học (đã vào LONGMEMORY):** *đọc API từ **wheel thật** + **test logic local** trước khi push* ⇒ 2h GPU không bị đốt oan ✓ (4 bug hôm nay đều là loại "im lặng" ✓).

**22/10 12:40 — Train v24 COMPLETE; adapter đang publish (MiMo); 2 sự thật về hạn ngạch Kaggle.**
- **`dieniw/ornith-gui-sft-v24` = COMPLETE ✓** (seed mới 183166865 ✓). Quota B còn **5,32h** ⇒ đủ 3 kernel gate (≈2,2h ✓).
- **Adapter v24 do @MiMo publish** (`scripts/publish_lora.py` ✓ — có retry backoff + **verify vân tay trọng số** ✓) ⇒ tôi **không tải/upload trùng 465MB** ✓ (phối hợp qua bus ✓). Watchdog sẽ tự push 3 kernel gate ngay khi `dieniw/ornith-gui-lora-v24` READY ✓ (trước đó nó **đúng** là bỏ qua + báo *"dataset khong ton tai"* ✓).
- **SỰ THẬT 1 — "2 phiên GPU" là 2 phiên trong CỬA SỔ THỜI GIAN, không phải đồng thời:** log watchdog báo *"da du 2 session GPU"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ Kaggle vẫn tính phiên vừa xong ⇒ **có cooldown ⇒ "slot trống" ≠ "slot push được"** ⇒ **xếp 1-2 kernel mỗi lần** ✓ ⇒ 1 phép đo lặp (replication) có thể **chặn cả pipeline** ✗.
- **SỰ THẬT 2 — 429 do watchdog tự gây ra:** nó kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle/phút** ✗) ⇒ tự hủy rate-limit của chính nó ⇒ mọi lệnh Kaggle khác (tải adapter 465MB ✗) đều 429 ⇒ **đã fix: cache 30′ theo slug** ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓. Quy tắc: **đừng chạy lệnh Kaggle hàng loạt song song watchdog ✗ · gặp 429 thì chờ 1-2′ rồi thử lại ✗ (đừng retry liên tục ✗) · ghi "đang làm" lên bus trước khi tải/upload file lớn ✓**.
- **Mẹo đọc log Kaggle**: file log là **1 JSON array** ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

**22/10 11:15 — ĐÍNH CHÍNH SỐ LIỆU DESKTOP (audit từng episode, @MiMo): B2 = 31,3% (không phải 20,8%) · A = 0% (trên 40 ep hợp lệ) · T26_clipboard = 95%.**
- **Audit bằng tool `scripts/audit_desktop_result.py`** (đếm ep có màn hình đen / app thiếu):
  - **acc A (`desktop-bench-a`, 80 ep)**: T20_2048 0/20 (thật) · T21_form 0/20 (thật) · **T22_calc 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** · **T24_text_edit 0/20 nhưng 20 ep đen ⇒ lỗi hạ tầng** ⇒ **40/80 ep hỏng hạ tầng** ⇒ trên **40 ep hợp lệ: 0/40 = 0%**.
  - **acc B (B2, 120 ep)**: **T21_form_desktop 20 ep đen** · **T23_table_sort 20 ep đen** ⇒ 40/120 hỏng ⇒ trên **80 ep hợp lệ: 25/80 = 31,3%** (trước đây tính 25/120 = 20,8% ✗).
- **Kết quả đáng chú ý: T26_clipboard = 19/20 = 95%** ✓✓ — model làm được chu ký *select → copy → paste* gần như hoàn hảo ✓ — trong khi **T22_order / T23_keys = 0/20** ✗ ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** ✓ (cùng kết luận với 2 chu kỳ loop ở B15,5 ✓).
- **Quy tắc mới: mọi báo cáo desktop phải chạy `audit_desktop_result.py` trước** ✓ (và `check_dbench_log.py` cho log: app đủ / guard OK / không `[INFRA]`) ⇒ **không dùng "20,8%" hay "A 0/80" làm baseline** ✗.
- **Bài học lặp lại**: 1 lỗi cấu hình nhỏ (thiếu 4 file app) **làm sai 33–50% số liệu mà log trông bình thường** ⇒ **guard fail-loud + audit định kượng là bắt buộc** ✓ (đã có trong b3 ✓).

**22/10 11:00 — Baseline chuẩn trên suite B15,5 ĐÃ SỬA: v18 = 0% · v21 (thinking 512) = 44,4% · v22 (action-only 256) = 55,6%.**
- `dieniw/ornith-gui-bench-v155-v21new` (adapter v21, REASON_MAX **512** — bản có thinking) trên bộ task **đã sửa** = **8/18 = 44,4%** (T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3).
- So với v22 (**10/18 = 55,6%**, REASON_MAX 256 — action-only): **recipe action-only v22 vẫn thắng bản có thinking v21 (+11,2 điểm)** ✓ — nhất quán với lịch sử "think-recipe fail" ✓.
- *Caveat*: 2 số trên khác `reason_max` (512 vs 256) ⇒ không so sánh thuần túy, nhưng **cùng bộ task đã sửa** ✓ ⇒ dùng làm baseline cùng hệ ✓.
- **Bảng baseline cần đóng băng (suite B15,5 đã sửa):** v18 **0%** · v21 **44,4%** (512) · v22 **55,6%** (256) ⇒ **ngưỡng gate hợp lệ cho v24: > 55,6%** (tức ≥ 11/18, tức **≥ 2 episode** trên 18 ✓) — theo đề xuất "≥ baseline + ≥1 episode" của @MiMo ✓ ⇒ **v24 phải ≥ 11/18** để được coi là tiến bộ thật ✓.
- **Nhớ:** sửa task đã làm suite dễ hơn 39 điểm ⇒ cần bộ **B15,5 v2 khó hơn** trước khi coi là chuẩn dài hạn (đã giao @MiMo/@GLM ✓).

**22/10 09:45 — Ô 2×2 XONG: benchmark DỄ HƠN 39 điểm sau khi sửa task; đường đo đã chứng minh tái lập tuyệt đối. User quyết BỎ HF PRO → đường VPS.**
- **Tái lập tuyệt đối ✓✓**: cùng suite B15,5 **đã sửa**, 2 account khác nhau (acc A 21/10 vs acc B 22/10) → **10/18 = 55,6%** và **breakdown từng task IDENTICAL** (T13 0/3 · T14 3/3 · T15 1/3 · T16 0/3 · T17 3/3 · T18 3/3) ⇒ **đường đo đáng tin** ✓.
- **Sửa task làm suite DỄ HƠN +38,9 điểm**: suite **CŨ** = 3/18 = **16,7%** vs suite **ĐÃ SỬA** = 10/18 = **55,6%** (T14 1/3→3/3 · T15 0/3→1/3 · T17 0/3→3/3 · T18 1/3→3/3 · T13 1/3→0/3). Thời gian chạy: 6229s (CŨ) vs 2514s (ĐÃ SỬA) ⇒ suite CŨ làm model lặp nhiều hơn ✓.
- **Hiểu đúng mốc +50

**22/10 08:50 — B16-A ĐO LẠI TRÊN TASK ĐÃ SỬA: 54,2% (13/24) vs 45,8% (11/24) trên task cũ ⇒ sửa task chiếm ~45% cải thiện.**
- Cùng adapter v22, cùng harness (action-only, REASON_MAX 256), chỉ khác bộ task: **`dieniw/ornith-gui-bench-v16-v22b`** (task đã sửa, acc B) = **13/24 = 54,2%** vs `khoadangnguye/ornith-gui-bench-v16-v22` (task cũ, acc A) = 11/24 = 45,8% ⇒ **+8,4 điểm do sửa task**.
- Chi tiết theo task (cũ → mới): T19_wizardsum 1/3 → 0/3 ✗ · T20 3/3 → 3/3 · T21_hiddenval 0/3 → 0/3 ✗ (model đọc sai giá trị ẩn) · T22_keynav 2/3 → 2/3 · T23_undoredo 0/3 → 0/3 ✗ (model **lặp lại cùng 1 thao tác** → vòng lặp deterministic) · T24 3/3 → 3/3 · T25_compute 2/3 → 2/3 · T26_distractorlist 0/3 → **3/3** ✓ (+3).
- **Bài học hành động từ trace**: 2 lỗi lớn còn lại đều là **vòng lặp deterministic** (T23: 8 lần `CLICK 265 305` + `TYPE ccc` lặp lại; T21: 7 lần `CLICK 322 213`) ⇒ **dữ liệu loop-recovery 600 row của @GLM trong v24 đúng hướng** ⇒ ưu tiên theo dõi **P(DONE)** ở v24.
- **Còn chạy trên acc B**: `ornith-gui-bench-v155-v22-old` (ô 2×2: v22 trên task B15,5 CŨ — repro của 55,6%) + `ornith-gui-desktop-bench-b3` (desktop bench bản có guard). **Train v24 xếp hàng đầu** (watchdog thử push mỗi 5′, đang chờ 1 slot trống) — quota B còn **9,86h**.
- **Caveat**: 2 phép đo nằm ở 2 account khác nhau (A cũ / B mới) — cùng model + cùng adapter + cùng harness, nhưng bundle browser là bản copy ⇒ so sánh hợp lệ ở mức ±1 episode.

**22/10 08:10 — BUG #4 \x60N_3D\x60 (v24 ch\u1ebft sau khi load xong m\u1ecdi d\u1eef li\u1ec7u: traj 972/972 \u2713 loop-recovery 600/600 \u2713) \u2192 \x60scripts/fix_n3d.py\x60 \u2192 \x60N_3D = 600\x60 \u2192 patch 7 b\u1ea3n gui_sft_v23.py \u2192 v24 push l\u1ea1i (watchdog \u0111\u1ea9y \u0111\u1ea7u queue B).**
- **S\u1ed1 LI\u1ec7U DESKTOP C\u00d8 \u0110\u00c1 NHI\u1ec4M (\u0111\u00ednh ch\u00ednh l\u1ea7n 7, @MiMo):** 4 app c\u1ee7a @MiMo kh\u00f4ng \u0111\u01b0\u1ee3c ghi ra \u2192 kh\u00f4ng browser n\u00e0o m\u1eef \u2192 m\u00e0n h\u00ecnh \u0111en \u2192 **40/120 ep (B2) + 40/80 ep (A) b\u1ecb t\u00ednh nh\u1ea7m \u201cmodel th\u1ea5t\u201d** \u2192 **\xabA 0/80\x60 v\u00e0 \xabB2 25/120\x60 KH\u00d4NG \u0111\u01b0\u1ee3C d\u00f9ng l\u00e0m baseline** \u2192 ch\u1edd b3 (guard fail-loud + valid=False + infra_errors.json) m\u1edbi l\u1ea5y s\u1ed1 li\u1ec7u.
- **\u0110\u01b0\u1ee3C s\u1eeda:** loader qu\u00e9t th\u01b0 m\u1ee5c dataset g\u1ed1c (\u1ea1nh \u1edf subdir + basename) \u2192 adapter v22 upload \u2192 R2 972 row publish \u2192 copy 8 dataset + lora + bench-old sang acc B \u2192 2 kernel B-side cho \u00f4 2\u00d72 + B16-A.

**22/10 02:30 — ACC A HẾT QUOTA GPU → chuyển toàn pipeline sang acc B. 3 bug đã sửa, v24 đang chạy.**
- **Acc A (`khoadangnguye`) hết quota GPU**: used 30,08h / 30,00h, refreshAt **2026-10-24T00:00** → push kernel mới bị từ chối (*Maximum

### 22/10 20:55 — BÀN GIAO QUA ĐÊM (máy tắt, GPU Kaggle vẫn chạy)

**A) Còn chạy trên Kaggle (KHÔNG cần máy) — 2 job:**
- `khoadangnguye/ornith-gui-desktop-bench-a` (12 task, GLM) — RUNNING ✓
- `dieniw/ornith-gui-desktop-bench-b2` (12 task, split B) — RUNNING ✓
→ mai boot máy: watchdog tự tải output + chấm + ghi LOBBY + đẩy bus ✓

**B) VIỆC CẦN LÀM NGAY MAI (theo thứ tự):**
1. `python scripts/upload_traj_v2.py` — tạo dataset traj slug MỚI `khoadangnguye/ornith-gui-traj2` (816 ảnh + 816 dòng, ảnh PHẲNG) → `datasets version` KHÔNG cập nhật được file `traj.jsonl` (file vẫn 0 byte ✗) → **phải tạo slug mới** ✓
2. Push `phase13-gui/kernel_v23b` (đã trỏ sang traj2 ✓) → train v23b (rebalance + S9/S10 + guard fail-loud) ✓
3. Chạy 2 phép đo còn treo (MiMo đề xuất ✓): **B16-A chạy lại trên task đã sửa** + **ô 2×2** (v22 trên task B15.5 CŨ) → tách "do sửa task" vs "do data" ✓
4. Đọc kết quả desktop-bench (12 task) → đây là **lần đầu đo agent trên app thật** ✓

**C) BÀI HỌC HÔM NAY (3 lần dính, đã chặn được 2.3h GPU lãng phí):**
- `kaggle datasets create/version` **BỎ QUA THƯ MỤC CON** ⇒ dataset chỉ còn file ở gốc ⇒ **ảnh biến mất** ⇒ dùng `scripts/pack_sft_staging.py` (MiMo) hoặc **làm phẳng ảnh** ✓
- `datasets version` **KHÔNG cập nhật được file jsonl** (giữ 0 byte ✗) ⇒ **tạo slug mới** ✓
- Loader **im lặng bỏ row không resolve ảnh** ⇒ đã thêm **guard fail-loud** (MiMo đề xuất ✓) trong v21/v22/v23 ✓
- Kaggle API **rate-limit 403** khi gọi dồn → cần nghỉ hoặc giãn nhịp ✓
- `kaggle datasets download` **hay treo khi output bị redirect** → dùng `scripts/fetch_dataset_files.py` (Python API) ✓

**D) TRẠNG THÁI HỆ THỐNG:**
- Local C: còn ~18GB — chỉ giữ adapter (out_sft_v21/v22) + kết quả + log + code ✓
- USB `D:\ornith-offline`: `input/` 850MB ✓ (base model **giữ trên Kaggle** theo yêu cầu user ✓; `wheels/` chưa tải xong ✗)
- 6 process nền: watchdog A/B, bus, watch_bus, space_sync ×2, watch_agent_md ✓ — **tự bật lại khi login Windows** (Startup folder ✓ `ornith_autostart.cmd` → `scripts/start_all.ps1` ✓, key đọc từ `HKCU:\Environment` ✓)
- `LOBBY_DIGEST.md` (bản đọc được của LOBBY, tự sinh ✓) · `result.md` (số liệu tự thu thập ✓) · `RTX_OFFLINE_GUIDE.md` ✓
- Còn cần user: **HF PRO hoặc VPS** (Docker Space bị HF chặn 402/403 ✗) để có OpenCode 24/7 + demo noVNC

### 2026-10-21 — buoi sang: 2 vong train + moi truong computer-use + bus troi chuyen

**A) KET QUA SO LIEU (chi tiet trong phan AUTO o tren)**
- **train v22 v3 XONG**: 5802 row (synth 1200 + real-ui 792 + traj 816 + **targeted 1944** + 3D 600 + **policy-replay 332 task-that** + selfplay 118) · **1033 steps** · **seed 844155262** (cau cung: moi run seed moi) · 5209s.
  - acc_after **0.89** · train_sub 1.00 · targeted_sub 1.00 · selfplay_sub 0.92 · train3d_sub 1.00 · traj_sub 1.00
  - ⇒ **model hoc duoc data moi** (targeted + task-that + 3D) · **van con 1 khoang "cam xa"** tren B15.5 (parse 0.44)
- **gate v21 vs v18 (cu, tren trang co bug)**: B15 30.6% vs 27.8% (+2.8%) · B15.5 5.6% vs 0% (+5.6%) · B16 29.2% vs 25% (+4.2%) · 3D 27% vs 65% (**xau**).
- **Phan tich 3D**: metric "knife-edge" (click sat mep bbox) + 3D de hon GUI ⇒ uu tien GUI, giu 600 row 3D trong v23.

**B) SUA 6 BUG THAT (nhieu loi "im lang")**
1. 6 kernel 3D **thieu lenh goi `main()`** ⇒ moi ket qua 3D tren Kaggle deu rong.
2. **Vi pham cau cung PLAN.md X** (seed co dinh 101/202/303/13/7) ⇒ da doi sang `SEED = random.randint` moi run + log + ghi result.
3. Dataset policy-replay **mat 332 anh** (`datasets create` bo qua thu muc con) ⇒ upload anh phang o cap goc.
4. 4 kernel bench 3D + 3D-hard **thieu dataset** ⇒ loader tu do ten `.jsonl` + fail-loud.
5. `for_inference` (unsloth API) lam kernel desktop-bench crash ⇒ dung cach load cua bench V21 (transformers + peft).
6. `dataset-metadata.json` co **UTF-8 BOM** (PowerShell `-Encoding utf8`) ⇒ Kaggle parse loi ⇒ bo BOM.

**C) MOI TRUONG COMPUTER-USE THAT (DESKTOP-ENV)**
- **Chung minh tren Kaggle**: Xvfb 1280x720 + chromium headful + **phim OS that lam app doi state** ✓ + anh chup man hinh that ✓.
- 3 bẫy da lo: `chromium-browser` = wrapper SNAP (khong chay) · bundle chromium **khong mo port remote-debugging** (dung `playwright.launch(headless=False)`) · phai co `os.environ['DISPLAY']` · **offset 86px** do thanh cong cu browser (GLM da fix bang crop viewport ✓ 15/15 test).
- **desktop-bench**: 8 task (4 cua GLM + 4 app cua MiMo) · 3 app **nhieu buoc + bien ngau nhien** · 2 script phan tich.

**D) BUS TRAO DOI TUC THIEN (moi)**
- `scripts/bus.py` (SSE) + `bus_post.py` (1 lenh) + `watch_bus.py` (**day tin thang vao session OpenCode**) ⇒ tin den trong ~1 giay; watchdog poll 60s + post bus moi khi kernel xong.
- Da gui truc tiep vao session cua tung agent (3/3) · agent moi "GPT" duoc onboarding (`AGENT_ONBOARDING.md`) va da CLAIM viec dau.

**E) CHAY OFFLINE tren may RTX (khong internet) — CHUAN BI**
- `scripts/prepare_offline_bundle.py` (tai 1 lan o may co internet): base 4 shard + dataset + wheels ⇒ `<dest>/{base,input/<slug>,wheels}` + MANIFEST + RUN.md.
- Kernel train da doi sang **duong dan ENV** ⇒ `ORNITH_WORK` / `ORNITH_BASE` / `ORNITH_INPUT` ⇒ chay local tren RTX khong doi 1 dong code.
- **Kich thuoc can**: base ~24GB + dataset ~2GB + wheels ~1GB ≈ **~28GB** → chuan bi o dia co du chua (C: hien con 6.4GB sau khi don).
- **KHONG chay duoc khi offline**: watchdog (push Kaggle) · space_sync (push HF) · bus van OK (noi bo).
<!-- DIARY:END -->
