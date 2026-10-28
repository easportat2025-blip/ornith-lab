# HANDOFF — 27–28/10/2026 (GitHub/HF ops)

## Trạng thái hiện tại
- **B17 v3 COMPLETE** trên Kaggle `dieniw/ornith-gui-bench-b17-v22` (RTX,
  competition ARC, internet OFF).
  - **15/27 = 0.5556** win; parse **0.8507**; prose leak **1.0**; 201 steps;
    modes action 98 / legacy 73 / none 30; mean_new 80.7; reason_max 512.
  - Per-task: T30_note_order 3/3 · T31_scroll_code 0/3 · T32_drag_slider 0/3 ·
    T33_error_retry 3/3 · T34_tab_nav 0/3 · T35_hover_code 3/3 ·
    T36_wizard_steps 0/3 · T37_terms_guard 3/3 · T38_recovery 3/3.
  - B17 v3 có **9 task × 3 variant = 27 episode** (T30–T38). T39/T40 chỉ có
    trong self-test/checker, không nằm trong `bench_b17/tasks/tasks.json`, nên
    không phải task bị mất khi chạy.
  - Holdout gate **PASS** (≥35%), nhưng **W1 FAIL**: 0.5556 > 20% và chưa đạt
    độ khó "gấp ≥3 lần bộ cũ". B17 v3 là holdout hợp lệ nhưng **chưa đủ khó**.
  - Result: `phase13-gui/kernel_bench_b17/output/b17_result.json`; log:
    `logs/b17_v3.log`; bản trên `ops-state`:
    `state/results/dieniw__ornith-gui-bench-b17-v22/`.
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
- **v26 đã push + QUEUED (28/10 07:10Z)** `phase13-gui/kernel_v26`:
  - Nền v25b + eval decode `EVAL_MAX=256` (sửa artifact traj 24 token).
  - Sửa lệch format: train `THINK: ...` + `ACTION: ...` khớp prompt eval
    B17/B18. v25b train action-only nên eval thinking ON sinh prose
    (`prose_leak=1.0`); v26 train đúng format parser.
  - Curated hard pack từ `ornith-policy-replay-data` (B15/B15.5/B16):
    13 task ×3 = **+498 row** — slider/drag, tab, scroll, wizard, clipboard,
    keyboard, distractor, undo/redo, filter, compute. **Không dùng B17/B18**.
  - Watchdog đã push `dieniw/ornith-gui-sft-v26` lúc **07:10Z**; Kaggle báo
    **QUEUED** (chờ GPU RTX). Chỉ 1 GPU session; B18 đã COMPLETE.
  - Eval kernels đã chuẩn bị và đã vào queue (state `blocked`):
    `phase13-gui/kernel_bench_b17_v26` → `dieniw/ornith-gui-bench-b17-v26`;
    `phase13-gui/kernel_bench_b18_v26` → `dieniw/ornith-gui-bench-b18-v26`.
    Watchdog tự push sau khi v26 COMPLETE + adapter `dieniw/ornith-gui-lora-v26`
    READY. Post-train: `scripts/post_v26_adapter.ps1` (download/publish/fingerprint).
  - Watchdog fix: Kaggle trả "Cannot access kernel / Permission denied" cho
    kernel private chưa tồn tại; nay coi là `MISSING` để auto-push hoạt động.
    Test `tests/test_watchdog.py` PASS.
  - Watchdog hỗ trợ optional `after` + `requires`: eval v26 đã nằm trong queue
    nhưng bị `blocked` đến khi kernel v26 COMPLETE và dataset adapter
    `dieniw/ornith-gui-lora-v26` READY. Không đẩy eval trước khi có adapter.
