# HƯỚNG DẪN: CHẠY ORNITH TRÊN MÁY RTX **KHÔNG CÓ INTERNET**

> Máy RTX của bạn **không có internet** → mọi thứ phải chuẩn bị trước ở máy có internet
> (hoặc 1 lần có mạng trên chính máy RTX) rồi copy sang.

---

## 0. Tóm tắt

| Việc | Cần internet? | Ghi chú |
|---|---|---|
| **Train** (`gui_sft_v22.py`) | ❌ KHÔNG | chỉ cần base + dataset + wheels + code |
| **Bench** (B15/B15.5/B16/3D) | ❌ KHÔNG | cần thêm browser offline (bundle) |
| **Desktop-env** (computer-use thật) | ❌ KHÔNG | cần Xvfb + browser offline |
| Watchdog (push kernel Kaggle) | ✅ CÓ | tắt khi offline |
| Space sync (đẩy state lên HF) | ✅ CÓ | tắt khi offline |
| Bus (trao đổi nội bộ) | ❌ KHÔNG | localhost, vẫn chạy ✓ |

---

## 1. Chuẩn bị bundle (máy CÓ internet, 1 lần)

> **Cập nhật 22/10 (theo yêu cầu user): KHÔNG tải 4 shard base model về máy này.**
> Base model **giữ trên Kaggle** (`dieniw/ornbase-s1..4` ✓).
> ⇒ USB chỉ chứa: `input/` (dataset) + `wheels/` (pip offline) — **~1.9GB** ✓
> ⇒ **Lưu ý**: nếu RTX thật sự phải train OFFLINE thì **cần 4 shard base (18GB)**
>   đặt cạnh máy (copy từ Kaggle về máy có mạng, hoặc dùng ổ ngoài 20GB+ ✓).
>   Không có base thì không load được model → không train offline được.

```powershell
# 1.1. tạo thư mục đích trên USB (ví dụ D:\ornith-offline)
python scripts\prepare_offline_bundle.py --dest D:\ornith-offline --only input
python scripts\prepare_offline_bundle.py --dest D:\ornith-offline --only wheels
# (KHÔNG chạy --only base: base ở lại Kaggle)
```

Kết quả:
```
D:\ornith-offline\
├─ base\          4 shard model (model-0000X-of-00004.safetensors + config + tokenizer)
├─ input\
│  ├─ gui-selfplay\            (118 row self-play)
│  ├─ ornith-policy-replay-data\ (332 row task-thật + ảnh)
│  ├─ ornith-gui-train3d\       (600 row 3D)
│  ├─ ornith-gui-train3d-hard\  (600 row 3D khó)
│  ├─ ornith-gui-real-ui\       (792 row)
│  ├─ ornith-gui-real-fixtures\ (42 row)
│  ├─ ornith-gui-traj\          (816 row)
│  ├─ ornith-gui-bench-v155\    (suite B15.5 ĐÃ SỬA)
│  ├─ ornith-gui-bench-v16b\    (suite B16 ĐÃ SỬA - bỏ lộ đáp án)
│  └─ ornith-offline-browsers\  (bundle chromium + deps)
├─ wheels\       unsloth/peft/transformers/trl/bitsandbytes (.whl)
├─ MANIFEST.json
└─ RUN.md
```

## 2. Copy sang máy RTX
- Copy **toàn bộ** thư mục `D:\ornith-offline` (USB/ổ ngoài/mạng nội bộ 1 lần).
- Copy **thư mục dự án** (`New folder`) — cần: `phase13-gui/`, `phase14-desktop/`, `phase14-blender/`, `scripts/`, `agent.md`, `PLAN.md`, `STATUS.md`, `MAIN_QUEST.md`, `result.md`.
- **KHÔNG cần** copy: `phase14-space/`, `scripts/logs/`, các thư mục `out_*` (trừ khi muốn xem lại kết quả cũ).

## 3. Cài thư viện (1 lần, offline)
```powershell
pip install --no-index --find-links "D:\ornith-offline\wheels" unsloth peft transformers trl bitsandbytes accelerate
pip install pillow numpy      # nếu chưa có (đã sẵn trong image Kaggle)
```

## 4. Biến môi trường (đặt vào `.env` hoặc set trước mỗi lần chạy)
```powershell
$env:ORNITH_WORK   = "D:\ornith-offline\work"
$env:ORNITH_BASE   = "D:\ornith-offline\base"
$env:ORNITH_INPUT  = "D:\ornith-offline\input"
$env:HF_HUB_OFFLINE    = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HF_DATASETS_OFFLINE = "1"
```

