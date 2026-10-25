# GITHUB + HUGGING FACE — nhà của code, data, adapter

> Mục tiêu: máy local tắt vẫn biết việc đang ở đâu; agent mới clone repo là tiếp tục được.
> **Không có key/token trong repo.** Key chỉ đọc từ HKCU hoặc env lúc runtime.

## 1. Repo layout (monorepo)

```
ornith-lab/
├─ README.md
├─ docs/
│  ├─ PLAN_2026_10_24.md
│  ├─ TRAINING_LOOP.md
│  ├─ COLAB_25H.md
│  ├─ DESKTOP_REAL.md
│  ├─ GITHUB_HF.md
│  └─ HANDOFF.md              # sinh tự động, trạng thái mới nhất
├─ configs/                   # queue, task list, eval config (không secret)
├─ scripts/                   # ops: watchdog, colab, openchat, idle ping, git state
├─ desktop_real/              # X11 desktop thật + task/checker
├─ experiments/               # manifest nhỏ, kết quả tóm tắt; không ảnh/dataset
├─ tests/                     # unit/smoke, không cần GPU
├─ state/                     # chỉ file mẫu; state thật ở nhánh ops-state
├─ .github/workflows/
│  ├─ ci.yml
│  └─ ops-heartbeat.yml
├─ .gitignore
└─ scripts/secret_scan.py
```

### Nguyên tắc tách
- `main`: code + docs + config + manifest.
- `ops-state` (orphan branch): `state/current.json`, `state/jobs.json`, `state/heartbeat.json`, `state/HANDOFF.md`.
- `exp/<run-id>` (optional): thay đổi thí nghiệm; merge vào main khi gate pass.
- Không commit output lớn; upload HF rồi ghi link/hash vào manifest.

## 2. Không được commit

| Loại | Ví dụ | Lý do |
|---|---|---|
| Credentials | `scripts/colab_accounts/**`, `token.json`, `oauth.json`, `sessions.json` | lộ tài khoản |
| Keys | `.env`, `*.key`, `*.pem`, `kaggle.json` | lộ quyền |
| Agent context | `agent.md` (chưa sanitize) | có thể chứa key/nội dung riêng |
| State runtime | `bus.jsonl`, `events.jsonl`, `*_state.json`, `quota_cache.json` | nhiễu, thay đổi liên tục |
| Logs | `scripts/logs/**`, `*.log`, `*.out`, `*.err` | lớn, có thể chứa token |
| Outputs | `phase13-gui/out_*/**`, screenshots, `*.zip` | lớn |
| Data/model | `data/**`, `*.safetensors`, `*.bin`, `*.pt`, `*.gguf` | HF là nhà |
| Temp | `.tmp_*`, `.glm_tmp`, `__pycache__`, `.venv` | rác |

`agent.md` chỉ được đưa lên sau khi `secret_scan.py` pass và đã tách phần nhạy cảm.

## 3. Secret policy

1. Kaggle: key trong `%USERPROFILE%\.kaggle\kaggle.json` hoặc HKCU; script `upload_staging.py` chọn account.
2. HF: `HF_TOKEN` / `HF_TOKEN_2` trong HKCU; không ghi ra file.
3. GitHub: `GITHUB_TOKEN` / `GH_TOKEN` trong HKCU hoặc env; scope tối thiểu `repo` (private) + `workflow` nếu sửa Actions.
4. Colab: token OAuth trong `scripts/colab_accounts/acc*/` — **không bao giờ** commit.
5. Nếu nghi lộ: rotate ngay, ghi incident vào `docs/HANDOFF.md`, không chỉ xóa file.

### Scan trước khi push
```powershell
python scripts\secret_scan.py
```
CI chạy lại; fail nếu thấy pattern. Scanner chỉ in `file:line` + loại, **không in giá trị**.

## 4. GitHub Actions

### `ci.yml`
- Trigger: push/PR.
- Python 3.12, không cài dependency nặng.
- `python -m compileall -q scripts desktop_real`
- `python scripts/secret_scan.py --tracked-only`
- `python -m unittest discover -s scripts/jobs -p "test_*.py"` (nếu có)
- `python -m py_compile` các file mới.
- Permissions: `contents: read`.