- **B18 hard holdout (28/10)**: dataset `dieniw/ornith-gui-bench-b18`
  **READY**; kernel `dieniw/ornith-gui-bench-b18-v1` **COMPLETE**.
  - 8 task / **42 episode**: 2 easy (T30 note-order, T33 error-retry) ×3 +
    6 hard (T31 scroll, T32 drag, T34 Tab, T36 wizard, T39 clipboard,
    T40 scroll+distractor) ×6.
  - Kết quả v25b: **14/42 = 0.3333**; parse **0.9132**; prose_leak **1.0**;
    mean_new 93.5; 7517s. Theo task: T30 3/3, T33 3/3, T34 2/6,
    T39 3/6, T40 3/6; T31/T32/T36 0/6.
  - **W1 >20% => B18 quá dễ**. Cần build B19 với mechanism khó hơn
    (không dùng B18 làm train). B18 vẫn là holdout cho v26.
  - Checker + GT self-test **8/8 PASS**, static lint **0 lỗi**.
  - B17 v4 local: `bench_b17/tasks/tasks.json` giờ có **11 task** (T30–T40),
    self-test **11/11 PASS**; T39 đã thêm `__state.ok`, T40 giữ nguyên.
  - Không train trên B18; B18 là holdout mới.
- **Self-dispatch verified** trên `easportat2025-blip/ornith-lab` (public):
  watchdog `40437526534` lúc 02:17:00Z, `ops-tick` `40436536797` lúc 02:06:52Z,
  heartbeat `40437528438` lúc 02:17:01Z; issue #2 cập nhật 02:17:20Z.
  Nhịp quan sát ~10–11 phút.
- **Self-dispatch end-to-end (28/10)**: `ops-tick` `40449497367` ngủ 600s,
  thức **04:33:48Z**, dispatch watchdog **`40450458765`**, rồi self-dispatch
  **`40450462556`**. Loop tiếp tục ~10 phút/lần; mới nhất lúc 03:49Z:
  `ops-tick` `40628876090` + watchdog `40628872862`. `ops-health` issue #13
  vẫn là fallback 30 phút.
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
- Cập nhật `configs/kaggle_queue.json`: v25b done, B17 **done**.

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
  outputs. Trigger thêm khi push queue/metadata/watchdog. Mặc định chỉ tải cho
  `kind=eval|bench`; target có thể override bằng `download_results`. v25b train
  đã tắt để tránh 429 từ endpoint output (adapter đã ở HF).
- **Ops status**: `scripts/ops_status.py` in queue/state/secret presence, không
  in giá trị secret. Thêm tests cho secret scan, watchdog, configs, ops status.
- **B17 v3 COMPLETE** (27/10); watchdog đã tải result + log vào
  `state/results/dieniw__ornith-gui-bench-b17-v22/` và cập nhật issue #2.
  `ops-tick` tự dispatch tiếp; không cần seed tay.

### Verify self-dispatch (04:50 UTC)
- Push `d755650` (self-dispatch + environment upgrade) đã trigger:
  - `ci` run **40271000533** — success, tất cả step xanh.
  - `hf-sync` run **40271000556** — success, code snapshot + chat docs lên HF.
  - `kaggle-watchdog` run **40271000550** — success; issue #2 cập nhật
    04:49:52Z; `ops-state/state/current.json` có v25b done, B17 QUEUED.
- `ops-tick` run **40271070108** được trigger bởi `workflow_run` lúc 04:49:58Z,
  đang sleep 600s. Dự kiến dispatch watchdog kế tiếp ~04:59:58Z.
- Lần đầu `--download-results` gọi output cho cả v25b (train), bị Kaggle
  **429 Too Many Requests**; đã sửa: mặc định chỉ tải cho `kind=eval|bench`,
  v25b có `download_results: false`. B17 eval vẫn tải khi COMPLETE.
- Dependabot mở nhiều PR actions riêng lẻ; đã đổi config sang group
  `github-actions` + `python-deps` để giảm nhiễu.

### Verify self-dispatch (05:00 UTC update)
- Push `4922766` (eval-only result download + grouped Dependabot) trigger:
  - `ci` run **40271291034** — success.
  - `hf-sync` run **40271290897** — success; HF `ornith-lab-code` và
    `ornith-chat` cập nhật lúc 04:53:28/04:53:30Z.
  - `kaggle-watchdog` run **40271291078** — success; issue #2 cập nhật
    04:52:53Z; v25b done **không** tải output (tránh 429), B17 QUEUED.
