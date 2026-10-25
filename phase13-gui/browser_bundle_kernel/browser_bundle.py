"""browser_bundle.py — builder dong goi playwright+chromium OFFLINE (TASK-8, GLM).

CPU + internet ON (duy nhat kernel nay duoc ON — can mang de pip download).
San pham trong output kernel /kaggle/working/:
  wheels/*.whl                     — playwright + deps (greenlet/pyee), manylinux
  browsers/ms-playwright/          — cache chromium ghi THANG vao day (khong copy lan)
  setup_playwright_offline.py      — snippet DeepSeek dan vao bench offline
  bundle_manifest.json             — versions / sizes / sha256 / launch_ok / platform

Sau khi chay: DeepSeek `kernels output` (hoac web UI) roi up dataset
`hhjiji/ornith-offline-browsers` de attach cho bench v18/v19 (kernel RTX, internet OFF).
Snippet bam installer_unsloth_offline(): KHONG mang, KHONG copy sang working
(gop y @MiMo), fail LOUD — khong fallback gui=False kin dao (diem 4 @MiMo).
"""
import glob
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

WORK = "/kaggle/working"
WHEELS = os.path.join(WORK, "wheels")
BROWSERS = os.path.join(WORK, "browsers")
PW_CACHE = os.path.join(BROWSERS, "ms-playwright")
SNIPPET_OUT = os.path.join(WORK, "setup_playwright_offline.py")
VERIFY_PY = os.path.join(WORK, "_verify_pw_tmp.py")
MANIFEST = os.path.join(WORK, "bundle_manifest.json")
TARGET_DATASET = "hhjiji/ornith-offline-browsers"

