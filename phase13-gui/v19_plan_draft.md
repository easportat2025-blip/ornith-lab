# DRAFT — Kế hoạch SFT v19 (mũi browser `phase13-gui`)

> Người viết: **GLM** (helper, model GLM-5.3-Flash Free) · 19/10 · theo **TASK-2** (CLAIM ở LOBBY `agent.md`).
> Bản **NHÁP** để @DeepSeek duyệt — **KHÔNG sửa** `kernel/gui_sft.py` theo file này; nếu duyệt, code v19 làm bằng file MỚI (`gui_sft_v19.py`).
> Mọi push kernel Kaggle đều chờ **user GO** (luật chung).

---

## 0. Mục tiêu v19 (rõ ràng, đo được)

| Chỉ số | v18 | Mục tiêu v19 |
|---|---|---|
| Synthetic held-out — parse | 53/100 = 0.53 | **≥ 0.95** |
| Synthetic held-out — hit | 0.50 | **≥ 0.90** |
| **leak-rate** (metric mới, §5) | ~0.47 (domain synth) | **≤ 0.05 ở mọi domain** |
| traj_sub | 13/16 = 0.8125 | **≥ 0.85** (cố giữ, nhỉnh hơn là tốt) |
| real_after (42 ảnh thật) | 33/42 = 0.786 | **≥ 0.85** |
| train_sub (canary) | 5/12 = 0.417 | **≥ 0.90** |
| Bench e2e (kernel bench) | 2/3 WIN (login chờ tải output) | **3/3 WIN** |

Bộ eval giữ nguyên từng chi tiết (synthetic held-out seed 202 / start 90000, real 42, traj-sub 16) — so thẳng với v18.

---

## 1. Hiện trạng v18 (đã đọc artifact gốc)

Nguồn: `phase13-gui/out_sft_v18/gui_result.json` + `kernel/gui_sft.py` (config v13 chạy dưới tên kernel version 18) + PLAN.md mục 8 + nhật ký 18-19/10.

```json
{"acc_after": 0.5, "acc_train_sub": 0.4167, "acc_traj_sub": 0.8125,
 "acc_real_after": 0.7857, "n_train": 2808, "steps": 500, "t_sec": 2527.8}
```

- Recipe v18: `RESPOND_ONLY=True`, LR 2e-4 cosine, STEPS 500, r64/alpha64, **dropout 0.0**, bs 2×8 (eff 16), wd 0.01, **seed 13**, max_seq 4096, vision frozen, target all-linear (LM); collator `resize="max"`.
- **Epoch thực chạy ≈ 500×16/2808 = 2.84** (vượt mốc "≤2" của LONGMEMORY).
- Môi trường thật: bench v14 (T4, transformers thuần + PeftModel) với adapter v18 **vẫn làm được việc thật** — click_green WIN (1 bước), counter5 WIN (5 bước); nhưng same-ảnh probe (blue square PIL) khác nhau theo phiên/stack: **v8 (RTX): adapter ra prose; v14 (T4): BASE ra prose NHƯNG adapter PARSE OK** (out=`'CLICK 500 446'`, log dòng 187) — cùng ảnh, khác session/stack (tiêu chí cũ "probe phải parse" chặn oan → v14 đổi thành "output khác base").
- Sự việc then chốt: ảnh **traj/real (render thật)** parse tốt (0.81 / 0.79), riêng domain **synthetic PIL "Mock App"** là nơi leak (~50%), NHƯNG trên chính ảnh train domain này cũng hỏng (train_sub 5/12).

## 2. Chẩn đoán — 3 giả thuyết (theo thứ tự khả năng)

### H1 — PHA LOÃNG ANCHOR DOMAIN (khả năng cao nhất) — trục "data"

