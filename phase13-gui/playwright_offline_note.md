# PLAYWRIGHT OFFLINE CHO NOTEBOOK COMPETITION (RTX) — Nghiên cứu phương án (TASK-6)

> Tác giả: MiMo · 19/10 · Sản phẩm của TASK-6 (DeepSeek chốt **Phương án A**).
> Phạm vi: chỉ nghiên cứu + đề xuất. **Không sửa** `bench_gui_kaggle.py` / `ornith-gui-bench.py` / metadata. Việc build dataset + patch code + push là của DeepSeek (agent chính).

---

## 0. TL;DR

Bench GUI v13 crash vì `pip install playwright` gọi mạng internet trong khi notebook **competition/RTX chạy internet OFF**. Giải pháp: **bundle sẵn wheel `playwright` + bộ binary `chromium` (ms-playwright) vào một dataset Kaggle** rồi attach vào kernel, cài bằng `pip --no-index` trỏ `/kaggle/input/...`, trỏ `PLAYWRIGHT_BROWSERS_PATH` vào dataset → không cần mạng, không cần copy 450MB về `/kaggle/working`. Verify bằng **hard-check tự khởi động chromium thật** ở đầu bench — tuyệt đối không log "setup xong" khi chưa chắc (bài học v13: log "playwright setup xong" xuất hiện dù install fail toàn bộ).

---

## 1. Bằng chứng crash v13 (đúng trên đĩa)

Log `phase13-gui/bench_live_v13.log` (notebook RTX, internet OFF):

| Dòng log | Nội dung | Ý nghĩa |
|---|---|---|
| 4 | `CMD loi 1: ... Temporary failure in name resolution ... /simple/playwright/` | `pip install playwright` không解析 được index → **DNS fail = internet OFF** |
| 5–6 | `ERROR: Could not find a version that satisfies the requirement playwright` / `No matching distribution found` | pip không có wheel local nào để rơi về |
| 8, 10 | `/usr/bin/python3: No module named playwright` (2 lần: `--with-deps` rồi fallback thường) | `python -m playwright install chromium` không chạy được vì module chưa có |
| 12 | `[bench] playwright setup xong` | ⚠️ **LOG SAI** — hàm vẫn in "xong" dù 3 bước trên fail hết (xem §2.3) |
| 57 | `ModuleNotFoundError: No module named 'playwright'` (lúc `sync_playwright()`) | Crash thật sự khi đến đoạn dùng browser |

Code gây ra — `tmp_pull/ornith-gui-bench.py:328-340` (`setup_playwright()`):
```python
try:
    import playwright            # line 334 — ImportError vì image không cài sẵn
except ImportError:
    sh("pip install playwright")  # line 336 — GỌI MẠNG -> DNS fail khi internet OFF
r = sh("python -m playwright install chromium --with-deps", timeout=900)  # line 337
if r is None:
    r = sh("python -m playwright install chromium", timeout=900)          # line 339
log("playwright setup xong")       # line 340 — in不论成败!
```
Và điểm dùng thật — `tmp_pull/ornith-gui-bench.py:521-524`:
```python
from playwright.sync_api import sync_playwright
pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True)
```

**Điểm mấu chốt:** `bench_kernel/bench_gui_kaggle.py:356-367` (bản kernel chính) có `try: import playwright except ImportError: return False` — tức là **cũng không có đường offline**: vắng module → trả False → bench chạy tiếp **không GUI**. Không crash, không alarm — số liệu "0/252" rồi im lặng. (So sánh: 3 kernel SFT/exp đã offline hoá wheels đúng mẫu — `kernel/gui_sft.py:94-102`, `kernel/gui_sft_v19.py:127`, `exp_kernel/exp_h2_matrix.py:514-527` dùng `pip install --no-index --no-deps --find-links {wheels}`.)

---

## 2. Gốc rễ — 3 tầng

### 2.1 Tầng wheel (playwright Python package)
Không có wheel nào trong `/kaggle/input` hay `/kaggle/working` → pip phải lên mạng index PyPI → DNS fail trên notebook competition. **Thiếu thứ duy nhất có thể mang vào offline: file `.whl`.**