- `ops-tick` run **40271321807** (head `4922766`) bắt đầu 04:52:59Z, đang sleep;
  run cũ **40271070108** bị cancel bởi concurrency. Dự kiến dispatch watchdog
  ~05:03:16Z.
- Dependabot: PR group **#11** (actions) và **#12** (pip); các PR lẻ #8-#10
  (kaggle/pytest/pyyaml) là bản trùng, có thể đóng sau khi #12 xanh.

### B17 v3 kết quả (27/10)
- `n=27`, `wins=15`, `win_rate=0.5556`, `parse_rate=0.8507`,
  `prose_leak_rate=1.0`, `steps=201`, `modes={action:98, legacy:73, none:30}`,
  `mean_new=80.7`, `reason_max=512`.
- Per-task: T30 3/3 · T31 0/3 · T32 0/3 · T33 3/3 · T34 0/3 · T35 3/3 ·
  T36 0/3 · T37 3/3 · T38 3/3.
- B17 v3 = **9 task × 3 variant** (T30–T38). T39/T40 chỉ có trong
  `scripts/b17_selftest.py` / `checker.py`, không có trong
  `phase13-gui/bench_b17/tasks/tasks.json`; không phải task bị mất khi chạy.
- **Holdout gate PASS** (0.5556 ≥ 0.35), nhưng **W1 FAIL**: bộ mới phải
  ≤20% (mục tiêu ≤10%) và khó gấp ≥3 lần bộ cũ. B17 v3 hiện quá dễ; cần B17 v4
  hoặc B18 với T39/T40 + cơ chế khó hơn, rồi đo lại W1.
- **Capability gaps** (0/3): scroll ngoài viewport (T31), drag slider (T32),
  keyboard tab navigation (T34), wizard nhiều bước (T36). Đây là target cho
  v26, lấy từ B15/B16/capability-similar failures — **không train trên B17**.
- **Format**: `prose_leak=1.0` + `legacy=73` + `none=30` cho thấy model vẫn
  xen prose ngoài THINK và dùng bare action. v26 nên train format
  `THINK:` ngắn + `ACTION:` dòng cuối, eval `EVAL_MAX=256`.
- File: `phase13-gui/kernel_bench_b17/output/b17_result.json`,
  `logs/b17_v3.log`; bản `ops-state`:
  `state/results/dieniw__ornith-gui-bench-b17-v22/`.
- `phase13-gui/gate_report.py` dùng schema B15 (không nhận B17 trực tiếp);
  B17 được tính trực tiếp từ `episodes`/`by_task`/`agg`.

### Nâng cấp upgrade-safe (27/10)
- Thêm `configs/ops.json`: `loop.enabled`, `delay_seconds`,
  `upgrade_delay_seconds`, `stale_after_minutes`, `features.*`,
  `upgrade.mode`.
- Thêm `scripts/ops_health.py` + `.github/workflows/ops-health.yml`: fallback
  độc lập mỗi 30 phút; nếu `ops-tick`/`kaggle-watchdog` cũ hơn 25 phút và
  không có run active thì dispatch watchdog. Watchdog xong trigger lại
  `ops-tick`. Cập nhật issue `[ops] loop health`.
- **Phát hiện 27/10**: loop đứng từ 02:17 → 04:12 UTC (không có `ops-tick`
  hay watchdog run mới), dù hai workflow vẫn enabled. `ops_health.py` phát hiện
  và dispatch lại thành công (`40448469730`); watchdog xong trigger `ops-tick`
  `40448514382` bình thường. Nguyên nhân chưa chốt (GitHub drop event/throttle/
  concurrency). Đã thêm self-dispatch + active guard để loop không phụ thuộc
  hoàn toàn vào `workflow_run`; đây là lớp dự phòng, không thay thế trigger cũ.
