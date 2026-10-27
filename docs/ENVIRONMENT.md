# Môi trường làm việc trên GitHub

Tài liệu này mô tả môi trường ops 24/7 của repo: workflow nào chạy, ai có quyền
gì, self-dispatch hoạt động ra sao, và cách xử lý khi một mắt xích hỏng.

## 1. Thành phần

| Thành phần | Vai trò |
|---|---|
| `main` | code, docs, config, manifest; CI chạy trên mọi push |
| `ops-state` | state runtime: `state/current.json`, `state/results/*` |
| Issue `[ops] kaggle watchdog` | trạng thái kernel, output, link run |
| Issue `[ops] heartbeat` | ping 10 phút, freshness của state |
| Issue `[ops] loop health` | tuổi run gần nhất, hành động re-seed của fallback |
| Kaggle | GPU RTX, train/eval kernel |
| HF `kkouadn/ornith-chat` | chat/state đã sanitize (private) |
| HF `kkouadn/ornith-lab-code` | zip code snapshot (private) |
| Local | client để đọc/ghi, không chạy watchdog 24/7 |

## 2. Workflows

| Workflow | Trigger | Quyền | Việc làm |
|---|---|---|---|
| `ci.yml` | push `main`, PR, dispatch | `contents: read` | compileall, YAML/JSON, secret scan, pytest, job tests, headless smoke |
| `kaggle-watchdog.yml` | schedule `*/10`, push queue/metadata, dispatch | `contents: write`, `issues: write` | poll Kaggle, tải result nhỏ, auto-push kernel `MISSING`, cập nhật issue + `ops-state` |
| `ops-tick.yml` | `workflow_run` của watchdog, dispatch | `actions: write`, `contents: read` | đọc `configs/ops.json`, nghỉ `delay_seconds` rồi dispatch watchdog + heartbeat |
| `ops-health.yml` | schedule `*/30`, dispatch | `actions: write`, `contents: read`, `issues: write` | kiểm tra tuổi run; dispatch watchdog nếu loop cũ; cập nhật issue `[ops] loop health` |
| `ops-heartbeat.yml` | schedule `*/10`, dispatch | `contents: read`, `issues: write` | cập nhật issue heartbeat, đọc state từ `ops-state` |
| `hf-sync.yml` | push `main`, dispatch | `contents: read` | upload code snapshot + docs sanitized lên HF (đọc flag `hf_sync`) |

`kaggle-watchdog.yml` có thêm trigger `push` cho `configs/kaggle_queue.json`,
`scripts/kaggle_watchdog_ci.py`, và `phase13-gui/**/kernel-metadata.json` để
queue mới được xử lý ngay, không phải chờ tick.

## 3. Self-dispatch

```
ops-tick (workflow_run hoặc self-dispatch)
        │  sleep delay_seconds (mặc định 600)
        ▼
kiểm tra watchdog active?
        │
        ├─ có  → bỏ qua dispatch (tránh chồng run)
        └─ không → dispatch kaggle-watchdog (auto_push=true)
        │
        ▼
dispatch ops-heartbeat (best-effort, trừ upgrade mode)
dispatch ops-tick (self-dispatch, delay_seconds = config)
        │
        ▼
lặp lại
```

- **Self-dispatch là chính.** `workflow_run` có thể bị delay/drop (quan sát
  27/10: loop đứng ~2 giờ dù workflow enabled; re-seed bằng `ops-health` thành
  công). Vì vậy `ops-tick` tự dispatch chính nó với `delay_seconds` lấy từ
  config, không phụ thuộc watchdog completion. `workflow_run` vẫn giữ để phản
  ứng ngay khi watchdog xong.
- **Active guard.** Trước khi dispatch watchdog, `ops-tick` gọi
  `listWorkflowRuns`; nếu watchdog đang `queued`/`in_progress` thì bỏ qua, chỉ
  self-dispatch để kiểm tra lại sau. Tránh chồng run khi GPU queue lâu.
- `concurrency: ops-tick` với `cancel-in-progress: true`: nếu có nhiều tick
  gần nhau, chỉ tick mới nhất tiếp tục; không tạo hàng đợi.
- `ops-tick` dispatch có retry 3 lần cho watchdog; heartbeat là best-effort.
- Nếu `ops-tick` fail, `schedule: */10` của watchdog và `ops-health` vẫn là seed
  dự phòng.
- Muốn seed ngay: Actions → `ops-tick` → Run workflow → `delay_seconds=0`.
  Tick kế tiếp vẫn dùng `delay_seconds` từ config (không bị 0 lặp).
- Muốn dừng: Actions → `ops-tick` → **Disable workflow**. Watchdog vẫn chạy theo
  schedule (chậm hơn), hoặc disable luôn watchdog nếu cần.
