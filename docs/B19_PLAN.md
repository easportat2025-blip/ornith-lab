# B19 hard holdout — plan

Mục tiêu: thay B18 (v25b 14/42 = 33.3%, quá dễ) bằng một holdout khó hơn cho
vòng sau. **Không dùng B18 task/HTML làm train; B19 chỉ để đo.**

## Quy mô

- 8 task × 6 variant = **48 episode**.
- Viewport 1280×720, action space giống B18:
  `CLICK x y | TYPE text | KEY name | DONE | SCROLL n | MOVE x y | DRAG x1 y1 x2 y2`.
- Mỗi app expose `window.__spec.vars` (GT) và `window.__state` (trạng thái thật).
- Checker đọc DOM + `__spec` + `__state`, không tin self-report.

## Task / mechanism

| id | mechanism | vì sao khó |
|---|---|---|
| T41_nested_scroll | outer panel + inner panel, target row ở cuối inner | phải chọn đúng panel, scroll 2 tầng rồi click; không chỉ scroll trang |
| T42_precision_drag | slider 0–100 có tick 0/25/50/75/100, target lệch | phải đọc note + kéo đúng vị trí, không kéo quá biên |
| T43_wizard_validation | text field + select, Next disabled đến khi hợp lệ, có error | phải type/select đúng thứ tự, không click Next sớm |
| T44_keyboard_only | form 3 field + select, chỉ Tab/Shift+Tab/Arrow/Enter | không dùng chuột; kiểm tra `mouse_clicks == 0` |
| T45_clipboard_verify | source readonly, ctrl+a/c, click target, ctrl+v, Verify | phải copy đúng, không DONE spam; kiểm tra nội dung |
| T46_dynamic_filter | type filter, list cập nhật, click đúng row | phải đọc kết quả sau khi filter, không click row cũ |
| T47_drag_reorder | kéo item từ vị trí A sang B, kiểm tra thứ tự | drag chính xác, không chỉ click |
| T48_hover_submenu | hover menu cha, submenu hiện, click item đúng | phải MOVE đúng menu rồi click, không click mù |

## Checker / self-test

- `phase13-gui/bench_b19/checker.py`: `CHECKS = {task_id: fn}`.
- `scripts/b19_selftest.py`: policy DOM-based cho từng app; checker self-test
  phải **8/8 PASS**.
- Mỗi task có ít nhất 2 tín hiệu độc lập (DOM value + `__state`/message).
- Static lint + JSON schema + self-test trước khi upload.

## Kernel / queue

- Dataset: `dieniw/ornith-gui-bench-b19`.
- Eval kernel: `dieniw/ornith-gui-bench-b19-v26` (copy B18 kernel, đổi suite,
  dataset, result filename `b19_result.json`).
- Queue target:
  - `after`: `dieniw/ornith-gui-sft-v26`
  - `requires`: `dieniw/ornith-gui-lora-v26`
  - `state`: `pending`, `download_results`: true.
- Watchdog chỉ push sau khi adapter READY; không train trên B19.

## Status (29/10)

- Dataset `dieniw/ornith-gui-bench-b19` **READY** (flat 10 file: `tasks.json`,
  `checker.py`, 8 HTML); kernel `dieniw/ornith-gui-bench-b19-v26` có metadata,
  chưa push (chờ B17/B18 xong).
- Checker + GT self-test **8/8 PASS**; static lint 0 lỗi; flat suite load
  48 episode đã test.
- Queue target đã thêm `after` v26 + `requires` adapter; sẽ push sau B17/B18.
- B19 eval mặc định `ORNI_THINK=0` để đo format `THINK:`/`ACTION:` sạch;
  B17/B18 đang thinking ON để so baseline.
- Chưa có kết quả model trên B19; không dùng B19 làm train.

## Acceptance

- Checker self-test 8/8.
- v25b W1 **< 20%** (mục tiêu < 10%); nếu v25b vẫn >20%, tăng mechanism khó
  hơn, không chỉ thêm variant của task dễ.
- v26 W1 ≤ 10%, parse ≥ 0.95, prose leak ≤ 5%; so per-task.
- B19 không xuất hiện trong bất kỳ train dataset nào.
