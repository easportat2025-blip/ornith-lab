# LONGMEMORY — Kinh nghiệm cứng (agent nào vào cũng đọc file này trước)

> Không ghi secret/key/token vào file này hay bất kỳ file nào.

## 0. Luật bất biến
- Câu cứng duy nhất: **mỗi train seed mới, ma trận mới — không để một khúc tham số học quá nhiều.**
- PLAN.md linh hoạt (số rank/steps/batch đổi được, ghi lại là được).
- Cứ 4 runs → merge → release HF public 1 lần (BF16 + GGUF Q4_K_M).

## 1. Kaggle CLI gotchas (đã trả giá)
- Slug/title dataset KHÔNG được trùng slug notebook (cùng namespace) → create fail im lặng.
- Image Kaggle mới (10/10): `datasets create/version` trong kernel gãy ở chmod /usr/local/bin (read-only) → publish dataset từ kernel TẠM HỎNG. Workaround: download về local → append/sửa → `datasets version` từ CLI local (đã verify OK 74MB). User đã cho phép tải local (ghi đè luật cũ), giữ data dưới `New folder\data\`.
- `datasets create` exit 0 vẫn có thể fail: đọc stdout tìm "creation error"; xong VERIFY bằng `datasets files` (có size thật).
- `kernel_sources` mount output nặng (GBs checkpoint) → flaky `ERRORED_MOUNTING_DATASET`. Fix: publish adapter/data nhỏ thành dataset riêng rồi attach dataset.
- `kernels output --file-pattern` match theo FILENAME (không theo path).
- Notebook attach competition + RTX: bắt buộc internet OFF → không gọi API HF/Kaggle từ trong (publish/upload phải làm ở kernel khác có mạng). Mọi dependency (wheels, tools binaries) phải attach sẵn, code try/except + fallback khi offline.
- Mount dataset nặng (19GB) CHẬM — check input ngay giây 0 sẽ trượt oan. Vòng đợi mount NGẮN (20s × 6 = 2 phút) rồi fallback tải HF (~80s), không đợi 10 phút phí GPU.
- Base Kaggle Model chính chủ (google/...) mount tin cậy (cache sẵn); dataset 19GB cross-account stage riêng từng session → hay trượt → luôn có đường fallback tải thẳng.
- Giới hạn Kaggle: input tối đa ~100GB/notebook (mình ~23GB, OK); `/kaggle/working` 20GB; `/kaggle/tmp` ~60GB; overlay `/tmp` ~1TB (CPU). Stage nặng vào /tmp.
- RTX 6000 không chọn được qua CLI `machine_shape` (docs chỉ có T4/L4/TPU) → bật trên web UI.
- Không có lệnh stop kernel qua CLI → stop trên web.
- Quota: GPU ~30h/tuần, TPU ~20h/tuần, reset weekly. Dataset private theo acc (acc khác không thấy).
- Reward shaping phải có răng: survival +0.1 mỗi turn khiến ~100% mẫu thành "good" → lọc RFT vô nghĩa. Đòi hỏi TIẾN TRIỂN (score delta > 0) mới tính good.
- Smoke test game gọi 1 lần là chưa đủ (game2 qua smoke rồi vẫn hỏng giữa chừng) → test 3-5 calls + timeout trước khi nhận.
- Token/key chỉ truyền qua env var lúc chạy lệnh, không ghi vào file.
- Public dataset: `dataset_metadata_update` với `isPrivate=false` (lấy metadata hiện tại về, giữ nguyên title/licenses, chỉ lật cờ). Đường local CLI sống khi image Kaggle hỏng.
- Dataset public thì acc khác (B/C) attach chạy ké được — không cần ferry/re-upload.
- LUẬT DISK LOCAL: tạo xong dataset là XÓA local ngay (disk chỉ ~10GB). Đã dọn: soup adapters 4GB, zip + jsonl r5.
- Bench codegen tĩnh (greedy) MÙ với SFT play/self-play: weights khác nhau (CPU-cmp max diff 0.03) vẫn cho điểm y hệt từng task (greedy plateau). Điểm nhảy theo setup (precision/batch/format), không theo weights. Eval play-phải end-to-end (build+chơi+verdict), cấm dùng code-bench tĩnh để kết luận SFT vô dụng.
- Dataset flat >50 file top-level bị từ chối im lặng → up `-r zip` (server tự bung, giữ cấu trúc).

## 2. Train/eval gotchas
- Image CPU vs GPU khác packages (unsloth_zoo/bitsandbytes/trl có thể thiếu) → probe `import` + version rồi mới chọn backend (unsloth → PEFT-bnb fallback).
- trl API drift theo version: `tokenizer` → `processing_class`, mất `dataset_text_field` → gate mọi kwarg bằng `inspect.signature` rồi mới truyền.
- peft mới bỏ `disable_adapter` → eval base bằng cách load riêng, không dùng context.
- Load adapter PHẢI đúng tên mặc định ("default"): sai tên → weights MISSING → chạy random mà vẫn ra điểm! Verify колес bằng LOAD REPORT.
- Bench: strip markdown fence trước khi chấm (model nào cũng bọc ```); base phải dùng chat template mới đúng sức; sampling temp>0 variance ±30 → số quyết định lấy GREEDY.
- Soup trung bình weights CHỈ ngon khi nhánh tương thích (cùng phân phối). Nhánh divergent (game vs tool thuần) soup xong HỎNG hẳn 1 track (soup unity=0). Quy tắc: bench soup vs từng nhánh, số thắng mới lấy.
- Bench thiếu config nào thì 99% là quên attach dataset (pick theo substring, thiếu là skip im lặng) — check dòng `configs=` trong log trước khi đợi.
- Merge-fp16 path chậm (không unsloth, ~7s/step) — chấp nhận hoặc train fresh từ base cho nhanh.
- RTX vẫn chậm (~4.5s/step) thì do: (1) unsloth offload gradients ra CPU (thừa với 96GB, làm chậm) → tắt khi VRAM đủ; (2) FA2=False/xformers None (không FlashAttention) → thử pip flash-attn. Đừng vội đổi GPU khi chậm, coi config trước.
- loss về 0 + grad NaN = diverged → bỏ bản final, dùng checkpoint trước đó. Phòng: ≤1 epoch, clip grad, dừng khi NaN.
- OVERFIT học thuộc: loss <0.5 + epoch 3+ + bench sập (main: 0.2/4.1/31). Phòng: ≤1.5 epoch, early-stop khi loss sàn, subset mới mỗi run.
- Branch tool-only không chấm bằng bench game được (aux 13 là sai sân) — mỗi họ skill cần bench riêng (tool → BFCL-style).
- Mount /kaggle/input mới lồng 3 tầng: datasets|models|competitions/{owner}/{slug}.

## 3. Release gotchas
- CPU kernel: disk /kaggle/working 20GB, RAM 30GB — NHƯNG /tmp (overlay) trống ~1TB → stage mọi thứ nặng ở /tmp.
- Unsloth GGUF cần ~46GB disk (merge 16-bit + F16 + quants cùng lúc) — `/kaggle/working` (19GB) không đủ → stage ở `/tmp` (overlay ~1TB) + `os.chdir("/tmp")` vì file trung gian F16 ghi ở CWD (kể cả khi save_dir đã ở /tmp!).
- PEFT merge tu base 4-bit xong NHO xoa `quantization_config` trong config saved (ke thua) + verify safetensors ~24GB, khong Unsloth/llama tuong weights van 4-bit va tu choi.
- merge_and_unload tren base BNB-4bit KHONG dequantize (luu ra van 4-bit ~7GB). Muon full fp16 phai merge tren base fp16 full + offload (24GB chia GPU + CPU/disk).
- Khi copy script sang kernel/acc khác (A→B) phải mang theo MỌI fix (chdir, device_map, find đệ quy) — check diff trước khi push, đừng tưởng bản copy đã mới.
- Config Gemma 4 Unified: transformers cũ (5.10) BẮT BUỘC `text_config.num_global_key_value_heads` là số (full-attn layers), thiếu → `16 // None` crash. Config save từ 5.16 không có key này → thêm tay (=1 cho 12B, khớp per_layer kv=1) + `global_head_dim`=512. Bài học: khác version transformers thì verify config keys.
- llama.cpp convert gãy ở tokenizer Gemma 4 (cả transformers 4.x/5.x) → dùng Unsloth `save_pretrained_gguf` thay thế.
- Unsloth GGUF cần: unsloth + unsloth_zoo + trl + bitsandbytes (cài từ wheels offline + pip online gói nhỏ).
- Luồng an toàn: upload BF16 TRƯỚC khi convert/quant (hỏng sau cũng không mất).
- Xong release thì rename repo qua API (giữ redirect). Xong việc cân nhắc revoke key.