- Muốn tạm dừng mềm: đặt `loop.enabled=false` trong `configs/ops.json`.
  `ops-tick` sẽ không dispatch/self-dispatch, nhưng watchdog schedule vẫn chạy.

### Fallback `ops-health`

`ops-health.yml` chạy độc lập mỗi 30 phút (và dispatch tay). Nó đọc tuổi run
gần nhất của `ops-tick` và `kaggle-watchdog`:

- Nếu một trong hai đang `queued`/`in_progress`: không làm gì (tránh trùng).
- Nếu `kaggle-watchdog` cũ hơn `loop.stale_after_minutes` (mặc định 25): dispatch
  watchdog với `auto_push=true`.
- Nếu `ops-tick` cũ nhưng watchdog còn mới: dispatch watchdog để watchdog xong
  trigger lại `ops-tick`.
- Nếu `loop.enabled=false`: không dispatch, chỉ báo cáo.

Một watchdog run mới là đủ để tái lập vòng lặp: watchdog xong → `ops-tick` →
sleep → watchdog. `ops-health` không sửa code/queue/state.

### Upgrade-safe config

`configs/ops.json` cho phép đổi hành vi mà không sửa workflow:

| Khóa | Mặc định | Tác dụng |
|---|---|---|
| `loop.enabled` | `true` | `false` = `ops-tick` không dispatch |
| `loop.delay_seconds` | `600` | nhịp self-dispatch |
| `loop.upgrade_delay_seconds` | `600` | nhịp khi `upgrade.mode=true` |
| `loop.stale_after_minutes` | `25` | ngưỡng fallback |
| `features.auto_push` | `true` | `false` = không tự push kernel `MISSING` |
| `features.download_results` | `true` | `false` = không tải result |
| `features.heartbeat` | `true` | `false` = không dispatch heartbeat |
| `features.hf_sync` | `true` | `false` = không upload HF |
| `upgrade.mode` | `false` | giữ loop, bỏ heartbeat + HF sync |

`ops-tick` đọc config qua GitHub API trước khi sleep. Nếu file thiếu/hỏng, nó
dùng default cũ (600s, enabled, heartbeat on). Watchdog đọc cùng file để áp
`auto_push`/`download_results`; config hỏng không làm watchdog dừng.

Quy trình nâng cấp đầy đủ: [`docs/UPGRADES.md`](UPGRADES.md).

### Chi phí runner

`ops-tick` ngủ 600s mỗi vòng, tức là chiếm runner gần như liên tục. Với repo
**public**, runner minutes miễn phí. Nếu repo chuyển **private**, hãy disable
`ops-tick` hoặc dùng một scheduler bên ngoài (cron-job.org, VPS) để tránh tiêu
hết quota Actions.

### Vì sao không dùng cron dày hơn?

GitHub throttle `schedule` trên repo bận: `*/10` thực tế có thể thành 1-2 giờ.
Self-dispatch bằng `workflow_run` + `sleep` giữ nhịp gần 10 phút mà không phụ
thuộc cron. Đây là lý do `ops-tick` tồn tại.

## 4. CI

`ci.yml` chạy các bước:

1. `python -m compileall -q scripts tests` + `py_compile` các kernel chính.
2. Parse toàn bộ `.github/workflows/*.yml`, `.github/dependabot.yml`,
   `configs/*.json`, `.devcontainer/devcontainer.json`.
3. `python scripts/secret_scan.py --tracked-only`.
4. `python -m pytest -q` (tests mới trong `tests/`).
5. `python -m unittest discover -s scripts/jobs -p "test_*.py"`.
6. Headless API smoke: `oc_chat/server.py --help`, `client.py --help`,
   `idle_ping.py --once --dry-run`.

Chạy local tương đương:

```powershell
python -m compileall -q scripts tests
python -m pytest -q
python -m unittest discover -s scripts\jobs -p "test_*.py" -v
python scripts\secret_scan.py --tracked-only
```

## 5. Devcontainer / Codespaces

`.devcontainer/devcontainer.json` dùng Python 3.12, cài `requirements-ci.txt`,
kèm GitHub CLI và các extension Python/YAML/Actions. Mở repo bằng Codespaces
hoặc VS Code Dev Containers là có môi trường gần giống CI.

## 6. Secrets

Chỉ tên, không giá trị:

- `KAGGLE_USERNAME`, `KAGGLE_KEY`
- `HF_TOKEN`
- `GEMINI_API_KEY`, `GEMINI_API_KEY_2`
- `MISTRAL_API_KEY`, `MISTRAL_API_KEY_2.._5`
- `DEEPSEEK_API_KEY`
- `GROQ_API_KEY`, `GROQ_API_KEY_2.._6`
- `OPENCODE_API_KEY`

`GITHUB_TOKEN` do Actions cấp tự động. Chi tiết và cách thêm: `docs/SECRETS.md`.

