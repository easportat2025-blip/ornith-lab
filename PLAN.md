## 0. Trạng thái nóng (20/10 12:05) — **ACC CHÍNH = `khoadangnguye`**
- **GPU chạy lại** (acc A còn 29.99h/30h). Kernel train `khoadangnguye/ornith-gui-sft-v21` v1 **RUNNING** (recipe v18 + self-play 123 row + synth targeted S1–S8 + 3D 600 row).
- Acc `hhjiji`: hết quota GPU (reset **thứ Bảy 24/10**). Acc `dieniw`/`phnguynh` + file `kaggle_backup.json`: key chết (401). **Key chỉ truyền qua env var, không ghi file.**
- Dataset **private theo acc** → dataset mới phải ferry sang acc A trước khi kernel mount (`scripts/ferry_dataset.py`).
- Hàng đợi 24/10 **đã chuyển sang acc A** (17 mục) + watchdog tự push khi pre-flight pass.

---

# PLAN — Train Gemma 4 12B làm game + 3D trên Kaggle

> FILE SỐNG: bắt buộc cập nhật sau mỗi bước. Xóa mục nào không cần thiết.
> AGENT MỚI VÀO: đọc `LONGMEMORY.md` trước (kinh nghiệm cứng + lỗi đã gặp).

## 0. Nguyên tắc

- [x] KHÔNG tải weights/dataset về máy local — mọi download chạy trên Kaggle CPU notebook (internet ON)
- [x] KHÔNG ghi API key vào file này hay git — key chỉ truyền qua env var lúc runtime
- [x] Notebook RTX 6000 / L4 chạy offline (internet OFF) — mọi thứ attach sẵn từ Dataset/Model input
- [x] Dọn dẹp: xóa dataset version cũ, kernel thử nghiệm, file tạm ngay khi xong việc

## 1. Auth (xong — 06/10/2026)

- [x] Test 3 acc: A full 30h GPU, B còn 29.78h, C full 30h — cả 3 sống
- [x] Chọn acc chạy chính: **A (khoadangnguye)** — user chốt

## 2. Phase 1 — CPU prep notebook (internet ON, accelerator NONE)

Mục tiêu: tải TẤT CẢ rồi publish thành Kaggle Dataset private.

- [x] Tạo notebook CPU, bật Internet (Settings → Internet ON), KHÔNG attach competition
- [x] Tải wheels offline: `pip download unsloth trl peft transformers datasets accelerate` → `/kaggle/working/wheels/`
  - Thực tế: `unsloth_zoo` + `peft` đã có sẵn trong image → chỉ tải `unsloth` + `trl` (--no-deps), 26.7MB
- [x] Tải data train: `wrayy/pub-instruct-unity.preview`, `vishnuOI/unity-dev-instructions`, mẫu bpy/Three.js tự tổng hợp → `/kaggle/working/data/` (chuẩn Alpaca)
  - Thực tế: unity_pub_instruct 11MB + unity_dev 68MB + blender_seed 6 records tay
- [x] Tải Blender portable Linux (để eval headless ở Phase 3) → `/kaggle/working/tools/`
  - Lần 1 lỗi 403 (urllib không UA) → fix bằng kernel riêng `phase1-tools/`, requests + browser UA → **Blender 5.2.0 linux-x64 366MB**
- [x] Weights Gemma 4 12B: KHÔNG cần tải — attach trực tiếp Kaggle Model `google/gemma-4` vào notebook Phase 2
- [x] Trong notebook chạy (CLI Kaggle có sẵn + đã auth sẵn trong notebook):
  `kaggle datasets init -p /kaggle/working/wheels` → sửa metadata → `kaggle datasets create -p /kaggle/working/wheels`
  lặp lại cho `data/`, `tools/`
- [x] Ghi lại slug 3 dataset vào đây:
  - wheels: `khoadangnguye/gemma12b-wheels` (26.7MB)
  - data: `khoadangnguye/gemma12b-gamedata` (22.4MB: unity_pub_instruct + unity_dev + blender_seed)
  - tools: `khoadangnguye/gemma12b-tools` (384MB: blender-5.2.0-linux-x64.tar.xz)

## Z. HƯỚNG CHUYÊN GAME (user chốt 10/10 — đính chính: BỎ văn/sử/địa/GDCD)

- Mục tiêu: model thuần chuyên gia game (code game/3D/tool), BỎ kiến thức xã hội văn-sử-địa-GDCD (không phải thêm vào).
- Cách làm: (1) data 90%+ game/code/3D/tool; (2) cặp OOD-refusal: hỏi văn sử địa → lịch sự từ chối + lái về game; (3) GIỮ slice tiếng Việt phổ thông (không thì mất luôn tiếng Việt); (4) bỏ qua safety filter (tính sau, user dặn).
- Quên kiến thức không mổ xẻ được từng phần — train hẹp lâu thì điểm tổng quát TỰ rớt (đã thấy r1 86 < base 108). Bench game/3D phải lên, bench tổng quát rớt là đúng ý đồ.

## Y. LUẬT RELEASE (user chốt 10/10/2026)

- Cứ mỗi 4 runs train → merge adapter vào base 1 lần → làm 2 bản: **BF16** (safetensors, train tiếp) + **4-bit** (GGUF Q4_K_M, xài local) → đẩy **public HuggingFace 1 lần** (acc himAgayem).
- HF token KHÔNG ghi vào file/repo — truyền lúc runtime, kernel private.
  - r4 = release đầu tiên theo luật này.
  - Release r4 DONE 10/10: repo public **`himAgayem/gamecraft`** (rename từ gamecraft-r4, redirect giữ) — BF16 7 shards + GGUF Q4_K_M + tokenizer/config patch + README. Bench r4 136/300.
  - TRẠNG THÁI: chờ user test thật trên Unsloth Studio (không gấp). Đây là dự án dài hạn — run 5+ tính sau khi có feedback test.
  - FEEDBACK TEST 10/10 (agent harness, model ta): (1) model KHÔNG biết dùng tool — chỉ nhả text chứ không tự tạo file/chạy lệnh (data train không có tool-calling trajectory nào); (2) bug `canvas.ctx` thay vì `getContext('2d')` (thiếu JS DOM execution-verified data). Hướng run 5: thêm data function-calling + agentic trajectories + JS exec-verify.
  - FEEDBACK TEST 11/10 (task AAPL multi-step): model (a) KHÔNG thinking thật — chỉ kể lại các bước rồi nhảy đáp án; (b) GIẢ VỜ gọi tool bằng văn xuôi ("Gọi công cụ web_search...") thay vì invoke thật; (c) BỊA data (giá 189.95 tự đặt) + kết luận rỗng (số nguyên tố nào tổng ước cũng =1). Cần: data thinking thật (Fable) + data đúng tool-schema của harness + bench tool-use live.
  - HARNESS PROMPT user gửi 11/10: liệt kê tool (search/write_file/execute_python/bash) nhưng KHÔNG thấy đặc tả CÚ PHÁP invoke (format/token nào để gọi?). Không có format thì model nào cũng chỉ biết kể. Chờ user gửi phần format + 1 transcript mẫu đúng.
  - RÕ 11/10: harness là Unsloth Studio chat thuần + KHÔNG có system prompt → không tồn tại kênh tool thật, model roleplay tool-talk học từ data agentic. Muốn tool thật phải qua agent harness (OpenCode/MCP...) + system prompt định nghĩa format invoke. Tôi viết system prompt này, train đúng format đó.
  - XEM XÉT ĐỔI BASE 11/10 (user đề xuất Ornith-1.5-9B): `ornith-ai/Ornith-1.5-9B` (MIT, dense 9B, Qwen3.5-arch) + GGUF chính chủ (5M pulls) — thinking `<think>` + tool-call NATIVE, Terminal-Bench 43.1 (gấp đôi Qwen3.5-9B/Gemma4-12B), 262K ctx, Unsloth support. Pilot: user pull GGUF test Studio (giờ + AAPL + 1 game); nếu tool sống thì run 7+ chuyển sang (lineage O1 mới, Gemma r-line đóng băng giữ lại).
  - [x] CHỐT BỎ GEMMA 11/10: kéo base Ornith về Kaggle (kernel `ornith-fetch-base` → dataset `ornith-15-9b-base` 19GB/4 shards verify đủ, public cho B) + Giữ file LICENSE gốc vì MIT. Gemma r-line đóng băng (r4 release + bench giữ nguyên).
  - [x] LOOP ORNITH O1 trên acc B (kernel `dieniw/ornith-looptrain`, T4 đủ cho 9B): fresh LoRA từ base gốc (không merge), 5 game Pygame, 20 turns/phase, ma trận mới mỗi phase, soup cuối. DONE 200 turns/8 phases → soup O1 publish (`dieniw/ornith-adapter-o1`, đủ 3 file).
  - [x] LOOP v2 ĐA-ENGINE + T4-first (v16): code TỰ NHẬN GPU (T4<20GB → batch 8 fp16, RTX → batch 16) + vòng đợi mount + offline-tolerant. Bỏ competition attach (T4 không cần). Đang chạy.
  - v19 RTX: godot parse OK 4/5, 1 pygame rớt do dòng văn xuôi đầu file (strip chưa sạch — fix bản sau, không stop run).
  - [x] LOOP v2 ĐA-ENGINE (v11): mix pygame maze + godot pong + unity enemy-AI + bpy oto + pygame asteroids. Verify trung thực: py full-play, gd boot-parse, cs static, bpy render thật. STATIC_ROWS trộn vào train. Đang chạy.
  - CHỐT 12/10: model duy nhất là ORNITH (bỏ Gemma hoàn toàn, KHÔNG so sánh Gemma vs Ornith). Đang đợi pub O1-soup xong.
  - [x] O1-soup publish xong (`dieniw/ornith-adapter-o1`: adapter 465MB + config tái tạo + info, verify đủ). Dọn local theo luật disk.
  - [x] Bench O1 (kernel `dieniw/ornith-bench-o1`, acc B, T4): base Ornith vs O1-soup, 60 game tasks + 20 computer-control MỚI (sandbox + verify deterministic + denylist), greedy batch-8, thang 400. SCORING.md cập nhật. Đang chạy.
  - TEST 11/10 (Studio, toggle ON, model r6-GGUF): hỏi "mấy giờ rồi" → đáp "10:49 sáng 12/06/2024" (BỊA, không gọi tool). Kết luận: pipeline Studio sống, MODEL không emit tool-call. Fix = train tool-call emission OpenAI-style (Studio backend OpenAI-compatible) + cân nhắc GGUF kèm tool template.
  - PIVOT 11/10 (user): NGỪNG SFT mù. Làm HARNESS tự tạo-tự chơi (`HARNESS_PLAN.md`): model Ornith tạo game ≤5p → XÓA context → autopilot chơi + NHẬN XÉT thật (5 yêu cầu/cycle). Trajectory thu được làm data train sau. Chờ user ra yêu cầu chi tiết.
  - [x] Research xong 11/10 → file `AGENT_SYSPROMPT.md`: chuẩn Hermes `<tool_call>` JSON (vLLM/Ollama/LM Studio đều parse), stack Ollama+OpenCode+MCP, Modelfile mẫu, spec data train (mọi trajectory phải có tool_call + tool_response thật, 10-15% honesty). Chờ user duyệt format rồi đúc data run 7.
  - v4 loi build (target doi ten llama-quantize) + v5 loi convert (transformers 5.x hong tokenizer Gemma). Fix v6: upload BF16 TRUOC khi convert + ha transformers 4.x cho convert.
  - Phat hien: file tokenizer do mình save lai moi la thu hong convert (tokenizer GOC load ngon). BF16 da du tren HF (7 shards). v8: merge lai + de tokenizer goc + bo qua upload BF16 + convert/quant/upload GGUF.
  - Convert llama.cpp gay cung loi ca 2 ban transformers (script tu nap tokenizer kieu la) -> bo duong llama, chuyen Unsloth GGUF tren T4 (kernel `gemma12b-gguf-t4`). Fix: thieu trl/bnb, /tmp+chdir (46GB), load full bf16 + device_map auto dual-T4, tim gguf de quy. v9 dang chay.
  - Unsloth doi weights 16-bit de-quan (khong convert tu bnb) -> v6 load full bf16 (24GB) nen BAT BUOC RTX 96GB (T4 16GB OOM). User tu export Studio thi gap config thieu key (da va). Kernel v6 dang cho.
  - Root cause that: key `extra_special_tokens` dang LIST trong tokenizer_config (transformers 5.x save ra) -> patch truc tiep file tren HF (xoa key, giu nguyen vocab). Kernel stage tool llama (`gemma12b-buildtools` -> dataset `gemma12b-llamatools`) de lam GGUF offline tren RTX: merge GPU -> patch tokenizer -> convert local -> quant -> output -> CPU upload sau.
  - User chốt: rename repo thành `himAgayem/gamecraft` SAU khi upload xong (move_repo qua API, giữ redirect).