## 4. B-loop (self-improving) gotchas
- Soup 1 tầng (mọi train cùng init) = OK; soup 2 tầng (soup của soup) serve lên bắt đầu DRIFT (v15: đề tự ra lệch "game 3D 300m tốc độ...", gen 0 chars) → ưu tiên serve adapter đơn / soup 1 tầng đã chứng minh.
- Điều kiện break wave trong harness B-alone quá dễ: `alive && static>=3` → v15 sống 1 game là chốt luôn → 500 plays toàn 1 game (buf=500) dù máy vẫn chạy 25 phase trông "bình thường". Lần sau đòi alive>=3 hoặc gen thêm.
- Lỗi tái diễn cần auto-patch ở harness thay vì trông model tự sửa: `module 'gN' has no attribute 'get_state'`, văn xuôi/bare-word lọt code (`down`, `done`), `pygame` chưa import.
- 2 lỗi "nhìn mới" của wave muộn thực ra là game repair re-verify (id 200+), đừng nhầm là wave 20.
- `kaggle kernels logs -f` hay 504 giữa chừng; chờ COMPLETE rồi lấy `kernels logs` đủ hơn là follow liên tục.

## 5. GUI / VL gotchas (Ornith-1.5-9B)
- Unsloth `FastVisionModel.from_pretrained` LOAD ĐƯỢC Ornith (Qwen3.5 VL) trên Kaggle stack 2026.9.14 — vision fine-tune khả thi.
- Dataset ornbase (fork từ shards) THIẾU 3 file processor → collator "requires an image or audio processor". Fix: tự viết `processor_config.json` + `preprocessor_config.json` + `video_preprocessor_config.json`, `processor_class: Qwen3VLProcessor` (transformers 5.16.1 có Qwen3VLProcessor/Qwen3VLVideoProcessor, KHÔNG có Qwen3_5Processor), rồi tự build processor bằng AutoProcessor và TRUYỀN ĐÈ processor của FastVisionModel.
- TRL 5.x: `train_dataset` phải là `datasets.Dataset` (list → TypeError).
- Eval VL: hit 0/120 chưa chắc train hỏng — phải log raw output + parse rate + eval luôn trên chính data train để tách "không học" vs "lỗi format/parse".
- **Loss loãng trong VL SFT full-seq**: mean loss có thể về 0.08 mà model vẫn KHÔNG học format đích — vì phần lớn token là system/user text hằng số (học dễ ≈0), token đích thật (vd `CLICK x y`) bị pha loãng. Bắt buộc verify: generate trên chính ảnh train + probe `adapter ON/OFF` (ON≠OFF mà vẫn sai format → chưa học, không phải adapter chết).
- Unsloth VL collator mặc định train **full sequence**; muốn ép học format đích: `train_on_responses_only=True` + `instruction_part="<|im_start|>user\n"`, `response_part="<|im_start|>assistant\n"` (marker theo template; không tìm thấy marker → nó raise rõ ràng, tốt).
- Collator resize gotcha: config `vision_config.image_size` thiếu/None → collator fallback **512** và tự resize ảnh train (log: "Model does not have a default image size - using 512") → train 176 token ảnh vs eval 384 = lệch scale. Fix: `UnslothVisionDataCollator(..., resize="max")` (tắt resize hẳn).
- Máy Kaggle cho cùng kernel có thể rơi vào T4 (float32, 22.6s/step — log "Using float16 precision ... won't work") hay RTX PRO 6000 Blackwell (bf16, ~1.8s/step). LUÔN đọc header log (Tesla vs RTX) trước khi kết luận về tốc độ.
- (Tooling) Chuỗi dạng `<|...|>` (vd `<|im_start|>`) bị ẨN khi hiển thị output tool — file có thể đúng dù hiển thị trông thiếu; verify bằng repr/codes trước khi "sửa".
- **RECIPE THÀNH CÔNG grounding VL (v10, 71.7% hit synthetic)**: `RESPOND_ONLY=True` (marker Qwen) + `LR=2e-4` + `STEPS=200` (1200 ảnh, batch 2×grad-accum 8) + `resize="max"` + vision frozen r64. Loss respond-only 1.0→0.05. Eval phải đo cả parse-rate; log raw output + 3 mẫu fail (parse=None) để bắt mode lỗi thay vì đoán.
- **Kaggle + peft 0.20 + torchao 0.10**: mọi đường inject LoRA chuẩn PEFT (kể cả `model.load_adapter` của transformers integration) raise `ImportError: Found an incompatible version of torchao. Found 0.10.0, but only versions above 0.16.0 are supported` → fix: **`pip uninstall -y torchao`** trước khi load adapter (đường Unsloth-train không dính vì không đi qua dispatcher này).
- **assemble_base "ăn tạp" + mount mới**: (a) nếu kernel attach dataset adapter (vd `ornith-gui-lora` có `adapter_config.json` + `adapter_model.safetensors`) mà copy file kiểu "walk mọi /kaggle/input, gom .json/.safetensors" → adapter rơi thẳng vào model dir → `from_pretrained` **tự động load adapter** lúc load model (→ dính torchao crash, hoặc load sai đường). (b) Kaggle đã đổi mount thành `/kaggle/input/datasets/<owner>/<slug>` và shards model rải ở ornbase-s1..s4 trong đó **s2-s4 không có config.json** → dò kiểu "config.json + model-*" bỏ sót shard → `FileNotFoundError model-00002-of-00004`. FIX chuẩn: dò thư mục `ornbase-s*` **ở mọi độ sâu** (os.walk theo tên), copy từ đó, xoá cứng adapter files khỏi dir base, **verify đủ shards từ `model.safetensors.index.json`** trước khi load (fail sớm). Đã áp cho cả 2 kernel (train + bench).
- **Bench/serve adapter = dùng transformers THUẦN + PeftModel + PROBE**: v1 (PeftModel trên model Unsloth) ra prose; nghi forward patch Unsloth bypass wrapper PEFT (chưa xác minh được vì log version bị cancel). Từ v3: không import unsloth khi inference, và sau mỗi chiến lược load phải **gen thử 1 ảnh probe — ra `CLICK x y` mới nhận**, in rõ strategy dùng. Máy bench = 2×T4 nhưng tốc độ **dao động cực mạnh**: v1 ~25s/gen, v4 ~430s/gen (nghi VRAM bận/chia sẻ → offload CPU) — không đoán trước được, đọc log từng lần.
- **Fixture parametrize dùng chung cho data v13**: counter `?goal=&start=`, click_button `?target=`, login `?eu=&ep=`; mọi fixture `?req=done` → goal CHỈ đạt khi model chủ động nói DONE (dạy tự kết thúc); login thêm Enter-submit + focus ring 3px (tín hiệu dạy TYPE). `gen_traj.py` = oracle Playwright sinh trajectory CLICK/TYPE/KEY/DONE (dry-run đã verify bằng mắt).
- **Blender headless trên Kaggle OK** (verify v3): URL đúng = `.../release/Blender4.2/blender-4.2.23-linux-x64.tar.xz` (thư mục theo **series** 4.2, KHÔNG phải 4.2.23); `download.blender.org` **chặn datacenter (403)** → dùng mirror `ftp.nluug.nl/pub/graphics/blender/release/` (hoặc RWTH Aachen) + **browser User-Agent** cho urllib (thiếu UA → 403, sai path → 404). Chạy `blender --background --factory-startup --python x.py`; Cycles CPU 384px/16 samples ≈ **0.56s** scene đơn giản; đầu ra verify GLB + PNG + rc=0. Kernel `ornith-blender-probe` = probe track t2 (phase14-blender).
- **`kaggle kernels logs <k> -f` = live tail -f** (CLI mới): xem log kernel ĐANG chạy realtime — hết cảnh "RUNNING nhưng logs trả 0 dòng". Mẹo: chạy follow trong background shell + `Tee-Object` ra file local để vừa xem vừa parse.
- **Blender headless trên Kaggle CPU siêu rẻ: ~1.2s/task** (87 task = 138s toàn bộ, kể cả export GLB + render Cycles). Batch vài trăm task/lần thoải mái. Task có màu hardcoded (gold/traffic_light) → 3 variants trùng nhau: dedupe theo (instruction, script).
- Kaggle **title dataset không được trùng tên notebook** (cùng namespace tên) — `datasets create` báo "already in use by a notebook"; đặt slug khác (vd thêm hậu tố `-data`).
- **Mốc SFT v18 (để so sánh vòng sau)**: 500 step / ~31' trên RTX Pro 6000 (~3.9s/it, bs=2×8); eval: base **0.000** → adapter **0.500** (synthetic held-out), traj_sub **0.812**, real UI ảnh thật **0.786**. Chưa no — còn leak prose ở counter task → lần sau thử 800-1000 steps.
- `-f` trên kernel **QUEUED → HTTP 500** (stream chưa tồn tại); phải chờ RUNNING mới attach — dùng watcher loop (status → sleep 300 → attach) hoặc follow thẳng khi status RUNNING. Đôi khi 500 cả khi kernel vừa RUNNING — retry sau vài phút.
- `kaggle kernels output` có **`--file-pattern <regex>`** (khớp tên file trong output): khi tải full liên tục `RemoteDisconnected` (output hàng trăm file nhỏ), nhắm đúng file cần (vd `--file-pattern "gui_lora/.*|gui_result\.json"`) → qua ngay. Retry full download tự skip file đã có (resume), nhưng file tải dở (partial) có thể bị skip nhầm → **kiểm tra size** (vd adapter 465.605.896 bytes) trước khi dùng.
- **VL max_seq_length phải ≥ token ảnh + text**: ảnh 1440×900 ≈ 1265 img token > 1024 → Unsloth collator truncation cắt input_ids → lệch số token ảnh → `ValueError: Mismatch in image token count between text and input_ids` + segfault. Ngân sách an toàn: **4096**. Ước lượng: img_tokens ≈ w×h/1024.
- **Bench adapter probe + prose-leak**: đừng dùng "probe phải parse action" làm điều kiện duy nhất để nhận adapter — model prose-leak (~50% với v18) sẽ chặn oan → bench chạy BASE. Tiêu chí đúng: **output có KHÁC base không** (greedy deterministic; giống hệt base = LoRA vô hiệu thật — bug v1), parse OK là ưu tiên cao hơn. Kèm retry pip/internet-check sớm trong script để fail nhanh, rõ.
- **Kernel cũ giữ "trạng thái UI" + internet chập chờn**: pull metadata lộ `enable_internet: false`, `competition_sources: arc...`, `docker_image: kaggle-private-byod` dù metadata push ghi ngược lại. v8: run MẤT internet (pip DNS fail) → chết; v14 CÙNG kernel + CÙNG metadata: `INTERNET OK (lan thu 1)` → v8 chỉ là fail **tạm thời** (boot session?). Bài học kép: (1) script luôn check internet sớm + retry; (2) đừng kết luận vội từ 1 session — session mới có thể khác.
- **RTX Pro 6000 = phải là notebook competition ARC-AGI-3**: machine_shape "NvidiaRtxPro6000" một mình KHÔNG đủ — thiếu `competition_sources: ["arc-prize-2026-arc-agi-3"]` thì session rớt về T4 x2 im lặng (user chốt 19/10). Competition notebook → **internet OFF** theo luật competition (SFT/exp offline sẵn nhờ wheels datasets; bench cần playwright offline — TASK-6 trong agent.md).
- **Bench login_done (adapter v18, T4) FAIL ở bước KẾT THÚC**: 4 bước CLICK/TYPE ngon → 6 bước cuối toàn prose `Clicking the "Sign in" button will submit…` → WAIT, không submit/KEY enter/DONE. Phụ: raw t1 lộ `</think>` giữa chuỗi + lặp "TYPE admin" (format chưa sạch). Bài học: (1) **end-actions phải nhồi thêm trong traj data**; (2) WAIT siêu đắt trên T4 (~670s/bước — riêng login 92.6'); (3) parse "dòng đầu hợp lệ" giúp cứu được các bước giữa trace.
- **Kaggle MCP chính thức (19/10 — cập nhật 12:30)**: remote `https://www.kaggle.com/mcp`; config `~/.config/opencode/opencode.jsonc` mục `mcp.kaggle` (flat V1-style; bản cài OpenCode = **1.18.34**) — **KHÔNG cần token/headers**: `opencode mcp list` → **"✓ kaggle connected"**; `opencode mcp auth list` → **OAuth-capable, chưa authenticated** → đường auth đúng: **user gõ `/mcps` → chọn kaggle → Sign in** (OAuth browser) hoặc `opencode mcp auth kaggle` trong terminal. KHÔNG dùng tool `authorize` in-band (schema zod lỗi). 76 tool: notebook session create/status/cancel/output, `save_notebook` (save+run ≈ thay `kernels push`), `get_accelerator_quota`, competitions submit, datasets upload/list... **Luật: helpers KHÔNG push/cancel — agent chính lo Kaggle.**
- **push version có thể nhảy số**: v8 → push lần sau báo "version 10" (server tự tạo version đầy đủ khi session restart) — đừng chỉ tin số mình đếm tay.
- **machine_shape `NvidiaRtxPro6000`**: server LƯU được string này nhưng **session đầu có thể vẫn cấp T4 x2 rồi tự restart sang RTX x1** — luôn đọc 2 dòng log đầu (`[bench] gpu:`) trước khi kết luận máy.
- **v11 = chốt recipe**: +100 steps (STEPS=300, 4 epochs) → parse **73%→100%**, synthetic **71.7%→90%**, train-sub 12/12, và **transfer sang UI thật (browser render, nền trắng, chữ thật, 1280×720) = 42/42 = 100%** (lệch 1-2px). Takeaway: khi format còn flaky, tăng steps là đòn rẻ nhất; SFT grounding transfer tốt sang "phân bố thật" miễn base model đã đọc được nội dung UI (cần verify bằng before-eval: base output mô tả đúng element → có năng lực, chỉ thiếu format).
- **PUSH CÓ THỂ LỖI IM LẶNG (19/10)**: `kaggle kernels push` báo "Kernel version 1 successfully pushed" nhưng kernel KHÔNG hề được tạo (không có trong `kernels list --mine`; `status` → "Permission 'kernels.get' was denied"; web 404) → **re-push NGAY** (lần 2 tạo được + RUNNING sau ~45s, vẫn báo "version 1" = lần 1 chưa tạo gì). **Luôn verify `kaggle kernels status` sau push.** Phụ: `~/.kaggle/kaggle.json` = acc **dieniw**, env `KAGGLE_USERNAME/KAGGLE_KEY` = **hhjiji** (env thắng CLI).

- **Playwright python package KHÔNG có `__version__`** — lấy version bằng `importlib.metadata.version("playwright")` (builder TASK-8 run v1 chết vì cái này, 19/10).
- **Unsloth phải import TRƯỚC transformers/peft**: nếu import sau → banner OK nhưng `FastVisionModel.from_pretrained` → `ImportError: Unsloth: Please install peft ...` dù peft 0.20.0 có sẵn (exp-h2 19/10; log có warning rõ).
- **Kaggle MCP auth (19/10)**: OAuth `/mcps` có thể chỉ ghi entry rỗng `{"kaggle": {}}` (flow không hoàn tất); thêm `headers: {"Authorization": "Bearer {env:KAGGLE_KEY}"}` vào `mcp.kaggle` vẫn "Unauthenticated" sau reconnect → cần điều tra tiếp. CLI vẫn là kênh chính.
- **RTX Kaggle (19/10)** = RTX PRO 6000 Blackwell **95GB**, Python **3.13**, torch 2.11+cu128, transformers 5.16.1 — wheel cần cp313/manylinux; builder CPU cũng py3.13.15 → khớp.
- **Lệnh user 19/10 (chốt 5 ngày)**: reasoning BẬT (THINK + ACTION, decode 256 token — 24 token là nguyên nhân cắt thinking exp H2), benchmark khó lên mỗi ngày, self-improving loop có verify ngoài model, DeepSeek tự quyết (push không cần hỏi, cancel phải hỏi user). Nguồn chân lý: `MAIN_QUEST.md`.
- **Kaggle datasets CLI gotchas (19/10)**: (1) title **6–50 ký tự** (dài hơn → fail ngay); (2) `datasets create` **bỏ qua thư mục con** với `--dir-mode=skip` (default) → muốn bundle nhiều cây file thì nén 1 file zip rồi tự extract ở kernel; (3) phải **tạo trước `%TEMP%\.kaggle\uploads`** không thì `No such file or directory`; (4) dùng `-p` path tuyệt đối.
- **`curve_tube` emitter bug**: `bp[0].co` trong Blender 4.2 cần sequence **3** phần tử (x,y,z); emitter truyền 4 (có w) → `ValueError`, rc=0 nhưng không VERIFY_OK. Verify mui2: **42/45 PASS** (bỏ curve_tube, giữ text_3d).
- **Snippet offline playwright v3**: dùng `importlib.metadata.version("playwright")`; dataset mount có thể là zip → tự extract `/tmp/ornith_offline_browsers`; gate V1–V6 fail LOUD (RuntimeError), không fallback gui=False.
- **Dataset zip tự extract (19/10, verified)**: upload 1 file `bundle.zip` (dir-mode skip) → Kaggle tự giải nén thành `bundle/` trong mount `/kaggle/input/<slug>/bundle/...`; extra file top-level (README/build scripts) vẫn nằm cạnh — vô hại. Đây là cách chuẩn ship cây file lớn (browsers 714MB; bench tasks bundle sau này).
- **v20 reasoning SFT design chốt (19/10)**: assistant = `THINK: <1–2 câu>` + dòng cuối `ACTION: <lệnh>`; THINK sinh từ template CÓ KIỂM CHỨNG (label/instruction + toạ độ của chính target, không tự bịa); decode giữa train/eval `max_new_tokens=256` greedy; parser ưu tiên dòng `ACTION:` CUỐI (tránh dính toạ độ trong THINK), fallback bare action (legacy); `prose_leak` = % sample có dòng không-THINK trước action; eval held-out seed 202/offset 90000 giữ nguyên để so chiếu v18/v19.

- **Parser semantics chốt (19/10, MAIN_QUEST §2)**: action = dòng `ACTION:` CUỐI (fallback bare legacy); toạ độ trong THINK KHÔNG được lấy làm action; `prose_leak` chỉ tính dòng không-THINK **và** không-ACTION trước action — các dòng `ACTION:` cũ tách riêng thành `extra_actions` (không tính leak). `fail_reason`: `no_action_truncated` | `invalid_action` | `empty`. Bản canonical `phase13-gui/reasoning/reason_parse.py`; kernels nhúng bản copy cùng thuật toán; test cross-check chống trôi (22 case).

- **B15 mechanics chốt (local-verified 19/10, playwright 1.58 headless)**: runner MiMo (`bench_v15.run_suite`) đã verify E2E (CLICK/TYPE/KEY Control+* + DONE + checker call): pass 5/5 + fail-bắt 2/2. Chi tiết quan trọng: T07 — sau batch cuối phải End THÊM 1 lần mới thấy item cuối (nếu không: y≈772 ngoài viewport 720); `premature` tự tăng 1 do click-focus (`list.focus()` gắn trong item handler) → checker T07 đừng đòi premature==0, chỉ `clicked==total-1 && clickedcount==total`. T04 range input: click tại x% lệch ±1 (thumb compensation) → arrow chỉnh. T05 clipboard mô phỏng in-page (không cần browser permission), copied/pasted tăng 2 do 2 handler — dùng `match`. Máy local có sẵn playwright 1.58 + chromium + pillow → từ nay có thể verify suite DOM/mechanics TRƯỚC khi đốt GPU Kaggle.

- **B15 verified toàn bộ 19/10 (local)**: 12 task × 3 variant pass hết qua runner thật + 12 kịch bản fail đều bị bắt. Bài học T08: trang errorfix **dịch layout khi hiện div lỗi** — sau submit#1 phải đo lại toạ độ mọi field/nút. T03/T09/T10 đều có "đường giải chuẩn" lấy từ DOM (#tile<target>, #plan<target>+code, #geo JSON cho canvas). Từ nay mọi suite GUI mới: bắt buộc có local_selftest kiểu này trước khi push Kaggle (rẻ, nhanh, độc lập checker).

- **Rollout kernel (TASK-12) — thiết kế chốt 19/10**: episode = goto → screenshot → sample (t0.7/p0.95/256 token) → parse → exec → verify `checker.check_task(page, task_id)` (2 arg!) → chỉ giữ steps của episode WIN; cap MAX_ROWS=480; zip chỉ ảnh được dùng (`rollout_rows.jsonl` + `rollout_summary.json` + `shots/*.png`), path trong zip relative `shots/...`. Bug đã gặp: `suite_check` trong kernel bench cũ fallback nhầm sang legacy check (luôn false) vì check_task ở module `checker` — TỪ NAY mọi verify suite phải import `checker` trực tiếp. Smoke plan: [T01_signup, T05_shortcut, T11_counter] × 1 rep trước khi full.

- **EACCES từ dataset mount (19/10 — bài học cứng)**: /kaggle/input là **read-only + KHÔNG có exec bit** — mọi binary (chromium, headless shell...) copy từ đó sang không chạy được; muốn exec phải COPY sang nơi ghi được (/tmp) rồi `chmod -R u+x`. Nhánh "auto-extract server-side" của dataset làm logic "chỉ extract khi thiếu manifest" của snippet v3 không chạy → path trỏ thẳng vào mount. Snippet v4 xử lý: detect dưới /kaggle/input → copy /tmp/pw-browsers (marker .copy_done_v4) + chmod trước V5/V6. **Từ nay mọi bundle có binary phải chạy qua bước copy+chmod.**
- **Format output v20 (chốt để đọc kết quả B15)**: `[reason tự do]` (có thể nhiều dòng) + (tuỳ mẫu `</think>`) + `THINK: ...` + `ACTION: <cmd>` dòng cuối; có mẫu KHÔNG có `THINK:` (chỉ reason + ACTION). Parser chuẩn (`parse_action_v2`) lấy ACTION cuối, fallback bare → luôn parse được. Các metric `leak`/`legacy_leak` kiểu "dòng đầu" bị vô hiệu hoá (luôn 1.0) — gate v2: parse_rate/trunc_rate/extra_actions/acc (MAIN_QUEST §2.3).
- **Rollout kernel output rows schema** (cho v21): giữ `target` (raw full output) để curate lấy THINK thật; curate (rollout_curate.py) xuất `{task_id, variant, step, rep, image, instruction, think, action, src}` — file `traj.jsonl` cho slot dataset `gui-selfplay` (kernel v20+ đọc file này, fail-soft).

- **Kaggle GPU eval + competition: internet LUÔN off (19/10)**: push `enable_internet: true` với `machine_shape: NvidiaRtxPro6000` + competition bị API trả **400 Bad Request** ngay; kernel CPU cùng competition + internet thì OK (probe `pw-net-probe`: curl 200/pip/apt chạy được). ⇒ Mọi thứ cần mạng phải bundle vào dataset (libs, wheels) + replay offline; đừng thiết kế GPU kernel dựa vào mạng.

- **Image Kaggle thiếu lib chromium (19/10 — bài học cứng #2 sau EACCES)**: `chrome-headless-shell` (Ubuntu 24.04 base) cần `libatk-1.0.so.0`, `libatk-bridge-2.0.so.0`, `libXcomposite.so.1`, `libatspi.so.0` — thiếu → `TargetClosedError: Target page, context or browser has been closed` (browser logs TRỐNG). Builder pass được vì internet + `playwright install-deps chromium`. Chẩn đoán: `ldd chrome-headless-shell | grep "not found"`; thu deps: snapshot `dpkg-query -W` trước/sau install-deps → `dpkg -L` package mới → copy giữ cây đường dẫn → zip; replay = extract vào `/` + `ldconfig`. Materialize symlink trong zip (Windows/Python zipfile làm mất symlink).

- **PowerShell + python inline = bẫy quoting (lần 3)**: `python -c "..."` với escape `"` trong PS 5.1 dễ SyntaxError/nuốt script — LUÔN viết file .py rồi chạy, không inline patch nhiều dòng.

## 6. Dataset upload / loader (22/10 — 3 lần dính, tốn 2.3h GPU)

- **QUY TẮC VÀNG: dataset = 1 file `.zip` duy nhất** (không phải hàng trăm file rời).
  - `kaggle datasets create` với **nhiều file (818)** → **TREO im lặng** (process `kaggle.exe` kẹt vô hạn) ✗
  - Gói ảnh vào 1 zip (6.5MB cho 816 ảnh) → upload **1 phút** ✓✓ (loader tự giải nén `.zip` trong thư mục dataset ✓ → `_resolve` tìm được basename ✓)
- `datasets create/version` **BỎ QUA THƯ MỤC CON** → ảnh trong `images/` **bi mất im lặng** ✗ (dataset chỉ còn `.jsonl`).
  - Sửa: đặt ảnh **phẳng ở gốc** hoặc đóng gói zip ✓
- `datasets version` **KHÔNG cập nhật được file `.jsonl`** (giữ nguyên 0 byte ✗) → **tạo slug MỚI** ✓
- `kaggle datasets download` **hay TREO khi output bị redirect** (pipe/Select-String) ✗ → dùng **Python API** (`scripts/fetch_dataset_files.py`) ✓
- API **rate-limit 403** khi gọi dồn ✗ → giãn nhịp + cache ✓ (`scripts/list_ds_files.py` có phân trang ✓)
- **VERIFY SAU MỖI LẦN UPLOAD**: đếm file + **so hash** dataset với local (`scripts/verify_ds_matches_local.py`) ✓ — không tin thông báo "success" ✗

## 7. Loader + train: im lặng là mất data (22/10)

- **Loader được bắt buộc FAIL-LOUD**: nếu có row không resolve được ảnh → `raise SystemExit` ✗ **không được** bỏ qua im lặng.
  - Thực tế: dataset traj 972 dòng **0 ảnh** → loader im lặng → train với dữ liệu rỗng, **không ai biết**.
  - Guard này **cứu 2.3h GPU** ✓ (chặn đúng lúc đó) ✓
- **Sau mỗi lần đổi dataset/loader: chạy 1 kernel 2-3 phút để kiểm tra số row resolve** ✓ (đừng push train 2.5h rồi mới biết ✓)
- **Câu cứng seed (PLAN.md §X) phải ENFORCE trong code, không chỉ ghi ra** ✗: v21/v22 dùng seed cố định (101/202/303/13/7) ✗ → đã đổi `SEED = random.randint(1, 10**9)` + log + ghi result ✓

## 8. Suy luận (thinking) — đọc RAW, đừng đoán (22/10)

- **`max_new_tokens=24` CẮT CỤT lời nghĩ** ✗ → tưởng model "nghĩ thay vì hành động" ✗ → **đọc RAW trong trace** ✓ mới thấy model nghĩ **rất đúng** (`ACTION: KEY right` ✓) → chỉ thiếu `ACTION:` ở một số bước ✗
- Suy ra: **`max_new_tokens` là TRẦN, không phải chi phí cố định** (model dừng ở EOS ✓) → **tăng lên 512 là gần như miễn phí** ✓
- **Greedy + state đứng yên = vòng lặp vô hạn** ✗ (cùng input → cùng output) → cần **fallback**: (a) quét text lấy action bare, (b) **sinh lại 1 lần với temperature > 0** ✓
- **Đừng bỏ "nghĩ" chỉ vì 1 recipe (think) fail** ✗ — v20 fail ở B15 nhưng trace desktop cho thấy model nghĩ đúng ✓ → **giữ reasoning + sửa parser/fallback** ✓

## 9. Môi trường computer-use thật (desktop-env) — bẫy đã gặp

- `chromium-browser` trên image Kaggle = **wrapper SNAP** (không chạy) ✗ → lấy chromium từ bundle `ornith-offline-browsers` ✓
- Chromium bundle **KHÔNG mở port `--remote-debugging`** ✗ → dùng **`playwright.launch(headless=False)`** ✓ (vẫn là cửa sổ X11 thật ✓ → xdotool bấm được ✓)
- Bắt buộc `os.environ['DISPLAY']=':99'` trước khi launch ✗ (thiếu → *"Missing X server or $DISPLAY"*) ✓
- **Lệch 86px** do thanh công cụ browser ✓ → cắt ảnh theo viewport ✓ (quan sát của agent = đúng vùng trang ✓)
- Kernel **GPU + competition KHÔNG được bật internet** ✗ (400 *"Internet cannot be enabled for this competition with the current accelerator"*) ✗ → cài tool offline qua dataset `.deb` ✓ (`ornith-gui-xdotool`)
- **Đo được năng lực thật**: model **đọc đúng giá trị ngẫu nhiên trên màn hình** ✓ (T26_clipboard 19/20 = 95% ✓) — tức là hướng "sinh data app thật có biến ngẫu nhiên" **đúng** ✓
- Metric 3D **"knife-edge"** (click sát mép bbox) → 0.65 vs 0.27 chỉ chênh 10-20px ✗ → **3D không phải thước đo tốt lúc này** ✓ (ưu tiên GUI ✓)

## 10. Vận hành / đa agent (22/10)

- **BUS tin nhắn tức thì** (`scripts/bus.py` + `bus_post.py` + `watch_bus.py`): tin đến **~1s** ✓ và **đẩy thẳng vào session OpenCode** (API `POST /api/session/<id>/prompt` ✓, auth trong `~/.config/opencode/service.json` ✓) → agent nhận tin mà không cần poll ✓
- `agent.md` viết kỹ thuật + ký tự lạ → người đọc hay bị lỗi font ✗ → **sinh `LOBBY_DIGEST.md`** (tự động ✓) làm bản đọc được ✓
- **2 acc × 2 session GPU** = 4 slot song song ✓ (rẻ hơn VPS GPU ✓) — nhưng **chạm trần 2 session/acc** ✓ → queue tự retry ✓
- **Ổ đĩa**: local chỉ giữ **thứ cần thiết** (adapter + log + kết quả + code) ✗ không lưu dataset (đã có trên Kaggle/USB) ✓; dọn VS Code + cache Chrome + npm-cache ✓
- **Tự bật lại khi bật máy**: `.cmd` trong **Startup folder** → `scripts/start_all.ps1` (đọc key từ `HKCU:\Environment` ✓ — **không ghi key vào file** ✓)
- **Máy RTX không có internet** ⇒ base model **giữ trên Kaggle** ✓; chuẩn bị dataset + wheels trên USB/ổ ngoài ✓; **vLLM** (`ENV_VLLM_URL` ✓) là đường tăng tốc cho RTX (9B bf16 ~20GB, RTX 96GB ✓)

## 11. Hết quota GPU + chuyển account (22/10) — bài học vận hành

**Sự kiện:** acc `khoadangnguye` hết quota GPU (used 30,08h / 30,00h, `refreshAt 2026-10-24T00:00`) → mọi `kaggle kernels push` bị từ chối: *"Maximum weekly GPU quota of 30.00 hours reached"* (ngay cả kernel **chưa từng chạy** ✗).

**Quy tắc mới:**
1. **Check `kaggle quota` (2 acc) TRƯỚC mỗi ngày train** — không phải giữa ngày ✗. Hết quota ⇒ **chuyển pipeline sang acc còn quota** (đây là lý do có 2 acc từ đầu ✓).
2. **Acc B KHÔNG mount được dataset PRIVATE của acc A** ✗ → Kaggle báo *"The following are not valid dataset sources and could not be added to the kernel"* **nhưng vẫn báo "successfully pushed"** ✗ ⇒ kernel chạy nhưng thiếu dữ liệu ⇒ chết âm thầm ⇒ **luôn `preflight_ds.py` trước khi push** (đọc `dataset_sources` trong `kernel-metadata.json` → `kaggle datasets status` từng dataset → FAIL nếu chưa READY ✓).
3. **Copy dataset A→B**: `kaggle datasets download` (1 file zip, đã gom thư mục con ✓) → unzip → **copy file `.jsonl` ra TOP-LEVEL staging** (loader đọc `base/<fname>.jsonl` ✗ nếu nằm trong zip ✗) → staging = `<fname>.jsonl` + `<slug>.zip` + `dataset-metadata.json` (2 file ✓) → `datasets create` (mới) hoặc **`datasets version`** (đã tồn tại ✗ — **"title already in use" ⇒ CLI trả rc=0 ✗ ⇒ phải tự gọi `version`** ⚠️).
4. **Tên dataset trên acc B phải GIỮ NGUYÊN** (chỉ đổi owner) ⇒ loader so khớp theo tên thư mục mount (`/kaggle/input/<tên-dataset>`) ⇒ code không phải sửa ✓.
5. **`kaggle kernels delete` cần đúng chữ `yes`** (`echo y|` ✗ bị từ chối) ⇒ `cmd /c "echo yes|kaggle kernels delete ..."` ✓.
6. **Không có `kaggle kernels cancel`** ✗ (CLI không có) và **endpoint nội bộ `KernelsCancel` trả 404** ✗ ⇒ muốn dừng 1 run thì phải **chấp nhận để nó chết** (thiết kế code để **fail-loud sớm** ✓ để tốn ít quota nhất) ⇒ **luôn đặt guard fail-loud ở đầu** (đọc dataset → fail trước khi tốn GPU) ✓.
7. **2 session GPU / acc**: `Maximum batch GPU session count of 2 reached` ⇒ push bị từ chối ⇒ **queue phải phân biệt ưu tiên** (train đứng đầu, phép đo bench sau) ✓.

## 12. Loader: phải quét CẢ thư mục dataset gốc (22/10 — 816/816 row mất)

- `r["image"]` trong jsonl có thể là **chỉ basename** (`click_button_...png`) trong khi file thực nằm ở **subdir** (`traj_images/`) ⇒ `_resolve` chỉ quét `ext/` (thư mục giải nén zip) ⇒ **0/816 resolve** ⇒ guard fail-loud dừng (may mắn) ⇒ **không phải lỗi upload, mà là lỗi quy ước đường dẫn**.
- **Fix đúng**: `_resolve` phải thử theo thứ tự: `base/rel` → `ext/rel` → **quét basename trong `ext/`** → **quét basename trong `base/`** ✓ (áp cho mọi loader: `kernel_v23`, `kernel_v23b`, `kernel_v24`, + bản `phase14-space/`).
- **Quy tắc chung**: *dataset nào có ảnh nằm trong subdir ⇒ jsonl phải ghi đường dẫn đầy đủ, hoặc loader phải quét basename ở cả 2 nơi* ⇒ **không bao giờ giả định ảnh nằm ở gốc dataset** ✗.
- **Ghi chú**: `datasets version` **KHÔNG cập nhật được file `.jsonl` ở gốc** (chỉ zip/subdir mới đổi được ✗) ⇒ mọi dataset phải để **`.jsonl` ở top-level + ảnh trong 1 file `.zip`** ✓ (đã áp dụng ✓).

## 13. Số liệu desktop: phân biệt lỗi HẠ TẦNG với lỗi MODEL (22/10 — đính chính lần 7)

- **"Ảnh đen" KHÔNG phải lỗi X11/CDP** ⇒ là **hệ quả của việc thiếu file app** (kernel build từ source cũ, app mới chưa inline) ⇒ **không có browser nào mở** ⇒ màn hình X11 rỗng ✓ (bằng chứng: log ghi *"khong tim thay app -> dung env hien tai"* + không có dòng *"app opened"*).
- **Hệ quả đo lường**: mỗi task mất app ⇒ **40/120 ep** (split B) hoặc **40/80 ep** (split A) bị tính nhầm là *"model thất"* (DONE + reward −1) ⇒ **mọi số liệu desktop cũ bị nhiễm** ⇒ **không dùng làm baseline** ✓.
- **Nguyên tắc đã vào code**: (1) `write_apps()` **guard fail-loud** (thiếu app >200 byte ⇒ `SystemExit` ngay đầu, **không đốt 6h GPU trên ảnh đen**) ✓; (2) harness **tách lỗi hạ tầng khỏi lỗi model**: app thiếu/browser không mở ⇒ **bỏ qua episode (không gọi model)** + `infra_errors.json` + `valid=False` ⇒ **không làm nhiễu mẫu số** ✓; (3) `raw`/`raw_first` cắt 200 → **2000 ký tự** (trước cắt 88/200 ⇒ mất thông tin lỗi) ✓.
- **Bài học chung**: *trước khi kết luận "model làm hỏng", phải hỏi "môi trường có đúng không?"* ⇒ **1 task phải được đối chiếu bằng CẢ 2 đường (local + Kaggle)** trước khi kết luận ✓ (đã áp dụng ✓).

## 14. Recipe: đo đúng "P(DONE)" trước khi tốn GPU (22/10 — @GLM)

- **Sai lầm cũ**: đếm **row DONE** ⇒ coi 816 row = 816 episode ⇒ P(DONE) sai (v22 10,7% / v23a 80,2%) ✗. **Đúng**: episode = **tên file** (`..._v00_s0.png` ⇒ episode `v00`, step `s0`) ⇒ traj = **216 episode**, 60 có DONE = 27,8% ✓.
- **Chỉ số đúng**: **P(DONE | bước cuối của episode nhiều bước)** trên mẫu 739 ep ⇒ v22 **16,4%** → v23a (`targeted dr0.75`) **68,9%** → **v23a + R2 = 83,6%** (tốt nhất) ⇒ **khuyến nghị: duyệt R2 + v23a, bỏ biến thể "long 250 ep"** (P(DONE) không tăng, chỉ tăng chi phí: +2365 row) ✓.
- **Bài học**: *đo P(DONE) trên tập episode nhiều bước, không đếm row* ⇒ **trước 1 lần train 2h, hãy đo chỉ số này trên data** (rẻ hơn nhiều) ✓.

## 15. Đo xong thì PHẢI kiểm tra "độ dễ của benchmark" (22/10 — ô 2×2)

**Bài học lớn nhất về benchmark:** khi một agent sửa task (để task hợp lệ), **độ khó của suite có thể đổi mạnh** ⇒ mọi mốc cũ trên suite đó **không comparable** nữa.

**Số đo thật (ô 2×2, cùng adapter v22 · cùng harness REASON_MAX 256 · chỉ khác bộ task):**

| bộ task | kết quả |
|---|---|
| task **CŨ** (trước khi sửa) | 3/18 = **16,7%** |
| task **ĐÃ SỬA** | 10/18 = **55,6%** |

⇒ **sửa task làm suite DỄ HƠN +38,9 điểm** ⇒ "v22 hơn v18" (0% → 55,6%) vẫn đúng **vì cả hai đều đo trên bộ ĐÃ SỬA** ✓ ⇒ nhưng mọi so sánh lịch sử trên bộ CŨ là **vô nghĩa** ✗.

**Quy tắc mới (bắt buộc):**
1. **Sửa task ⇒ bắt buộc đo lại (old vs new) bằng cùng adapter + cùng harness** ⇒ ô 2×2 2×2 là **một phép đo bắt buộc**, không phải phép đo tùy chọn ✓ (chính xác 4 cell: {adapter cũ, adapter mới} × {task cũ, task mới} ✓).
2. **Vì sửa task làm dễ ⇒ phải BÙ bằng task khó hơn** (luật "bench khó hơn mỗi ngày" ✓): giữ nguyên task, thêm biến thể + độ khó (nhiều bước, giá trị phải đọc từ màn hình, distractor) ✓ ⇒ **đừng coi suite đã sửa là "chuẩn" khi nó vừa dễ đi 39 điểm** ✗.
3. **Tái lập phải được chứng minh, không giả định**: cùng suite, 2 account khác nhau → **10/18 và breakdown từng task IDENTICAL** ✓ ⇒ **pipeline đo là deterministic** ✓ ⇒ **tin được số** ✓ (nếu lệch → có bug hạ tầng ✗).
4. **Thời gian chạy là tín hiệu**: suite CŨ 6229s vs ĐÃ SỬA 2514s ⇒ suite khó hơn cũng khiến model **lặp nhiều hơn** (nhiều bước × lỗi loop) ⇒ **thời gian chạy tăng = cảnh báo loop** ✓.

## 16. Quyết định vận hành: bỏ HF PRO (22/10)

- **User: "khỏi HF pro đi"** ⇒ HF **Docker Space không dùng được** (Space mới cần PRO → 402/403; Space cũ bị *"Flagged as abusive"* → disable) ⇒ **đã dừng `space_revive.py` + `space_sync_docker_loop.py`** ✓ (không còn vòng lặp gọi API vô ích ✓).
- **Còn lại**: Space **tĩnh** (`himagayem-ornith-agent.static.hf.space`) chạy làm **dashboard/mirror** ✓ (`space_sync_loop.py` giữ nguyên ✓) + bản web "sống" chạy ở **máy local** (`127.0.0.1:4096` ✓) + **đường VPS** (`VPS_DEPLOY.md` ✓ — Docker + Caddy + OpenCode, 1 lệnh ✓, tái dùng `phase14-space/_push_docker/` ✓).
- **Bài học**: *khi một hạ tầng ngoài bị chặn bởi gói cưỡng/điều khoản dịch vụ, hãy dừng vòng lặp retry ngay* (nó chỉ đốt API + ý chí ✓) ⇒ **luôn có đường dự phòng local + tĩnh** ✓.

## 17. Kaggle giới hạn theo CỬA SỔ THỜI GIAN, và 429 tự gây ra (22/10 — @MiMo phát hiện, đo được)

**1) "2 phiên GPU" KHÔNG phải "2 phiên đồng thời" — mà là 2 phiên trong một CỬA SỔ THỜI GIAN:**
- Bằng chứng: log watchdog lúc 11:25→11:54 vẫn báo *"da du 2 session GPU, cho"* trong khi **cả 2 kernel vừa COMPLETE** và `kernels list` ⇒ **0 kernel RUNNING** ⇒ ⇒ **Kaggle vẫn tính 2 phiên vừa xong ⇒ có COOLDOWN ⇒ "slot trống trên CLI" ≠ "slot push được"** ✗.
- **Hệ quả vận hành**: acc B **không** chạy liên tục N kernel ⇒ **xếp 1-2 kernel mỗi lần** ✓, đọc log trước khi xếp tiếp ✓. Và **mỗi kernel nhỏ (replication/smoke) cũng chiếm 1 phiên trong cửa sổ** ⇒ 1 phép đo lặp có thể **chặn cả pipeline** ✗ ⇒ **đừng chạy replication khi còn kernel quan trọng đang chờ** ✓.

**2) 429 (rate limit) do watchdog tự gây ra:**
- Nguyên nhân: watchdog kiểm tra dataset cho **mọi mục queue** (9 dataset × 13 mục ≈ **117 lệnh Kaggle mỗi vòng 60s**) ⇒ **tự hủy rate-limit của chính nó** ⇒ mọi lệnh Kaggle *khác* (tải adapter 465MB ✓, list kernel ✓) đều 429 ✗.
- **Fix**: **cache 30′ theo slug** (`dataset_exists` trong `scripts/watchdog.py` ✓) ⇒ log watchdog **12 dòng/vòng → 4** ⇒ **giảm ~30× số lệnh API** ✓ ⇒ 429 hiếm ✓.
- **Quy tắc cho agent**: (a) **đừng chạy lệnh Kaggle hàng loạt song song với watchdog** ✗; (b) gặp 429 ⇒ **chờ 1-2′ rồi thử lại** ✗ (đừng retry liên tục ✗ — retry liên tục càng làm nặng ✗); (c) **phối hợp trước khi tải/upload file lớn** (465MB × 2 agent = 930MB + 429 ✗) ⇒ **ghi "đang làm" lên bus trước** ✓.

