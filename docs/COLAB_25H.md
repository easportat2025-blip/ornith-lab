# COLAB 25H/NGÀY — lease, keepalive, log/artifact

> 5 tài khoản Google, mỗi acc ~5h GPU/ngày → ~25h/ngày. Dùng cho test 4-bit, data gen,
> desktop CPU và ablation; **không thay thế gate trên Kaggle**.
>
> Code hiện có: `colab_accounts.py`, `colab_run_task.py`, `colab_exec_bg.py`,
> `colab_wait_run.py`, `colab_stage.py`. Hệ job mới nằm ở `scripts/jobs/`.

## 1. Vì sao cần keeper

Colab free/PRO thu hồi session khi:
- idle quá lâu (không có exec/notebook activity),
- hết quota/ngày,
- VM bị preempt,
- token/OAuth hết hạn,
- đổi account giữa job (token global) → session tạo nhầm acc.

`colab_run_task.py` đã poll 60s và swap token; nhưng nếu job im lặng hoặc agent khác
dùng cùng token, session có thể mất. Keeper thêm:
- **lease**: một job giữ một account/session, không cho job khác chen.
- **keepalive**: ping `colab exec` mỗi 4 phút khi job không in log.
- **fetch**: tải log + artifact khi xong, kể cả fail.
- **release**: trả account, ghi trạng thái.

## 2. Job lifecycle

```
pending -> starting -> running -> fetching -> done
                         |          |
                         +-> failed |
                         +-> lost --+-> retry (tối đa N)
cancelled (từ pending/running)
```

Trạng thái lưu ở `scripts/jobs/state.json` (atomic, lock). OpenChat đọc qua `/api/jobs`.

Job fields tối thiểu:
```json
{
  "id": "colab-20261024-001",
  "backend": "colab",
  "account": 4,
  "session": "glm-cpu2",
  "script": "scripts/desktop_replay_gen.py",
  "args": ["--episodes", "36"],
  "status": "running",
  "created": "2026-10-24T08:00:00",
  "started": "2026-10-24T08:00:10",
  "finished": "",
  "pid": 1234,
  "log_path": "scripts/logs/colab-20261024-001.log",
  "artifacts": ["/content/desktop_replay.zip"],
  "keepalive_until": "2026-10-24T10:00:00",
  "attempts": 1,
  "error": "",
  "meta": {"gpu": "T4", "priority": "high"}
}
```

## 3. Lease & scheduler

- Mỗi account chỉ 1 session; 1 job nặng/account.
- Lease key: `account` + `session`; TTL mặc định 2h, gia hạn khi job còn chạy.
- Nếu job xin account đang bận: xếp `pending`, không swap token.
- Ưu tiên:
  1. gate eval (B15/B15.5/B16/B17)
  2. data generation/replay
  3. ablation 4-bit
  4. desktop B18 CPU
  5. cleanup/test
- Không chạy 2 job cùng account dù một job CPU; tránh token swap race.
- Token swap phải có lock file (`scripts/colab_accounts/.swap.lock`) và retry.

## 4. Keepalive

- Poll trạng thái mỗi 60s (đọc `/content/out.log` + pid).
- Nếu 4 phút không có log mới: chạy một lệnh nhỏ:
  ```bash
  colab exec -s <session> -c "print('keepalive')"
  ```
  (hoặc `echo` tương đương) để giữ session.
- Nếu session mất:
  - thử reconnect 1 lần;
  - nếu vẫn mất, tạo session mới cùng account, chạy lại từ checkpoint;
  - nếu account hết quota, chuyển acc kế tiếp;
  - ghi `lost` + lý do, không treo job.
- Không ping quá dày (<2 phút) để tránh rate limit.

## 5. Log & artifact

- Log VM: `/content/out.log`; launcher ghi pid `/content/job.pid`.
- Khi xong/fail:
  1. `colab exec` đọc log (tail toàn bộ hoặc file);
  2. tải artifact bằng `colab download`/`scp` tương đương;
  3. lưu local `scripts/logs/<job>.log`, `scripts/artifacts/<job>/`;
  4. upload HF `ornith-evals` hoặc `ornith-gui-data`;
  5. ghi `manifest.json` (sha256, size, source).
- Nếu artifact quá lớn: chỉ upload zip đã nén; không commit.
- Nếu log chứa token/key: redact trước khi lưu/upload (`***`).

## 6. Commands (dự kiến)

```powershell
# doctor: kiểm tra account/session/quota, không tạo job
python scripts\jobs\cli.py doctor

# submit job
python scripts\jobs\cli.py submit --backend colab --acc 4 --session glm-cpu2 `
  --script scripts\desktop_replay_gen.py --wait 7200 `
  --download /content/desktop_replay.zip

# xem trạng thái
python scripts\jobs\cli.py list
python scripts\jobs\cli.py status <job-id>
python scripts\jobs\cli.py logs <job-id> --tail 120

# keeper chạy nền
python scripts\jobs\colab_keeper.py --once
python scripts\jobs\colab_keeper.py --loop
```

## 7. Phân bổ 25h/ngày (gợi ý)

| Acc | Giờ/ngày | Việc |
|---|---|---|
| 1 | 5h | gate eval B15/B15.5 |
| 2 | 5h | gate eval B16/B17 |
| 3 | 5h | data gen/replay |
| 4 | 5h | ablation 4-bit / desktop CPU |
| 5 | 5h | backup, test mới, B18 |

Nếu một acc hết quota: dừng, không cố retry; chuyển việc sang acc còn lại. Không dùng
Colab để train 9B full nếu T4 16GB không đủ; 4-bit QLoRA only.

## 8. Failure modes

| Lỗi | Xử lý |
|---|---|
| Session reclaimed | reconnect; nếu fail, tạo mới + checkpoint |
| Token expired | login lại thủ công 1 lần; không lưu code |
| Quota exhausted | đánh dấu acc `quota=0`; chuyển acc |
| OOM | giảm batch/seq; 4-bit; gradient checkpointing |
| Disk full | xóa `/content` tạm; dùng Drive/HF |
| Token swap race | lock + retry; 1 job/acc |
| Log rỗng | kiểm tra launcher/pid; chạy lại với `--verbose` |

## 9. Liên kết

- OpenChat `/api/jobs`, `/api/logs`.
- `docs/GITHUB_HF.md` cho upload HF.
- `docs/TRAINING_LOOP.md` cho eval/gate.
- `scripts/jobs/README.md` cho chi tiết code.

---

*Không giữ session "cho vui": chỉ lease khi có job; hết job thì release để acc khác dùng.*
