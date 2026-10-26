# Ornith Lab — GUI / computer-use agent

[![ci](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/ci.yml)
[![kaggle-watchdog](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/kaggle-watchdog.yml/badge.svg?branch=main)](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/kaggle-watchdog.yml)
[![ops-tick](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/ops-tick.yml/badge.svg?branch=main)](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/ops-tick.yml)
[![ops-heartbeat](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/ops-heartbeat.yml/badge.svg?branch=main)](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/ops-heartbeat.yml)
[![hf-sync](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/hf-sync.yml/badge.svg?branch=main)](https://github.com/easportat2025-blip/ornith-lab/actions/workflows/hf-sync.yml)

Repo điều phối để train **Ornith-1.5-9B** thành GUI/computer-use agent, chạy benchmark
desktop X11 thật, dùng Kaggle + Colab GPU, và tiếp tục được khi máy local tắt.
Local chỉ là client; **GitHub Actions là nơi chạy 24/7**.

## Trạng thái nhanh

| Hạng mục | Trạng thái |
|---|---|
| Base | Ornith-1.5-9B (Qwen3.5-VL), QLoRA 4-bit |
| v25b | **COMPLETE** trên RTX: 8716 samples, 2.846 epochs, loss 0.1231 |
| v25b eval | synth **0.890**, real **0.881**, train-sub **0.917**, traj **0.438** (artifact decode 24 token) |
| B17 holdout | v3 **QUEUED** trên `dieniw/ornith-gui-bench-b17-v22` (RTX, competition, offline) |
| v26 | đã chuẩn bị local, `EVAL_MAX=256`, **chưa queue** — chờ B17 để curate data |
| Self-dispatch | `ops-tick` chạy sau mỗi watchdog run, nghỉ 600s rồi dispatch tiếp |
| GPU | Kaggle RTX PRO 6000 Blackwell 95 GB; Actions không có GPU |
| HF | chat/state `kkouadn/ornith-chat`; code `kkouadn/ornith-lab-code` (private) |
| State | `ops-state` branch + issue `[ops] kaggle watchdog` |

## Kiến trúc

```
Agent / local ──push──> GitHub main ──> ci.yml (compile, secret scan, pytest)
                         │
                         ├─ kaggle-watchdog.yml ──> Kaggle RTX (train / eval)
                         ├─ ops-tick.yml ──(sleep 600)──> dispatch watchdog
                         ├─ ops-heartbeat.yml ──> issue [ops] heartbeat
                         └─ hf-sync.yml ──> HF private (chat + code snapshot)

GitHub ops-state  <── state/current.json + state/results/*.json
GitHub issue #2   <── watchdog summary (kernel, status, outputs)
```

## Vòng lặp tự dispatch

1. `kaggle-watchdog` chạy xong (schedule, push queue, hoặc dispatch tay).
2. `ops-tick` được trigger bởi `workflow_run`, nghỉ `600` giây.
3. `ops-tick` dispatch `kaggle-watchdog` (và best-effort `ops-heartbeat`).
4. Watchdog xong → `ops-tick` lại → lặp.

`schedule: */10` trong `kaggle-watchdog.yml` là **backup seed**: nếu `ops-tick` bị
disable hoặc token mất `actions: write`, schedule sẽ khởi động lại vòng lặp.
Repo public dùng runner minutes miễn phí; nếu chuyển private, hãy tắt `ops-tick`
hoặc giảm tần suất để tránh tốn quota.

Muốn dừng: GitHub → Actions → `ops-tick` → **Disable workflow**. Muốn seed lại:
dispatch `ops-tick` với `delay_seconds=0`, hoặc dispatch `kaggle-watchdog` tay.

## Quick start

```powershell
# trạng thái queue/state/secrets (không in giá trị secret)
python scripts\ops_status.py

# kiểm tra secret đang set/missing
python scripts\check_secrets.py

# test + secret scan
python -m pytest -q
python -m unittest discover -s scripts\jobs -p "test_*.py" -v
python scripts\secret_scan.py --tracked-only

# watchdog một lần (cần KAGGLE_USERNAME/KAGGLE_KEY trong env/HKCU)
python scripts\kaggle_watchdog_ci.py

# sync code snapshot lên HF (dry-run trước)
python scripts\hf_code_sync.py --dry-run
python scripts\hf_chat_sync.py --dry-run --files docs/HANDOFF.md docs/CONTINUITY.md README.md
```

Nếu `git push` qua HTTPS bị treo, dùng Git Data API:

```powershell
$env:GH_TOKEN = "<token>"
python scripts\github_push_files.py --repo easportat2025-blip/ornith-lab `
  --branch main --message "ops: update" docs/HANDOFF.md configs/kaggle_queue.json
```

## Repo layout

```
.github/workflows/   ci, kaggle-watchdog, ops-tick, ops-heartbeat, hf-sync
configs/             queue/eval config (không secret)
docs/                HANDOFF, ENVIRONMENT, TRAINING_LOOP, DESKTOP_REAL, ...
scripts/             watchdog, HF sync, secret scan, ops status, git push API
phase13-gui/         kernel train/bench hiện tại
desktop_real/        X11 desktop thật + task/checker
tests/               pytest + unit tests
state/               placeholder; state thật nằm trên nhánh ops-state
```

## Workflows

| Workflow | Trigger | Việc làm |
|---|---|---|
| `ci.yml` | push main, PR, dispatch | compileall, YAML/JSON, secret scan, pytest, job-registry tests, headless smoke |
| `kaggle-watchdog.yml` | schedule 10m, push queue/metadata, dispatch | poll Kaggle, tải result nhỏ (eval/bench), auto-push kernel `MISSING`, cập nhật issue + ops-state |
| `ops-tick.yml` | `workflow_run` của watchdog, dispatch | nghỉ 600s rồi dispatch watchdog + heartbeat |
| `ops-heartbeat.yml` | schedule 10m, dispatch | cập nhật issue `[ops] heartbeat`, đọc state từ ops-state |
| `hf-sync.yml` | push main, dispatch | upload code snapshot + docs sanitized lên HF private |

## Secrets

Chỉ dùng **GitHub Actions secrets** hoặc **HF secrets**; không commit, không ghi ra file:

`KAGGLE_USERNAME`, `KAGGLE_KEY`, `HF_TOKEN`, `GEMINI_API_KEY(_2)`,
`MISTRAL_API_KEY(_2.._5)`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY(_2.._6)`,
`OPENCODE_API_KEY`.

`GITHUB_TOKEN` do Actions cấp tự động. Chi tiết: `docs/SECRETS.md`.
PAT/API key từng gửi trong chat phải **rotate** sau khi mọi thứ ổn định.

## Đọc gì trước

| File | Nội dung |
|---|---|
| `docs/HANDOFF.md` | trạng thái mới nhất, việc đang làm, blocker |
| `docs/ENVIRONMENT.md` | môi trường GitHub, workflow, self-dispatch, troubleshooting |
| `docs/PLAN_2026_10_24.md` | kế hoạch tổng, lịch, compute, gate |
| `docs/TRAINING_LOOP.md` | action space, v25b, vòng lặp tự cải thiện, manifest |
| `docs/COLAB_25H.md` | lease/keepalive, 5 account, log/artifact |
| `docs/DESKTOP_REAL.md` | B18, task/checker, setup X11 |
| `docs/GITHUB_HF.md` | layout repo, secret policy, HF, ops-state |
| `docs/SECRETS.md` | danh sách secret và cách thêm |
| `docs/CONTINUITY.md` | việc tiếp tục khi hết quota chat |
| `AGENTS.md` | protocol cho agent mới |

## Nguyên tắc

1. Capability > loss.
2. Gate > cảm giác; không regression.
3. **B17 là holdout** — không train trên task B17.
4. Kernel mới phải dùng slug mới; watchdog chỉ auto-push kernel `MISSING`.
5. Mỗi run có manifest + fingerprint; artifact lớn đẩy HF, không commit.
6. Không chạy local watchdog 24/7; GitHub Actions là vòng lặp chính.
7. Không có key/token trong repo, log, issue hay dataset công khai.