**3) `kaggle datasets status` trả 403/404 khi dataset đang processing ⇒ false positive ✗** ⇒ **dùng `kaggle datasets files` để đợi READY** ✓ (đúng như `scripts/publish_lora.py` ✓).

**4) Mẹo đọc log Kaggle**: file log là **1 JSON array** (không phải mỗi dòng 1 JSON ✗) ⇒ `json.loads(whole_file)` ✓ (`scripts/klog2.py` ✓).

## 18. LUẬT MỚI TỪ USER 22/10 — độ khó bench · mục tiêu đo · RL/GRPO · nhịp chấm điểm

**Nguồn chuẩn: `PLAN.md` § W** (đã chèn ✓) + LONGMEMORY này (bài học) + `agent.md` LOBBY (agent phụ đọc ✓).

**1) "Bộ bench mới phải THỰC SỰ khó hơn — gấp 5-10× là ít":**
- Bài học nền: sửa 15 task (22/10) làm B15,5 **dễ hơn 39 điểm** ⇒ tạo "cải thiện giả" ⇒ **độ khó phải ĐO, không CẢM NHẬN** ✓.
- **Công thức**: `ĐỘ_KHÓ(bộ mới) = win_rate(bộ cũ) / win_rate(bộ mới)` ⇒ chỉ chuẩn khi **≥ 3 (mục tiêu ≥ 5)** VÀ `win_rate(bộ mới) ≤ 20%` (mục tiêu ≤ 10%) ⇒ + 3 tiêu chí nữa (model mới ≤ 30% ✓, v18 ≤ 10% ✓, không rò đáp án ✓, ≥ 1/3 task là bẫy ✓).
- **Cấm tuyệt đối**: bộ mà model hiện tại vẫn ≥ 50% ⇒ gọi là "bộ khó" ✗.

