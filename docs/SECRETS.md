# Secrets — GitHub Actions / HF

Không ghi key vào file, repo, log, hay dataset công khai. Chỉ dùng
**GitHub Actions secrets** (hoặc HF Space secrets).

## GitHub Actions secrets cần có

| Name | Dùng cho | Ghi chú |
|---|---|---|
| `KAGGLE_USERNAME` | watchdog + push kernel | `dieniw` |
| `KAGGLE_KEY` | watchdog + push kernel | Kaggle API key của account B |
| `HF_TOKEN` | sync chat + upload adapter | token HF có quyền write |
| `GEMINI_API_KEY` | fallback LLM | do user cung cấp |
| `MISTRAL_API_KEY` | fallback LLM | do user cung cấp |

## Cách thêm

Repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret** → nhập đúng tên ở trên.

Hiện PAT đã đưa trong chat **không có quyền `Secrets: write`**, nên API
trả `403 Resource not accessible by personal access token`. Vì vậy phải
thêm tay trên web, hoặc tạo PAT mới có quyền:

- `Actions secrets`: Read and write
- `Contents`: Read and write
- `Issues`: Read and write
- `Workflows`: Read and write

## Bảo mật

- PAT vừa gửi trong chat phải **rotate ngay** sau khi cấu hình xong.
- Không commit `.env`, `token.json`, `kaggle.json`, `sessions.json`.
- `scripts/secret_scan.py --tracked-only` chạy trong CI; nếu fail thì
  không merge.
- Chat/state nhạy cảm chỉ đẩy lên dataset **private** `kkouadn/ornith-chat`.

## Kiểm tra nhanh (không in giá trị)

```powershell
python scripts/check_secrets.py
```

Script chỉ in `set/missing` và độ dài, không in nội dung.