- Bằng chứng: cùng adapter, cùng run v18 → **traj 0.812 / real 0.786 NHƯNG synth 0.53 (train-sub 0.417 còn thấp hơn eval!)**. Leak tập trung 100% ở domain synth, kể cả ảnh đã học ⇒ không phải overfit "thuộc bài xấu" kinh điển, mà là **anchor CLICK-format bị pha loãng trong phân bố data**.
- So v11: synth thuần 1200 rows, 300 steps (**4.0 epoch**) vẫn parse 100% ⇒ **epoch cao KHÔNG phải kẻ thù chính** khi data thuần; v18 2.84 epoch nhưng data trộn 57% rows domain khác (1.608) mới sập domain synth.
- Hệ quả đề xuất: cần cân lại tỉ lệ/anchor + siết format; KHÔNG cần đổi LR/backbone.

### H2 — DTYPE / MÔI TRƯỜNG RTX (giả thuyết @DeepSeek đặt ra — cần bằng chứng trong log)

- Tip gốc: "v8 trên RTX in prose (~50%) vs T4 parse OK". Vấn đề: hiện chưa tách được 3 biến lồng nhau — (a) dtype/máy RTX-bf16 vs T4-fp32, (b) serving stack Unsloth `for_inference` (kernel train dùng nó) vs transformers-thuần+PeftModel (bench dùng nó), (c) domain ảnh (synth vs thật).
- Các run trước (v8→v14 bench) chưa tách riêng từng biến — (a)(b)(c) luôn đi kèm nhau trong 1 run. v19 phải **gắn matrix tách biến vào log** (§4) — chạy 1 lần, ~10-15 phút, sau đó mọi kết luận về "prose-leak" settled, không cần đoán mờ nữa.
- Nếu sau đó dtype/serving-stack vẫn là thủ phạm thật → hướng xử lý là dùng eval ở serving stack chuẩn của bench (hoặc kẹp metric ở cả 2 stack); recipe train KHÔNG đổi.

### H3 — OVERSTEP trên data trộn (phụ H1, nhỏ hơn)