**2) "Benchmark đó làm chấm cái gì?" — bảng năng lực 10 mục** (§ W2 ✓):
read-before-act ✓ · nhiều bước ✓ · **phá vòng lặp** ✓ (chưa có task nào ✗) · phục hồi sau lỗi ✓ · clipboard (95% ✓) · điều hướng phím (0/20 ✗) · scroll ngoài viewport ✓ · distractor ✓ · 3D grounding ✓ · **desktop thật** ✓.
⇒ Mọi báo cáo bench **phải in bảng theo năng lực** ✓ (không chỉ tổng win rate ✓).

**3) "Ngoài SFT thì cho RL/GRPO nữa" (§ W3 ✓):**
- GRPO cho GUI: prompt = (ảnh, instruction) ✓; G=8-16 mẫu/prompt ✓; **reward verifiable** (đúng GT ✓ / bbox overlap ✓ / khớp hành động đã ghi ✓); advantage `(r-mean)/std` ✓; KL với adapter SFT (β=0.01-0.05 ✓); TRL `GRPOTrainer` ✓ + Unsloth ✓ (wheels có `trl-1.14.1` ✓).
- **3 ràng buộc sống còn**: reward set **TÁCH** tập eval ✓✓ (không trùng prompt ✓) · luôn gate bằng bench **thật** (chống reward hacking ✓) · sau mỗi lần RL chạy **suite rẻ** (chống suy thoái ✓).
- Chi phí ~300 prompt × 8 = 2400 generation ≈ **1-2h GPU** ⇒ xen kẽ SFT ✓.