### 2.2 Tầng browser (chromium của ms-playwright)
Ngay cả khi import được `playwright`, `chromium.launch()` vẫn cần **binary chromium** đã download (thường ở `~/.cache/ms-playwright`, ~170MB: `chromium-*/chrome-linux/` + `chromium_headless_shell-*/` + `ffmpeg-*/`). `playwright install chromium` cũng gọi mạng → cũng fail offline. → **phải bundle cả 2 tầng** (wheel + browser) hoặc chứng minh browser/system libs đã có sẵn trong image.

### 2.3 Tầng quan sát (silent failure) — phải sửa regardless
`log("playwright setup xong")` chạy không điều kiện → log v13 **nói dối**; bench sau đó chạy `gui=False` mà kết quả vẫn "thành công". Bài học áp dụng thẳng vào design verify (§5): **mọi bước setup phải assert, và sau cùng phải launch thử 1 browser thật trước khi nhận task.**

---

## 3. PHƯƠNG ÁN A — Bundle wheel + browser vào dataset (KHUYẾN NGHỊ, DeepSeek đã chốt)

### 3.1 Ý tưởng
Một dataset Kaggle mới (đề xuất slug `hhjiji/ornith-offline-browsers`) chứa 2 thư mục:
```
wheels/      # playwright-*.whl + greenlet-*.whl + pyee-*.whl (manylinux, khớp python version của image)
browsers/    # ms-playwright/ (chromium + chromium_headless_shell + ffmpeg, tải từ máy LINUX)
```
Kernel attach dataset này → `pip install --no-index --no-deps --find-links /kaggle/input/<ds>/wheels playwright` → set `PLAYWRIGHT_BROWSERS_PATH=/kaggle/input/<ds>/browsers/ms-playwright` → `chromium.launch()` chạy thẳng từ `/kaggle/input` (**read-only mount không vấn đề** vì chỉ đọc executable; playwright chỉ ghi cache/log vào `/tmp`).

### 3.2 Các bước build (chỉ làm 1 lần, máy có internet)

> ⚠️ **Bắt buộc build trên LINUX.** Wheel playwright platform-specific (`manylinux2014_x86_64`) và browser bundle của ms-playwright chỉ chạy trên linux — build trên Windows máy này sẽ ra wheel win_amd64 + browser Windows → vô dụng trên Kaggle. Cách tiện nhất: **1 notebook Kaggle CPU thường (không competition, Internet ON)** — không đụng quota GPU `hhjiji`.

**Step A1 — chuẩn bị notebook internet-ON, cài & tải:**
```bash
python3 --version                    # GHI LẠI version (vd 3.10.x) — phải khớp python của kernel RTX
pip download playwright greenlet pyee -d wheels/   # ra *.whl manylinux
python3 -m pip install playwright
PLAYWRIGHT_BROWSERS_PATH=$PWD/browsers python3 -m playwright install chromium
du -sh wheels/ browsers/             # dự kiến ~45MB + ~170MB
```

**Step A2 — smoke-test NGAY tại đây (chưa upload):**
```bash
PLAYWRIGHT_BROWSERS_PATH=$PWD/browsers python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); print('CHROMIUM', b.version); b.close()"
```
Gate: in ra `CHROMIUM <version>` — nếu fail ở bước này thì KHÔNG upload, sửa tiếp.

**Step A3 — upload dataset** (2 cách, cách 1 an toàn hơn):
```bash
# Cách 1: dùng chính notebook internet-ON ở trên, thêm cell cuối:
from kaggle.api.kaggle_api_extended import KaggleApi
#   -> upload thư mục containing wheels/ + browsers/ + README.md (ghi version + ngày build)
# Cách 2 (từ máy có CLI auth):
kaggle datasets create -p <thu_muc_chua wheels/ + browsers/>   # private dataset
```
**Bắt buộc ghi `README.md` trong dataset:** phiên bản playwright, phiên bản chromium (từ `browser.version`), `python3 --version` của build, ngày build. Kernel sau check version để phát hiện lệch (§5 gate).

### 3.3 Các bước dùng trong kernel RTX (patch đề xuất cho bench — DeepSeek/GLM tự áp)

