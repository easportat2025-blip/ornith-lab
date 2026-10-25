# HANDOFF — 24/10/2026 (local session)

## Trạng thái hiện tại
- **v25b v4 đang RUNNING** trên Kaggle B (đã fix lỗi mount GPU: bỏ wheels/tools/stack/competition, bật internet, pip install fallback).
- B17 metadata đã sửa (6 datasets, internet on) nhưng **chưa push** vì v25b đang chạy; push sau khi v25b xong.
- OpenChat **headless** đang chạy port 8788; API `/api/ping`, `/api/jobs`, `/api/logs`.
- `idle_ping.py` đang chạy (pid file `scripts/state/idle_ping.pid`), heartbeat 10 phút.
- Job registry rỗng (`scripts/jobs/state.json`); keeper dry-run OK.
- Desktop thật: `desktop_real/` có proof + 6 task + setup; chưa chạy trên Colab.

## Việc đã làm
- GitHub/HF scaffold: `README.md`, `docs/*`, `.gitignore`, CI, heartbeat workflow, `scripts/secret_scan.py`, `scripts/github_state.py`.
- OpenChat headless API + client + start/stop scripts.
- Colab keeper + job registry + tests (21 tests pass).
- Desktop real PoC + task/checker.
- Secret scan: 0 findings (đã sanitize 5 HF token hardcoded).
- v25b metadata fixed; v25b running.

## Việc tiếp theo (ưu tiên)
1. Theo dõi v25b; khi COMPLETE: fetch log, publish adapter, đăng ký fingerprint, chạy 4 gate.
2. Push B17 (sau v25b), lấy W1 baseline.
3. Chạy `desktop_real/proof_real.py` + `tasks.py --selftest` trên Colab CPU.
4. Nếu có GitHub key: init repo, push curated files, bật CI + heartbeat.
5. Chạy `github_state.py --once` sau khi có key/repo.
6. Mine failure v25b → v26 data (seed/matrix mới).

## Lệnh nhanh
```powershell
python scripts\oc_chat\client.py --json status
python scripts\idle_ping.py --once --dry-run
python scripts\jobs\cli.py doctor
python scripts\secret_scan.py
python scripts\github_state.py --dry-run
```

## Lưu ý
- Không push B17 khi v25b đang chạy (tránh batch GPU session limit).
- Bỏ wheels offline: v25b cài `unsloth/trl/bitsandbytes` từ PyPI (internet on).
- `agent.md` bị .gitignore; sanitize trước khi đưa lên GitHub.
- v25b v4 đang chạy; adapter chưa tồn tại.