**4) "Mỗi vài lần train chấm điểm 1 lần" (§ W4 ✓):**
- Trong train: eval nội bộ (free ✓) · **mỗi 2-3 lần train**: 1 suite rẻ (B15,5 18 ep ≈40′ ✓) · **mỗi 3-4 lần train / trước khi chốt phiên bản**: full gate (36+18+24+30 ep ✓) · **sau mỗi lần RL**: full gate bắt buộc ✓ · **mỗi lần sửa bench**: ô 2×2 bắt buộc ✓.
- Lý do: quota acc A đã **0/30h** ⇒ không thể chấm full mỗi lần ✓ ⇒ **nhịp + quy trình là luật** ✓.

**5) Bài học bổ sung (từ 2×2):** khi đo "task cũ vs task mới" trên **cùng adapter**, ta tách được **phần do data** vs **phần do benchmark** ⇒ **mọi phát biểu về "model mạnh hơn" phải kèm 1 ô 2×2** ✓ (v21→v22 = **+11,1 điểm trên bộ cũ** và **+11,2 trên bộ mới** ⇒ cải thiện thật ✓, trong khi "+50 vs v18" là hệ quả benchmark dễ hơn ✗).

## 19. Google Colab CLI là GPU thứ 2 (22/10 — mở ra ~25h GPU/ngày từ 5 acc)