### `ops-heartbeat.yml`
- Trigger: `schedule: */10 * * * *` + `workflow_dispatch`.
- Không chạy GPU; chỉ cập nhật một issue `[ops] heartbeat`.
- Nội dung: thời gian UTC, run URL, trạng thái `local` (đọc `state/current.json` trên `ops-state`), cảnh báo nếu local heartbeat >30 phút.
- Permissions: `issues: write`, `contents: read`.
- Đây là "ping" khi máy local tắt; agent mở issue là biết trạng thái cuối.

## 5. Local → GitHub state

`scripts/github_state.py`:
- Đọc `scripts/jobs/state.json`, `scripts/state/heartbeat.json`, watchdog/queue state.
- Tạo snapshot **không secret**:
  ```json
  {"ts": "...", "host": "...", "jobs": {...}, "queues": {...},
   "openchat": {...}, "last_logs": {...}, "git_commit": "..."}
  ```
- PUT lên nhánh `ops-state` qua GitHub Contents API.
- Chạy mỗi 10 phút (cùng nhịp idle ping) hoặc sau mỗi milestone.
- Nếu không có token/repo: in hướng dẫn, exit 2; không treo.

```powershell
$env:GITHUB_REPO="owner/ornith-lab"
python scripts\github_state.py --once
python scripts\github_state.py --loop 600
```

Không commit token vào `configs/`; repo name có thể để trong `configs/github.json` (không phải secret).

## 6. Hugging Face

| Repo | Nội dung | Ai ghi |
|---|---|---|
| `ornith-gui-data` | dataset train/rollout, card + manifest | data pipeline |
| `ornith-gui-adapters` | LoRA adapter, fingerprint, eval | trainer |
| `ornith-desktop-replay` | screenshot + action replay | desktop harness |
| `ornith-evals` | kết quả eval, actions.jsonl, summary | evaluator |
| `ornith-desktop-images` | snapshot/asset desktop (nếu cần) | infra |

Quy ước:
- Mỗi version có `README.md` (dataset card), `manifest.json` (rows, sha256, source), `LICENSE` nếu cần.
- Tên version: `v25b`, `v26-s1`, `b18-w1`.
- Upload bằng `huggingface_hub` hoặc `hf upload`; token từ HKCU.
- Không upload checkpoint giữa chừng nếu chưa cần; ưu tiên adapter + log + manifest.
- Link HF ghi vào `experiments/<run>/manifest.json`, không copy file lớn về local.

## 7. Quy trình làm việc

1. `git switch -c exp/<run-id>` từ `main`.
2. Code/data manifest nhỏ; chạy local test/secret scan.
3. Push branch; CI xanh.
4. Train/eval trên Kaggle/Colab; upload artifact HF.
5. Gate pass → merge `main` + cập nhật `docs/HANDOFF.md` + fingerprint.
6. Gate fail → giữ branch, ghi post-mortem, không merge.
7. `ops-state` chỉ nhận state, không nhận code.

## 8. User cần cung cấp

- GitHub key (fine-grained PAT hoặc classic) với quyền:
  - `contents: read/write`
  - `issues: read/write` (cho heartbeat)
  - `workflow: write` nếu muốn sửa Actions
- Owner/repo name (hoặc đồng ý dùng `dieniw/ornith-lab`).
- Xác nhận private repo (khuyến nghị; data/agent context không public).

Khi có key: lưu vào HKCU `GITHUB_TOKEN` (không gửi qua chat nếu có thể), rồi:
```powershell
python scripts\secret_scan.py
git init
git add <curated files>
git commit -m "init: lab scaffold"
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

## 9. Remote continuity

- Local bật: `idle_ping.py` + `github_state.py` cập nhật mỗi 10 phút.
- Local tắt: GitHub Actions vẫn cập nhật issue heartbeat; state cuối cùng vẫn đọc được.
- Colab/Kaggle job dài: keeper tự fetch log/artifact; upload HF; ghi manifest.
- Agent mới: đọc `docs/HANDOFF.md` + `state/current.json` + issue heartbeat → biết việc tiếp theo.
- Không hứa "GitHub Actions train 9B": Actions không có GPU. GPU vẫn ở Kaggle/Colab.

---

*Mục tiêu: repo là nguồn sự thật; state là nhịp tim; HF là kho artifact.*