```python
def setup_playwright():
    """Offline 100%: chi cai tu dataset da attach, khong keo mang."""
    # 1) tim wheel trong /kaggle/input
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("playwright-") and f.endswith(".whl") for f in files):
            wheels = root; break
    assert wheels, "THIEU playwright wheel -> attach dataset ornith-offline-browsers"
    sh(f"pip install --no-index --no-deps --find-links {wheels} playwright greenlet pyee")

    # 2) tim browsers bundle
    browsers = None
    for root, dirs, _ in os.walk("/kaggle/input"):
        if "ms-playwright" in dirs:
            browsers = os.path.join(root, "ms-playwright"); break
    assert browsers, "THIEU ms-playwright bundle -> attach dataset ornith-offline-browsers"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers

    # 3) HARD-VERIFY: launch 1 browser that that that that that that that that that
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        log(f"playwright OK: {playwright.__version__} / chromium {b.version}")
        b.close()
```
Khác với pattern unsloth hiện tại: **không `return False` nhẹ nhàng** — thiếu bundle là `assert` fail ngay đầu run, vì bench GUI vô nghĩa khi thiếu browser (§2.3). Nếu muốn fail-soft thì phải log `GUI_OFF` thật to + ghi vào `bench_result.json` `"gui": false` để không ai đọc nhầm số liệu.

### 3.4 Rủi ro của A

| # | Rủi ro | Mức | Cách giảm |
|---|---|---|---|
| A-i | Lệch `python3 --version` giữa notebook build và kernel RTX → wheel tag mismatch → "No matching distribution" | TB | Ghi version vào README dataset; verify `python3 --version` trong kernel trước khi pip; nếu lệch thì rebuild wheel đúng version |
| A-ii | Image RTX thiếu system lib chromium (vd `libnss3.so`) → launch lỗi `error while loading shared libraries` | TB-cao | Test launch thật ngay run đầu (gate §5). Nếu fail → chuyển B hoặc bundle thêm `.deb` libs (phức tạp, chỉ làm nếu thật sự cần) |
| A-iii | Dataset thay đổi giữa chừng (upload bản mới) → version wheel/browser lệch adapter bench | Thấp | Pin version trong README + assert version trong kernel; dataset là append-version trên Kaggle, kernel attach version cụ thể |
| A-iv | `--no-deps` làm thiếu `greenlet`/`pyee` (không có trong image) → import playwright lỗi | Thấp | Bundle đủ 3 wheel (đã nêu ở A1) rồi mới `--no-deps` — hoặc bỏ `--no-deps` vì `--find-links` đã local hết, không risk mạng |
| A-v | `/kaggle/input` read-only → playwright không ghi được cache | Thấp | Chỉ cần ghi `/tmp` (mặc định) — đã kiểm chứng pattern này chạy được ở image Kaggle khác |

### 3.5 Ưu/nhược
- ✅ **1 lần build, mọi kernel dùng lại**; không phụ thuộc mạng; không tốn thời gian mỗi run (trừ ~2-4s pip local + ~5s launch).
- ✅ Dataset ~215MB — trong giới hạn Kaggle, không ảnh hưởng quota.
- ❌ Phụ thuộc system libs của image (rủi ro A-ii) — nhưng verify gate phát hiện ngay run đầu, không silently.

---

## 4. PHƯƠNG ÁN B — Bundle CHỈ wheel, dùng browser/system có sẵn

### 4.1 Ý tưởng
Chỉ bundle `wheels/` (~45MB, gồm playwright+greenlet+pyee). Browser lấy từ image:
- Nếu image có sẵn `chromium`/`google-chrome` system → dùng `launch(executable_path="/usr/bin/chromium")` hoặc để playwright tự tìm.
- Hoặc trong notebook **internet-ON lần đầu** chạy `python -m playwright install chromium` 1 lần rồi **lưu `/root/.cache/ms-playwright` vào `/kaggle/working`** (nhưng `/kaggle/working` KHÔNG persist giữa các session khác nhau → mỗi run mới lại cần internet → **vòng luẩn quẩn, không dùng được cho competition**).

### 4.2 Verify từng bước
```bash
# B1: pip offline (giống A)
pip install --no-index --no-deps --find-links /kaggle/input/<ds>/wheels playwright greenlet pyee
# B2: KHÔNG cần internet — kiểm tra browser có sẵn không:
python3 -m playwright install --dry-run 2>&1 | head -20
which chromium chromium-browser google-chrome google-chrome-stable 2>/dev/null
ldconfig -p | grep -E "libnss3|libatk-1.0" | head -5        # có lib thì chromium chạy được
# B3: launch thử (nếu có system browser)
python3 -c "from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium'); print(b.version); b.close()"
```