**Bối cảnh:** acc Kaggle A hết quota (0/30h, reset 24/10) ⇒ cần GPU thay thế ✓. `google-colab-cli` (CLI **chính thức** Google, 6/2026 ✓) chạy được **trên Windows** ✓ (README ghi "Linux/macOS only" ✗ — nhưng test thật thì OK ✓).

**5 bài học vận hành (đều đã dính thật):**
1. **Token OAuth lưu ở đường dẫn HARDCODE global** `~/.config/colab-cli/token.json` (`auth.py:54` ✓) ⇒ **mỗi acc = 1 bộ token riêng** ⇒ phải **swap token** (copy acc→global trước lệnh CLI ✓, ngược lại sau ✓) ⇒ `scripts/colab_accounts.py` ✓.
2. **`colab upload` (endpoint `contents`) trả 500** ✗ (thử 4 lần ✓) ⇒ **tránh upload** ✗ ⇒ **host data trên HF dataset repo PUBLIC** (`scripts/hf_host_data.py` ✓) ⇒ VM `wget https://huggingface.co/datasets/<repo>/resolve/main/<file>.zip` ✓ **không cần token** ✓ (đã test HTTP 206 + magic ZIP ✓). *Space tĩnh thì **private ⇒ 401** ✗ nên không dùng được ✓.*
3. **`colab exec` có timeout phía CLIENT** (~25-30′) ⇒ job dài **mất output** ✗ (script vẫn chạy trên VM ✓ nhưng ta không thấy log ✓) ⇒ **chạy nền + ghi log ra file** ✓ (`nohup ... > /content/out.log` ✓) rồi `colab download` ✓.
4. **File gửi lên VM KHÔNG ĐƯỢC CÓ BOM** ✗ (PowerShell 5.1 `Out-File -Encoding utf8` **thêm BOM** ✗ → `SyntaxError: invalid non-printable character U+FEFF` ✗) ⇒ tạo `.py` bằng **UTF-8 không BOM** ✓ (dùng `write` tool ✓) — *cùng bài học "BOM trong metadata Kaggle" ✓ ⇒ **luôn kiểm BOM trước khi gửi/ghi file** ✓.*
5. **Session có thể chết giữa chừng** ✗ (404/401 ✓ ⇒ phải tạo lại ✓) ⇒ **luôn có script dựng lại + kiểm tra `colab sessions` ✓**.