## 7. Branch model

| Branch | Nội dung | Ai ghi |
|---|---|---|
| `main` | code/docs/config | người và agent, qua PR hoặc API push |
| `ops-state` | state runtime + result nhỏ | watchdog workflow, force-push mỗi tick |
| `exp/<run-id>` | thử nghiệm | agent, merge khi gate pass |

`ops-state` là orphan branch; không chứa code. `state/results` chỉ nhận file
JSON/MD/TXT ≤ 2 MB; file lớn bị xóa trước khi commit. Mặc định watchdog chỉ tải
result cho `kind=eval|bench`; target có thể override bằng `download_results`
(true/false) trong `configs/kaggle_queue.json`.

## 8. Troubleshooting

| Triệu chứng | Kiểm tra / xử lý |
|---|---|
| Watchdog không chạy đúng 10 phút | Xem `ops-tick` có enabled không; xem run gần nhất; seed lại bằng dispatch `delay_seconds=0` |
| Loop im > 25 phút | Xem issue `[ops] loop health`; dispatch `ops-health` tay hoặc `ops-tick` với `delay_seconds=0` |
| `ops-health` không re-seed | Kiểm tra `loop.enabled`, `actions: write`, và `GITHUB_TOKEN`; xem `state/loop_health.json` trong run |
| Config mới không có tác dụng | JSON phải hợp lệ và nằm trên `main`; `ops-tick` đọc qua API mỗi vòng |
| Muốn tạm dừng mềm | `configs/ops.json` → `loop.enabled=false`; watchdog schedule vẫn chạy |
| `ops-tick` lỗi 403 khi dispatch | Token thiếu `actions: write`; workflow phải có `permissions: actions: write` |
| `kaggle-watchdog` lỗi 401 | `KAGGLE_USERNAME`/`KAGGLE_KEY` sai hoặc hết hạn; cập nhật GitHub secret |
| Kernel `QUEUED` lâu | Hết GPU quota, competition/internet sai, hoặc Kaggle đang bận; xem `kaggle kernels status` |
| Kernel `ERROR` | Đọc log tail trong issue/`state/current.json`; kiểm tra offline browsers, adapter, `tasks.json` |
| `state/current.json` missing | Watchdog run fail trước khi ghi state; xem log run, chạy lại |
| `state/results` quá lớn | Giảm `--results-max-bytes` hoặc thu hẹp `--result-pattern` |
| `git push` HTTPS treo | Dùng `scripts/github_push_files.py` (Git Data API) |
| HF upload 402/403 | Kiểm tra `HF_TOKEN`, quyền write, repo private; HF Jobs 402 không ảnh hưởng upload thường |
| OpenCode 429 / DeepSeek 402 / Mistral 429 | Fallback chain tự bỏ qua; thử lại sau hoặc dùng Groq/Gemini |
| CI fail ở secret scan | Xóa/rotate giá trị bị flag; không thêm ngoại lệ tùy tiện |
| `ops-state` bị force-push mất file | State chỉ là snapshot; chạy lại watchdog để tạo lại |

## 9. Security / rotation

- Không commit key; không in key ra log.
- `secret_scan.py` chạy trong CI và `hf-sync`.
- `hf_code_sync.py` chỉ archive file tracked, scan trước khi upload.
- `hf_chat_sync.py` redact pattern token trước khi upload.
- PAT/API key từng xuất hiện trong chat phải rotate sau khi ổn định.
- Ghi incident vào `docs/HANDOFF.md` **không kèm giá trị**.

## 10. Runbook ngắn

```powershell
# 1. Xem trạng thái
python scripts\ops_status.py

# 2. Kiểm tra secret
python scripts\check_secrets.py

# 3. Chạy watchdog một lần (không auto-push)
python scripts\kaggle_watchdog_ci.py

# 4. Kiểm tra code trước khi push
python scripts\secret_scan.py
python -m pytest -q
python -m unittest discover -s scripts\jobs -p "test_*.py" -v

# 5. Push bằng API nếu git push treo
$env:GH_TOKEN = "<token>"
python scripts\github_push_files.py --repo easportat2025-blip/ornith-lab `
  --branch main --message "ops: ..." <files>

# 6. Sync HF thủ công (nếu workflow không chạy)
python scripts\hf_code_sync.py --ref origin/main
python scripts\hf_chat_sync.py --files docs/HANDOFF.md docs/CONTINUITY.md README.md

# 7. Health check loop (dry-run, không dispatch)
python scripts\ops_health.py --dry-run

# 8. Re-seed nếu loop cũ (token chỉ ở env, không ghi file)
$env:GITHUB_TOKEN = $env:GH_TOKEN
python scripts\ops_health.py --repo easportat2025-blip/ornith-lab --ref main --redispatch
```