SNIPPET = '"""setup_playwright_offline() — TASK-8 (GLM), cập nhật theo note @MiMo 17:35.\n\nĐối chiếu note playwright_offline_note.md (Phương án A + VERIFY GATE §5 V1–V6):\nbench chạy trên kernel competition RTX (internet OFF) vẫn dùng được GUI browser\nbằng bundle dataset `hhjiji/ornith-offline-browsers` (wheels/ + browsers/ +\nREADME.md + bundle_manifest.json).\n\nCách dùng trong bench: dán hàm này thay cho `setup_playwright()` hiện có (hoặc\nimport rồi đổi chỗ gọi tương ứng). File này để DeepSeek copy vào kernel.\n\nBám mẫu install_unsloth_offline() (exp_h2_matrix.py):\n  + KHÔNG mạng: pip --no-index --find-links trỏ thẳng vào /kaggle/input/...\n  + KHÔNG copy ~450MB sang /kaggle/working (góp ý @MiMo — mỗi lần mỗi run).\n  + PLAYWRIGHT_BROWSERS_PATH trỏ thẳng vào cache chromium trong dataset.\n\nVERIFY GATE §5 của note — mỗi bước fail = FAIL RUN (RuntimeError), KHÔNG fallback\n`gui=False` kín đáo (điểm 4 @MiMo / §2.3 — log "setup xong" lúc rỗng là lỗi v13):\n  V1  python (kernel) TRÙNG python ghi trong bundle_manifest.json của dataset\n      (lệch = A-i wheel tag mismatch → phải rebuild, không cưỡng pip).\n  V2  pip --no-index --find-links exit 0.\n  V3  import playwright + version TRÙNG manifest.\n  V4  chromium.launch(headless=True) không exception (thiếu .so → A-ii → dừng).\n  V5  browser.version TRÙNG version trong manifest (khác = browser lạ thay → FAIL).\n  V6  smoke file:// + click nút (#btn) → text = "ok" (chốt end-to-end).\n\nTầng wheel: bundle ĐỦ deps (greenlet/pyee do builder pip download); NHÂN VẬT\npip KHÔNG dùng --no-deps để pip tự phân giải từ --find-links (được phép theo\nA-iv của note — local hết, không risk mạng).\n"""\nimport json\nimport os\nimport platform\nimport subprocess\nimport sys\nimport time\n\n\ndef setup_playwright_offline():\n    """Cài playwright OFFLINE + run VERIFY GATE V1–V6; trả dict version/dir.\n    Mọi gate fail -> RuntimeError (FAIL RUN — không có fallback kín đáo)."""\n    t0 = time.time()\n\n    def _fail(msg):\n        raise RuntimeError("PLAYWRIGHT OFFLINE FAIL: " + str(msg))\n\n    def _log(m):\n        print("[pw-offline] " + str(m), flush=True)\n\n    # ---- V1: python của kernel phải TRÙNG python build (manifest dataset) ----\n    meta_path = None\n    for root, _, files in os.walk("/kaggle/input"):\n        if "bundle_manifest.json" in files:\n            meta_path = os.path.join(root, "bundle_manifest.json")\n            break\n    if not meta_path:\n        _fail("khong thay bundle_manifest.json trong /kaggle/input — dataset "\n              "attach hhjiji/ornith-offline-browsers thieu manifest "\n              "(up lai full output cua builder)")\n    try:\n        meta = json.load(open(meta_path, encoding="utf-8"))\n    except Exception as e:\n        _fail(f"doc bundle_manifest.json loi: {type(e).__name__}: {e}")\n    py_expected = (meta.get("platform") or {}).get("python")\n    py_actual = platform.python_version()\n    if not py_expected:\n        _fail("manifest thieu platform.python — khong the gate V1")\n    if py_actual != py_expected:\n        _fail(f"V1 PYTHON SA LECH: build={py_expected} kernel={py_actual} "\n              "(A-i wheel tag mismatch — rebuild theo note §3.2 A1)")\n    _log(f"V1 python OK: {py_actual} (trung manifest {meta_path})")\n\n    # ---- V2: tim wheels dir + pip --no-index (KHONG --no-deps; xem A-iv) ----\n    whl_dir = None\n    for root, _, files in os.walk("/kaggle/input"):\n        if any(f.startswith("playwright-") and f.endswith(".whl") for f in files):\n            whl_dir = root\n            break\n    if not whl_dir:\n        _fail("V2 khong thay playwright-*.whl trong /kaggle/input")\n    _log(f"V2 wheels dir: {whl_dir}")\n    r = subprocess.run(["pip", "install", "--no-index",\n                        "--find-links", whl_dir, "playwright"],\n                       capture_output=True, text=True, timeout=900)\n    if r.returncode != 0:\n        _fail("V2 pip --no-index install fail: "\n              + (r.stderr or r.stdout or "")[-500:])\n\n    # ---- V3: import + version playwright TRÙNG manifest ----\n    try:\n        import playwright\n    except Exception as e:  # noqa: BLE001 — fail loud theo luật\n        _fail(f"V3 import playwright fail: {type(e).__name__}: {e}")\n    pw_expected = meta.get("playwright_version")\n    if pw_expected and playwright.__version__ != pw_expected:\n        _fail(f"V3 PLAYWRIGHT SA LECH: dataset={pw_expected} "\n              f"da-installed={playwright.__version__}")\n    _log(f"V3 playwright OK: {playwright.__version__} (t={time.time() - t0:.0f}s)")\n\n    # ---- V4: PLAYWRIGHT_BROWSERS_PATH trỏ thẳng dataset (không copy) ----\n    cache_dir = None\n    for root, dirs, _files in os.walk("/kaggle/input"):\n        if os.path.basename(root) == "ms-playwright":\n            cache_dir = root\n            break\n        if any(d.startswith("chromium") for d in dirs):\n            cache_dir = root\n            break\n    if not cache_dir:\n        _fail("V4 khong thay ms-playwright cache trong dataset")\n    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = cache_dir\n    _log(f"V4 PLAYWRIGHT_BROWSERS_PATH: {cache_dir}")\n\n    # dry-run chỉ để LOG (offline; không tải gì — báo khi trỏ sai sẽ thấy đây)\n    try:\n        r2 = subprocess.run([sys.executable, "-m", "playwright",\n                             "install", "--dry-run"],\n                            capture_output=True, text=True, timeout=300)\n        tail = ((r2.stdout or "") + (r2.stderr or ""))[-400:].replace("\\n", " | ")\n        _log(f"install --dry-run rc={r2.returncode}: {tail}")\n    except Exception as e:  # noqa: BLE001 — log and continue\n        _log(f"install --dry-run bo qua ({type(e).__name__})")\n\n    # ---- V5 + V6: launch headless THẬT + smoke goto/click ----\n    fixture = "/tmp/pw_offline_fixture.html"\n    with open(fixture, "w", encoding="utf-8") as f:\n        f.write("<html><body><button id=\'btn\'>ok</button></body></html>\\n")\n    ver = None\n    from playwright.sync_api import sync_playwright\n    px = sync_playwright().start()\n    try:\n        browser = px.chromium.launch(headless=True, args=["--no-sandbox"])\n        ver = browser.version\n        page = browser.new_page()\n        page.goto("file://" + fixture.replace("\\\\", "/"))\n        page.click("#btn")\n        txt = (page.text_content("#btn") or "").strip()\n        browser.close()\n    except Exception as e:  # noqa: BLE001 — fail loud (A-ii thiếu .so)\n        _fail(f"V5/V6 launch/smoke fail — {type(e).__name__}: {str(e)[:300]} "\n              "(thiếu lib hệ thống? đối chiếu Phương án B/C của note)")\n    finally:\n        try:\n            px.stop()\n        except Exception:\n            pass\n    br_expected = meta.get("browser_version")\n    if br_expected and ver != br_expected:\n        _fail(f"V5 BROWSER SA LECH: dataset={br_expected} bundle-used={ver} "\n              "(browser lạ được dùng thay — FAIL theo gate §5)")\n    if txt != "ok":\n        _fail(f"V6 smoke click/JS khong ranh: text_content={txt!r}")\n    _log(f"V5 browser OK: {ver} (trung manifest)")\n    _log(f"V6 smoke OK: goto(file://) + click(#btn) -> {txt!r}")\n    _log(f"ALL GATE PASS t={time.time() - t0:.0f}s")\n    return {"playwright": playwright.__version__, "browser_version": ver,\n            "python": py_actual, "wheels_dir": whl_dir,\n            "browsers_path": cache_dir, "manifest": meta_path}\n\n\nif __name__ == "__main__":  # smoke: python setup_playwright_offline.py (kernel offline)\n    setup_playwright_offline()\n'


