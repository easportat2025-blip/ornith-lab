# HANDOFF — 25/10/2026 (GitHub/HF ops)

## Trạng thái hiện tại
- **v25b v9 đã push, đang RUNNING** trên Kaggle `dieniw/ornith-gui-sft-v25b`.
  Metadata mới: RTX + competition ARC + internet OFF + base4 + `ornith-mini-wheels`
  + 10 dataset nhỏ (tổng 18.07 GB, dưới giới hạn 20 GB).
- **Probe `dieniw/ornith-probe-rtx-ready-1024` đang RUNNING** với cùng metadata;
  dùng để xác nhận RTX + mount đủ dataset. Logs API còn rỗng (Kaggle chỉ trả log
  sau khi container chạy xong hoặc rất muộn).
- **B17** (`dieniw/ornith-gui-bench-b17-v22`) đã sửa metadata: thêm competition,
  internet OFF, RTX; **chưa push**, chờ v25b.
- **GitHub repo** `easportat2025-blip/ornith-lab` đã tạo (public) nhưng **rỗng**.
  PAT hiện tại chỉ tạo repo/issue, **thiếu `Contents: write` và `Secrets: write`**:
  - `git push` → 403 Permission denied.
  - `PUT /actions/secrets/...` → 403 Resource not accessible.
- **HF chat sync**: đã đẩy `agent.md`, `bus.jsonl`, `events.jsonl`, `HANDOFF.md`
  lên dataset private `kkouadn/ornith-chat` (0 redaction; files verified).
- **HF code snapshot**: `kkouadn/ornith-lab-code` (private) chứa `ornith-lab.zip`
  17 MB (chỉ tracked files, secret scan OK).
- **GitHub Actions watchdog** đã viết trong repo local:
  `.github/workflows/kaggle-watchdog.yml` + `scripts/kaggle_watchdog_ci.py`.
  Chưa chạy được vì repo rỗng + thiếu secrets.
- **Local watchdog đã tắt**; không chạy idle_ping local.

## Việc đã làm trong phiên này
- Xác nhận không có competition → GPU là **2× Tesla T4 14.6 GB**; có competition
  + internet ON → Kaggle trả 400. Vì vậy RTX bắt buộc competition + internet OFF.
- Tạo dataset `dieniw/ornith-mini-wheels` (4 wheel: unsloth, unsloth_zoo, trl,
  bitsandbytes; 67 MB) để tổng input 18.07 GB.
- Sửa metadata v25b và B17 sang RTX/competition/offline.
- Push v25b version 9.
- Tạo repo GitHub, issue #1 cảnh báo thiếu quyền PAT.
- Viết `docs/SECRETS.md`, `docs/CONTINUITY.md`, `scripts/check_secrets.py`,
  `scripts/llm_fallback.py`, `scripts/hf_chat_sync.py`.
- Upload chat + code snapshot lên HF.

## Blocker
1. **GitHub PAT thiếu quyền**. Cần PAT mới (classic `repo` + `workflow`, hoặc
   fine-grained có Contents/Actions/Secrets/Issues read-write). Sau đó:
   - push code local lên `main`;
   - set 5 secrets: `KAGGLE_USERNAME`, `KAGGLE_KEY`, `HF_TOKEN`,
     `GEMINI_API_KEY`, `MISTRAL_API_KEY`;
   - chạy `kaggle-watchdog.yml` manually để verify.
2. **Gemini/Mistral keys không có trên máy**. Không tìm thấy trong env/HKCU/files.
   Cần user set `GEMINI_API_KEY`, `MISTRAL_API_KEY` (User env) hoặc nhập tay vào
   GitHub Secrets. Không đưa key vào repo/chat.
3. **HF Space `kkouadn/dual_orchtractor` bị PAUSED** (`Flagged as abusive`) —
   không dùng làm relay được.
4. **HF Jobs cần credit** (402 Payment Required) — không dùng scheduled job được.
5. **Completion dataset**: hiện chỉ có competition ARC-AGI-3; nếu “completion
   dataset” là dataset riêng thì cần tên chính xác để gắn thêm.

## Việc tiếp theo
1. Chờ v25b/probe COMPLETE; đọc log xác nhận `NvidiaRtxPro6000` và không OOM.
2. Nếu v25b OK: tải adapter, publish lên HF/Kaggle, chạy 4 gate.
3. Push B17 lấy W1 baseline.
4. Có PAT mới: push repo + secrets + chạy watchdog.
5. Cập nhật `docs/HANDOFF.md` sau mỗi lần kernel đổi trạng thái.

## Lệnh nhanh
```powershell
# trạng thái kernel
python -X utf8 -c "import sys,subprocess; sys.path.insert(0,'scripts'); from upload_staging import env_for; env,_=env_for('dieniw'); print(subprocess.run(['kaggle','kernels','status','dieniw/ornith-gui-sft-v25b'],capture_output=True,env=env).stdout.decode())"

# secret check (không in giá trị)
python scripts\check_secrets.py

# watchdog local (chỉ test, không bật 24/7)
python scripts\kaggle_watchdog_ci.py --auto-push
```

## Lưu ý
- Không chạy local watchdog 24/7; GitHub Actions là nơi chạy.
- Không push B17 khi v25b đang chạy (tránh batch GPU session limit).
- Không ghi key vào file; chỉ env/GitHub Secrets.
- PAT đã gửi trong chat phải rotate sau khi tạo PAT mới.
