# Nâng cấp an toàn (upgrade-safe ops)

Mục tiêu: **đang nâng cấp dở thì vòng lặp Kaggle vẫn chạy**. Mọi thay đổi phải
additive (thêm mới), có default giữ hành vi cũ, và có đường lùi.

## 1. Nguyên tắc

1. **Không đổi tên workflow cũ** khi chưa có workflow mới chạy ổn. `ops-tick`
   đang tham chiếu trực tiếp `kaggle-watchdog.yml` và `ops-heartbeat.yml`.
2. **Không bỏ trigger cũ** (`schedule`, `workflow_run`, `workflow_dispatch`)
   trong cùng một lần push. Thêm trigger mới trước, xác nhận rồi mới cân nhắc bỏ.
3. **Default phải giữ hành vi cũ.** Input mới phải optional; config thiếu/hỏng
   phải fallback về 600s, bật loop, bật heartbeat.
4. **Feature flag thay vì sửa workflow.** Dùng `configs/ops.json` để tắt
   auto-push/download/HF sync/heartbeat mà không đụng YAML.
5. **Health check độc lập.** `ops-health.yml` không phụ thuộc `ops-tick`; nó
   dispatch watchdog khi loop cũ. Đây là lưới an toàn cuối.
6. **Một thay đổi = một commit nhỏ.** Push qua API, xem CI, xem một vòng loop
   rồi mới làm tiếp.
7. **Không có secret trong file.** Token chỉ từ `GITHUB_TOKEN`, `KAGGLE_*`,
   `HF_TOKEN` trong Actions/HF.

## 2. Các lớp dự phòng hiện tại

```
kaggle-watchdog (schedule */10)  <- lớp 1: seed dự phòng
        │
        ▼
ops-tick (self-dispatch, sleep delay)  <- lớp 2: nhịp ~10 phút
        │  kiểm tra watchdog active -> bỏ qua nếu đang chạy
        ▼
kaggle-watchdog (dispatch) + ops-tick (self-dispatch) -> ...
        │
        ▼
ops-health (schedule */30)  <- lớp 3: thấy loop cũ thì dispatch watchdog
```

- Lớp 1 vẫn chạy dù `ops-tick` bị disable.
- Lớp 2 là nhịp chính; đọc `configs/ops.json` mỗi vòng và **tự dispatch
  chính nó**. Lý do: `workflow_run` có thể bị delay/drop (quan sát 27/10: loop
  đứng ~2 giờ dù workflow enabled; `ops-health` re-seed thành công).
- Lớp 2 có active guard: nếu watchdog đang `queued`/`in_progress`, không
  dispatch thêm; chỉ self-dispatch để kiểm tra lại sau.
- Lớp 3 là fallback; không sửa state, chỉ dispatch watchdog và (nếu cần)
  `ops-tick` với `delay_seconds=0` để dựng lại timer.
- Nếu GitHub API lỗi, `ops-health` ghi lỗi vào issue `[ops] loop health` và
  không làm gì thêm.

## 3. Feature flags — `configs/ops.json`

| Khóa | Mặc định | Tác dụng |
|---|---|---|
| `loop.enabled` | `true` | `false` = `ops-tick` không dispatch; watchdog schedule vẫn chạy |
| `loop.delay_seconds` | `600` | nhịp self-dispatch bình thường |
| `loop.upgrade_delay_seconds` | `600` | nhịp khi `upgrade.mode=true` |
| `loop.stale_after_minutes` | `25` | ngưỡng để `ops-health` coi là cũ |
| `features.auto_push` | `true` | `false` = watchdog không tự push kernel `MISSING` |
| `features.download_results` | `true` | `false` = không tải result (tránh 429) |
| `features.heartbeat` | `true` | `false` = `ops-tick` không dispatch heartbeat |
| `features.hf_sync` | `true` | `false` = `hf-sync` bỏ qua upload |
| `upgrade.mode` | `false` | `true` = giữ loop nhưng bỏ heartbeat + HF sync |

Ví dụ đang nâng cấp nặng: sửa `upgrade.mode` thành `true`, push, loop vẫn
chạy 10 phút/lần; xong việc đổi lại `false`.

Ví dụ Kaggle đang 429 vì tải output: đặt `features.download_results=false`.
Watchdog vẫn poll và cập nhật issue, chỉ không tải file.

## 4. Quy trình nâng cấp

### Trước khi sửa

```powershell
python scripts\ops_status.py
python scripts\ops_health.py --dry-run
python -m pytest -q
python scripts\secret_scan.py --tracked-only
```

