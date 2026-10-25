# GUI AGENT — SCHEMA (phase13)

## Quan sát (observation)
- Ảnh chụp màn hình PNG, viewport 1280x720 (resize trước khi đưa vào model).
- Text kèm theo: `Task: ...`, `Step: n`, `Last: <kết quả action trước>`.

## Hành động (model output, 1 dòng mỗi step)
| Action | Format | Ghi chú |
|---|---|---|
| Click | `CLICK x y` | x,y ∈ [0,1000], chuẩn hóa theo W/H — resolution-independent |
| Gõ | `TYPE <text>` | gõ tại vị trí focus hiện tại |
| Phím | `KEY <tên>` | `enter`, `tab`, `esc`, `backspace`, `ctrl+a`, `ctrl+c`, `up/down/left/right` |
| Cuộn | `SCROLL up|down n` | n = bước lăn |
| Chờ | `WAIT` | render chậm |
| Xong | `DONE` | báo hoàn thành task |
| Bỏ | `FAIL` | không làm được |

Quy tắc: CHỈ 1 action/dòng. coords làm tròn int. Không giải thích.

## Chấm điểm (harness tự chấm)
- Mỗi fixture có biến JS `window.__goal_reached` → harness eval sau mỗi action.
- Episode kết thúc khi: goal reached / DONE / FAIL / quá `max_steps` (mặc định 15).
- Reward: 1.0 nếu goal, 0.0 nếu hết bước.

## Vòng luyện tự cải thiện (kế hoạch)
1. **Grounding SFT**: screenshot + "click the X" → `CLICK x y` (data tự sinh từ DOM, xem `gen_grounding.py`; thêm ScreenSpot để eval).
2. **Loop agent**: policy = model đang serve (vLLM), env = fixtures/MiniWob++ offline, tự chơi → lọc episode thắng → SFT lại (giống vòng game hiện tại nhưng modality ảnh).
3. **Mở rộng**: OSWorld (VM Linux), VideoGameBench (emulator) — phase sau.