**Giới hạn cứng của T4 (free):** VRAM 16GB ⇒ model 10B **bf16 (~20GB) không vừa** ⇒ **bắt buộc 4-bit QLoRA** ⇒ **số liệu KHÔNG so sánh được** với run bf16 Kaggle ✗ ⇒ dùng cho **train thử / ablation / so sánh nội bộ** ✓; muốn bf16 ⇒ **Colab Pro (A100/L4)** ✓. CPU **2 core** ✗ ⇒ không sinh data CPU-heavy trên VM ✓ (tạo sẵn ở Kaggle rồi host ✓).

**Quy mô:** 5 acc × ~5h/ngày = **~25h GPU/ngày** ✓ ⇒ **5 biến thể recipe/seed/dữ liệu song song trong 1 ngày** ✓ (thay vì 1 ✓).

**Bài học chung (nhớ lâu):** *khi một nguồn compute bị chặn (quota/giới hạn), hãy tìm **backend thứ 2** và **đo sức chứa thật của nó** trước khi hứa hẹn ✓* — và **luôn kiểm tra bằng chạy thật** ✓ (4 lỗi hôm nay đều là loại "im lặng" ✓).

## 21. OpenChat: chat trực tiếp giữa các session OpenCode (23/10)

**Bối cảnh:** agent phụ chạy ở session riêng; muốn trao đổi phải ghi LOBBY/bus rồi chờ agent khác poll ⇒ trễ, dễ mất tin. Yêu cầu: "agent từng session trò chuyện trực tiếp".

