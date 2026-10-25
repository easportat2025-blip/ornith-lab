# Ornith Lab — GUI / computer-use agent

Repo điều phối để train **Ornith-1.5-9B** thành GUI/computer-use agent, chạy benchmark
desktop X11 thật, dùng Kaggle + Colab GPU, và tiếp tục được khi máy local tắt.

## Trạng thái nhanh

- Base: Ornith-1.5-9B (Qwen3.5-VL), QLoRA 4-bit.
- v24: aggregate **60.3%** (47/78), fingerprint `c7d318...`.
- v25b: data desktop-replay + synth-s11; metadata RTX + competition + mini-wheels
  (15 dataset, dưới 20GB); kernel tự retry qua GitHub watchdog.
- Desktop thật: B18 (Xvfb + openbox + app Linux thật), chưa thay phase14.
- OpenChat: **headless API** (không UI), endpoint `/api/ping`.
- GitHub: `easportat2025-blip/ornith-lab` (public) — watchdog 10 phút, không cần local.
- HF chat/state: `kkouadn/ornith-chat` (private).
- Heartbeat: GitHub Actions 10 phút/lần; local không chạy watchdog.

## Đọc gì trước

| File | Nội dung |
|---|---|
| `docs/PLAN_2026_10_24.md` | kế hoạch tổng, lịch 7 ngày, compute, gate |
| `docs/TRAINING_LOOP.md` | action space, v25b, vòng lặp tự cải thiện, manifest |
| `docs/COLAB_25H.md` | lease/keepalive, 5 account, log/artifact |
| `docs/DESKTOP_REAL.md` | B18, task/checker, setup X11 |
| `docs/GITHUB_HF.md` | layout repo, secret policy, HF, ops-state |
| `docs/SECRETS.md` | 5 secret GitHub Actions cần thêm |
| `docs/CONTINUITY.md` | việc tiếp tục khi hết quota chat |

## Quick start (local)

```powershell
# OpenChat headless (không mở Chrome)
scripts\oc_chat\start.cmd

# kiểm tra API
python scripts\oc_chat\client.py health
python scripts\oc_chat\client.py status

# heartbeat local chỉ khi user bật; mặc định dùng GitHub Actions
# start "" /b pythonw scripts\idle_ping.py

# xem job/queue
python scripts\oc_chat\client.py jobs

# kiểm tra secret (không in giá trị)
python scripts\check_secrets.py
```

UI legacy (chỉ khi cần debug): `scripts\oc_chat\start_ui.cmd`.

## Repo layout

```
docs/            kế hoạch + hướng dẫn
scripts/         ops: openchat, idle ping, colab, watchdog, github state
desktop_real/    X11 desktop thật + task/checker
phase13-gui/     kernel train/bench hiện có
phase14-desktop/ desktop-like cũ (HTML trong Chromium)
configs/         queue/eval config (không secret)
experiments/     manifest nhỏ; artifact ở HF
.github/         CI + heartbeat
```

## Secrets

- Không commit key/token. Chỉ đọc từ HKCU hoặc env lúc runtime.
- `scripts/colab_accounts/**`, `agent.md`, log/state bị `.gitignore` chặn.
- Trước khi push: `python scripts\secret_scan.py`.
- Nếu nghi lộ: rotate ngay, ghi incident vào `docs/HANDOFF.md`.

## Compute

| Nguồn | Dùng cho |
|---|---|
| Kaggle A/B/C (30h/tuần/acc) | train 9B, gate eval, data gen |
| Colab 1–5 (~25h/ngày) | test 4-bit, ablation, desktop CPU |
| Local | orchestration, OpenChat, heartbeat, git sync |
| GitHub Actions | CI, heartbeat; **không GPU** |

## Nguyên tắc

1. Capability > loss.
2. Gate > cảm giác; không regression.
3. Mỗi run có manifest + fingerprint.
4. Benchmark khó lên mỗi ngày, không chỉ tăng episode.
5. Local tắt vẫn thấy trạng thái qua GitHub issue + `ops-state`.