def log(m):
    print("[bundle] " + str(m), flush=True)


def sh(argv, timeout=1800):
    r = subprocess.run([str(a) for a in argv], capture_output=True, text=True,
                       timeout=timeout)
    out = (r.stdout or "")[-500:].replace("\n", " | ")
    err = (r.stderr or "")[-400:].replace("\n", " | ")
    log(f"$ {' '.join(str(a) for a in argv)} -> rc={r.returncode} "
        f"out: {out} err: {err}")
    return r


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_stats(path):
    n = 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
                n += 1
            except OSError:
                pass
    return n, round(total / (1024 * 1024), 1)


VERIFY_CODE = (
    "import os\n"
    "from playwright.sync_api import sync_playwright\n"
    "fx = '/tmp/pw_offline_fixture.html'\n"
    "with open(fx, 'w', encoding='utf-8') as fh:\n"
    "    fh.write(\"<html><body><button id='btn'>ok</button></body></html>\\n\")\n"
    "p = sync_playwright().start()\n"
    "try:\n"
    "    b = p.chromium.launch(headless=True, args=['--no-sandbox'])\n"
    "    print('PW_LAUNCH_VERSION: ' + b.version)\n"
    "    pg = b.new_page()\n"
    "    pg.goto('file://' + fx)\n"
    "    pg.click('#btn')\n"
    "    print('PW_SMOKE: ' + (pg.text_content('#btn') or '?').strip())\n"
    "    b.close()\n"
    "finally:\n"
    "    p.stop()\n")