**Cách làm:** app desktop riêng (`scripts/oc_chat/`) chạy trên **local HTTP API của OpenCode**, không sửa app gốc (app là Electron đã build, không có source trong repo):
- `engine.py`: dò port OpenCode bằng `netstat` + probe `/api/info` (port **đổi mỗi lần mở app** — hardcode 45278 là chết), cache 60s; map `agent → session` theo keyword, lưu `agents.json`.
- `server.py`: HTTP + SSE + 2 thread nền (bus watcher, reply poller). User gửi → `POST /api/session/<sid>/prompt`; agent trả lời → mirror vào phòng + **relay ngược** về session người hỏi nếu tin gốc có `--from`.
- `app.html`: UI 3 cột (phòng / feed / trạng thái), không dependency.

**Bài học kỹ thuật (đã dính thật):**
1. **Không hardcode port** của app desktop — mỗi lần khởi động lại đổi port; `watch_bus.py` từng chết im lặng vì 45278 (log `oc_session loi: connection refused`).
2. **Chrome headless trên máy này không trả output với URL localhost** (data: URL thì OK) ⇒ dùng **Edge/Playwright bundled** để test UI; luôn kiểm tra `pageerror` + screenshot thay vì tin "exit 0".
3. **Không `taskkill /F /IM chrome.exe`** — giết cả browser của user. Nếu cần, chỉ kill PID mình vừa spawn.
4. **Server khởi động trong shell bị timeout sẽ bị kill theo job** ⇒ chạy detached (`cmd /c start /b pythonw ...`) để sống qua các lần gọi.
5. **Bus bị trùng tin** (notify_agents + lobby sync post 2 lần) ⇒ dedupe `(kind, from, text[:200])` trong 120s.
6. **State file cũ schema khác** (`str` vs `dict`) làm watchdog crash `'str' object has no attribute 'get'` ⇒ luôn **normalize khi load**, đừng tin format cũ.

**Quy ước mới:** agent muốn nhắn agent khác → `python scripts/chat_send.py <Tên> "..."` (không cần chờ LOBBY). Broadcast vẫn `bus_post.py`; `--to` để gửi riêng.


## 22. B17 benchmark + quota-reset traps (23/10)

- **B17 = 9 task (T30-T38), 23 capabilities, 27 ep (3 variant).** Apps + checker
  da co tu truoc; thieu package Kaggle. Da tao dataset `dieniw/ornith-gui-bench-b17`
  + kernel `dieniw/ornith-gui-bench-b17-v22` (SCROLL/MOVE/DRAG). Local GT 9/9.
- **2x2 (GLM):** sua task +38.9 diem, sua data +11.1, interaction 0 => uu tien
  benchmark/task gap hon recipe. Desktop 13.3%, stuck 76.7% (loop).
- **Quota Kaggle reset 00:00 UTC**, may local la UTC+7 => 07:00 local. Parse
  `refreshAt` phai gan `tzinfo=UTC`, neu khong watchdog push som 7h va cache
  6h co the giu 0h qua moc reset.
- **v25b phai chay acc B** (`dieniw/ornith-gui-sft-v25b`), khong phai A: toan bo
  17 source da doi sang B-owned. A quota 0 khong anh huong.
- **Kaggle zip:** CLI bo qua subdir; zip `<ten>.zip` chua `<ten>/...` co the ra
  `<ten>/<ten>/...`. Kernel phai walk tim `tasks.json`/`checker.py`, dung tin
  duong dan tuyet doi trong file list.
