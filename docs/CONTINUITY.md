# Continuity — việc không dừng khi hết quota chat

## Nguyên tắc

1. **Máy local chỉ là orchestrator**, không phải nơi duy nhất giữ trạng thái.
2. **GitHub Actions** chạy watchdog mỗi 10 phút trên repo public
   `easportat2025-blip/ornith-lab` — không cần máy bật, không tốn GPU.
3. **Kaggle/Colab** làm GPU. GitHub chỉ poll, push kernel kế tiếp, lưu state.
4. **HF private dataset** `kkouadn/ornith-chat` giữ chat/state đã sanitize.
5. Khi quota model chat hết, việc vẫn tiếp tục nhờ queue + watchdog; phiên
   sau đọc `docs/HANDOFF.md`, `state/current.json`, issue `[ops] kaggle watchdog`.

## Luồng tự động

```
GitHub Actions (10 phút)
  -> scripts/kaggle_watchdog_ci.py
     -> đọc configs/kaggle_queue.json
     -> poll trạng thái kernel
     -> nếu rảnh: push kernel pending
     -> ghi state/current.json
     -> push nhánh ops-state
     -> cập nhật issue [ops] kaggle watchdog
```

## Fallback LLM

Khi agent chính hết quota:

```powershell
$env:GEMINI_API_KEY=...
$env:MISTRAL_API_KEY=...
python scripts/llm_fallback.py --file docs/HANDOFF.md `
  --prompt "Tom tat trang thai, de xuat 3 viec tiep theo, ngan gon"
```

Chain mặc định: **Gemini -> Mistral**. Không ghi key ra file.

## Trạng thái cần đọc khi resume

- `docs/HANDOFF.md` — tóm tắt phiên gần nhất.
- `state/current.json` — trạng thái kernel do watchdog ghi.
- `configs/kaggle_queue.json` — việc nào đang chờ.
- Issue `[ops] kaggle watchdog` — log mới nhất trên GitHub.
- `https://huggingface.co/datasets/kkouadn/ornith-chat` — chat đã sanitize.

## Việc còn thiếu để chạy 24/7

- Thêm 5 secrets vào GitHub Actions (xem `docs/SECRETS.md`).
- Cấp PAT có quyền `Secrets: write` hoặc thêm tay.
- Rotate PAT đã gửi trong chat.