Xem issue `[ops] kaggle watchdog` và `[ops] loop health` để biết run gần nhất.

### Trong khi sửa

- Thêm file/step mới; giữ nguyên tên workflow, trigger cũ, input cũ.
- Nếu sửa `ops-tick.yml`, giữ `delay_seconds` input và default 600.
- Nếu sửa `kaggle-watchdog.yml`, giữ input `auto_push` và default true.
- Nếu thêm config, cho phép thiếu file (fallback), đừng `require`.
- Chạy `python -m pytest -q` trước khi push; contract tests sẽ bắt việc đổi tên
  workflow/trigger/permission.

### Push

```powershell
$env:GH_TOKEN = "<token>"
python scripts\github_push_files.py --repo easportat2025-blip/ornith-lab `
  --branch main --message "ops: upgrade-safe ..." <files>
```

`github_push_files.py` lấy `main` HEAD hiện tại làm parent, nên không cần
`git pull`/`git push` (và tránh được lỗi HTTPS treo).

### Sau khi push

1. `ci.yml` xanh (compile, YAML/JSON, secret scan, pytest, contract tests).
2. `hf-sync.yml` xanh hoặc skip có lý do (flag/upgrade mode).
3. `kaggle-watchdog.yml` chạy và cập nhật issue + `ops-state`.
4. `ops-tick.yml` chạy sau watchdog, sleep đúng `delay_seconds`.
5. `ops-health.yml` (hoặc dispatch tay) báo loop fresh, không dispatch thừa.
6. Issue `[ops] loop health` có timestamp mới.

### Nếu hỏng

- **`ops-tick` hỏng:** watchdog schedule `*/10` vẫn chạy; `ops-health` sẽ
  dispatch watchdog mỗi 30 phút. Có thể dispatch tay `kaggle-watchdog` với
  `auto_push=true`.
- **`kaggle-watchdog` hỏng:** sửa script/config; dispatch tay lại. Loop sẽ tự
  tiếp tục khi watchdog xong.
- **Config hỏng:** xóa/sửa `configs/ops.json`; `ops-tick` và watchdog fallback
  default. Không cần sửa workflow.
- **Muốn dừng hẳn:** đặt `loop.enabled=false` (giữ watchdog schedule) hoặc
  disable cả `ops-tick` + `kaggle-watchdog` trong GitHub Actions.
- **Rollback:** `git revert <commit>` trên `main` (hoặc push lại file cũ bằng
  API). Không force-push `main`.

## 5. Contract tests

`tests/test_workflow_contracts.py` giữ các hợp đồng tối thiểu:

- `ops-tick` vẫn trigger bởi `kaggle-watchdog` và dispatch đúng tên workflow.
- `ops-tick` vẫn có input `delay_seconds`.
- `kaggle-watchdog` vẫn có input `auto_push`.
- `ops-health` có `actions: write` + `issues: write` và gọi `ops_health.py`.
- `configs/ops.json` có đủ `loop/features/upgrade`.
- `hf-sync` vẫn dùng `requirements-hf.txt` và đọc flag.

Nếu đổi tên workflow/trigger có chủ đích, sửa test **và** tài liệu trong cùng
commit; đừng để test cũ che lỗi.

## 6. Điều không nên làm

- Đổi `name:` của `kaggle-watchdog`/`ops-tick` khi `workflow_run` còn tham
  chiếu tên cũ.
- Xóa `schedule` của watchdog trước khi `ops-health` được verify.
- Thêm bước bắt buộc (`pip install`, checkout) vào `ops-tick` khi chưa cần;
  `ops-tick` hiện không checkout, chỉ đọc config qua API.
- Để `upgrade.mode=true` lâu dài; nhớ đổi lại `false`.
- Push thẳng nhiều thay đổi workflow trong một commit mà không chạy contract
  tests.

## 7. Trạng thái nâng cấp 27/10/2026

- Thêm `configs/ops.json` (feature flags + upgrade mode).
- Thêm `ops-health.yml` + `scripts/ops_health.py` (fallback re-seed).
- `ops-tick` đọc config qua API, fallback default, vẫn giữ input `delay_seconds`.
- Watchdog đọc feature flags `auto_push`/`download_results`; state có `ops_config`.
- `hf-sync` đọc flag `hf_sync` và `upgrade.mode`.
- Thêm contract tests + tài liệu này.
- Không đổi tên/trigger cũ; loop hiện tại vẫn chạy trong lúc push.
