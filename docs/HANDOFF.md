# HANDOFF — 26/10/2026 (GitHub/HF ops)

## Trạng thái hiện tại
- **v25b v9 COMPLETE** trên Kaggle `dieniw/ornith-gui-sft-v25b`, RTX PRO 6000
  Blackwell 95 GB, competition ARC + internet OFF.
  - Train: **8716 samples**, 2.846 epochs, loss **0.1231**.
  - Eval: synth **89/100 = 0.890** (parse 0.99), real **37/42 = 0.881**
    (parse 0.905), train-sub **11/12 = 0.917**, targeted **8/12 = 0.667**,
    selfplay **4/12 = 0.333**, train3d **8/8**, traj **7/16 = 0.438**
    (parse 12/16 = 0.75).
  - Gate: parse/real/train-sub PASS; **traj FAIL (0.438 < 0.85)**.
- **Adapter đã tải + publish**: `dieniw/ornith-gui-lora-v25b` (private,
  465.6 MB `adapter_model.safetensors`, kèm tokenizer/processor/README).
- **B17 v3 đã push** `dieniw/ornith-gui-bench-b17-v22` lúc ~04:12 UTC, trạng thái
  **QUEUED** (kiểm tra 04:46 UTC, chưa có log). Metadata: base4 +
  `ornith-offline-browsers` + `ornith-gui-lora-v25b` + `ornith-gui-bench-b17`;
  RTX/competition/offline. Tổng input ~18.87 GB (< 20 GB).
- **CPU probe Playwright** `dieniw/ornith-pw-probe` đã push (CPU, offline,
  attach `ornith-offline-browsers`) để verify V1-V6 trước khi B17 chạy.
- **v26 đã chuẩn bị local** `phase13-gui/kernel_v26`: y hệt v25b nhưng eval
  decode `EVAL_MAX=256` (sửa artifact traj 24 token). **Chưa queue** — chờ B17
  để quyết định data mới trước khi push.
- **GitHub repo** `easportat2025-blip/ornith-lab` (public) đã có code + workflows.
  Watchdog chạy theo schedule 10 phút; run gần nhất `40253573698` success.
  Issue #2 đang báo v25b COMPLETE, B17 ERROR (bản cũ trước v3).
- **GitHub Actions secrets** đã set: `KAGGLE_USERNAME`, `KAGGLE_KEY`,
  `HF_TOKEN`, `GEMINI_API_KEY(_2)`, `MISTRAL_API_KEY(_2.._5)`,
  `DEEPSEEK_API_KEY`, `GROQ_API_KEY(_2.._6)`, `OPENCODE_API_KEY`.
- **HF chat/state**: `kkouadn/ornith-chat` (private). Code snapshot:
  `kkouadn/ornith-lab-code` (private) — cần upload lại sau commit mới.
- **HF Space** `kkouadn/dual_orchtractor`: PAUSED / flagged abusive; secrets đã
  lưu nhưng runtime không dùng được.
- **Local watchdog đã tắt**; GitHub Actions là nơi chạy 24/7.

## Việc đã làm trong phiên này
- Xác nhận RTX: `NVIDIA RTX PRO 6000 Blackwell Server Edition`, 94.971 GB,
  CUDA true. Không có competition → T4; có competition + internet ON → HTTP 400.
- v25b chạy xong, tải adapter, tạo dataset `dieniw/ornith-gui-lora-v25b`.
- Sửa B17 metadata: thêm offline browsers + adapter v25b, bỏ adapter v22.
- Cập nhật `scripts/llm_fallback.py`: thêm provider `opencode`
  (`https://opencode.ai/zen/v1/chat/completions`, models free), giữ
  Groq/Gemini/Mistral/DeepSeek; User-Agent `ornith-fallback/1.0`.
- Lưu `OPENCODE_API_KEY` vào GitHub Actions + HF Space secrets (không ghi file).
  Free models hiện trả 429 `FreeUsageLimitError`; fallback tự bỏ qua và dùng
  Groq/Gemini. Có thể thử lại khi quota reset.
- Cập nhật `configs/kaggle_queue.json`: v25b done, B17 active.

## Việc đã làm trong phiên này (GitHub environment upgrade)
- **Bật self-dispatch**: thêm `.github/workflows/ops-tick.yml`. Watchdog xong →
  `ops-tick` nghỉ `delay_seconds` (mặc định 600s) → dispatch `kaggle-watchdog`
  (`auto_push=true`) + best-effort `ops-heartbeat`. `schedule: */10` vẫn là
  backup seed. Có retry 3 lần và concurrency guard.
- **Nâng cấp CI**: `.github/workflows/ci.yml` chạy compileall, parse YAML/JSON,
  secret scan, pytest, unittest `scripts/jobs`, headless smoke; pip cache.
- **Môi trường dev**: `.devcontainer/devcontainer.json`, `requirements-ci.txt`,
  `requirements-hf.txt`, `requirements-watchdog.txt`, `pyproject.toml`,
  `.editorconfig`, `.gitattributes`, `.github/dependabot.yml`.
- **Tài liệu/agent**: `AGENTS.md`, `docs/ENVIRONMENT.md`, `SECURITY.md`; cập nhật
  `README.md`, `docs/SECRETS.md`, `docs/GITHUB_HF.md`.
- **HF auto-sync**: `.github/workflows/hf-sync.yml` + `scripts/hf_code_sync.py`
  (chỉ archive file tracked, secret scan trước, zip ≤60 MB, upload private
  `kkouadn/ornith-lab-code`); chat sync docs sanitized lên `kkouadn/ornith-chat`.
