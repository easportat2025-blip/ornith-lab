# Secrets — GitHub Actions / HF

Không ghi key/token vào file, repo, log, issue, kernel, hay dataset công khai.
Chỉ dùng **GitHub Actions secrets**, **HF secrets**, hoặc env/HKCU lúc runtime.

## GitHub Actions secrets

| Name | Dùng cho | Ghi chú |
|---|---|---|
| `KAGGLE_USERNAME` | watchdog + push kernel | tài khoản Kaggle đang dùng |
| `KAGGLE_KEY` | watchdog + push kernel | API key tương ứng |
| `HF_TOKEN` | `hf-sync`, upload adapter/chat | quyền write |
| `GEMINI_API_KEY` | fallback LLM | key chính |
| `GEMINI_API_KEY_2` | fallback LLM | key dự phòng |
| `MISTRAL_API_KEY` | fallback LLM | key chính |
| `MISTRAL_API_KEY_2.._5` | fallback LLM | key dự phòng |
| `DEEPSEEK_API_KEY` | fallback LLM | có thể 402 khi hết balance |
| `GROQ_API_KEY` | fallback LLM | key chính |
| `GROQ_API_KEY_2.._6` | fallback LLM | key dự phòng |
| `OPENCODE_API_KEY` | fallback LLM | free models có thể 429 |

`GITHUB_TOKEN` do GitHub Actions cấp tự động; không cần thêm tay. Các workflow
dùng nó cho `ops-state` và issue.

## Thêm / sửa secret

1. Repo → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret** (hoặc update secret cũ).
3. Nhập đúng tên ở bảng trên, dán giá trị, lưu.
4. Không ghi giá trị vào `docs/`, `configs/`, hay chat.

Với HF: token dùng cho `hf-sync.yml` nằm trong GitHub Actions secret `HF_TOKEN`.
Nếu chạy local, đọc từ HKCU/env:

```powershell
$env:HF_TOKEN = [Environment]::GetEnvironmentVariable("HF_TOKEN", "User")
python scripts\hf_code_sync.py --ref origin/main
```

Không lưu token vào file `.env` được commit; `.env*` đã nằm trong `.gitignore`.

## Quyền tối thiểu

- GitHub PAT (nếu dùng API push): `contents: read/write`, `issues: read/write`,
  `actions: read/write` (dispatch workflow), `workflow` (sửa file workflow).
- HF token: write trên các repo private `kkouadn/ornith-chat` và
  `kkouadn/ornith-lab-code`.
- Kaggle API key: quyền push/pull kernel của tài khoản.

## Kiểm tra nhanh (không in giá trị)

```powershell
python scripts\check_secrets.py
python scripts\secret_scan.py --tracked-only
```

`check_secrets.py` chỉ in `set/missing` và độ dài. `secret_scan.py` chỉ in
`file:line` + tên pattern.

## Rotation

Rotate ngay nếu key xuất hiện trong chat, log, issue, commit, hoặc artifact:

1. Revoke key cũ ở provider.
2. Tạo key mới với quyền tối thiểu.
3. Cập nhật GitHub Actions secret (và HF secret nếu có).
4. Chạy lại workflow liên quan để xác nhận.
5. Ghi incident vào `docs/HANDOFF.md` **không kèm giá trị**.

PAT/API key từng gửi trong chat phải rotate sau khi mọi thứ ổn định. Không
dùng lại key cũ để "tiết kiệm"; coi như đã lộ.