## X. YÊU CẦU CỨNG DUY NHẤT (user chốt 07/10/2026)

> **Mỗi lần train: seed mới, ma trận mới — không để một khúc tham số học quá nhiều.**

- PLAN này ngoài câu trên ra đều LINH HOẠT (rank/steps/batch/LR được phép đổi theo từng run, chỉ cần ghi lại).
- Thực thi câu cứng trong script: seed random mỗi run + log seed, adapter init mới từ base mỗi run, subset shuffle mới mỗi run, phân tán target khắp model.

## 3. Phase 2 — Train trên RTX 6000 (internet OFF, attach ARC-AGI-3)

- [ ] Tạo notebook attach competition ARC-AGI-3, Accelerator = RTX 6000, Internet OFF
- [ ] Add input: 3 dataset Phase 1 + model `google/gemma-4`
  - Gemma 12B đã verify 06/10/2026: variation `transformers/gemma-4-12b-it` v2, full precision (model.safetensors 23.9GB + tokenizer + chat_template) — attach path `google/gemma-4/transformers/gemma-4-12b-it/2`, KHÔNG tải
- [ ] Cài offline: `pip install --no-index --find-links /kaggle/input/<wheels-slug> unsloth`
- [ ] QLoRA config: rank 32–64, alpha = rank, lr 2e-4, seq 2048–4096, batch 2 + accum 4, AdamW 8-bit, target all-linear + tuân thủ YÊU CẦU CỨNG #1
- [ ] LƯU Ý RTX: CLI docs chỉ liệt kê machine_shape T4/L4/TPU — RTX 6000 chưa chắc chọn được qua CLI + đòi attach competition ARC-AGI-3 (acc A phải accept rules). Phương án: smoke-train T4x2 qua CLI trước, RTX bật trên web UI sau
- [ ] Train → lưu adapter ra `/kaggle/working/` → Save & Run All → version mới
  - v1-v3: lỗi mount /kaggle/input (layout mới lồng datasets/models/competitions) + nhầm wheels competition → fix discovery đệ quy, chọn đúng dir có unsloth/trl
  - v4-v5: GPU image thiếu unsloth_zoo + bitsandbytes → fallback PEFT-bnb + wheels v2/v3 (bnb 0.50.2 + trl)
  - v6: trl 1.14.1 bỏ arg `tokenizer` → v7 dùng `processing_class` (tự thích nghi 2 bản). Weights load OK 677/677