- **Watchdog upgrade**: `--download-results` tải result JSON/MD/TXT ≤2 MB cho
  kernel COMPLETE vào `state/results/`, commit lên `ops-state`; issue có cột
  outputs. Trigger thêm khi push queue/metadata/watchdog.
- **Ops status**: `scripts/ops_status.py` in queue/state/secret presence, không
  in giá trị secret. Thêm tests cho secret scan, watchdog, configs, ops status.
- **B17 v3 vẫn QUEUED** lúc 04:46 UTC; chưa có run ID mới để verify self-dispatch.
  Sau khi push sẽ seed `ops-tick` với `delay_seconds=0` và cập nhật run ID.

## Gate v25b (ngưỡng: parse ≥0.95, leak ≤5%, traj ≥0.85, real ≥0.85, train-sub ≥0.90)
| Gate | Kết quả | Đạt |
|---|---|---|
| parse (synth) | 0.990 | ✅ |
| real | 0.881 | ✅ |
| train-sub | 0.917 | ✅ |
| traj | 0.438 | ❌ |
| leak | chưa đo trong log v25b | ? |

**Kết luận**: v25b tốt trên synth/real/train-sub. **Lưu ý quan trọng**: eval
traj-sub trong kernel v25b dùng `max_new_tokens=24` (dòng 451), nên các output
prose bị cắt giữa thinking trước khi ra action — 0.438 có thể là **artifact do
decode ngắn**, không phải model hỏng. B17 dùng `REASON_MAX=512`, là thước đo
thật. v26 nên nâng eval lên 256–512 token và đo lại traj trước khi kết luận.

## Blocker
1. **B17 v3 chưa có kết quả** — đang QUEUED; cần chờ GPU và đọc log.
2. **OpenCode free models 429** (`FreeUsageLimitError`) với cả key user và
   `public`; key đã lưu, có thể thử lại sau.
3. **DeepSeek 402** (hết balance), **Mistral 429** (rate limit).
4. **HF Space PAUSED**, **HF Jobs 402** — không dùng scheduled jobs/relay được.
5. **Completion dataset**: hiện chỉ có competition ARC-AGI-3; nếu “completion
   dataset” là dataset riêng thì cần tên chính xác để gắn thêm.

## Việc tiếp theo
1. **Verify self-dispatch**: push workflow mới, seed `ops-tick` với
   `delay_seconds=0`, xác nhận watchdog run kế tiếp bắt đầu sau ~10 phút, issue
   `[ops] kaggle watchdog` + `ops-state` được cập nhật. Ghi run ID vào đây.
2. Poll B17 v3: nếu RUNNING chờ; nếu ERROR đọc log (Playwright offline,
   adapter load, tasks.json); nếu COMPLETE tải `bench_out`, chạy
   `phase13-gui/gate_report.py`, tính W1 baseline. Watchdog mới cũng tự tải
   result nhỏ vào `state/results/`.
3. So sánh B17 với gate: B15 ≥35%, holdout ≥35%, v14 ≥2/3, B15.5 ≥ baseline.
4. Từ failure của B17 + traj yếu → curate v26 (traj/selfplay/targeted + format
   `THINK` ngắn + `ACTION` dòng cuối), tạo kernel slug mới để watchdog tự push.
5. Cập nhật `docs/HANDOFF.md` + `configs/kaggle_queue.json` sau mỗi thay đổi.
6. Sync HF chat + code snapshot sau commit (workflow `hf-sync` hoặc chạy tay).
7. Rotate PAT/API keys sau khi ổn định; giữ secrets chỉ trong GitHub/HF.

## Lệnh nhanh
```powershell
# trạng thái kernel
python -X utf8 -c "import sys,subprocess; sys.path.insert(0,'scripts'); from upload_staging import env_for; env,_=env_for('dieniw'); print(subprocess.run(['kaggle','kernels','status','dieniw/ornith-gui-bench-b17-v22'],capture_output=True,env=env).stdout.decode())"

# log B17 (JSON lines -> text)
python -X utf8 -c "import sys,subprocess,json; sys.path.insert(0,'scripts'); from upload_staging import env_for; env,_=env_for('dieniw'); p=subprocess.run(['kaggle','kernels','logs','dieniw/ornith-gui-bench-b17-v22'],capture_output=True,env=env,timeout=300); raw=((p.stdout or b'')+(p.stderr or b'')).decode('utf-8','replace'); open('logs/b17_v3.log','w',encoding='utf-8').write(''.join(x.get('data','') for x in json.loads(raw)) if raw.strip().startswith('[') else raw); print('saved logs/b17_v3.log')"

# fallback LLM (keys từ env)
python scripts\llm_fallback.py --prompt "Say OK"

# secret check (không in giá trị)
python scripts\check_secrets.py

# ops status + self-dispatch seed (sau khi workflow có trên main)
python scripts\ops_status.py
# GitHub UI: Actions -> ops-tick -> Run workflow -> delay_seconds=0

# sync HF code snapshot (sau khi fetch origin/main)
python scripts\hf_code_sync.py --ref origin/main
```

## Lưu ý
- Không chạy local watchdog 24/7; GitHub Actions là nơi chạy.
- `ops-tick` ngủ 600s mỗi vòng; repo public dùng runner minutes miễn phí. Nếu
  chuyển private, disable `ops-tick` hoặc giảm tần suất.
- Không commit adapter/output lớn; `.gitignore` đã chặn
  `phase13-gui/kernel_*/output/` và `phase13-gui/lora_v25b_dataset/`.
- Không ghi key vào file; chỉ env/GitHub Secrets/HF secrets.
- Watchdog chỉ auto-push kernel `MISSING`; v26 phải dùng slug mới.
- B17 là holdout; không train trên task B17.
- PAT/API key đã gửi trong chat phải rotate sau khi ổn định.