- `ops-tick` đọc config qua GitHub API trước khi sleep; file thiếu/hỏng →
  default cũ (600s, enabled, heartbeat on). Vẫn giữ input `delay_seconds`.
- Watchdog đọc `features.auto_push`/`features.download_results`; state có
  `ops_config`. `hf-sync` đọc `features.hf_sync` + `upgrade.mode`.
- Thêm `tests/test_workflow_contracts.py`, `tests/test_ops_health.py` và
  `docs/UPGRADES.md`; không đổi tên workflow/trigger cũ.
- Trong lúc push, loop cũ vẫn chạy; sau push cần verify `ci`, `hf-sync`,
  `ops-health` run đầu, và `ops-tick` đọc config đúng.

### Verify upgrade-safe layer (27/10)
- Push commit **`1b7eb3a`** lên `main` qua Git Data API.
- `ci` **`40449109556` success**; `hf-sync` **`40449109522` success**.
- `ops-health` dry-run **`40449138317` success**; tạo issue **#13**
  `[ops] loop health`; thấy `ops-tick` active và **không dispatch trùng**.
- `ops-tick` self-dispatch test **`40449202101`**: config load đúng
  (`delay_seconds=600`, enabled, heartbeat on), seed 0s → next **600s**;
  dispatch watchdog **`40449241603`**, heartbeat, rồi self-dispatch
  **`40449245157`**. Đây là bằng chứng timer tự chạy.
- Loop hiện sống: `ops-tick` **`40449497367`** đang sleep 600s; issue #2 cập nhật
  **04:23:43Z** với v25b/B17 đều `COMPLETE` + `done`, active `none`.
- Active guard đã có trong workflow; chưa quan sát trực tiếp vì watchdog run
  hiện rất ngắn (~20–25s). Khi GPU kernel chạy lâu, `ops-tick` sẽ bỏ qua
  dispatch trùng và chỉ self-dispatch.
- Lưu ý: các run `ops-tick` bị `cancelled` trong lúc test là do self-dispatch
  hoặc `workflow_run` mới hơn thay thế qua `concurrency`; timer vẫn tiếp tục.

## Gate v25b (ngưỡng: parse ≥0.95, leak ≤5%, traj ≥0.85, real ≥0.85, train-sub ≥0.90)
| Gate | Kết quả | Đạt |
|---|---|---|
| parse (synth) | 0.990 | ✅ |
| real | 0.881 | ✅ |
| train-sub | 0.917 | ✅ |
| traj | 0.438 | ❌ |
| leak | chưa đo trong log v25b | ? |

**B17 v3 (holdout, cùng adapter v25b)**: **15/27 = 0.5556**, parse 0.8507,
prose leak 1.0. Holdout ≥35% **PASS**, nhưng **W1 FAIL** vì bộ quá dễ (>20%).
B17 cũng cho thấy 4 lỗ hổng 0/3: scroll, drag, tab navigation, wizard steps.

**Kết luận**: v25b tốt trên synth/real/train-sub. **Lưu ý quan trọng**: eval
traj-sub trong kernel v25b dùng `max_new_tokens=24` (dòng 451), nên các output
prose bị cắt giữa thinking trước khi ra action — 0.438 có thể là **artifact do
decode ngắn**, không phải model hỏng. B17 dùng `REASON_MAX=512`, là thước đo
thật. v26 nên nâng eval lên 256–512 token và đo lại traj trước khi kết luận.

## Blocker
1. **B18 quá dễ (W1 FAIL)** — v25b **14/42 = 0.3333 > 20%**. B18 vẫn là holdout
   cho v26, nhưng cần **B19** với mechanism khó hơn (nested scroll, precision
   drag, wizard validation, keyboard-only, clipboard verify, dynamic filter).
   Không train trên B18; không chỉ hạ variant của task dễ.