## 5. Train
```powershell
python phase13-gui\kernel_v22\gui_sft_v22.py
```
- Kết quả: `$env:ORNITH_WORK\gui_result.json` (acc + **seed** + recipe) ✓
- Adapter LoRA: `$env:ORNITH_WORK\gui_lora\` ✓ (đưa sang máy khác / Kaggle được)
- **Câu cứng PLAN.md §X**: seed mỗi lần train ✓ (code đã tự random ✓ — **đừng sửa thành seed cố định** ✗)

## 6. Bench (đo trên chính máy RTX)
```powershell
# cần PLAYWRIGHT_BROWSERS_PATH trỏ tới bundle đã giải nén
$env:PLAYWRIGHT_BROWSERS_PATH = "D:\ornith-offline\input\ornith-offline-browsers\bundle\browsers\ms-playwright"
python phase13-gui\kernel_bench_v21\bench_v15_kernel.py
```
- Đổi `INPUT_ROOT`/`WORK`/`ORN` trong file theo env ở mục 4 ✓ (đã sửa sẵn cho kernel_v22/v23 ✓; các kernel bench cũ hãy sửa tương tự ✓).

## 7. Desktop-env (computer-use thật) — cũng offline được
```powershell
python phase14-desktop\harness.py --policy dummy --tasks T20_2048   # kiểm tra pipeline
python phase14-desktop\kernel_desktop_proof\desktop_proof.py        # chứng minh chuột/phím thật
```
- Cần: Xvfb + xdotool + imagemagick (cài offline qua apt: `apt-get install xvfb x11-utils xdotool imagemagick` — **cần 1 lần có mạng** ✗ hoặc tải .deb trước ✓).

## 8. Bẫy đã biết (đừng lặp lại)
1. `kaggle datasets create` **bỏ qua thư mục con** → ảnh phải để **phẳng ở gốc** ✓
2. Kaggle **không giải nén zip lồng nhau** → giải nén local rồi upload ✓
3. Kernel chỉ upload `code_file` → thư viện phải **inline** ✓ (mã local đã inline ✓)
4. `for_inference` của unsloth (bản trong wheels) **gọi sai** → dùng `transformers.from_pretrained` + `peft` ✓
5. `dataset-metadata.json` phải **không có BOM** (đừng dùng PowerShell `-Encoding utf8` ✗)
6. Chromium phải `playwright.launch(headless=False)` + `os.environ['DISPLAY']` ✓; **offset 86px** do thanh công cụ → cắt ảnh theo viewport ✓
7. `playwright` cần `PLAYWRIGHT_BROWSERS_PATH` trỏ tới bundle (không có internet để tải browser ✓)

## 9. Còn dùng được gì khi offline
- ✅ Train, bench, desktop-env, bus nội bộ, `scripts/collect_results.py`, `scripts/update_result.md.py` (cập nhật result.md ✓)
- ❌ Watchdog (push Kaggle) · Space sync (push HF) · HF Inference / Mistral / Gemini chat (cần internet) → tắt 2 tiến trình này khi offline ✓

## 10. vLLM tren may RTX (nhanh gap 10-30x so voi `model.generate`)
> User: *"cu cho models nghi, nhieu k sao, tang max-new va co the dung vllm tang toc"*
> -> da thuc hien: `REASON_MAX` 256 -> **512** (moi kernel bench/rollout + harness) va
> harness **tu chuyen sang vLLM** neu co `ENV_VLLM_URL` ✓

### 10.1 Chay vLLM server (1 lan, offline)
```bash
# RTX 96GB: model 9B bf16 (~20GB) fit thoai mai
export HF_HUB_OFFLINE=1
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/ornith-base-or-adapter \
  --served-model-name ornith \
  --port 8000 --max-model-len 8192 --gpu-memory-utilization 0.85
# neu dung adapter: them --enable-lora --lora-modules ornith=/path/to/adapter
```

### 10.2 Tro harness/bench vao vLLM
```powershell
$env:ENV_VLLM_URL   = "http://127.0.0.1:8000/v1"
$env:ENV_VLLM_MODEL = "ornith"
$env:ENV_VLLM_KEY   = "EMPTY"
$env:ENV_REASON_MAX = "512"      # cho model nghi lau hon
python phase14-desktop\harness.py --policy model --tasks T20_2048
```
- Harness dung `VLLMPolicy` (OpenAI-compatible `/chat/completions` + anh base64) -> **khong can load model local** ✓
- `max_new_tokens` la **tran** chu khong phai chi phi co dinh (model dung o EOS) -> tang thoai mai ✓
- Voi vLLM: bat **prefix caching** + **batching** de 4 episode chay song song van nhanh ✓

### 10.3 Luu y khi van dung HF generate (Kaggle GPU)
- Kaggle T4 16GB: model 9B **khong vua** vLLM bf16 -> dung AWQ/4bit hoac giu `transformers` ✓
- Kaggle GPU kernel co **internet OFF** -> vLLM phai cai tu wheels san (dong goi `.whl` vao dataset nhu `gemma12b-wheels` ✓)