def verify_launch():
    try:
        with open(VERIFY_PY, "w", encoding="utf-8") as f:
            f.write(VERIFY_CODE)
        r = subprocess.run([sys.executable, VERIFY_PY], capture_output=True,
                           text=True, timeout=300)
        out = ((r.stdout or "") + "\n" + (r.stderr or ""))
        ver = None
        smoke = None
        for line in out.splitlines():
            if line.startswith("PW_LAUNCH_VERSION:"):
                ver = line.split("PW_LAUNCH_VERSION:", 1)[1].strip()
            elif line.startswith("PW_SMOKE:"):
                smoke = line.split("PW_SMOKE:", 1)[1].strip()
        err = out[-300:].replace("\n", " | ")
        return (ver is not None and smoke == "ok"), ver, smoke, err
    except Exception as e:
        return False, None, None, f"{type(e).__name__}: {str(e)[:200]}"


def write_manifest(st):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    log(f"manifest ghi (stage={st.get('stage')})")


def main():
    t0 = time.time()
    log("BROWSER BUNDLE builder — TASK-8 GLM — CPU + internet ON")
    st = {"stage": "start", "builder": "TASK-8 (GLM)",
          "target_dataset": TARGET_DATASET,
          "platform": {"python": sys.version.split()[0],
                       "platform": platform.platform(),
                       "machine": platform.machine()},
          "wheels": [], "wheels_total_mb": 0,
          "playwright_version": None, "chromium_dirs": [],
          "browsers_total_mb": 0, "launch_ok": None,
          "smoke_ok": None, "browser_version": None, "launch_err": None,
          "snippet_written": None, "readme_written": None,
          "error": None, "t_sec": None}
    write_manifest(st)
    os.makedirs(WHEELS, exist_ok=True)
    os.makedirs(PW_CACHE, exist_ok=True)

    # 1) wheels: playwright + deps (greenlet/pyee) — manylinux cung platform
    st["stage"] = "pip-download"
    write_manifest(st)
    r = sh([sys.executable, "-m", "pip", "download", "--dest", WHEELS,
            "playwright"], timeout=1200)
    if r.returncode != 0:
        st["error"] = "pip download playwright fail"
        write_manifest(st)
        raise SystemExit("pip download THAT BAI — giu log, dung")
    whls = sorted(glob.glob(os.path.join(WHEELS, "*.whl")))
    st["wheels"] = [{"name": os.path.basename(p), "bytes": os.path.getsize(p),
                     "sha256": sha256(p)} for p in whls]
    _n, _mb = dir_stats(WHEELS)
    st["wheels_total_mb"] = _mb
    log(f"wheels: {len(whls)} file / {_mb} MB: "
        + ", ".join(os.path.basename(p) for p in whls))
    write_manifest(st)

    # 2) browsers: cache ghi THANG output (PLAYWRIGHT_BROWSERS_PATH set truoc)
    st["stage"] = "playwright-install"
    write_manifest(st)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PW_CACHE
    r = sh([sys.executable, "-m", "pip", "install", "--no-cache-dir",
            "playwright"], timeout=1200)
    if r.returncode != 0:
        st["error"] = "pip install playwright (builder) fail"
        write_manifest(st)
        raise SystemExit("pip install (builder) THAT BAI")
    try:
        import playwright  # noqa: F401 — chi can import duoc
        from importlib.metadata import version as _pkg_version
        st["playwright_version"] = _pkg_version("playwright")
    except Exception as e:
        st["error"] = f"import playwright fail {type(e).__name__}: {e}"
        write_manifest(st)
        raise SystemExit("import playwright THAT BAI (builder)")
    log(f"playwright {st['playwright_version']} (builder) — install chromium")
    r = sh([sys.executable, "-m", "playwright", "install", "chromium"],
           timeout=2400)
    if r.returncode != 0:
        log("install chromium rc!=0 -> install-deps roi thu lai lan 1")
        sh([sys.executable, "-m", "playwright", "install-deps", "chromium"],
           timeout=1800)
        r = sh([sys.executable, "-m", "playwright", "install", "chromium"],
               timeout=2400)
    st["chromium_dirs"] = sorted(
        d for d in os.listdir(PW_CACHE) if d.startswith("chromium"))
    _nb, _bmb = dir_stats(PW_CACHE)
    st["browsers_total_mb"] = _bmb
    log(f"browsers cache: dirs={st['chromium_dirs']} files={_nb} "
        f"({_bmb} MB)")
    write_manifest(st)

    # 3) verify launch headless trong-builder (launch fail -> deps + lan 2)
    st["stage"] = "verify-launch"
    write_manifest(st)
    ok, ver, smoke, err = verify_launch()
    if not ok:
        log(f"launch/smoke fail ({(err or '')[:120]}) -> "
            f"install-deps + thu lan 2")
        sh([sys.executable, "-m", "playwright", "install-deps", "chromium"],
           timeout=1800)
        ok, ver, smoke, err = verify_launch()
    st["launch_ok"] = ok
    st["smoke_ok"] = (smoke == "ok")
    st["browser_version"] = ver
    st["launch_err"] = err or None
    log(f"launch_ok={ok} smoke={smoke!r} browser={ver or '?'}")
    write_manifest(st)

    # 4) snippet (giong file repo) + README dataset + manifest cuoi + cleanup
    st["stage"] = "snippet-manifest-final"
    write_manifest(st)
    with open(SNIPPET_OUT, "w", encoding="utf-8") as f:
        f.write(SNIPPET)
    st["snippet_written"] = os.path.isfile(SNIPPET_OUT)
    readme = ("# ornith-offline-browsers — bundle playwright + chromium "
              "OFFLINE\n\n")
    readme += (f"- build_utc: "
               f"{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
    readme += f"- python (build): {st['platform']['python']}\n"
    readme += (f"- playwright (wheel + installed): "
               f"{st['playwright_version']}\n")
    readme += f"- chromium (browser.version): {st['browser_version']}\n"
    readme += f"- chromium_dirs: {', '.join(st['chromium_dirs']) or '?'}\n"
    readme += (f"- dung luong: wheels={st['wheels_total_mb']}MB "
               f"browsers={st['browsers_total_mb']}MB\n")
    readme += (f"- launch_ok trong-builder: {st['launch_ok']} "
               f"(smoke goto+click: {st['smoke_ok']})\n")
    readme += ("\nLayout file: wheels/*.whl | browsers/ms-playwright/ | "
               "setup_playwright_offline.py | bundle_manifest.json | "
               "README.md\n")
    readme += ("\nKernel RTX: run VERIFY GATE V1-V6 (note @MiMo §5) qua "
               "snippet setup_playwright_offline() — python/playwright/"
               "chromium PHAI TRUNG versions trong README nay "
               "(bundle_manifest.json cung nam trong dataset de snippet "
               "assert). Thieu bundle = FAIL LOUD — khong fallback "
               "gui=False.\n")
    with open(os.path.join(WORK, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    st["readme_written"] = os.path.isfile(os.path.join(WORK, "README.md"))
    try:
        os.remove(VERIFY_PY)
    except OSError:
        pass
    st["t_sec"] = round(time.time() - t0, 1)
    st["stage"] = "done"
    write_manifest(st)
    log(f"DONE t={st['t_sec']}s wheels={st['wheels_total_mb']}MB "
        f"browsers={st['browsers_total_mb']}MB launch_ok={ok} "
        f"smoke_ok={st['smoke_ok']}")
    if not ok:
        log("CANH BAO: launch/smoke fail trong builder (launch_ok=False trong "
            "manifest) — DeepSeek doi chieu phuong an B/C truoc khi up "
            "dataset")
    log(f">> DeepSeek: kernels output -p <dir-local> (hoac web UI) roi up "
        f"dataset {TARGET_DATASET} (wheels/ + browsers/ + README.md + "
        f"setup_playwright_offline.py + bundle_manifest.json) — sau push "
        f"nho VERIFY status nhu bai hoc push-1")


if __name__ == "__main__":
    main()
