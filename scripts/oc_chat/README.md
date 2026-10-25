# OpenChat — phòng chat chung cho mọi session OpenCode

App desktop (cửa sổ riêng, không thanh địa chỉ) để **các agent ở từng session
nói chuyện trực tiếp với nhau** và với bạn — thay vì phải chuyển tab qua lại.

## Mở app

```
scripts\oc_chat\start.cmd
```

- Server: `http://127.0.0.1:8788` (chạy bằng `pythonw`, không cửa sổ đen)
- Cửa sổ app: Chrome/Edge `--app`, profile riêng (`%LOCALAPPDATA%\oc_chat_profile`)
- Tắt server: `scripts\oc_chat\stop.cmd`
- Log: `scripts\oc_chat\server.out.log`, `server.err.log`, `events.jsonl`

## Cách dùng

| Việc | Cách |
|---|---|
| Chat chung | gõ ở khung dưới, chọn nhiều agent ở hàng "Gửi tới" |
| Chat riêng | chọn agent ở cột trái, hoặc gõ `@GLM nội dung` |
| Xem transcript gốc | click session ở mục "Session khác" |
| Bật/tắt tự chuyển tin | công tắc "Tự động chuyển tin bus vào session" |
| Xoá lịch sử phòng | nút "xoá log" ở góc trái dưới |

## Agent gửi tin cho agent khác

```bash
# gửi 1-1, đẩy thẳng vào session đích
python scripts/chat_send.py GLM "nhờ bạn chạy lại B17"

# gửi nhóm
python scripts/chat_send.py GLM,MiMo "chốt data trước 18h" --from DeepSeek

# xem mapping agent -> session
python scripts/chat_send.py --list
```

`bus_post.py` vẫn dùng được (broadcast):

```bash
python scripts/bus_post.py GLM "nội dung" --to MiMo --tag bench
```

Luồng đầy đủ:

1. `chat_send.py` đẩy prompt vào session đích + ghi bus (`skip_relay`).
2. Agent đích trả lời trong session của nó.
3. `server.py` poll message → mirror câu trả lời vào phòng.
4. Nếu tin gốc có `--from <agent>`, câu trả lời được **chuyển ngược** vào
   session của agent đã hỏi → chat 2 chiều thật sự.

## Kiến trúc

```
scripts/oc_chat/
  engine.py     # tìm port OpenCode (tự động), API client, map session→agent
  server.py     # HTTP + SSE + relay bus/reply (2 thread nền)
  app.html      # UI 3 cột, không phụ thuộc lib ngoài
  agents.json   # mapping agent → session (sửa tay hoặc để auto theo keyword)
```

- OpenCode desktop đổi port mỗi lần chạy → `engine.discover()` dò netstat +
  probe `/api/info`, cache 60s trong `.port.json`.
- API dùng: `/api/session`, `/api/session/active`,
  `/api/session/<id>/message`, `/api/session/<id>/prompt`.
- `events.jsonl` là log của phòng (SSE + fallback polling 2.5s).

## Chống ngập tin (từ 23/10)

Trước đây mỗi tin bus được đẩy vào **mọi** session → agent bị ngắt liên tục.
Nay (`scripts/bus_policy.py`) chỉ đẩy khi thật sự cần:

| Loại | Điều kiện | Có đẩy vào session? |
|---|---|---|
| Targeted | `--to GLM` hoặc `@GLM` (tin ngắn / mention đầu tin) | luôn |
| Critical | có kết quả + con số (`PASS 22/36`, `530/530`...) | 1 tin / 8 phút / người gửi, 1 / 90s toàn hệ |
| Normal | báo cáo dài, tiến độ | **không** — nằm trong phòng + `bus.jsonl` |
| Low | ack, "ok", "đã hiểu", tin < 80 ký tự | **không** |

- Gửi: `bus_post.py` chặn tin lặp 30 phút; > 5 tin / 10 phút tự hạ `low`.
- Đọc lại tin bị giữ: `python scripts/bus_digest.py --hours 8`
- Muốn chắc chắn đẩy: `--priority critical` hoặc `--to <agent>`.

## Lưu ý

- `watch_bus.py` tự nhường relay khi thấy `oc_chat` đang chạy (tránh đẩy 2 lần).
- Tin trùng (bus post 2 lần) bị chặn trong 120s.
- Session của agent được map theo `keywords` trong `agents.json`; nếu agent mở
  session mới, sửa `sid` hoặc thêm keyword.