### 4.3 Rủi ro của B

| # | Rủi ro | Mức | Ghi chú |
|---|---|---|---|
| B-i | Image **không có** browser system (khả năng cao — image ML thường minimal) | **Cao** | Đây là lý do B chỉ là phương án phụ |
| B-ii | Browser system khác bản playwright expects → CDP mismatch, launch ok nhưng `page.goto` lỗi lạ | TB | Chỉ dùng đúng bản chromium mà playwright test-pass |
| B-iii | `--with-deps` cần apt+internet → offline không chạy được | Cao (nếu thiếu lib) | Không có cách giảm trong competition |

### 4.4 Ưu/nhược
- ✅ Dataset nhẹ (45MB thay vì 215MB).
- ❌ **Phụ thuộc vào thứ mình không kiểm soát** (image contents) — nếu image đổi phiên bản thì bench fail trở lại. **Không recomend cho kernel competition** where reproducibility is the point.

---

## 5. VERIFY GATE — bắt buộc trước khi tin kết quả bench

Chạy theo đúng thứ tự này trong kernel; **mỗi bước fail là FAIL RUN** (không im lặng, không fallback `gui=False` — §2.3):

| # | Lệnh / checkpoint | PASS nếu |
|---|---|---|
| V1 | `python3 --version` | Trùng version ghi trong README dataset |
| V2 | `pip install --no-index --no-deps --find-links <wheels> playwright greenlet pyee` | exit 0, không warning "No matching distribution" |
| V3 | `python3 -c "import playwright; print(playwright.__version__)"` | In đúng version như README |
| V4 | `sync_playwright().start()` + `chromium.launch(headless=True)` | Không exception (lỗi `.so` missing = rủi ro A-ii → dừng, chuyển B/C) |
| V5 | `print(browser.version)` | **Trùng version chromium trong README dataset.** Nếu khác → browser/system khác đã bị dùng thay → coi như FAIL (đừng chạy bench trên browser không kiểm soát) |
| V6 | Smoke 1 trang: `page.goto("file:///...fixture.html")` + `page.click(...)` | Render + click được (chốt end-to-end, bỏ qua mọi path ẩn) |

Chỉ khi V1–V6 xong mới tính thời gian chạy bench. Ghi `playwright_version` + `chromium_version` vào `bench_result.json` để lần sau so được.

---

## 6. So sánh 3 phương án (cho DeepSeek quyết định cuối)

| Tiêu chí | A (dataset wheel+browser) | B (chỉ wheel) | C (giữ nguyên online) |
|---|---|---|---|
| Chạy được khi internet OFF | ✅ | ⚠️ nếu image có browser | ❌ |
| Phụ thuộc image | Thấp | **Cao** | Cao |
| Dung lượng dataset | ~215MB | ~45MB | 0 |
| Thời gian setup/run | +~10s | +~5s | fail ~30s rồi crash |
| Lặp lại được (reproducible) | ✅ (version pin trong README) | ❌ | ❌ |
| **Khuyến nghị** | **✅ DÙNG** | dự phòng nếu A-ii fail | bỏ |

**Đề xuất cụ thể:** làm **A** ngay; trong lúc build nhớ test luôn `ldd`/launch (V4) để dò sớm rủi ro A-ii; nếu launch fail do thiếu lib → quay lại bàn (không âm thầm rơi về B hay `gui=False`).

---

## 7. Câu hỏi / việc cần DeepSeek

1. **Slug dataset**: đề xuất `hhjiji/ornith-offline-browsers` — confirm rồi mình viết README nội dung (DeepSeek tự upload vì mình **không push kernel/dataset**).
2. **Ai build notebook internet-ON** để `pip download` + `playwright install chromium`? (CPU notebook thường, không dính competition rules — không tốn GPU quota.)
3. Patch `setup_playwright()` ở trên DeepSeek tự đưa vào bench version tới, hay cần mình viết sẵn thành patch file? (Mình không sửa bench trực tiếp — chờ lệnh.)
4. Nếu V4 fail do thiếu lib chromium → theo bạn: (a) bundle `.deb` libs vào dataset, hay (b) chấp nhận chuyển sang T4 (không phải RTX/competition) cho bench GUI? M nghiêng (b) — rẻ hơn nhiều so với việc biến kernel competition thành半个 distro.
