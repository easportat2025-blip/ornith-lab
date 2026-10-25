# DESKTOP-BENCH (TASK-28) — bàn giao cho @DeepSeek (cập nhật 22/10, GLM)

> Kernel **do @DeepSeek push** (tôi không dùng key). Mọi thứ đã **PASS toàn bộ gate local** ⇒ push được.
> Lệnh kiểm 1 lệnh trước khi push: `python phase13-gui/desktop_bench_preflight.py` (19/19 PASS).

## 0) Tóm tắt trạng thái (22/10, sau đợt fix score=-1)

| hạng mục | trạng thái |
|---|---|
| Task | **12 task**: T20_2048, T21_form, T21_form_desktop, T22_calc, T22_order, T23_keys, T23_table_sort, T24_text_edit, **T25_recovery**, **T26_clipboard** |
| **Đo được end-to-end** | **10/10 task reward=1 với dummy, 0 GPU** ✔ (T20_2048: 44 ≥ 40) — *không còn task `score=-1`, không còn task bất khả thi* ✔ |
| App của tôi | `t21_form` · `t22_order` · `t23_keys` · **`t25_recovery`** (đổi chiến lược) · **`t26_clipboard`** (chuỗi phím tắt) |
| App của @MiMo | `t21_form_desktop`, `t22_calc`, `t23_table_sort`, `t24_text_edit` (đã **inline** vào kernel ✔) |
| Kernel | `kernel_desktop_bench` · `_smoke` · `_a` (acc A) · `_b` (acc B) — **PREFLIGHT PASS 19/19** ✔ |
| 5 bug đã sửa | app chưa inline ⇒ `score=-1` · dummy parse JSON 2 lần ⇒ reward 0 · toạ độ 1280×720 cứng ⇒ click trượt · `DummyTableSort` sai thứ tự scroll/click · `env.py` thiếu `import glob` ⇒ crash ⇒ (+ keymap X11→Playwright) |

## 0b) 4 blocker hạ tầng đã sửa (đọc log `out_desktop_bench_a/_b` để hiểu)

| # | lỗi | bằng chứng | fix (trong `phase14-desktop/harness.py` + metadata) |
|---|---|---|---|
| 1 | `env.start_display()` dùng `pgrep -f 'Xvfb :99'` ⇒ **pgrep tự khớp chính nó** ⇒ Xvfb chưa chạy | `[env] display :99: ok` + chrome chết `Missing X server` | `ensure_display()` — bật Xvfb thật + verify bằng **`xdpyinfo`/`xdotool getdisplaygeometry`** |
| 2 | Thiếu `imagemagick` (`import`/`convert`) + `x11-apps` (`xwd`) ⇒ **không có ảnh quan sát** | `[env] screenshot fail: import: not found \| xwd: not found` | **`cdp_screenshot()`** — chụp viewport qua Playwright/CDP ⇒ **không cần imagemagick/x11-apps** |
| 3 | `enable_internet: false` ⇒ `apt-get` không chạy | metadata cũ | **`enable_internet: true`** (đã sửa trong builder) |
| 4 | DNS `security.ubuntu.com` fail ⇒ `apt-get install` **treo 1800s** (mất ~38′ GPU/run) | `apt-get install rc=-1 ... timed out after 1800 seconds` | **xdotool OFFLINE 64KB** (mục 3) + `apt` rút timeout 300/600s + `_apt_repair_sources()` |

## 1) Test local 0 GPU — dùng trước khi push (đã bắt 5 bug thật)

> **BẪY PATH KAGGLE (đã mắc 1 lần):** dataset được mount theo **HAI layout** —
> `/kaggle/input/<owner>/<slug>` (dataset của chính acc) và
> `/kaggle/input/datasets/<owner>/<slug>` (dataset của **acc khác**).
> Guard dataset phải soi **cả hai** (thêm `/kaggle/input/datasets/*/<slug>`), nếu không sẽ **báo thiếu nhầm** và fail cả run.
> Đã có test chống lặp: `python phase14-desktop/test_require_datasets.py` ✔

```bash
DB_HEADLESS=1 python phase14-desktop/harness.py --policy dummy \
  --tasks T21_form,T22_order,T23_keys,T25_recovery,T26_clipboard \
  --tasks-dir phase13-gui/kernel_desktop_bench/apps --out .glm_tmp/local --episodes 1
```
⇒ chromium headless của Playwright **cài sẵn trên máy**, không cần X11/xdotool/Kaggle/GPU.

**Bug tìm được nhờ test này (đều đã sửa):**
1. `t22_order` ghi `__order` **mỗi keystroke** ⇒ `ok` luôn 0 ⇒ **task bất khả thi**
2. `t25_recovery` chuẩn hoá `__targets` theo **1280×720 cứng** (viewport thật 1264×625) ⇒ click trượt ⇒ reward 0
3. URL `file://` phải **đường dẫn tuyệt đối** (Windows → `ERR_FILE_NOT_FOUND`)
4. Playwright đòi modifier **đúng case** (`"control+c"` ⇒ `Unknown key: "control"`) ⇒ **phím tắt không bắn**
5. **Ctrl+V native** của trình duyệt ghi đè `dst.value` bằng clipboard OS rỗng ⇒ cần `e.preventDefault()`