- 2.84 epoch trộn 3 domain + loss ~0.15 chạm sàn → giai đoạn cuối run có thể đẩy adapter lệch. Checkpoint giữa có thể "ngọt" hơn — chọn qua mini-eval (§4, rẻ: ~1-2'/ckpt trên RTX).
- Ghi chú: luật ≤1.5-2 epoch (LONGMEMORY §0/§2) vẫn tôn trọng, nhưng v18 bổ sung 1 dữ điểm: giảm epoch đơn thuần KHÔNG giải quyết nếu giữ data trộn y nguyên.

---

## 3. Bảng thay đổi cấu hình v18 → v19 (đề xuất)

| Thành phần | v18 | v19 đề xuất | Lý do |
|---|---|---|---|
| synth rows | 1200 (seed 101) | **1200 REGEN, seed MỚI** (giữ template/scale 768×512 để so được; eval held-out seed 202 KHÔNG đụng) | Luật "seed mới mỗi run"; tăng anchor CLICK |
| real-ui rows | 792 | 792 (giữ nguyên) | domain thật, đang ổn |
| traj rows | 816 (18 variants) | 816 giữ + **+600…1000 traj MỚI** gen thêm (login/counter-style, chuỗi click→type→enter→done; mở rộng tham số `?eu/ep/goal/start/req=done` của `gen_traj.py`) | tăng skill multi-step TYPE/KEY/DONE — đang là điểm mạnh 0.81, không được mất |
| Tổng rows | 2808 | **≈ 3400–4000** |  |
| STEPS | 500 (2.84 ep) | **STEPS = 2 × rows / 16** → 425 nếu 3400; 475 nếu 3800; 500 nếu 4000 (khoảng 2.0 epoch: đúng tính trên rows "sạch" sau resolve ảnh) | cân domain, tránh overstep |
| LR | 2e-4 cosine | **giữ 2e-4 cosine** | recipe v10/v11 đã chứng minh; không đổi 2 biến nặng 1 lúc |
| warmup | 10 | 15 | chi tiết nhỏ |
| lora_dropout | 0.0 | **0.05** | chính tắc nhẹ khi thêm data |
| weight_decay | 0.01 | giữ |  |
| rank / alpha | 64 / 64 | giữ |  |
| target_modules | all-linear (LM) | giữ |  |
| vision layers | frozen | giữ |  |
| max_seq_length | 4096 | giữ + guard log "img lon nhat ~X tokens" (bài học ảnh 1440×900 ≈ 1265 img-token) |  |
| batch | 2 × 8 | `per_device_train_batch_size=2`, `gradient_accumulation_steps=8` (giữ nguyên số dùng trong recipe) | giữ ngang |
| seed | 13 | **MỚI mỗi run** (random, GHI vào `gui_result.json`) | LUẬT CỨNG §0 |
| save_steps | 150 | **100** → 4-5 ckpt | chọn điểm ngọt qua mini-eval (§4) |
| `RESPOND_ONLY`, `resize="max"` | True / max | **giữ** | chốt từ v10/v11 |
| SYS prompt | kết thúc bằng "No explanation." | **+ FORMAT hard-rules (xem dưới)** | đòn trực diện cho prose |

SYS v19 (chỉ NỐI thêm vào SYS cũ, không đổi phần trước):

```python
SYS_V19 = SYS + (
    "\nFORMAT (hard rules):\n"
    "- Reply with EXACTLY ONE line total.\n"
    "- The FIRST word MUST be CLICK, TYPE, KEY or DONE.\n"
    "- Never narrate, never plan out loud, never explain."
)
```

Collator/processor/`fix_processor` — giữ nguyên (đã ổn định v8→v18).

## 4. Bằng chứng phải gắn vào log (quan trọng, theo yêu cầu @DeepSeek)

1) **Header kernel** — log ngay đầu: số/tên GPU (T4 hay RTX), default dtype `torch.get_default_dtype()`, dtype của parameter đầu `model.parameters()`, version transformers/unsloth/trl/peft. Mục đích: soi H2 có mặt thật hay không.
2) **Per-domain parse/hit** — thay 1 con số tổng: log bảng riêng synth / real / traj (parse & hit cả hai). Đây là thông tin chốt H1 đúng/sai.
3) **A/B serving+dtype matrix** (1 lần sau train, rẻ): 5 ảnh synth chuẩn + 5 ảnh real cố định × 2 stack serving (Unsloth `for_inference` vs transformers-thuần+PeftModel) — ghi toàn bộ câu trả lời. Kết luận 2 nhánh: stack A ra prose / stack B parse trên CÙNG ảnh ⇒ chứng cứ H2; cả 2 stack prose trên synth NHƯNG cả 2 OK trên real ⇒ chốt H1.
4) **train-sub canary 12 mẫu** + log 10 output fail ĐẦU TIÊN đủ dài — tìm mô-típ lỗi (kiểu "leak ở counter task" của v18).
5) **Mini-EVAL theo ckpt** (save_steps=100): mỗi ckpt đo 24 ảnh synth + 8 ảnh traj (≈1-2') — ra parse; chọn ckpt tốt nhất (tie → chọn ckpt muộn nhất).

## 5. Metric MỚI: leak-rate

- `leak-rate` = tỷ lệ output **không** bắt đầu bằng (CLICK|TYPE|KEY|DONE) (case-insensitive, trim khoảng trắng đầu).
- Đo cho từng bộ eval (synthetic / real / traj / train-canary), ghi vào `gui_result.json`:
  `{"leak_rate_synth": …, "leak_rate_real": …, "leak_rate_traj": …}` — đây là con số mục tiêu chính của v19.
- Số gốc v18: leak-synth ≈ 0.47 (suy ra từ parse 53/100); khi log đầy đủ sẽ tính chính xác cho cả 3 domain.

## 6. Chống overfit (bám sát luật)

- **Epoch ≤ 2.0 chính xác** (tính theo rows sạch); KHÔNG tăng STEPS nếu thiếu rows mới.
- **Checkpoint selection** (§4.5); nếu loss < 0.10 mà leak-rate mini-eval tăng → dùng ckpt TRƯỚC đó (giống kiểu r4 diverge, LONGMEMORY §2).
- Guard NaN đã có sẵn trong code — giữ nguyên.
- Luật Cứng §0: **seed mới + subset shuffle mới** — đã nằm trong đề.
- Không bump rank/alpha/targets — giữ ma trận "vùng an toàn" đã chốt; đổi nhiều biến thuộc run dạng khác.

## 7. Lộ trình thực hiện (ai, thứ tự — KHÔNG tự đi Kaggle)

1. @DeepSeek duyệt plan (sửa gì ghi LOBBY trước, giữ file này nguyên vẹn) và trả lời Q1–Q3 (§9).
2. Helper (GLM nếu được giao): viết **`kernel/gui_sft_v19.py`** = copy `gui_sft.py` + theo §3/§4/§5; file MỚI, không đụng v18.
3. Gen traj v19 MỚI bằng `gen_traj.py` hiện có (oracle Playwright, vài phút local) → jsonl MỚI do DeepSeek đóng gói vào dataset riêng / version riêng (KHÔNG đè dataset cũ) sau khi được GO.
4. User GO → DeepSeek push kernel RTX; follow live log. Thời lượng ~35-40' train + ~15' eval trên RTX Pro 6000; nếu máy giao T4 → chậm ~12 lần, cân nhắc đòi RTX.
5. Chọn ckpt theo gate §0; nếu pass → upload adapter v19 `hhjiji/ornith-gui-lora` (version mới), đăng ma trận log vào LOBBY.
6. Chỉ khi gate §0 đạt toàn bộ (trừ bench) mới đủ điều kiện đẩy bench end-to-end.

## 8. Plan B — nếu v19 lượt 1 vẫn leak > 5%

| Phương án | Thay đổi | Ưu / nhược |
|---|---|---|
| B1: Curriculum 2 giai đoạn | stage A: 250-300 steps CHỈ synth+real-ui (anchor CLICK, LR 2e-4) → stage B: giữ adapter, +100-150 steps đủ data tại LR 5e-5 | đòn mạnh nhất theo H1; hơi phức tạp (thêm 1 lần load/eval) |
| B2: LR 1e-4 + dropout 0.1 | giữ data | rẻ, "trôi chậm" — hợp nếu v19 đã giảm phần lớn (còn leak 5-15%) |
| B3: Rebalance 70/30 | synth 1400 + real 792 : traj 600 | cẩn trọng: thiệt hại traj (đang là 0.81) |
| B4 (dự phòng): custom collator tăng weight token đầu action | code riêng | phức-tạp nhất — chỉ khi B1-B3 thất bại |

## 9. Câu hỏi mở cho @DeepSeek (trả bằng LOBBY — đừng tự đoán)

- **Q1.** "Prose-leak ~50%" tôi hiểu là **cụ thể domain synth** (từ parse 53/100 + train-sub 0.417); trên real/traj fail chỉ ~19-21%. Đúng quy mô? (Nếu leak ~50% cả real/traj thì H1 sai → cần số chi tiết từng domain của v18.)
- **Q2.** Có muốn chạy trước một **"thí nghiệm tách biến"**: serve adapter v18 hiện tại trên kernel RIÊNG (máy nào rảnh dùng máy đó), chạy matrix §4.3 để chốt H1/H2 TRƯỚC khi tốn 1 run v19 (tốn ~10-15' GPU)? Hay gộp matrix vào v19 luôn?
- **Q3.** Với traj MỚI (+600…1000): gen bằng `gen_traj.py` hiện có là đủ, hay mở thêm biến `?viewport=` (4 cỡ màn — tăng tổng quát scale; max_seq 4096 còn dư ngân sách?)?

## 10. Dọn dẹp / phạm vi

- File này là NHÁP của tôi (@GLM); @DeepSeek chỉnh trực tiếp được sau khi RELEASE. Tôi không đụng `gui_sft.py`, `harness.py`, kernels, datasets.
- Mọi đẩy kernel/upload cần USER GO trước (luật chung).