- [x] User đổi accelerator sang RTX 6000 trên web UI (user xác nhận run hiện tại chạy trên RTX, ~2s/step)
- [x] v8/v9: wheels v4 (unsloth+zoo OK) → backend unsloth chạy được, train 300 steps, loss log mỗi 10 steps (1.5 → 1.2...), tốc độ ~2s/step
- [x] Run 1 DONE 07/10/2026 trên RTX: adapter `gemma12b-lora-r1` (adapter_model.safetensors + config + tokenizer + run_info.json) đã lưu trong kernel output
- [x] Run 2 (user chốt, đẩy 07/10/2026): r=128, batch 8 (4x2), LR 1e-4, dropout 0.1, subset 12k shuffle mới, steps 1500, adapter mới từ base → output `gemma12b-lora-r2`. User CANCEL giữa chừng trên web.
- [x] User đổi hướng 07/10: MERGE r1 thẳng vào base rồi train LoRA mới r128 (v17). Adapter mới + seed mới + subset mới → đúng câu cứng. Kernel attach thêm dataset adapter-r1. Đang QUEUED chờ GPU.
- [x] Merge OK (seed 321006250, r128 fresh, trl mới tự thích nghi processing_class). Đang train 1500 steps.
- [x] Run 2 DONE 07/10: adapter `gemma12b-lora-r2` trong kernel output (merge r1→base + LoRA r128 mới).
- [ ] Publish r2 thành dataset + kernel bench game: V-GameGym-style (Pygame execute+smoke) / Mage-style (Unity 4-axis lite) / CodeGen-3D-style (bpy→Blender render)
  - [x] Data run 4 DONE: unity-code đặc 13.102 + bpy procedural 300/300 pass Blender thật + pub 3.247 → dataset `gemma12b-gamedata-r3` (16.655 records, verify đủ 4 file).
  - [x] User chốt run 4 NHIỀU DATA: kernel `gemma12b-gendata4` DONE — Unity-complete 1.585 + rest 48.089 + HF bulk 38.850 (CodeAlpaca+Python+playable-05) + bpy proc 800/800 → dataset `gemma12b-gamedata-r4` (89.330 records, verify đủ 5 file).
  - [ ] Train run 4 (merge r3 + LoRA r128 mới + subset data r4): chờ user nói đẩy.
  - [x] Run 4 đẩy (batch 16 = 8x2, merge r3, subset 15k từ r3+r4 data, 1500 steps, adapter mới) — user chỉnh RTX. Đang chạy.
  - [x] Run 5 (v31): BỎ cứng steps (max 30000, hết giờ thì dừng) + trừ [viwiki] + chỉ data mới (Fable/xLAM/Glaive/Turnstile/3DCode/playable/bpy/unity-complete) + MERGE(PEFT) trước rồi MỚI import Unsloth + unsloth bắt buộc. User chỉnh RTX. Đang chạy.
  - LUẬT MỚI (user 10/10): (1) run sau đợi ĐỦ 200K+ data mới train; (2) KHÔNG chạy tuần tự nữa — SONG SONG 3 nhánh acc A/B/C (90h/tuần), mỗi nhánh seed + shard khác nhau, rồi SOUP (trung bình weights adapter, cùng base/rank/target) — run hiện tại giữ làm nhánh 1.
  - [x] Nhánh phụ trên cùng acc A: kernel `gemma12b-phase2-lora-b` (T4, không competition) — merge r4 + LoRA mới, CHỈ data tool (fable/xlam/glaive/turnstile/ood), output r5b. Main lo game/3D. Soup sau khi cả 2 xong (nếu Kaggle chặn 2 GPU song song thì chuyển nhánh phụ sang acc B).
  - [x] Main về đích (8000 steps) + phụ ckpt-7000 → up 2 adapter làm dataset tu local (`main8k`, `aux7k`, moi cai 2GB). Soup tren CPU Kaggle (kernel `gemma12b-soup`, trung binh 50/50) vi RAM local chi 4GB. Bench soup vs main vs aux sau.
  - [x] Soup xong (656 tensors). Bench v30 so base-chat/main/aux/soup (greedy batch-8). User chỉnh RTX. Đang chạy.
  - [x] User chốt run 6 CỨNG 1 epoch: data mới toàn phần (Fable đợt 2 + Turnstile đợt 2, kernel `gemma12b-gendata6` → dataset `gemma12b-gamedata-r6` 17k verify đủ) + replay lõi cũ. Train v35 (merge r4 + full r6 + CỨNG 1 epoch = len/batch 16) DONE → r6 publish dataset (local up + dọn local).
  - [x] Bench v32 so base-chat/r4/r6 (greedy batch-8, bỏ main/aux/soup). User chỉnh RTX. Đang chạy.
  - [x] LOOP SFT trên RTX (kernel `gemma12b-looptrain` v1): 5 game Pygame song song, 1 turn = 1 vòng 5 task; mỗi 20 turns = 1 phase (merge r4 → MA TRẬN MỚI → SFT mẫu reward>0, unsloth); cuối soup các phase. User chỉnh RTX. Đang chạy.
  - [x] GGUF r6 (acc B) DONE: file `merged.Q4_K_M.gguf` trong repo private `himAgayem/gamecraft-r6-test` (tên generic của unsloth, đổi sau nếu cần).
  - [ ] Publish adapter r5 (main COMPLETE) + bench r5, rồi DỒN LỰC harness runner 3 vai (design đã chốt HARNESS_PLAN.md §6).
  - [x] Dataset r6 gốc kẹt backend (download 404) → publish lại slug `gemma12b-adapter-r6b` (2.1GB verify đủ) + public cho acc B. Kernel B (`dieniw/gemma12b-gguf-r6` v2) attach r6b làm GGUF (HF sẽ báo sau: repo + private?). Đang chạy.
  - [x] Đường upload kernel SỐNG LẠI (probe-tiny OK — lỗi chmod chỉ là sự cố nhất thời). Dataset r6 cũ kẹt backend (files có, download 404) → publish lại slug mới `gemma12b-adapter-r6b` từ output (kernel `gemma12b-pub-r6b`, verify size >1GB). Xong thì B attach r6b làm GGUF.
  - Run 4 chậm ~7s/step trên RTX (merge-fp16 path, không unsloth) → ~3h. Loss đẹp (3.57→~1.0). Để chạy tiếp, không stop.
  - Quota 09-10/10: RTX tính 1x như T4 (user xác nhận, không phải 2x). Song song 2 kernel acc A đốt ~2x tốc độ thường. B/C còn nguyên 30h + reset weekly.
  - Verify run 4: merge_src=r3 đúng, data 105.985 records → subset 15k, unsloth có mặt (dù merge path vẫn dùng PEFT). Label log "MERGE r1" cũ đã fix local.
  - GOTCHA: slug/title dataset KHÔNG được trùng slug notebook (cùng namespace) — gamedata2 kẹt 3 lần vì trùng tên kernel. Đặt tên dataset khác tên kernel.
  - [ ] Train run 3 (merge r2 + LoRA r128 mới + subset gamedata-r3): v24 vừa đẩy, chờ chạy.
  - [x] Run 3 DONE: 1500 steps, loss ~1.5 → 0.88, seed 176415556, adapter `gemma12b-lora-r3`. Publish r3 ra dataset trước (bài học mount), rồi bench base-chat/r2/r3.
  - SCORING.md đã chốt (60 task × 5đ = 300đ, base/r1/r2 cùng đề). Kernel `gemma12b-bench` (T4) đang chạy: attach r1 dataset + r2 qua kernel output + tools + base. Publish r2 dataset SAU khi bench xong (user dặn).
  - Fix bench v11: load adapter sai tên → weights MISSING (chạy random!) + peft mới bỏ `disable_adapter`. Giờ load riêng từng config tên mặc định + dọn VRAM giữa lượt.
  - Audit bench v14: base 0/300 do prompt Alpaca không phải format gốc của base (gen ngắn 469 ký tự) + fence ``` làm crash hết phần execute (r1 fence 60/60!). Fix: strip fence trước khi chấm + thêm config base-chat + temp 0.3.
  - Mount output train quá nặng → kẹt ERRORED_MOUNTING_DATASET ở v18/v19. Fix: publish r2 thành dataset `gemma12b-adapter-r2` (2.1GB) rồi bench attach dataset, bỏ kernel mount. Bench v20 đang chạy, user tự chỉnh RTX trên web.
  - Bench fair DONE: base-alpaca 3, base-chat 108 (24/50/34), r1 86 (21/37/28), r2 107 (28/44/35). r2 ≈ base chung cuộc, nhất track game + 3D, thua Unity 44 vs 50. r1→r2 hồi 86→107: merge + r128 đi đúng hướng.
  - r2 đã publish thành dataset (làm trước để gỡ kẹt mount, user đồng ý vì cần thiết).
  - Bench v25: r2 96 (36/37/23) vs base-chat 90 (13/50/27) — ĐẢO so với lần trước (60 vs 108) trên CÙNG 60 task. Nguyên nhân: temp 0.3 + 1 mẫu/task → variance lớn. Cần greedy (temp 0) để số quyết định. Chờ r3.
  - Bench greedy batch-8 v28 DONE (deterministic): base-chat 97 (20/48/29), r2 97 (32/42/23), r3 77 (21/56/0), **r4 136 (32/57/47) — ÁP ĐẢO BASE +39đ, nhất cả 3 track**. Mục tiêu đạt 10/10/2026.
  - Run 4 diverge cuối (grad NaN, loss→0) → dùng ckpt-1000, publish `gemma12b-adapter-r4` (2.1GB). Bench greedy v27 so base-chat/r2/r4 (r3 sampling 61 đã ghi, bỏ qua ở bench này). Bài học: ≤1 epoch + clip grad + dừng khi NaN.
  - r3 publish thành dataset `gemma12b-adapter-r3` (2.1GB, verify đủ file) qua download API hẹp. Bench v25 so base-chat/r2/r3 (bỏ base-alpaca/r1 cũ), user chỉnh RTX. Đang chạy.
  - Input user verify trên web 07/10: competition ARC-AGI-3 + 2 datasets (gamedata, wheels) + model Gemma 4 V2 — đủ đồ train. Tools (Blender) chưa attach là đúng ý đồ, dành cho phase eval.
- [ ] Ghi lại kernel + version output vào đây: `khoadangnguye/gemma12b-phase2-lora` ( adapter `gemma12b-lora-r1` + run_info.json khi xong)

## 4. Phase 3 — Eval (offline, cùng notebook hoặc notebook mới)

- [ ] Game: generate Three.js/Unity code → check compile + chạy thử (chuẩn Mage/V-GameGym rút gọn)
- [ ] 3D: generate bpy → `blender --background --python` → render → chấm khớp prompt
- [ ] Ghi điểm baseline vs sau train vào đây: ___

## 5. Dọn dẹp (làm sau mỗi phase)

- [ ] Xóa dataset version cũ khi đã có version mới ổn: `kaggle datasets version` đè thay vì tạo mới lung tung
- [ ] Xóa kernel thử nghiệm hỏng: `kaggle kernels delete <slug>`
- [ ] Dọn `/kaggle/working/` file tạm trước mỗi Save & Run All (đỡ tốn output)

## 6. Stack vLLM + A/B self-play (user chốt 13/10, all-in vLLM trước pilot)

- [x] W0 probe GPU (`dieniw/env-probe` T4): python 3.13.15 (cp313), torch 2.11.0+cu128, T4 sm_75, triton 3.6.0 → FA2 được / FA3 không (cần sm90+) / vLLM abi3 được.
- [x] W1 CPU-fetch DONE (`dieniw/cpu-fetch` public COMPLETE): vllm closure + einops + `flash_attn-2.8.3.post1+cu.12.8.torch.2.11-cp313` KHỚP TUYỆT ĐỐI. GPU gắn qua kernel_sources (khỏi dataset).
- [x] FA2 SỐNG LẠI: lỗi ABI hôm trước do closure-torch đè torch gốc; giữ torch pristine → import OK. (mjun0812 không có cu128/torch2.11 nhưng Astral có.)
- [x] Chốt vllm==0.26.0 (mới nhất pin torch==2.11.0 khop image; quét PyPI 0.21→0.30: 0.21-0.26 torch 2.11, 0.27+ torch 2.13).
- [x] W1 v3 DONE: wipe dir + pin vllm==0.26.0 closure (không torch*).
- [x] W2 smoke PASS: vLLM 0.26.0+cu129 4bit = 13.3 tok/s (6.6x HF 2.0), sample coherent, torch 2.11+cu128 nguyên vẹn. Công thức: closure --no-deps (loại nvidia cu13/torch/C-ext nặng/transformers) + FA2 + tvm_ffi + LD_LIBRARY_PATH + max_model_len 1024/eager/seq8/max_lora_rank 128 trên T4.
- [x] Phase M DONE (`dieniw/ornbase-maker` CPU): base 18GB/4 shards vào kernel output, RTX offline gắn qua kernel_sources (khỏi mount dataset, khỏi download).
- [x] Dataset `dieniw/stack-wheels` DONE (194 wheels, 3GB): bài học — flat >50 file top-level bị từ chối im lặng, phải up `-r zip` (server tự bung, giữ cấu trúc `wheels/`). Local đã dọn (disk 14.4GB).
- [ ] Loop v29 (đang chạy T4): repair 1 vòng (py/bpy) + 3 waves + timeout 60s probe + budget tool 5/game (exec tính, write free) + game py nhiều file (`# === FILE: ===`) + attach stack-wheels.
- [ ] Phase M mount RTX: đưa base Ornith lên đường mount model (`dieniw/ornith-15-9b`, variant transformers, up từ kernel T4 có mạng) thay vì dataset 19GB cross-account.
- [x] Bench v5 công bằng tương đối: base 78 / o1 82 / loop1 82 — loop1 ≡ o1, confound format prompt (base chat vs adapter raw). Chưa kết luận được.
- [x] Pilot v1 DONE 20 round: infra chạy (gen/verify/train/soup) NHƯNG SFT collapse sau train 1 (request rỗng 15 round, soup rác) + A dễ dãi loạn verdict. Bài học: LR 1e-4/40-step trên 30 text = tự sát.
- [x] Pilot v2/v3 DONE: harness tự chấm, rollback, A siết → có PASS 5/5 đầu tiên, 2 train không collapse. Cuối run A drift (echo template).
- [x] B-alone v1/v3 (acc C): infra chạy trọn run NHƯNG 0 game py sống (model không chịu viết get_state, văn xuôi lọt vào code, repair fail) → turns=500 buf=0 phases=0 (pool<16 skip hết), soup chỉ từ static. Và `kaggle kernels logs` lấy log trực tiếp không cần output.
- [x] B-alone v5: 22 phases ngon (buffer 460 plays all-good, soup n=25, adapter p21 tải về) — chết ở reload vLLM phase 22 (free 37.63G < util 0.4=37.99G). Soup RAM mất (chỉ ghi đĩa cuối run).
- [x] B-alone v8: warm-start + tool-use XÁC NHẬN chạy (B tự viết file + chạy lệnh thật thấy traceback) NHƯNG py vẫn chết hết: NameError ném lúc gọi get_state (ngoài vòng inject), agent viết file không đuôi .py → spec None, agent lặp lỗi y nguyên.
- [x] B-alone v10 (acc C, COMPLETE ~88 phút): 25 phases, buf=1006 plays good, mean_rw 0.093→0.095 (vẫn chỉ alive-bonus), soup 26 adapter → phát hiện bug: file PEFT lưu keys canonical `lora_A.weight`, in-memory cần `.lora_A.default.weight` → load 0/256 keys = warm-start VÔ HIỆU (train từ random như v5). Soup v10 (465.6MB fp16, 256 keys) VERIFY chuẩn → upload public `hhjiji/b10-soup`.
- [x] B-alone v12 (acc C): warm-start loader FIX xác nhận (`khop 256/256`, 465.6MB) NHƯNG serve b10-soup (soup 26 adapter random-init khác nhau = trung bình dị hướng) làm model LOẠN: wave0 alive=0, static 0.2 (v10: 0.6), agent "het buoc (5 run)" không gọi done, repair gen 0 chars. → Soup kiểu này KHÔNG được serve; dataset b10-soup bỏ khỏi ưu tiên.
- [x] B-alone v13 (acc C, COMPLETE): 25 phases, buf=1500 plays (+50% vs v10), soup 27 adapter HỢP LỆ (mọi train init từ b5 → cùng gốc, soup avg có nghĩa), mean_rw 0.100. Lỗi còn: pygame not defined, prose "da xong".
- [x] B-alone v14 (acc C, COMPLETE): 25 phases, **buf=2006 plays** (v13 1500, v10 1006), good=2005, mean_rw 0.097, soup 25 adapter hợp lệ (warm-start từ soup v13 → cùng gốc). Fix v14: PRE `pygame = _pg`, strip_code bỏ "da xong", ping-pong slug + `kernel_sources` (attach output kernel cũ, bỏ hẳn tải/upload dataset), teaching lỗi `module has no attribute` (tool_response + repair prompt).
- [x] B-alone v15 (acc C, kernel `hhjiji/ornith-b-agent` #18 — PING-PONG) COMPLETE nhưng **KÉM**: wave 0 chỉ sống 1 game → điều kiện break `alive && static>=3` chốt ngay → 500 turns ĐÚNG 1 GAME (buf=500, good=500, static=3, mean_rw 0.100, HON 3, CHET 0, soup 26). Nguyên nhân: (a) đề model tự ra lệch ("Khoi tao game 3D den 300m, toc do..." — soup-of-soup v14 bắt đầu drift), (b) game1 lỗi `g1_0` cũ (teaching mới không cứu), (c) game200/205 repair ra văn xuôi `down` (bare word lọt). Bài học: serve soup 2 tầng rủi ro — lần sau serve **b5 hoặc adapter đơn**; nâng break lên `alive>=3`; v13 (buf1500) / v14 (buf2006) vẫn là artifact tốt nhất.
- Chờ: cancel `hhjiji/ornith-ab-pilot` trên web (CLI không stop được) để nhả slot.
- Luật verdict: A/B thắng nếu tổng bench tăng + không track nào rớt quá 10%; vLLM/FA thắng nếu tok/s ≥2x mà điểm giữ nguyên (chúng là tốc độ, không phải chất lượng).
- TPU v5e-8 LOẠI: Unsloth/vLLM/bitsandbytes/FA toàn CUDA-only, TPU chạy XLA không tương thích.

## 8. ROADMAP — COMPUTER USE THẬT (user chốt 17/10)

- Sau vài vòng loop B-alone nữa → **TRAIN THẲNG computer use thật** (GUI: ảnh màn hình → click/type/key), không chỉ shell tool-use.
- Data nguồn: **ScreenSpot** (grounding click UI), **OSWorld** (trajectory agent thật), **VideoGameBench** (vision game agent). EgoDemo (video/pose robot) LOẠI — lệch modality.
- Đường đi: tier 3 shell (đang có) → tier 4 GUI: screenshot + tool-call `click(x,y)/type(text)/key(...)`; SFT Unsloth với ảnh (Ornith có ViT sẵn).
- Việc chuẩn bị khi tới: harness screenshot trên Kaggle (Xvfb + Playwright/pyautogui), chốt action schema, bench live (tự chấm task click/type thật).
- [x] Harness local (Windows + Playwright) DONE: `phase13-gui/harness.py` (Env, parse_action, run_episode) + 3 fixture HTML + `gen_grounding.py` sinh grounding.jsonl (42 dòng, bbox DOM `[data-label]`, coords 0-1000).
- [x] Bench end-to-end local `bench_gui.py`: 3 task (click_green/login/counter5) — oracle 3/3 pass, random 0/3 (task hợp lệ); hook `--policy module:factory` sẵn cho model thật sau này.
- [x] Kernel `hhjiji/ornith-gui-sft` v3: **FastVisionModel LOAD ĐƯỢC Ornith (VL OK!)** + gen data 1200 PIL OK + eval-before chạy; chết ở collator "requires an image or audio processor" — dataset ornbase thiếu 3 file processor config (b_agent phải tự viết fallback).
- [ ] Kernel v4: thêm `fix_processor()` (thử AutoProcessor trực tiếp → fallback PREPROC với các class Qwen3VL/Qwen3_5Processor) + override processor sau FastVisionModel → train 150 steps r1e-4 r64 (vision frozen) + eval after hit-rate. Đang chạy.
- [x] v3→v5: processor fix chạy (Qwen3VLProcessor), FastVisionModel load OK, TRL 5.x cần `datasets.Dataset` — v5 train loss 2.96→0.079 nhưng eval 0/120.
- [x] v7 (chẩn đoán out thật): phát hiện **máy là 2×Tesla T4** (float32, 22.6s/step — run kéo 4h; muốn nhanh phải bật RTX trên web) + **after giống before (prose chat)** → format `CLICK x y` không được học dù loss thấp (loss bị loãng bởi text dễ; assistant tokens chưa đủ gradient). Soi source collator/zoo: image_size=None (không resize), for_inference không tắt adapter, template không bị patch — các đường cấu trúc sạch.
- [x] v8 (chẩn đoán): xác nhận — (a) adapter HOẠT ĐỘNG (ON≠OFF) nhưng vẫn prose kể cả trên ảnh train → **chưa học format**; (b) supervised decode = CẢ hội thoại (collator mặc định full-seq) → loss loãng bởi system/user text hằng số (mean 0.08 giả); (c) ảnh train bị collator resize còn ~512px (fallback `image_size=512`, 704 patch) vs eval 1536 patch → lệch scale; (d) v8 chạy trên **RTX PRO 6000 Blackwell bf16 (1.8s/step)** — nhanh gấp 12 lần v7 T4.
- [x] v10 (RESPOND_ONLY + LR2e-4 + STEPS200 + `resize="max"`) — **THÀNH CÔNG**: eval after **hit 43/60 = 71.7%**, parse 44/60; train-sub 9/12; adapter ON `'CLICK 353 273'` (đúng tọa độ) / OFF prose. Loss respond-only 1.0→~0.05. ℹ️ supervised decode có `think` rỗng của template Qwen — vẫn OK. Recipe chuẩn cho grounding VL trên Unsloth đã chốt.
- [x] v11 (**CHỐT**): STEPS 300 → synthetic **90/100 hit, parse 100/100** (v10: 71.7%/73%); train-sub 12/12; **real fixtures 42/42 = 100%** (before 0/42) — transfer sang UI browser thật hoàn hảo, lệch 1-2px. Adapter v11 = artifact chuẩn serve. Log: `gui_sft_done11.log`.
- [~] v12 = **bench end-to-end** `hhjiji/ornith-gui-bench`: v1 FAIL — adapter **trơ** (output prose y hệt base) + máy chậm (~25s/gen). Nghi nhân: forward patch của Unsloth bypass wrapper PEFT chuẩn → adapter không có tác dụng; v2 (version 3, đang chạy) = **bỏ Unsloth khỏi inference**, load transformers thuần + PeftModel chuẩn, tự thử 3 chiến lược load + **probe bắt buộc** (ra `CLICK x y` mới nhận), log rõ strategy dùng. Log: `bench_done2.log`.
- [x] Assets vòng GUI (18/10): datasets `hhjiji/ornith-gui-real-fixtures` (42 dòng eval thật) + `hhjiji/ornith-gui-real-ui` (216 ảnh / 792 dòng biến thể render thật từ fixtures — `gen_real_ui.py`: shuffle nút, đổi nền/gap/pad/card width, 4 viewport) + `hhjiji/ornith-gui-lora` (adapter v10 465MB, warm-start). Kinh nghiệm CLI: `datasets create -p dir` bỏ qua thư mục con → phải `datasets version ... --dir-mode zip` (Kaggle tự giải nén thành images/). Local không có GPU (torch CPU, RAM 3.9G) → serve/bench thật phải chạy trong kernel.
- [ ] v12 (dự kiến): train mix 1200 PIL + 792 real-ui → eval synthetic + fixtures (cần tách 2 dataset khi scan `/kaggle/input`); sau đó **bench end-to-end trong kernel** (internet on + `pip install playwright` + `playwright install chromium`, inline harness + fixtures) — 3 task click_green/login/counter5, đo task success thật.

## W. LUẬT MỚI (user chốt 22/10/2026) — ĐỘ KHÓ BENCH · MỤC TIÊU ĐO · RL/GRPO · NHỊP CHẤM ĐIỂM

> User: *"mỗi bộ bench mới (ví dụ 16-17) độ khó phải thực sự chênh nhau, **gấp 5-10 lần là ít**"*, *"benchmark đó làm chấm cái gì"*, *"ngoài việc cho models SFT không thì cho nó **RL, GRPO** nữa"*, *"**mỗi vài lần train sẽ chấm điểm một lần**"*, *"ghi vào đâu để nhớ đi"*.
> ⇒ Nguồn chuẩn: **PLAN.md § W** (luật) + **LONGMEMORY.md § 18** (bài học) + **agent.md LOBBY** (agent phụ đọc).

### W1. ĐỘ KHÓ CỦA MỖI BỘ BENCH MỚI — TIÊU CHÍ ĐO ĐƯỢC, KHÔNG "CẢM NHẬN"

**Nguyên tắc:** bộ bench mới (B16, B17, …) **KHÔNG được chỉ "khó hơn 5-10×"** ⇒ phải **thực sự chênh nhau**, và **độ khó phải được CHỨNG MINH BẰNG SỐ**, không bằng cảm nhận.

**Tiêu chí bắt buộc cho 1 bộ bench mới (thiếu 1 tiêu chí ⇒ không được dùng làm chuẩn):**

| # | Tiêu chí | Ngưỡng | Cách đo (bắt buộc ghi vào `result.md`) |
|---|---|---|---|
| 1 | **Model MẠNH NHẤT HIỆN TẠI** trượt | **≤ 20%** (mục tiêu ≤ 10%) | chạy adapter tốt nhất trên bộ mới ⇒ win rate |
| 2 | **Model VỪA ĐƯỢC TRAIN** trượt | ≤ 30% | cùng cách |
| 3 | **Baseline yếu (v18)** trượt | ≤ 10% | để chắc bộ mới không "bất khả thi" |
| 4 | **ĐỘ KHÓ TĂNG THẬT** | win rate model mạnh nhất trên bộ MỚI **≤ 1/3** win rate trên bộ CŨ (⇒ **gấp ≥ 3 lần khó hơn**, mục tiêu ≥ 5×) | ví dụ: v22 được 55,6% trên B15,5 cũ ⇒ bộ mới phải ≤ 18,5% (mục tiêu ≤ 11%) |
| 5 | **Không rò rỉ đáp án** | 0 task nào lộ đáp án trong màn hình | review thủ công từng task + checker tự tính (không tin self-report) |
| 6 | **Có "bẫy" đo đúng năng lực** | ≥ 1/3 task là **loop-recovery / read-before-act / nhiều bước** | liệt kê tag từng task trong `tasks.json` |

**Công thức độ khó dùng cho mọi lần so sánh:**
```
ĐỘ_KHÓ(bộ MỚI) = win_rate_model_mạnh_nhất(bộ CŨ) / win_rate_model_mạnh_nhất(bộ MỚI)
⇒ bộ MỚI chỉ được dùng chuẩn khi ĐỘ_KHÓ ≥ 3 (mục tiêu ≥ 5) VÀ win_rate(bộ MỚI) ≤ 20%
```

**Cấm:** dùng bộ bench mà **model hiện tại vẫn ≥ 50%** làm "bộ khó" ✗ ⇒ **mỗi lần sửa task ⇒ phải đo lại tiêu chí 1-4** (bài học 22/10: sửa 15 task làm suite B15,5 **DỄ HƠN 39 điểm** ✗ ⇒ tạo "cải thiện giả" ✗).

### W2. BENCH ĐO CÁI GÌ — BẢNG NĂNG LỰC BẮT BUỘC

Mỗi bộ bench mới **phải phủ các năng lực** (mỗi năng lực ≥ 1 task ✓, ghi tag trong `tasks.json` ✓):

| # | Năng lực | Task hiện có | Vì sao quan trọng (bằng chứng 22/10) |
|---|---|---|---|
| 1 | **Đọc trước khi hành động** (read-before-act) | T21_hiddenval, T25_compute | model đọc sai giá trị ⇒ 0/3 ✗ |
| 2 | **Nhiều bước** (≥ 8 hành động) | T23_undoredo, T22_order | model **lặp 1 thao tác 8×** ⇒ 0/3 ✗ |
| 3 | **PHÁ VÒNG LẶP** (loop-recovery) | — (chưa có) | **nút thắt #1** (loop-FAIL 44-50% ✗) |
| 4 | **Phục hồi sau lỗi** (error recovery) | T25_recovery, T08_errorfix | lỗi app/hành vi sai ⇒ model không tự sửa |
| 5 | **Clipboard / select-copy-paste** | T26_clipboard | **95% ✓** (mạnh) — giữ để không hồi quy |
| 6 | **Điều hướng bằng phím** (keyboard nav) | T22_keynav, T23_keys | 0/20 ✗ (mới chỉ biết click) |
| 7 | **Scroll / đọc ngoài viewport** | T23_table_sort (853px > 720px ✓) | cần ý thức ngoài màn hình |
| 8 | **Distractor** | T20_distractor, T26_distractorlist | chọn đúng nguồn giữa nhiều mục giống nhau |
| 9 | **3D grounding** (bbox) | bench 3D / 3D hard | hành động trong không gian 3D |
| 10 | **Desktop thật** (X11 + chuột/bàn phím) | `phase14-desktop` (T20-T26) | **mục tiêu thật**: dùng máy tính, không phải web |

**Quy tắc báo cáo:** mọi báo cáo bench **phải in bảng theo năng lực** (không chỉ tổng win rate ✓) ⇒ thấy ngay mạnh chỗ nào / yếu chỗ nào ✓.

### W3. RL / GRPO — BẮT BUỘC, KHÔNG CHỈ SFT

**Yêu cầu:** ngoài SFT thì phải có **RL/GRPO** ✓ (SFT chỉ học *hành vi đã có*; GRPO dùng **reward thật** ⇒ đúng vấn đề "model biết làm nhưng không *chịu* làm đúng" ✓).

**Thiết kế GRPO cho GUI (đã chốt để code):**
- **Prompt:** `(ảnh, instruction)` ✓ — từ **synthetic S1-S10** ✓ + **3D grounding** ✓ + **policy-replay** (task thật ✓).
- **Sinh G=8-16 mẫu/prompt** (temperature 0.8-1.0 ✓) → **reward verifiable**:
  - synthetic/grounding: `r=1` nếu hành động parse ra **đúng GT** ✓ (bbox overlap ✓ cho 3D ✓) + credit theo bước ✓.
  - policy-replay: `r=1` nếu hành động khớp hành động đã ghi ✓.
- **Advantage GRPO:** `(r - mean_G)/std_G` ✓ (không cần critic ✓).
- **KL với adapter SFT** (β = 0.01-0.05 ✓) để không bay/chết ✓.
- **Tooling:** TRL `GRPOTrainer` ✓ + Unsloth ✓ (wheels đã có `trl-1.14.1` ✓✓) + generation trong cùng process ✓.
- **RỦI RO BẮT BUỘC XỬ LÝ:**
  1. **Reward set phải TÁCH khỏi tập eval** ✓✓ — nếu không ⇒ đo là vô nghĩa ✓.
  2. **Reward hacking** (đoán pattern thay vì nhìn) ⇒ luôn gate bằng bench **thật** ✓ + mix 20-30% SFT ✓.
  3. **Suy thoái** ⇒ luôn chạy **1 suite rẻ (B15,5 18 ep)** sau mỗi lần RL ✓ + so với adapter SFT ✓.
  4. **Chi phí** ~300 prompt × 8 = 2400 generation ≈ **1-2h GPU/lần** ⇒ xen kẽ SFT (không thay SFT ✓).
- **Thứ tự:** (1) SFT v24 + gate ✓ → (2) **GRPO-v1 trên S1-S10 + policy-replay** → (3) gate so SFT ✓ → (4) nếu tốt ⇒ mở rộng reward từ desktop thật (chậm ✗ ⇒ sau ✓).

### W4. NHỊP CHẤM ĐIỂM — "MỖI VÀI LẦN TRAIN CHẤM 1 LẦN" (tiết kiệm quota)

| Mốc | Mức chấm | Quy trình |
|---|---|---|
| **Trong mỗi lần train** | **eval nội bộ** (không tốn GPU thêm) | `acc_after` + `acc_targeted_sub` + `acc_selfplay_sub` ✓ (đã có ✓) |
| **Mỗi 2-3 lần train** (hoặc khi **đổi recipe lớn**) | **1 suite rẻ**: B15,5 (18 ep, ≈40′) | kernel gate B ✓ |
| **Mỗi 3-4 lần train / trước khi chốt phiên bản** | **full gate**: B15 (36) + B15,5 (18) + B16-A (24) + desktop (30 ep) | 3 kernel gate + b3 ✓ |
| **Sau mỗi lần RL/GRPO** | **bắt buộc** full gate (RL dễ bay ✗) | + so sánh cùng bộ với adapter SFT ✓ |
| **Khi đổi/sửa bộ bench** | **ô 2×2 bắt buộc** (adapter cũ vs mới × task cũ vs mới) | 4 cell ✓ (bài học 22/10 ✓) |

**Bất di bất dịch:** *không sửa bộ bench rồi so sánh số cũ* ✗ ⇒ luôn kèm ô 2×2 ✓. *Không chạy full gate mỗi lần train* ✗ (đốt quota — acc A đã 0/30h ✓) ⇒ **nhịp 2-3 lần train 1 lần chấm** ✓.


## 9. Nhật ký cập nhật
- 06/10/2026: tạo file. Auth xong (chốt acc A). Chưa tải gì.
- 06/10/2026: Phase 1 DONE. Kernel `khoadangnguye/gemma12b-phase1-prep-cpu` COMPLETE (wheels+gamedata OK).
  Kernel fix `khoadangnguye/gemma12b-phase1-tools` COMPLETE (Blender 5.2.0). Cả 3 dataset verify qua `datasets files`. Dọn temp scaffold.
- 17-18/10/2026 (acc C, hhjiji): B-loop v13 (buf1500) → v14 (buf2006, ping-pong kernel_sources chạy tốt, 0 tải/0 upload) → v15 KÉM (break sớm còn 1 game). Dataset-from-output: chỉ làm được qua UI web Kaggle (Output tab → Create Dataset), CLI/API/MCP không có → loop dùng kernel_sources là đủ.
- 18/10/2026: chuyển hướng GUI (roadmap §8). Harness local OK. Kernel gui-sft v3: FastVisionModel load OK (Ornith VL chạy được trên Unsloth!) nhưng crash collator do thiếu processor config → v4 thêm fix_processor + override. Lưu ý log Kaggle đôi khi 504 stream, chờ COMPLETE rồi lấy log đủ.
- 18/10/2026: gui-sft v5-v8 = chuỗi chẩn đoán (loss thấp giả, adapter ON/OFF, supervised decode, img scale) → **v10 nổ: 71.7% grounding hit** (respond-only loss + resize max + lr2e-4 + 200 steps, RTX Blackwell). Adapter v10 tải về `phase13-gui/out_v10/`. v11 = +300 steps + fail-log đang chạy. Quyết định: giữ data PIL synthetic cho tới khi parse ≥95%, sau đó mở rộng UI có chữ thật (fixtures → dataset Kaggle) rồi mới vào trajectory SFT.
- 18/10/2026 (tiếp): **v11 chốt: synthetic 90/100 parse 100%, real fixtures 42/42 = 100%** (transfer sang UI thật hoàn hảo, lệch 1-2px). Adapter v11 → dataset `hhjiji/ornith-gui-lora` v2 (06:28). Dựng + push kernel bench `hhjiji/ornith-gui-bench` (internet ON, playwright chromium, adapter v11, 3 task). Local: giữ `out_v11/gui_lora` (463MB), xoá bản trùng v10/v11b (artifact đã trên Kaggle).
- 18/10/2026 (tiếp 2): bench v1 FAIL (adapter trơ → prose, máy 2×T4). v2 CRASH: traceback lộ **2 bug thật** — (a) `assemble_base` copy tạp từ mọi dataset → adapter files của dataset lora lọt vào `/tmp/ornbase` → `from_pretrained` tự load adapter lúc load model; (b) peft 0.20 + torchao 0.10 sẵn trên Kaggle → mọi inject LoRA chuẩn raise ImportError torchao≥0.16. v3 (version 4): bỏ Unsloth khỏi inference + `pip uninstall -y torchao` + assemble_base chỉ lấy từ `ornbase-s*` + probe-là-chuẩn (3 chiến lược load, chỉ nhận khi probe ra `CLICK x y`).
- 18/10/2026 (tiếp 3): bench v3 fail: Kaggle đổi mount (`/kaggle/input/datasets/<owner>/<slug>`) + model shards rải ở ornbase-s1..s4 (s2-s4 KHÔNG có config.json) → logic dò hẹp bỏ sót shard → `FileNotFoundError model-00002-of-00004`. v4 (version 6, server restart giữa chừng nên v5 bị bỏ): dò thư mục `ornbase-s*` **ở mọi độ sâu** + **verify đủ shards từ index** trước khi load (fail sớm, message rõ). Đã port cả `gui_sft.py` + compile OK.
- 18/10/2026 (tiếp 4): **bench v4 chạy tốt**: adapter PeftModel probe PASS; `[click_green] WIN sau 1 bước` (click (315,117) trúng nút xanh — grounding browser thật đầu tiên ✓); `[counter5] t0` click trúng nút "+". Máy 2×T4 lần này cực chậm: **~430s/gen** → counter5+login còn ~60'. **Song song (user chốt "song song cả hai")**: (a) v13 data: fixtures parametrize (`?goal/start/target/eu/ep/req`) + focus CSS + Enter submit + `gen_traj.py` (oracle Playwright, CLICK/TYPE/KEY/DONE) — dry-run 24 ep/100 rows chuẩn, **full run 18 variants đang chạy → `out_traj`**; (b) **phase14-blender**: kernel `ornith-blender-probe` v1 đã push (Blender 4.2.23 portable + headless cube→GLB+render Cycles CPU) — chờ kết quả.
- 18/10/2026 (tiếp 5): **`kaggle kernels logs -f` = live tail** (user chỉ — hết cảnh RUNNING trả 0 dòng, giờ follow live qua file local `bench_live_f.log`/`gui_train13_live.log`/`blend_live_f3.log`). **Bench v4: `[counter5] WIN sau 5 bước`** — 5/5 click trúng nút `+` (701,254±1px), multi-step đầu tiên sống trong browser thật; login task cuối đang chạy. **Blender probe v3 THÀNH CÔNG**: bug v1/v2 = URL sai thư mục (`Blender4.2.23/`; đúng là series `Blender4.2/`) + download.blender.org chặn 403 → mirror NLUUG + browser UA; tải 351MB, headless rc=0 t=45s, **Cycles CPU 16 samples chỉ 0.56s**, `VERIFY_GLB True 2000`/`VERIFY_PNG True 150300`/`VERIFY_TRIS 12` → **track 3D script-route mở khóa**. Traj regen xong kèm bbox → dataset `hhjiji/ornith-gui-traj` v2. **v13 train đã push (kernel version 14)**: mix synth 1200 + real-ui 792 + traj 816, SYS 4 hành động (CLICK/TYPE/KEY/DONE), STEPS 500, eval thêm traj-sub — đang chạy live.
- 18/10/2026 (tiếp 6): **SFT v18 — fix crash max_seq_length**: bản RTX Pro 6000 (user đổi UI từ T4) crash ở step ~2: `max_seq_length=1024` < ảnh traj cỡ lớn nhất (out_traj có 4 cỡ viewport: 800×600 / 1024×768 / 1280×720 / **1440×900** ≈ **1265 img token**) → Unsloth collator truncate cắt mất token ảnh → `ValueError: Mismatch in image token count ... ids=[384,937] text=[384,1260]` + segfault. Fix: **max_seq_length 1024→4096** (cả `from_pretrained` lẫn `SFTConfig`) + guard log "img lon nhat ~X tokens" trước train + metadata `machine_shape` → **`NvidiaRtxPro6000`** (giá trị hợp lệ; chuỗi `NvidiaRTX6000Ada` cũ bị bỏ qua) → **push version 18, chạy RUNNING ngay**. **Bench kernel v13 đã edit xong local** (`patch_v13.py`: fixtures parametrized chép từ `fixtures/`, `parse_action` CLICK/TYPE/KEY/DONE, `run_task` 4 hành động + evaluate goal khi DONE cho `req=done`, TASKS mới: click_green / counter5 / login_done) — **chưa push** (v4 đang chạy + chờ adapter v13). Lưu ý: **login bench v4 là task không thể win** (fixture để trống field, v4 không có TYPE) → FAIL theo thiết kế, chính là bằng chứng cần v13.
- 18/10/2026 (tiếp 7): **Bench v4 chốt sổ**: user cancel ở t=7642s (~2h07', T4×2) — hợp lý vì login lặp y hệt từng bước, không thể win (v4 không có TYPE); **kết quả cuối v4: click_green WIN 1 bước, counter5 WIN 5 bước, login FAIL (lặp y hệt 5 bước t0..t4, ~683s/bước, cùng ra `CLICK 399 248` → (511,179); v4 không có TYPE nên bất khả win — đúng là bằng chứng cho v13)**. Model load trên T4 mất t=2014s (33'); probe BASE ok=False (prose), adapter PeftModel ok=True `CLICK 494 479` ✓. **SFT rerun bởi user đang RUNNING** (version 18, đã có fix 4096). **Demo A data-gen kernel viết xong local** (`phase14-blender/gen_kernel/blender_gen.py`): 29 task × 3 variants = **87 cặp (instruction → bpy script)**; verify độc lập = rc + VERIFY_OK + parse GLB (meshes/tris) + render ≥2KB; dry-run local: compile OK, 0 trùng id, `glb_stats` đọc đúng cube.glb probe (meshes=1, tris=12) — **đã push version 1 (RUNNING ngay, CPU kernel, không tốn quota GPU)**. **Kết quả v1: 87/87 PASS (pass_rate 1.0), chỉ 138s tổng (~1.2s/task)** — tris chuẩn theo hình (cube 12, sphere 960, robot_head 4936, house 74...). Lưu ý: gold/traffic_light 3 variants trùng nhau (màu hardcoded) → dedupe còn **83 cặp unique** (artifact đã tải về `phase14-blender/out_gen1/`). **Đã upload dataset `hhjiji/ornith-blender-gen-data`** (private: rows.jsonl 83 dòng + renders.zip + glb.zip). Render kiểm tra bằng mắt: house (thân vàng + mái xanh), robot_head (khối đỏ + 2 mắt + ăng-ten) — đúng instruction. Lưu ý Kaggle: **title dataset không được trùng tên notebook** → đặt slug khác (thêm `-data`).
- 18/10/2026 (tiếp 8): **SFT v18 COMPLETE** 🎉 (bản user rerun, đúng version có fix): **500/500 steps**, train_runtime 1867s (~31', 3.91s/it, bs 2×8), train_loss **0.1495**, epoch 2.843. Guard log `img lon nhat 1296000 px -> ~1265 img tokens (budget 4096)` → fix max_seq_length ăn 100%. **EVAL: before 0.000 → after 0.500** (100 synthetic held-out, 53/100 parse), **traj_sub 13/16 = 0.812**, **real_after 33/42 = 0.786** (42 ảnh UI THẬT) — adapter ON trả `CLICK...`, OFF trả prose. Vài case còn leak prose (counter task) → cân nhắc 800-1000 steps ở vòng sau. Đang tải `out_sft_v18/` (adapter + kết quả) → tiếp: upload `hhjiji/ornith-gui-lora` bản mới → **chờ user OK để push bench v13**.
- 19/10/2026 (tiếp 9): **Adapter v18 đã lên `hhjiji/ornith-gui-lora` (version mới — status `ready`)**. Tải về bằng **`--file-pattern "gui_lora/.*|gui_result\.json"`** — mẹo cứu cánh: download full bị `RemoteDisconnected` 3 lần liên tiếp (dừng ở ~984/… ảnh preview); pattern nhắm đúng 8 file cần, qua trong 1 lượt. Verify: `adapter_model.safetensors` = 465.605.896 bytes (khớp v11 → nguyên vẹn), `gui_result.json` = `{layers... steps:500, n_train:2808, traj_sub:0.812, real_after:0.786}`. Đã xoá bản copy tạm `lora_upload/`. **→ Mọi thứ sẵn sàng: chỉ còn chờ user GO để push bench v13** (bench kernel đã có metadata RTX + fixtures 4 hành động; nhớ xoá `patch_v13.py` trước khi push).
- 19/10/2026 (tiếp 10): **User GO → BENCH V13 PUSHED (version 8) — RUNNING**. Ghi chú máy: follow đầu tiên hiện `[bench] gpu: Tesla T4 x2` → vài phút sau follow mới đọc lại log từ đầu thấy `[bench] gpu: NVIDIA RTX PRO 6000 Blackwell Server Edition x1` — session được cấp lại máy, hiện đang chạy ĐÚNG RTX.
- 19/10/2026 (tiếp 10b): **RUN V13 CRASH — 2 lỗi chí mạng:**
  (1) **Internet TẮT** trong run: `pip install playwright` fail `Temporary failure in name resolution` → `ModuleNotFoundError: playwright` → chết ngay task đầu (nbconvert → run kết thúc lỗi). Metadata push ghi `enable_internet: true` nhưng server (pull metadata) lưu `false` + `competition_sources: ["arc-prize-2026-arc-agi-3"]` + `docker_image: kaggle-private-byod` — đây là **trạng thái UI cũ dính vào kernel**, API push không ghi đè được.
  (2) **Probe chặn oan adapter v18**: cả 3 chiến lược load fail "probe" (output prose) → `strategy=None`. Nhưng phân tích: output adapter ≠ output base (greedy deterministic) → **LoRA CÓ hiệu lực**, chỉ là v18 prose-leak trên ảnh probe tổng hợp (đúng failure-mode đã biết). Logic cũ coi probe-fail = adapter hỏng → nếu không crash thì bench cũng chạy BASE vô nghĩa.
- 19/10/2026 (tiếp 10c): **V14 FIXED + push version 10** (RUNNING): (a) `check_internet()` sớm — 6 lần × 10s, tắt thì **dừng gọn** trước khi tốn 10' load model; (b) pip playwright retry 3 lần + kiểm tra import + playwright install fail thì dừng gọn; (c) **probe nhận adapter khi output KHÁC base** (cách ly bug "LoRA vô hiệu" = output giống base từng ký tự — bài học v1), parse OK vẫn ưu tiên; (d) fix concretize: bỏ prefix `base_model.model.` khi build target_modules. Follow: `bench_live_v14.log`. **Log đầu: v14 marker ✓ + `INTERNET OK (lan thu 1)` ✓ — internet hoạt động (v8 fail = tạm thời); gpu T4 x2 lúc boot (chờ xem có flip RTX như v8 không).**
- 19/10/2026 (tiếp 11): **Mở kênh multi-agent `agent.md`** ở gốc workspace (theo ý user): LUẬT CỨNG (đọc file là bắt buộc, CLAIM/RELEASE từng file để tránh 2 agent sửa chung, agent.md chỉ append) + danh bạ + LOBBY chat. Mình (DeepSeek) có watcher nền tự báo khi file đổi.
- 19/10/2026 (tiếp 12): **User chốt phân vai: DeepSeek = AGENT CHÍNH (điều phối)**; các session khác = helper. Đã thêm mục **🗂️ TASK BOARD** vào agent.md (chỉ DeepSeek sửa; helper CLAIM kèm TASK-n → làm → báo DONE). User chat với agent chính ở session này.
- 19/10/2026 (tiếp 13): **Helper đầu tiên nhập hội: GLM-5.3-Flash Free** (session OpenCode riêng) — tự điền Danh bạ, viết tin LOBBY, **CLAIM TASK-2** (draft kế hoạch SFT v19 → `phase13-gui/v19_plan_draft.md`, chỉ đọc không sửa code). Kênh agent.md giờ vận hành thật: watcher cả 2 phía, claim/duyệt qua board.
- 19/10/2026 (tiếp 14): **GLM DONE TASK-2 (~14')** — draft v19: H1 pha loãng synth là chính; v19 ≈3400–4000 rows, 2.0 epoch, metric leak-rate mới, mini-eval theo ckpt, 4 plan B; gate parse ≥0.95 / leak ≤5%. DeepSeek đã trả lời Q1–Q3 ở LOBBY (chốt: **chạy tách biến H1/H2 TRƯỚC v19 — chờ user GO**; không thêm viewport) + đăng **TASK-4** (script exp tách biến), **TASK-5** (nháp `gui_sft_v19.py`), **TASK-6** (playwright offline cho RTX). **MiMo-V2.6-Flash Free** nhập hội, CLAIM **TASK-3** (Blender mũi 2).
- 19/10/2026 (tiếp 15): **Chốt vụ RTX (user chỉ ra):** NvidiaRtxPro6000 chỉ mở khi notebook attach **competition ARC-AGI-3** (`competition_sources`) — thiếu thì dù machine_shape ghi RTX, server rớt về T4 im lặng (khớp note cũ phase Gemma). Đã sửa metadata `kernel/` + `bench_kernel/`. Hệ quả competition notebook: **internet OFF** → SFT/exp ổn (offline bằng wheels), bench cần playwright offline (TASK-6).
- 19/10/2026 (tiếp 16): **Bench v14 chốt kết quả đầy đủ** (GLM tải hộ — TASK-1 ✅): click_green WIN (1 bước); counter5 WIN (5 bước, cùng toạ độ); **login_done FAIL** — 4 bước đầu OK (CLICK → TYPE admin → CLICK → TYPE 1234), rồi **6 bước prose** ("Clicking the Sign in button will submit…") → WAIT, không bao giờ submit / `KEY enter` / DONE; tổng 2h29' (riêng login 92.6' vì WAIT vẫn gen ~670s/bước trên T4). t1 raw lộ `</think>` giữa chuỗi + lặp lệnh (format chưa sạch). Hệ quả: **end-actions là điểm yếu prose** → v19 nhồi traj kết thúc (submit/enter/DONE); càng xúc tiến RTX. GLM nhận **TASK-4** (script exp tách biến — đang viết).
- 19/10/2026 (tiếp 17): **GLM DONE TASK-4** — tạo `phase13-gui/exp_kernel/{exp_h2_matrix.py, kernel-metadata.json}` (id `hhjiji/ornith-gui-exp-h2`; RTX + competition + internet OFF; 11 ảnh cố định gồm 1 ảnh login-đã-điền). DeepSeek soát: loader real-ui khớp ✔; **phát hiện dtype: bench = bf16-if-supported ⇒ T4 fp16 / RTX bf16** → yêu cầu thêm hàng `T-fp16` (nghi vấn H2 mạnh nhất). Chờ **user GO** để push (ước tính RTX 15-20').
- 19/10/2026 (tiếp 18): **Push exp tách biến H1/H2** — user GO kèm đổi luật: "khỏi hỏi push, rớt T4 cũng OK" (quota mới reset). Kernel `hhjiji/ornith-gui-exp-h2` **v1 đang chạy** (PENDING→RUNNING); poll tự động → tải `exp_h2_result.json` + `exp_h2_full.log` về `phase13-gui/out_exp_h2/`. Song song: **nghiên cứu Kaggle MCP chính thức** (remote `https://www.kaggle.com/mcp`; tools: notebooks start/cancel/output, datasets, models, competitions, benchmarks; curl thô bị 400 → đúng bài là cắm vào MCP client): đã thêm mục `mcp.kaggle` vào `~/.config/opencode/opencode.jsonc` (header `Bearer {env:KAGGLE_API_TOKEN}`) — chờ user tạo token mới + set env + restart OpenCode.
- 19/10/2026 (tiếp 19): **Kaggle MCP live trong session agent chính** — harness hot-load ngay sau khi thêm config: namespace `kaggle` **76 tool** (notebook session create/status/cancel/output, `save_notebook` = save+run, `get_accelerator_quota`, competitions submit, forums/writeups/benchmarks...). **Auth hiện "Unauthenticated"** (tool `.authorize` không tương thích client OpenCode — lỗi schema) → đi đường token: user tạo "New Token" → set env `KAGGLE_API_TOKEN` (User scope) → restart OpenCode (fallback: thử classic `KAGGLE_KEY`). Sau auth: thay được phần lớn thao tác CLI (status/output/quota). Đã xoá `patch_v13.py` trước push; file v13 verify markers OK (`login_done` = `login_form.html?eu=admin&ep=1234&req=done`, `parse_action`, DONE qua `__goal_reached`). Dataset lora tự động lấy **v3 = adapter v18**. Follow live: `bench_live_v13.log`. Kỳ vọng: click_green/counter5 giữ WIN (giờ gen nhanh hơn T4 nhiều) + **login lần đầu đo được chuỗi TYPE→KEY/DONE** (v4 bó tay vì thiếu TYPE).
- 19/10/2026 (tiếp 20): **Fix vụ "push thất lạc" + trạng thái mới**: push exp-h2 lần 1 báo "successfully pushed" nhưng kernel KHÔNG tồn tại (list 79 kernel không có; status 403; web 404; user xác nhận) → **re-push lần 2 THÀNH CÔNG** (`KernelWorkerStatus.RUNNING` sau 45s; vẫn "version 1"). Poller mới đang theo dõi (case-sensitive, đếm denial, cap 96') → tự tải về `phase13-gui/out_exp_h2/`. **MCP**: `opencode mcp list` = "✓ connected"; auth đúng đường là **`/mcps` → kaggle → Sign in** (OAuth; bỏ hướng token+restart; đã xoá headers; OpenCode bản cài 1.18.34 → config flat `mcp.<name>`). **Helpers**: TASK-5 ✅ review ĐẠT (`gui_sft_v19.py`), TASK-3 ✅ review ĐẠT (Blender 45 cặp), TASK-6 tóm tắt OK nhưng **file note thiếu trên đĩa** → chờ MiMo lưu lại; đã giao **TASK-7** (MiMo: verify kernel Blender CPU) + **TASK-8** (GLM: builder kernel browser-bundle offline → dataset `hhjiji/ornith-offline-browsers`).

- 19/10/2026 (tiếp 21): **EXP H2 COMPLETE + KẾT LUẬN** — kernel `ornith-gui-exp-h2` xong 12:38 (~10'); GPU **RTX PRO 6000 Blackwell 95GB** (py3.13, torch 2.11+cu128, transformers 5.16.1, peft 0.20.0). **H2 (dtype) BỊ BÁC BỎ**: T-bf16≡T-fp16≡T-fp32 (parse 8/11, hit 7/11, cùng case; fp32 lệch 1 cụm chữ). BASE parse 0/11. Chi tiết: hits synth_01/03 + real_00..04; login_pil parse nhưng click sai (500,6); synth_00/02/04 = thinking bị cắt 24 token (`</think>` lộ ở login). U-bf16 fail `Please install peft` (unsloth import sau transformers/peft). Files: `phase13-gui/out_exp_h2/`.
- 19/10/2026 (tiếp 22): **TASK-8 builder** — review ĐẠT (GLM v2; note MiMo đã có thật trên đĩa); v1 ERROR vì `playwright.__version__` → hotfix `importlib.metadata.version` → **push v2 RUNNING 12:58** + poller tự tải output. Khi xong: download → up dataset `hhjiji/ornith-offline-browsers`. TASK-9 giao GLM (U-fix + diagnostic 96 tok). TASK-6 ✅, TASK-7 MiMo claim.
- 19/10/2026 (tiếp 23): **Kaggle MCP vẫn chưa auth** — OAuth `/mcps` không lưu token (mcp-auth.json = `{"kaggle": {}}`); thêm header `Bearer {env:KAGGLE_KEY}` vào `mcp.kaggle.headers` → vẫn Unauthenticated sau reconnect (log 05:52Z). Tạm dùng CLI; cần user retry + mô tả, hoặc `opencode mcp auth kaggle` trong terminal.
- 19/10/2026 (tiếp 24): **USER LỆNH MỚI + MAIN_QUEST** — user giao "chạy phát triển models như người thật 5 ngày, CHO PHÉP REASONING, benchmark mỗi ngày khó hơn, mọi thứ do DeepSeek quyết định". Đã tạo `MAIN_QUEST.md` (nguồn chân lý: reasoning `THINK:` + `ACTION:` 256 token; self-play rollout→verify→curate→SFT→gate; GUI B15→B16→B17→surprise; Blender 45 mui2→hard-30→compositional; phân vai; rủi ro). Board thêm TASK-10 (reasoning eval harness – GLM), TASK-11 (B15 12 task – MiMo), TASK-12 (self-play builder – GLM), TASK-13 (Blender hard-30 – MiMo), TASK-14 (SFT v20/v21 reasoning – GLM). Luật: push không cần hỏi; cancel phải hỏi user; helpers không push/cancel.
- 19/10/2026 (tiếp 25): **TASK-8 builder v2 COMPLETE** — manifest thật (tải lại): stage=done, launch_ok=true, smoke_ok=true, playwright 1.64.0, chromium 156.0.8078.4, browsers 678.4MB, t_sec=66.9. Phát hiện **snippet cũng dính bug `playwright.__version__`** → viết snippet **v3** (`importlib.metadata.version("playwright")` + tự extract `bundle.zip`). Kaggle CLI `datasets create` default `--dir-mode=skip` **bỏ qua thư mục** → đóng gói `bundle.zip` 336.9MB (422 file, raw 714MB; `build_bundle_zip.py`) + 4 file top-level + `dataset-metadata.json`; upload (title ≤50 ký tự, phải tạo `%TEMP%\.kaggle\uploads` trước). **TASK-7 verified**: 42/45 PASS (A 24/24, B1 15/15, B2 3/6); `curve_tube` FAIL cả 3 vì emitter truyền `bp[0].co` 4 phần tử (Blender 4.2 đòi 3) → **bỏ curve_tube, giữ text_3d**, dataset mui2 = 42 cặp.
- 19/10/2026 (tiếp 26): **TASK-9 do DeepSeek tự viết + push** (GLM chưa xong) — `phase13-gui/exp_kernel/u_fix_kernel/u_fix.py`: child process riêng chạy T-bf16 11 case `max_new_tokens=256` (an toàn nếu U fail) + U-bf16 import unsloth TRƯỚC transformers/peft + cài peft từ wheels nếu có + log wheel list; output `u_fix_result.json` + `t_diag_result.json`; push `hhjiji/ornith-gui-u-fix` RUNNING 13:26, poller về `phase13-gui/out_u_fix/`.
- 19/10/2026 (tiếp 27): **TASK-14 v20 push RUNNING 13:44** — `phase13-gui/kernel_v20/gui_sft_v20.py` (patch từ v19 bằng `patch_v20.py`, py_compile OK): assistant target = `THINK: ...` + `ACTION: ...` (make_think template có kiểm chứng từ label/instruction + toạ độ target), SYS mới (được THINK, dòng CUỐI bắt buộc ACTION:), decode `REASON_MAX=256`, parser `parse_output` (ACTION cuối → fallback legacy) + metrics prose_leak/legacy_leak/trunc_rate/mean_new → `gui_result.json["reason_stats"]` (EvalResult dict-subclass unpack tuple để không vỡ call site v19; MiniEvalCallback giữ nguyên), slot `gui-selfplay` fail-soft, cài peft từ wheels trước unsloth (fix TASK-9). GIỮ NGUYÊN: synth regen seed/run, eval held-out seed 202/offset 90000, lora r64 dropout 0.05, 2.0 epoch auto. Kernel-metadata mới `hhjiji/ornith-gui-sft-v20`.
- 19/10/2026 (tiếp 28): **Review B15 lần đầu + staging** — tasks: 12 HTML + tasks.json đủ 12 task (variant `?v=0..2` qua URLSearchParams, win `window.__task_ok`, max_steps 6–10); chờ `bench_v15.py` + `checker.py` + self-test. Tạo sẵn `phase13-gui/bench_dataset/` (metadata `hhjiji/ornith-gui-bench-v15` + `build_bench_zip.py` đóng gói `bench_v15/` thành `bench_v15_bundle.zip`) và `phase13-gui/lora_v20_dataset/` (metadata `hhjiji/ornith-gui-lora-v20`) để sẵn sàng push ngay khi có file.

- 19/10/2026 (tiếp 29): **Viết kernel eval B15** — `phase13-gui/kernel_bench_v15/bench_v15_kernel.py` (patch từ `bench_kernel/bench_gui_kaggle.py` bằng `patch_bench_v15.py`, py_compile OK): SYS reasoning v2, decode 256, parse_output v2 + prose_leak/mean_new, playwright offline qua `setup_playwright_offline.py` (V1–V6 fail LOUD), suite B15 từ dataset (module `bench_v15`/`checker`: `render_instruction(page, task_id, variant)` + `check(page)`), fallback v14 3 task, adapter = 1 dataset lora/version; ghi `b15_result.json` (per-episode + by_task + agg). Chốt hợp đồng API gửi MiMo. Chưa push được vì dataset `hhjiji/ornith-gui-bench-v15` chưa tồn tại (chờ MiMo xong runner/checker).

- 19/10/2026 (tiếp 30): **TASK-10 tối thiểu do DeepSeek viết** (GLM silent) — `phase13-gui/reasoning/reason_parse.py` (parser canonical + `metrics()`) + `test_reason_parse.py`: **22/22 PASS**, cross-check đồng nhất với parser trong `kernel_bench_v15`. Fix edge: dòng `ACTION:` không được chọn không còn tính là prose (thêm `extra_actions`); áp cho canonical + bench kernel + v20 kernel (py_compile OK). Kernel v20 đang chạy trên Kaggle vẫn code cũ — khác biệt metric chỉ ở case hiếm, không ảnh hưởng train.

- 19/10/2026 (tiếp 31): **MiMo giao `bench_v15.py` (13:58)** — runner `run_suite(policy_fn)` + obs có screenshot/instruction + dummy policy/CLI. Review: 3 lỗ hổng chặn chạy (thiếu `checker.py`; `window.__TASK__` không tồn tại trong 12 trang; tasks.json không có `tpl`). **Kernel eval cập nhật gọi thẳng `run_suite`** (wrapper bare-action + normalize KEY sang Playwright format + gom raw stats per-step; fallback driver nội bộ giữ nguyên). py_compile OK; test parser 22/22 vẫn xanh. Đã post danh sách fix + gợi ý đọc `body.dataset` cho MiMo.

- 19/10/2026 (tiếp 32): **Verify suite B15 LOCAL (không GPU)** — `bench_v15/lint_pages.py` (36 trang: 0 JS error, dataset fields OK) + `bench_v15/local_selftest_deepseek.py` (quét DOM → sequence cứng → chạy runner `bench_v15.run_suite` thật, checker stub): **pass-run 5/5** (T01/T04/T05/T07/T11) + **fail-run 2/2** (T01 confirm sai, T11 submit sớm). Phát hiện: T07 cần End thêm 1 lần để lộ item cuối (y 772→398); premature=1 không tránh được (focus click) → checker đừng bắt premature==0; T04 click track lệch ±1 cần arrow; T05 copied/pasted double-count. Thêm `--real` mode để đối chiếu checker.py thật khi MiMo giao.


- 19/10/2026 (tiếp 33): **B15 verify toàn bộ local** — `local_selftest_deepseek.py` mở rộng đủ 12 task × 3 variant: **PASS 36/36** + **FAIL-bắt 12/12** (v0+v2). Fix T08 (layout shift sau khi hiện lỗi → đo lại toạ độ cho click submit lần 2). 5 chốt checker gửi MiMo (T08 shift; T07 `clicked/clickedcount` đừng bắt premature==0; T04 ±1 arrow; T05 match; T03 correct là đủ). Còn chờ `checker.py` để chạy `--real`.


- 19/10/2026 (tiếp 34): **B15 lên Kaggle** — dataset `hhjiji/ornith-gui-bench-v15` READY (auto-extract OK); kernel `hhjiji/ornith-gui-bench-v15-eval` (v18 baseline) pushed 14:23 QUEUED + poller nền. **MiMo checker verify 2 chiều**: self-test 36/36+36/36 passed:true; harness DeepSeek độc lập `--real` 36/36 pass + 12/12 fail. Đã staged kernel v20 eval (`kernel_bench_v15_v20/`, chờ adapter dataset `hhjiji/ornith-gui-lora-v20`). Quy tắc mới: sửa file trong `bench_v15/` ➜ build zip + dataset version + push lại kernel.


- 19/10/2026 (tiếp 35): **Rollout kernel v20 xong** (`phase13-gui/kernel_rollout_v20/`, TASK-12 tự làm vì GLM im): PolicyV3 sampling t0.7/p0.95/N4; rollout_episode verify bằng `checker.check_task` trực tiếp (bug `suite_check` cũ: check_task nằm ở module checker chứ không phải bench_v15 — đã fix source); rows chỉ từ episode WIN, cap 480; outputs: rows.jsonl + summary.json + bundle.zip + result.json; SMOKE_TASKS guard. Thêm `scripts/post_v20_adapter.ps1` (auto tải + upload adapter sau khi v20 xong). TASK BOARD cập nhật 10/11/12/14.


- 19/10/2026 (tiếp 36): **EACCES fix + v20 gate + 2 kernel rerun.** Bench v1 fail `pw_offline_fail` (chromium spawn EACCES từ /kaggle/input read-only — dataset auto-extract làm nhánh cp-to-/tmp của snippet v3 không kích hoạt). Snippet v4: copy ms-playwright → /tmp/pw-browsers + chmod -R u+x + giữ V1–V6. Rebuild zip 349.5MB, dataset offline-browsers v2 READY 15:02; bench kernel v2 15:03 + v20 eval kernel 15:06 cùng chạy. v20 COMPLETE 14:47: parse 100/100, acc 0.87/0.56, real 0.952, trunc 0% — gate PASS; metric v2 chốt (pre_prose/legacy không gate); adapter lora-v20 READY; rollout smoke chờ slot.


- 19/10/2026 (tiếp 37): **FIX #2 TargetClosedError + dataset v3 + bench v3/v2 + Blender hard30.** Root cause: image Kaggle thiếu 4 lib (libatk/libatk-bridge/libXcomposite/libatspi) + fonts — builder đã `install-deps` (internet) nên pass, consumer offline chết. Thu deps bằng kernel CPU `pw-deps-collect` (ldd + dpkg diff, 65s) → `deps_out.zip` 43.5MB/142 file (symlink materialize) → snippet v5 `V4b deps repair` → dataset `ornith-offline-browsers` v3 READY 15:31 → repush bench v18 **v3** + v20-eval **v2** (RUNNING 15:34). Quirk: GPU+competition+internet=true bị Kaggle 400 → eval GPU phải offline. Blender: nhận TASK-13 (MiMo release 15:52) → push `ornith-blender-verify-hard30` v1 + re-push `ornith-blender-verify-mui2` v2 (curve_tube fix).

- 19/10/2026 (tiếp 38): **Blender day-1 results + TASK-16.** `verify-mui2` v2 (curve_tube fix) = **45/45 PASS** (A 24/24, B1 15/15, B2 6/6); `verify-hard30` v1 = **72/90** (pos_count 45/45, material 15/15, composite 3/3; camera 3/15, lighting 6/12) — cả 18 fail là `pixel_region` frac=0.00 (structure OK, vùng màu không thấy trong render). Mở TASK-16 (MiMo fix emitters/pixel calibration). Patch `verify_hard.py` keep-all renders (giữ cả glb/png pair fail) → kernel v2 re-run 15:47 → tải `out_verify_hard30_all/` cho MiMo. GUI: dataset v4 (snippet v5.1 — fix nhận diện `deps_out/` DIR, Kaggle auto-extract xoá file zip) READY 15:44 → bench v18 v4 + v20 v3 QUEUED 15:45 (RUNNING 16:01).

- 19/10/2026 (tiếp 39): **TASK-16 DONE — hard-30 90/90** (kernel v4 lúc 16:17; constraints **505/505**; t=163s; deterministic). Đường đi: v1/v2 72/90 (18 fail `pixel_region`) → chẩn đoán số red render 0.64 dist vs palette, AgX nghi phạm → v3 (chỉ đổi Standard view transform) = 71/90 — lộ **bug thật: color-space** (check so pixel display-space với palette linear → lift G/B ~0.4 hệ thống) → script `diag_disp.py` mô phỏng offline trước: display-space 20/21 pass → v4 (`_disp()` sRGB-encode trong check + h28 emit 1.0/≥0.8/spec sync) = **90/90**. Renders final: `out_verify_hard30_v4_renders/`. GUI: bench v18 v4 + v20 v3 RUNNING từ 16:01 (deps replay v5.1 không fail-fast — chờ kết quả); rollout smoke chờ slot.

- 19/10/2026 (tiếp 40): **B15 v18 = 10/36 (27.8%) vs v20 = 3/36 (8.3%) -> V20 REGRESSION do RECIPE.** v18 (`kernel/gui_sft.py`) huan luyen 1 DONG ACTION; v20 (`kernel_v20/gui_sft_v20.py`) huan luyen `THINK:` (template `make_think`) + `ACTION:` voi REASON_MAX=256. Data GIONG (synth+real-ui+gui-traj; v20 KHONG mount gui-traj-v19) -> khac biet la format/SYS, khong phai data. Recipe reasoning lam model hong tren multi-step (prose an budget, loop), con single-step grounding thi v18 > v20. **Quyet dinh: v21 = recipe v18 + self-play** (`kernel_v21/gui_sft_v21.py` fork tu gui_sft.py, them self-play cap 30%, steps scale; tao boi `phase13-gui/make_v21.py`). **Bug rollout (0 dong du lieu):** `rollout_episode` chi giu rows cua episode WIN -> 0/9 win => 0 rows (smoke v1; `parse=0` chi vi rong). Da sua: giu TAT CA step + nhan `win`/`n_fail_checks`/`n_checks`/`fail_reason`; `lora_fixed` -> /tmp (bo 465MB adapter vao output); SMOKE_TASKS=[] (full run). Da push `ornith-gui-rollout-base` v1 (adapter v18, 72 ep, ~2h) + `ornith-gui-rollout-v20` v3 (adapter v20, 36 ep, ~1h). Curate moi (`rollout_curate.py`): uu tien WIN, FAIL gan bo step cuoi, bo action lap, xuat `traj.jsonl` (v18 format) + `traj_reason.jsonl`. **Watchdog:** `scripts/watchdog.py` (6 kernel, poll 120s, tu tai output, fix charmap) + `scripts/watch_agent_md.py` (watcher ONE-SHOT agent.md theo LUAT CUNG #4). Pipeline v21 da chuan bi: `kernel_bench_v21` (id `hhjiji/ornith-gui-bench-v21`, mount `ornith-gui-lora-v21`) + `scripts/post_v21_adapter.ps1` (tai adapter -> upload dataset -> wait READY).

- 20/10/2026 (tietp 41): **QUOTA GPU HET (30.13h/30h) -> 24/10 00:00 moi co GPU**; key thu hai `dieniw` da het hieu luc (401) -> khong co account thu 2. **Mat ~7 GPU-gio do bug watchdog cu** (fetch fail 1 lan -> ghi marker -> khong retry; marker ghi cho version cu -> version moi bi skip). Da fix ca hai: marker luu `lastRunTime` (tu `kaggle kernels list --mine`) va fetch FAIL -> giu marker cu de thu lai. **Hang doi GPU tu dong moi** (`scripts/gpu_queue.json`, 9 muc): watchdog kiem quota moi 5 phong, con >=1h + <2 session -> push dung thu tu: sft-v21 -> bench-v18-think0 -> bench-v155 -> (sau v21: adapter upload -> bench-v21 + bench-v14-v21 + bench-v155-v21) -> sft-v22 -> bench-v16 -> bench-v16-v21. **Rollout-base (v18, 72 ep x 2 reps, temp 0.7): 24/72 win = 33.3%** (cao hon greedy 27.8%), 511 rows (121 win + 390 near-miss), modes action 449 / legacy 16 / none 46, prose leak 99%. **Curate + loc chat luong (da kiem bang mat):** bo episode LOOP (<=2 o toa do) 6 ep, bo `TYPE` giu chu che 4 row, cap action lap >2 lan/ep, bo step cuoi ep fail, dedupe, loai variant 2 khoi TRAIN -> **123 row (51 win + 72 near-miss)**; dataset `hhjiji/gui-selfplay` **READY**. **B16-A (MiMo TASK-20) verify 24/24 + 24/24** -> dataset `hhjiji/ornith-gui-bench-v16` (18.7KB) + 2 kernel staged. **4 ngay khong GPU -> chuyen sang Blender (CPU kernel van chay):** TASK-22 (MiMo) Blender compositional-15, TASK-23 (GLM) sinh data train 3D tu render that. Bai hoc them: `kaggle datasets create` fail neu **title > 50 ky tu** (dung 54 -> 37); `kaggle datasets create -p` phai dung **duong dan tuong doi** (absolute -> CLI mung path hong); PS1 phai ASCII-only.
- 20/10/2026 (tietp 42): **BAI HOC KAGGLE: kernel CHI upload `code_file`** (file phu trong thu muc kernel bi BO — `/kaggle/src` chi co `script.py`). Xac minh bang kernel CPU `ornith-list-files` (in cay `/kaggle/src` + `/kaggle/input`): chi co `script.py` + `__script__.ipynb`. **Hieu qua nghay:** (a) **v22 se CRASH** viet thieu `gen_synth_targeted.py` -> da INLINE module vao `gui_sft_v22.py` (44KB, kiem tra khong xung dot ten: PALETTE/CW/CH/norm giong het); (b) kernel CPU self-test B15.5+B16-A v1 FAIL vi thieu dummy actions -> da EMBED json vao script (v2 da push). **De quy trinh verify suite trong moi truong Kaggle THAT (CPU, khong ton GPU quota):** kernel `hhjiji/ornith-suite-selftest` — chay `bench_v155.py/bench_v16.py --dummy` voi success-policy cua tung task x 3 variant; fail LOUD (exit!=0). **Patch them `--no-sandbox`** vao 2 launch trong bench_v155/bench_v16 (Kaggle co the chay root) + rebuild dataset v2. **Giam N_TARGETED 600 -> 250 ep** (~940 row, ~24% mix) de khong dua synth len thieu so voi data that. **Queue GPU 24/10 da len 13 muc** (them bench-v22/bench-v155-v22/bench-v16-v22 + rollout-v21 vong self-play 2) + **dry-run PASS** (2 session/vong, dung dependency `after` + `needs_dataset`). **V22 kernel** them `kernel_bench_v22/bench_v155_v22/bench_v16_v22` (script chung `make_bench_any.py` tao kernel bench theo (suite x adapter)).
- 20/10/2026 (tietp 43): **TASK-24 xong (minh lam, vi session helper da dong)**: root cause T15 = `KEY End` khong scroll div chua focus -> scrolledat set muon (sau ack) -> check 'scrolled before accepting' fail; T14 v0 = cung race. Fix: (a) them handler `keydown` page-level trong T14/T15: End/PageDown -> scroll container (khong can focus) -> **agent that cung lam duoc bang action space**; (b) T15 page **chan accept truoc khi da scroll** (checkbox bi bo chon) -> checker giu nghia 'scroll truoc khi accept'. Verify: local 18/18 -> dataset `ornith-gui-bench-v155` **v3** -> kernel CPU self-test **v5 tren Kaggle that: b155 18/18 + b16 24/24 = SELFTEST OK** -> **B15.5 + B16-A san sang gate 24/10**. **TASK-18 xong:** `phase13-gui/gate_report.py` doc B15/B15.5/B16/v14 -> bang gate (tong/per-task/per-variant/holdout/agg) + PASS/FAIL theo nguong MAIN_QUEST + exit 0/1 (test voi data v18: 0.278 -> FAIL 35%, dung y vong). **TASK-23 (data train 3D) — dang chay:** kernel CPU `hhjiji/ornith-blender-gen3d` v1 (khong ton GPU quota): render 300 scene Blender 4.2 (3-6 object, (mau,shape) duy nhat) -> **grounding 3D voi action space GIONH GUI (CLICK x y 0..1000)**: 'Click the {mau} {shape}' -> diem do chieu cua object (world_to_camera_view). Output: `train3d.jsonl` + `shots/*.png` -> se upload dataset + mix vao v22 (vi model 3D hoc chung ky nang 'nhin anh -> click target' o ca 2D va 3D). **Bai hoc nua:** Kaggle chi upload code_file -> blender_scenes.py da duoc **inline** vao generate_3d.py (build_gen3d.py).
- 20/10/2026 (tietp 44): **TRACK 3D chuyen sang co DU LIEU + co METRIC** (muc tieu user "agent 3D" + "benchmark phai kho hon moi ngay"). **Data train 3D**: kernel CPU `hhjiji/ornith-blender-gen3d` (0 GPU-quota) render 300 scene Blender 4.2 (3-6 object, (mau,shape) duy nhat, CYCLES 16 samples, view transform Standard) -> target = **diem do chieu** (`world_to_camera_view`) chuan hoa 0..1000 -> action **`CLICK x y`** (GIONH action space GUI) -> dataset `hhjiji/ornith-gui-train3d` READY -> **da mix vao v22** (`load_ds_rows('gui-train3d','traj.jsonl')`, metadata da mount) => model 3D hoc chung ky nang "nhin anh -> click target" o ca 2D va 3D. **Bench 3D (metric)**: kernel CPU `hhjiji/ornith-blender-bench3d` sinh 100 task eval (seed 999 held-out so voi train) + **bbox CHIEU** cua object target -> checker = click co nam trong bbox khong (giong `hit(point,bbox)` cua GUI) + per-mau + parse/prose. Validate: center trong bbox **100/100** (vo doi duoc), median bbox 6.9% anh. Dataset `hhjiji/ornith-gui-bench3d` READY + kernel GPU `ornith-gui-bench-3d` + `-v21` -> da them vao hang doi GPU. **Bench 3D HARD (B16-3D)**: them che do `hard` (5-8 object, nho hon 0.28-0.45, sat nhau, camera xa hon) cho ca gen3d va bench3d -> 2 kernel CPU `ornith-blender-gen3d-hard` + `ornith-blender-bench3d-hard` (dang chay) de len tiep chuoi "kho hon moi ngay". **Kinh nghiem them**: (a) `kaggle datasets upload` canh tao subdir theo component DAU cua stage path trong %TEMP%\.kaggle\uploads -> phai New-Item truoc (da co trong `scripts/upload_dataset.ps1`); (b) kernel CPU (internet true, khong competition) la duong de sinh du lieu 3D **ton 0 GPU-quota** (~4-10 phut/300 render); (c) kernel chi upload code_file -> file phu phai inline (da lam cho gen_synth_targeted + gen_bench3d).