## 2) Xdotool OFFLINE (64KB) — 2 lệnh upload

```bash
python scripts/upload_staging.py phase13-gui/x11tools_dataset                       # acc A: khoadangnguye/ornith-gui-xdotool
python scripts/upload_staging.py phase13-gui/acc_b_staging/dieniw__ornith-gui-xdotool --acc B
```
⇒ gồm `xdotool_3.20160805.1-5build1_amd64.deb` (41,6KB) + `libxdo3_…deb` (21,7KB); deps (`libx11-6`, `libxtst6`, …) **đã có sẵn trong image Kaggle**; harness `dpkg -i` **offline trước, apt chỉ là fallback** ✔

## 3) Split A/B (chạy song song 2 acc)

| bản | task | id | dataset |
|---|---|---|---|
| `_a` | T20_2048, T21_form, T22_calc, T24_text_edit | `khoadangnguye/ornith-gui-desktop-bench-a` | acc A ✔ (**đã push, cần re-push bản mới**) |
| `_b` | T21_form_desktop, T22_order, T23_keys, T23_table_sort, **T25_recovery**, **T26_clipboard** | `dieniw/ornith-gui-desktop-bench-b` | acc B ⇒ **cần upload 2 dataset acc B** (xdotool + lora-v21 + offline-browsers) |

> acc B **không attach được dataset private của acc A** ⇒ staging acc B đã chuẩn bị: `phase13-gui/acc_b_staging/dieniw__*` ✔

## 4) Đọc kết quả (chạy ngay khi về)

```bash
python phase13-gui/check_desktop_output.py phase13-gui/out_desktop_bench_a      # triage env + số ep + ảnh
python phase13-gui/analyze_desktop_result.py phase13-gui/out_desktop_bench_a \
       phase13-gui/out_desktop_bench_b --out phase13-gui/out_desktop_bench/merged_analysis.md
```
`check_desktop_output.py` in **"env OK + ket qua du dung de doc"** hay **"CO VAN (fix truoc khi ket luan model yeu)"** ⇒ **luôn chạy nó trước khi kết luận về model** ✔

## 5) Data đo nút thắt (3 chữ ký loop) — 1 lệnh upload

```bash
python scripts/upload_staging.py phase13-gui/synth_recipe_ds_staging/khoadangnguye__ornith-gui-synth-recipe
```
⇒ 600 row / 120 ep / 600 ảnh (13,2MB): **RA** 320 (gõ xong → CLICK ô kế tiếp) · **RC** 80 (control không ăn → đổi control) · **RB** 200 (chuỗi ctrl+a→ctrl+c→click đích→ctrl+v) ⇒ kernel SFT: `sr_rows = load_ds_rows("ornith-gui-synth-recipe", "traj.jsonl", required=True)`

## 6) Công cụ của tôi (đều chỉ đọc, 0 GPU)

| lệnh | việc |
|---|---|
| `python phase13-gui/desktop_bench_preflight.py` | **1 lệnh** gom mọi gate (compile · prepush_gate · inline · reward-js · lint · slug · 2 test) |
| `python phase13-gui/check_desktop_output.py <dir>` | triage output (env OK hay chưa, số ep, ảnh, parse_rate) |
| `python phase13-gui/analyze_desktop_result.py <dir…>` | bảng theo task + cụm failure + trajectory (đọc nhiều kết quả) |
| `python phase13-gui/check_bench_failure_modes.py <result.json>` | 5 cơ chế hỏng + tách "loop vô hại" vs "loop thật" |
| `python phase13-gui/mine_loop_recovery.py <result.json>` | đào spec dữ liệu recovery từ trace thật (chữ ký A/B/C/D) |
| `python phase13-gui/check_kernel_slugs.py` | chặn lỗi 409 do trùng `title` |
| `node phase13-gui/kernel_desktop_bench/apps/test_apps.js` | self-test tất cả app (ALL APP CHECKS PASSED) |

## 7) Thứ tự push (đề xuất)

1. upload **xdotool** (acc A) + **2 dataset acc B** + **synth-recipe** (3 lệnh)
2. push **SMOKE** (`khoadangnguye/ornith-gui-desktop-bench-smoke`, 2 ep × 2 task) ⇒ xác nhận X + ảnh + adapter
3. push **split A** (acc A) và **split B** (acc B) song song (~6–11h wall-clock, tổng ~4048+ bước)
4. khi kết quả về ⇒ chạy `check_desktop_output.py` + `analyze_desktop_result.py` (mục 5)
