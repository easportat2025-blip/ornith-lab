# HƯỚNG DẪN DÙNG BUS — trao đổi tức thì giữa các agent (21/10)

> Đọc file này **trước khi** hỏi/đáp/ngủ chờ. Tin gửi qua bus **đến trong ~1 giây** và
> được **đẩy thẳng vào session OpenCode của bạn** (bạn không cần poll, không cần đọc agent.md).

## 1. Gửi tin (1 lệnh)

```powershell
python scripts/bus_post.py TEN_BAN "NOI DUNG TIN" --tag bench|app|harness|question|done
```

- `TEN_BAN`: `MiMo` / `GLM` / `DeepSeek` ✓
- Nếu bus chưa chạy → lệnh tự ghi vào `scripts/bus_outbox.jsonl` ✓ (không mất tin ✓)
- Tin **dài** (nhiều dòng) → ghi vào file rồi gửi đường dẫn:
  ```powershell
  python scripts/bus_post.py MiMo "chi tiet: xem file phase13-gui/xxx.md" --tag question
  ```

## 2. Ba luật bắt buộc (thay đổi từ 21/10)

| # | Luật | Vì sao |
|---|---|---|
| 1 | **Trao đổi nhanh → BUS**, không dùng agent.md | agent.md chỉ đọc khi agent tình cờ mở → gọi nhau sẽ bị trễ hàng giờ |
| 2 | **`agent.md` = SỔ CÃI (append-only)**: ghi quyết định / số liệu / CLAIM / RELEASE / kết luận | để người và agent sau đọc lại được; đây là bản ghi bền |
| 3 | **Không "ghi rồi ngủ"**: post bus xong → làm việc khác tiếp | tin sẽ tự đến bạn trong 1s; chờ là lãng phí |

## 3. Watchdog giờ báo tin ngay (bạn không cần tự chạy `kaggle kernels output`)

- Poll mỗi **60s** ✓ (trước 120s) ✓
- **Post bus** khi kernel COMPLETE/ERROR ✓ và khi push xong ✓
- Watcher `agent.md` cũng **post bus** mỗi dòng mới ✓ → tin của agent khác đến bạn ngay ✓

## 4. Việc cụ thể của từng agent (21/10 11:45)

### MiMo — ưu tiên #1: làm sạch suite B15.5
- **Đọc trace T14–T18**: `phase13-gui/out_bench_v155_v21/b15_result.json` (mỗi episode có `trace`/`trajectory` ✓) + `phase13-gui/out_bench_v155_B/b15_result.json` ✓
- Câu hỏi: **task nào (ngoài T13) có màn hình tự mâu thuẫn / thiếu phản hồi?** → nếu có: sửa ✓
- Đã sửa T13 ✓ (validate lại khi gõ/blur) — dùng đó làm mẫu: sửa → `checker --self-test` 18/18 + 18/18 fail-rejected + dummy replay 18/18 ✓ → **báo bus ngay** ✓
- Sau đó (ưu tiên #2) **TASK-26**: 5 app thật, mỗi app có **biến ngẫu nhiên** (mật khẩu/mã/số đổi mỗi lần chạy ✓) + **nhiều bước** ✓ + 1 task cần phím/scroll ✓ + success-policy **đọc biến từ DOM** ✓ + fail-policy ✓ + self-test ✓ (đặt file trong `phase14-desktop/tasks/` ✓)

### GLM — ưu tiên: DESKTOP-BENCH (TASK-28)
- `phase14-desktop/harness.py` **đã chuyển sang Playwright headful** ✓ (bạn KHÔNG cần sửa lại phần đó ✓):
  `launch(headless=False)` ✓ + `page.evaluate` ✓ + tự tìm chromium trong bundle `ornith-offline-browsers` ✓ + **`os.environ['DISPLAY']=':99'`** ✓ + đóng browser mỗi episode ✓
- **Còn 1 lỗi chưa giải: OFFSET 86px** ✗ (ảnh chụp cả màn hình → có thanh công cụ browser → tọa độ CSS lệch 86px ✓) → **cắt ảnh theo viewport** ✓ (`off_y = chiều cao cửa sổ - chiều cao viewport thật` ✓) để tọa độ agent khớp CSS ✓
- Viết kernel GPU `phase13-gui/kernel_desktop_bench/` ✓: task `T20_2048` ✓ (điểm = reward ✓) + ≥ 1 task nhiều bước ✓ (app của MiMo ✓ nếu có ✓) + ≥ 20 episode/task ✓ + ghi `desktop_result.json` (schema giống `b15_result.json` ✓) + `obs/*.png` + `actions.jsonl` + `reward.json` ✓
- **Không push kernel** (tôi push) ✓ + **báo bus khi xong** ✓

## 5. Trạng thái chung (để các agent biết bối cảnh)

| Mục | Số |
|---|---|
| v21 vs v18 baseline | B15 **30.6%** vs 27.8% ✓ · B15.5 5.6% vs 0% ✓ · B16 29.2% vs 25.0% ✓ (sẽ đo lại trên trang đã sửa ✓) |
| Model thắng | T09_coupon 18/18 · T11_counter 8/8 · T03_delayed 7/7 · T10_canvas 5/5 |
| **Model thua 0** | signup 0/20 · pagecode 0/19 · errorfix 0/18 · login 0/16 · tabcode 0/7 |
| ⇒ Kết luận | lỗi là **nhiều bước + gõ chữ + đọc yêu cầu**, **không phải format** ✓ |
| 3D | metric "knife-edge" ✓, dễ hơn GUI ✓ → ưu tiên GUI ✓ |
| Train v22 | đang chạy (v3 ✓ — đã sửa 2 bug ✓) · v23 kernel đã dựng sẵn ✓ (`phase13-gui/kernel_v23/` ✓) |
| GPU | A 19.2h + B 22.5h còn ✓ (reset 24/10 thêm 60h ✓) |
| Space | Docker `kkouadn/dual_orchtractor` đang PAUSED (hết 16h CPU/ngày free tier) → có agent phụ đang push lại ✓ |

## 6. Lệnh kiểm tra nhanh

```powershell
# tin moi (2 tin cuoi)
python -c "import io;print(''.join(io.open('scripts/bus.jsonl',encoding='utf-8').readlines()[-2:]))"
# bus con song?
python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8777/health',timeout=5).read())"
# tat ca ket qua bench
python scripts/collect_results.py
```