2. **v26 đang QUEUED** — watchdog đã push `dieniw/ornith-gui-sft-v26` lúc
   07:10Z; chờ GPU RTX. Cần theo dõi train, tải `gui_result.json`, publish
   adapter bằng `scripts/post_v26_adapter.ps1`, rồi để watchdog auto-push eval.
3. **OpenCode free models 429** (`FreeUsageLimitError`) với cả key user và
   `public`; key đã lưu, có thể thử lại sau.
4. **DeepSeek 402** (hết balance), **Mistral 429** (rate limit).
5. **HF Space PAUSED**, **HF Jobs 402** — không dùng scheduled jobs/relay được.
6. **Completion dataset**: hiện chỉ có competition ARC-AGI-3; nếu “completion
   dataset” là dataset riêng thì cần tên chính xác để gắn thêm.
7. **Local repo lệch remote**: local `master` tại `a5df1da`, remote `main` mới
   hơn; `git push` HTTPS treo. Dùng `scripts/github_push_files.py`.
8. **Dependabot**: #11 (actions) và #12 (pip/HF major) đều CI-green; đã comment
   defer đến sau v26 vì chạm ops workflow/HF stack. #8–#10 là bản trùng.

## Việc tiếp theo
1. **Theo dõi v26**: `dieniw/ornith-gui-sft-v26` QUEUED → RUNNING → COMPLETE;
   tải `gui_result.json`; kiểm tra format/parse/prose; publish adapter bằng
   `scripts/post_v26_adapter.ps1`.
2. **Eval v26**: sau adapter READY, watchdog tự push B17-v26 rồi B18-v26
   (`after` + `requires`). So per-task với v25b; B18 W1 mục tiêu ≤10%.
3. **Build B19**: thiết kế 8 task/48 episode với mechanism khó hơn B18; checker
   self-test; dataset riêng; **không** dùng B18 task làm train.
4. **B17 v4**: local 11 task đã self-test 11/11; nếu cần so sánh, tạo
   dataset/kernel slug mới và chạy (không tái dùng slug v22).
5. **Gate v26**: holdout ≥35%, W1 ≤20% (mục tiêu ≤10%), parse ≥0.95, prose leak
   ≤5%, traj ≥0.85; so per-task, không chỉ tổng.
6. Cập nhật `docs/HANDOFF.md` + `configs/kaggle_queue.json` sau mỗi thay đổi.
7. Sync HF chat + code snapshot sau commit (workflow `hf-sync` hoặc chạy tay).
8. Rotate PAT/API keys sau khi ổn định; giữ secrets chỉ trong GitHub/HF.

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
python scripts\ops_health.py --dry-run
# GitHub UI: Actions -> ops-tick -> Run workflow -> delay_seconds=0
# hoặc Actions -> ops-health -> Run workflow (dry_run=false) để re-seed

# sync HF code snapshot (sau khi fetch origin/main)
python scripts\hf_code_sync.py --ref origin/main
```

## Lưu ý
- Không chạy local watchdog 24/7; GitHub Actions là nơi chạy.
- `ops-tick` ngủ 600s mỗi vòng; repo public dùng runner minutes miễn phí. Nếu
  chuyển private, disable `ops-tick` hoặc giảm tần suất.
- Hành vi loop đọc `configs/ops.json`; `ops-health` là fallback mỗi 30 phút.
  File config thiếu/hỏng không làm loop dừng (fallback default).
- Không commit adapter/output lớn; `.gitignore` đã chặn
  `phase13-gui/kernel_*/output/` và `phase13-gui/lora_v25b_dataset/`.
- Không ghi key vào file; chỉ env/GitHub Secrets/HF secrets.
- Watchdog chỉ auto-push kernel `MISSING`; tôn trọng `after`/`requires` để
  không đẩy eval trước khi adapter READY. v26 dùng slug mới.
- B17/B18 là holdout; không train trên task B17/B18. B17 v3 (0.5556) và B18
  (0.3333) đều quá dễ; dùng B18 làm thước đo v26, build B19 khó hơn.
- PAT/API key đã gửi trong chat phải rotate sau khi ổn định.
