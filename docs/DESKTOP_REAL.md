# DESKTOP THẬT (B18) — X11 + app OS, không phải HTML giả lập

> phase14-desktop hiện tại: Xvfb + Chromium + app HTML. Nó là "desktop-like", không phải
> desktop OS thật. B18 dùng **cửa sổ X11 thật** và **ứng dụng Linux thật**, thao tác bằng
> xdotool/wmctrl, quan sát bằng screenshot, kiểm tra bằng file/CLI/OCR.

## 1. Mục tiêu

- Đo capability computer-use thật: mở app, focus window, gõ, kéo/thả, menu, dialog,
  clipboard, file system, phím tắt, recovery.
- Không phụ thuộc DOM/CDP; model chỉ thấy ảnh và action.
- Chạy được trên Colab/Kaggle CPU (không cần GPU) để tiết kiệm quota train.
- Tái lập: setup script + version + reset mỗi episode.

## 2. Kiến trúc

```
Xvfb :99 (1280x800x24)
  └─ openbox (window manager)
      ├─ xterm
      ├─ gedit
      ├─ thunar / pcmanfm
      ├─ galculator
      ├─ libreoffice --writer/--calc
      └─ chromium (task web thật, không DOM)
screenshot: import/scrot
action: xdotool (mouse/key), wmctrl (window)
clipboard: xclip
checker: file, CLI, pdftotext, OCR (tesseract), wmctrl
```

- **Quan sát**: PNG 1280×800; có thể crop/scale theo recipe.
- **Hành động**: cùng schema B15:
  `CLICK x y`, `TYPE text`, `KEY ctrl+a`, `SCROLL n` (1 step=100px),
  `MOVE x y`, `DRAG x1 y1 x2 y2`.
- **Reset**: kill app, xóa file task, khôi phục config; không dùng lại state cũ.
- **Timeout**: mỗi episode 60–120s; quá thì fail + screenshot.

## 3. Task set B18 (12 task / 9 capability)

| ID | Capability | Task | Checker |
|---|---|---|---|
| D01 | terminal | mở xterm, tạo file bằng lệnh | file tồn tại + nội dung |
| D02 | file manager | tạo/rename file trong thunar | tên file + content |
| D03 | text editor | gedit: gõ text, save | file content |
| D04 | calculator | galculator: 17*23, copy kết quả | clipboard/OCR = 391 |
| D05 | spreadsheet | LibreOffice Calc: nhập bảng, save CSV | CSV parse |
| D06 | writer | LibreOffice Writer: gõ, export PDF | pdftotext |
| D07 | browser | Chromium: form local, submit | file/server state |
| D08 | window | mở 2 app, move/resize, alt-tab | wmctrl geometry/focus |
| D09 | clipboard | copy từ gedit sang terminal/file | clipboard/file |
| D10 | menu/dialog | mở menu, chọn item, đóng dialog | app state/file |
| D11 | recovery | dialog lỗi → dismiss → hoàn thành | file + no dialog |
| D12 | multi-app | lấy dữ liệu từ app A, ghi vào app B | file cuối |

Task có thể tăng độ khó dần (W1/W2) mà không đổi checker.

## 4. Determinism & checker

- Ưu tiên checker **file/CLI**; OCR chỉ khi bắt buộc (calculator).
- Mỗi task có `setup` tạo trạng thái sạch; `checker` chạy ngoài app.
- Không dùng pixel diff làm pass/fail chính; chỉ dùng để debug.
- Dummy expert phải pass 12/12 trước khi đo model. Nếu task không pass với expert → task lỗi.
- Lưu `actions.jsonl`, screenshot mỗi bước, `reward.json`, `summary.json`.
- Task fail phải lưu screenshot bước cuối + window list + clipboard.

## 5. Setup

### Colab/Kaggle (khuyến nghị)
```bash
bash desktop_real/setup_linux.sh
python desktop_real/proof_real.py
python desktop_real/tasks.py --selftest
```
- Cần `sudo`/apt; Colab có internet; Kaggle có thể thiếu package → pre-stage .deb.
- Xvfb/openbox/xdotool có sẵn hoặc cài nhanh; LibreOffice nặng, cài khi cần.
- Nếu không có `xdotool`: dùng bundle offline (như phase14) hoặc `python-xlib`.

### Local Windows
- Cách sạch: WSL2 + Ubuntu + cùng setup script; hoặc Docker image.
- Hiện máy chưa có Docker/WSL distro → **chưa phải đường chạy chính**.
- Không chạy task trên desktop Windows thật của user (rủi ro mất dữ liệu).

### Docker (tương lai)
- Base `ubuntu:24.04`, cài Xvfb/openbox/apps, entrypoint chạy proof.
- Mount task workspace tạm; không mount home.
- Image tag theo ngày; snapshot để reset nhanh.

## 6. So sánh với phase14

| | phase14 | B18 |
|---|---|---|
| App | HTML trong Chromium | app Linux thật |
| Quan sát | screenshot | screenshot |
| Hành động | xdotool | xdotool |
| Checker | DOM/CDP | file/CLI/OCR/wmctrl |
| Window manager | không/đơn giản | openbox thật |
| Độ khó | thấp | cao hơn |
| Rủi ro | thấp | cần reset/isolate |

## 7. Acceptance

- `proof_real.py` PASS trên Colab CPU (xterm tạo file thật).
- `tasks.py --selftest` 12/12 PASS với expert (hoặc SKIP có lý do cho app thiếu).
- v25b baseline chạy 12 task, không crash; stuck/repetition <50%.
- Recovery task không tệ hơn v22; ít nhất 1 task multi-app pass.
- Log/artifact upload HF; manifest ghi package version + commit.

## 8. Rủi ro

| Rủi ro | Chặn |
|---|---|
| App không cài được | fallback xterm/gedit; pre-stage .deb |
| Checker flaky | file/CLI; chạy 2 lần; timeout rõ |
| Window focus sai | wmctrl focus + wait; retry 1 lần |
| OCR sai | dùng clipboard/file thay thế |
| Task quá dễ/khó | dummy expert + baseline; chỉnh W1/W2 |
| Local Windows | WSL2/Docker; không chạy host |

## 9. Việc tiếp theo

1. Chạy proof trên Colab CPU; chụp screenshot làm bằng chứng.
2. Hoàn thiện 6 task deterministic trước; 6 task còn lại sau.
3. Tích hợp harness model (vLLM/HF) + checker.
4. Đo v25b; mine failure; thêm task recovery/clipboard.
5. Đưa B18 vào gate hàng ngày; tăng độ khó mỗi ngày.

---

*Desktop thật = OS thật + app thật + checker thật. Không đánh đổi bằng DOM cho dễ.*
