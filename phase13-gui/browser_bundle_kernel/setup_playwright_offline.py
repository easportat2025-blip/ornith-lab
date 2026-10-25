"""setup_playwright_offline() - TASK-8 (GLM) v4 (DeepSeek hotfix 19/10 15:0x).

v5 changes vs v4 (FIX TargetClosedError - thieu lib he thong chromium):
  - v4 da fix EACCES (copy /tmp/pw-browsers) nhung image thieu .so he
    thong (libnspr4/libnss3/libatk...) -> launch chet ngay:
    'TargetClosedError: Target page, context or browser has been closed'.
    (Builder phai chay `playwright install-deps chromium` moi launch duoc.)
  - v5: V5 launch lan 1 fail -> V4b deps repair:
      + co deps_out.zip / dir deps_out trong dataset -> replay vao / +
        ldconfig (duong OFFLINE deterministic);
      + neu khong co -> thu `python -m playwright install-deps chromium`
        (can internet; kernel enable_internet=true) - duong repair online;
      + LAUNCH LAI 1 lan; van fail => fail LOUD nhu cu.
  - v5.1 (fix 19/10 15:45): Kaggle auto-extract LAM MAT file zip goc
    (chi con dir deps_out/) -> _find_deps_payload nhan dien dir bang
    cau truc usr//etc/ hoac .so bat ky, KHONG doi .so ngay top-level.
  - Khong doi V1-V6 gates; khong fallback gui=False.

v4 changes vs v3 (FIX EACCES that o bench kernel v15 14:53):
  - /kaggle/input mount READ-ONLY (khong co exec bit) -> chromium launch tu
    dataset = "spawn ... EACCES". v4: sau khi tim cache trong bundle, neu cache
    nam duoi /kaggle/input thi COPY sang /tmp/pw-browsers (1 lan/run) +
    `chmod -R u+x` TRUOC khi launch; env PLAYWRIGHT_BROWSERS_PATH tro ban copy.
  - Ap dung chmod ca cho nhanh zip-extract (Python zipfile khong khoi phuc
    quyen exec tren POSIX).
  - Giu nguyen VERIFY GATE V1-V6, fail LOUD, khong fallback gui=False.

v3 changes vs v2:
  - HOTFIX: playwright package has no `__version__` attribute (builder v1 died on
    this at 12:55). Use importlib.metadata.version("playwright") instead.
  - Dataset is uploaded as ONE zip (kaggle CLI default --dir-mode=skip ignores
    folders), so this helper auto-extracts `*bundle*.zip` from /kaggle/input to
    /tmp/ornith_offline_browsers (once per run) when bundle_manifest.json is not
    directly visible in the mount.
  - Kept: VERIFY GATE V1-V6, fail LOUD (RuntimeError), no gui=False fallback,
    PLAYWRIGHT_BROWSERS_PATH points at the extracted ms-playwright cache.

Usage in bench kernel (internet OFF):
    from setup_playwright_offline import setup_playwright_offline
    info = setup_playwright_offline()   # raises RuntimeError if anything is off
    # -> info["browsers_path"] for sync_playwright(), info["browser_version"]
"""
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile

INPUT_ROOT = "/kaggle/input"
EXTRACT_DIR = "/tmp/ornith_offline_browsers"


def _log(m):
    print("[pw-offline] " + str(m), flush=True)


def _fail(msg):
    raise RuntimeError("PLAYWRIGHT OFFLINE FAIL: " + str(msg))


def _find_bundle_root(base=None):
    """Return dir containing bundle_manifest.json under base (default /kaggle/input)."""
    base = base or INPUT_ROOT
    if not os.path.isdir(base):
        return None
    for root, _dirs, files in os.walk(base):
        if "bundle_manifest.json" in files:
            return root
    return None


def _ensure_bundle_root():
    """Locate the bundle; extract bundle zip to /tmp if the dataset ships one."""
    root = _find_bundle_root()
    if root:
        return root
    # look for the zip (dataset uploaded with --dir-mode=skip as single file)
    zpath = None
    for r, _d, files in os.walk(INPUT_ROOT):
        for name in files:
            if name.lower().endswith(".zip"):
                zpath = os.path.join(r, name)
                break
        if zpath:
            break
    if not zpath:
        _fail("khong thay bundle_manifest.json lan *.zip trong /kaggle/input - "
              "dataset hhjiji/ornith-offline-browsers chua attach (hoac upload "
              "thieu file)")
    marker = os.path.join(EXTRACT_DIR, "bundle_manifest.json")
    if not os.path.exists(marker):
        _log(f"extract {zpath} -> {EXTRACT_DIR} (~700MB, 1 lan/run)")
        if os.path.isdir(EXTRACT_DIR):
            shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
        os.makedirs(EXTRACT_DIR, exist_ok=True)
        try:
            with zipfile.ZipFile(zpath) as z:
                z.extractall(EXTRACT_DIR)
        except Exception as e:  # noqa: BLE001 - fail loud
            _fail(f"extract zip loi: {type(e).__name__}: {e}")
    root = _find_bundle_root(EXTRACT_DIR)
    if not root:
        _fail(f"extract xong nhung khong thay bundle_manifest.json trong {EXTRACT_DIR}")
    return root


def _find_deps_payload(bundle_root):
    """Tim dir deps_out (dataset auto-extract) hoac deps_out.zip gan bundle.

    Kaggle auto-extract LAM MAT file zip goc -> thuong chi con dir deps_out/
    (files nam sau usr/, etc/). Nhan dien dir bang cau truc usr//etc/ hoac
    .so bat ky trong dir (khong doi .so ngay top-level).
    """
    anchors = []
    a = os.path.abspath(bundle_root)
    for _ in range(3):
        anchors.append(a)
        parent = os.path.dirname(a)
        if parent == a:
            break
        a = parent
    anchors.append(INPUT_ROOT)
    seen = set()
    for anchor in anchors:
        if anchor in seen or not os.path.isdir(anchor):
            continue
        seen.add(anchor)
        for root, dirs, files in os.walk(anchor):
            depth = root[len(anchor):].count(os.sep)
            if depth > 6:
                dirs[:] = []
                continue
            if "deps_out.zip" in files:
                return ("zip", os.path.join(root, "deps_out.zip"))
            if "deps_out" in dirs:
                cand = os.path.join(root, "deps_out")
                if (os.path.isdir(os.path.join(cand, "usr"))
                        or os.path.isdir(os.path.join(cand, "etc"))):
                    return ("dir", cand)
                try:
                    has_so = any(".so" in f for f in os.listdir(cand))
                except Exception:  # noqa: BLE001
                    has_so = False
                if has_so:
                    return ("dir", cand)
    return (None, None)


def _replay_deps(kind, src):
    """Cai deps tu dataset vao / (usr/lib/...) + ldconfig. Tra so file."""
    n = 0
    if kind == "zip":
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            z.extractall("/")
            n = len([x for x in names if not x.endswith("/")])
    else:
        for root, _dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            tgt_dir = "/" if rel in (".", "") else os.path.join("/", rel)
            try:
                os.makedirs(tgt_dir, exist_ok=True)
            except Exception:  # noqa: BLE001
                continue
            for f in files:
                s = os.path.join(root, f)
                dst = os.path.join(tgt_dir, f)
                try:
                    if os.path.islink(s):
                        if os.path.lexists(dst):
                            os.remove(dst)
                        os.symlink(os.readlink(s), dst)
                    else:
                        shutil.copy2(s, dst)
                    n += 1
                except Exception:  # noqa: BLE001
                    pass
    try:
        subprocess.run(["/sbin/ldconfig"], capture_output=True, text=True,
                       timeout=120)
    except Exception:  # noqa: BLE001
        pass
    return n


def _apt_install_deps():
    """Duong online: playwright install-deps chromium (can internet)."""
    try:
        r = subprocess.run([sys.executable, "-m", "playwright",
                            "install-deps", "chromium"],
                           capture_output=True, text=True, timeout=900)
        return r.returncode == 0, ((r.stderr or r.stdout or "")[-200:])
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def setup_playwright_offline():
    """Install playwright OFFLINE + run VERIFY GATE V1-V6; return dict."""
    t0 = time.time()

    # ---- locate bundle (direct mount or extracted zip) ----
    bundle_root = _ensure_bundle_root()
    _log(f"BUNDLE ROOT: {bundle_root}")

    # ---- V1: python cua kernel phai TRUNG python build (manifest dataset) ----
    meta_path = os.path.join(bundle_root, "bundle_manifest.json")
    try:
        meta = json.load(open(meta_path, encoding="utf-8"))
    except Exception as e:
        _fail(f"doc bundle_manifest.json loi: {type(e).__name__}: {e}")
    py_expected = (meta.get("platform") or {}).get("python")
    py_actual = platform.python_version()
    if not py_expected:
        _fail("manifest thieu platform.python - khong the gate V1")
    if py_actual != py_expected:
        _fail(f"V1 PYTHON SA LECH: build={py_expected} kernel={py_actual} "
              "(wheel tag mismatch - rebuild theo note A3.2 A1)")
    _log(f"V1 python OK: {py_actual} (trung manifest)")

    # ---- V2: tim wheels dir + pip --no-index (KHONG --no-deps) ----
    whl_dir = None
    for r, _d, files in os.walk(bundle_root):
        if any(f.startswith("playwright-") and f.endswith(".whl") for f in files):
            whl_dir = r
            break
    if not whl_dir:
        _fail("V2 khong thay playwright-*.whl trong bundle")
    _log(f"V2 wheels dir: {whl_dir}")
    r = subprocess.run(["pip", "install", "--no-index",
                        "--find-links", whl_dir, "playwright"],
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        _fail("V2 pip --no-index install fail: "
              + (r.stderr or r.stdout or "")[-500:])
    _log(f"V2 pip install OK (t={time.time() - t0:.0f}s)")

    # ---- V3: import + version playwright TRUNG manifest ----
    try:
        import playwright  # noqa: F401
    except Exception as e:  # noqa: BLE001 - fail loud
        _fail(f"V3 import playwright fail: {type(e).__name__}: {e}")
    try:
        pw_actual = importlib.metadata.version("playwright")
    except Exception as e:  # noqa: BLE001
        _fail(f"V3 importlib.metadata.version('playwright') fail: {type(e).__name__}: {e}")
    pw_expected = meta.get("playwright_version")
    if pw_expected and pw_actual != pw_expected:
        _fail(f"V3 PLAYWRIGHT SA LECH: dataset={pw_expected} da-installed={pw_actual}")
    _log(f"V3 playwright OK: {pw_actual}")

    # ---- V4: PLAYWRIGHT_BROWSERS_PATH + FIX EACCES (v4) ----
    # /kaggle/input read-only (no exec bit) -> launch tu day = EACCES (da gap that
    # o bench kernel v15 14:53). Vi vay: cache nam duoi /kaggle/input ->
    # COPY sang /tmp/pw-browsers (1 lan/run) + chmod -R u+x TRUOC khi launch.
    cache_src = None
    for root, dirs, _files in os.walk(bundle_root):
        if os.path.basename(root) == "ms-playwright":
            cache_src = root
            break
        if any(d.startswith("chromium") for d in dirs):
            cache_src = root
            break
    if not cache_src:
        _fail("V4 khong thay ms-playwright cache trong bundle")
    cache_dir = cache_src
    if cache_src.replace("\\", "/").startswith("/kaggle/input"):
        cache_dir = "/tmp/pw-browsers"
        marker = os.path.join(cache_dir, ".copy_done_v4")
        if not os.path.exists(marker):
            t_copy = time.time()
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
                os.makedirs(cache_dir, exist_ok=True)
                r_cp = subprocess.run(
                    ["cp", "-a", cache_src + "/.", cache_dir + "/"],
                    capture_output=True, text=True)
                if r_cp.returncode != 0:
                    _log(f"V4 cp -a loi ({(r_cp.stderr or '')[:120]}) -> copytree")
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    shutil.copytree(cache_src, cache_dir)
                with open(marker, "w") as fh:
                    fh.write("ok")
            except Exception as e:  # noqa: BLE001 - fail loud
                _fail(f"V4 copy cache {cache_src} -> {cache_dir} loi: "
                      f"{type(e).__name__}: {e} (het dung luong /tmp?)")
            _log(f"V4 copy cache -> {cache_dir} ({time.time() - t_copy:.0f}s)")
        else:
            _log(f"V4 cache da copy san: {cache_dir}")
    # chmod u+x toan bo (binary can exec bit; zip-extract khong khoi phuc quyen)
    try:
        subprocess.run(["chmod", "-R", "u+x", cache_dir],
                       capture_output=True, text=True)
    except Exception as e:  # noqa: BLE001 - log and continue (co the la mount writable)
        _log(f"V4 chmod bo qua ({type(e).__name__})")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = cache_dir
    _log(f"V4 PLAYWRIGHT_BROWSERS_PATH: {cache_dir}")

    try:
        r2 = subprocess.run([sys.executable, "-m", "playwright",
                             "install", "--dry-run"],
                            capture_output=True, text=True, timeout=300)
        tail = ((r2.stdout or "") + (r2.stderr or ""))[-400:].replace("\n", " | ")
        _log(f"install --dry-run rc={r2.returncode}: {tail}")
    except Exception as e:  # noqa: BLE001 - log and continue
        _log(f"install --dry-run bo qua ({type(e).__name__})")

    # ---- V5 + V6: launch headless THAT + smoke goto/click ----
    fixture = "/tmp/pw_offline_fixture.html"
    with open(fixture, "w", encoding="utf-8") as f:
        f.write("<html><body><button id='btn'>ok</button></body></html>\n")
    ver = None
    txt = None
    from playwright.sync_api import sync_playwright
    px = sync_playwright().start()
    try:
        try:
            browser = px.chromium.launch(headless=True,
                                         args=["--no-sandbox"])
        except Exception as e1:  # noqa: BLE001 - V4b repair + retry 1 lan
            _log(f"V5 launch lan 1 fail: {type(e1).__name__}: "
                 f"{str(e1)[:160]}")
            kind, src = _find_deps_payload(bundle_root)
            repaired = False
            if kind:
                try:
                    n = _replay_deps(kind, src)
                    _log(f"V4b replay deps ({kind}: {src}) -> "
                         f"{n} file + ldconfig")
                    repaired = True
                except Exception as e2:  # noqa: BLE001
                    _log(f"V4b replay loi: {type(e2).__name__}: "
                         f"{str(e2)[:160]}")
            if not repaired:
                ok, tail = _apt_install_deps()
                _log(f"V4b apt install-deps chromium: ok={ok} "
                     f"tail={tail[:160]!r}")
            browser = px.chromium.launch(headless=True,
                                         args=["--no-sandbox"])
        ver = browser.version
        page = browser.new_page()
        page.goto("file://" + fixture.replace("\\", "/"))
        page.click("#btn")
        txt = (page.text_content("#btn") or "").strip()
        browser.close()
    except Exception as e:  # noqa: BLE001 - fail loud (thieu .so)
        _fail(f"V5/V6 launch/smoke fail - {type(e).__name__}: {str(e)[:300]} "
              "(da thu V4b deps repair: kiem tra deps_out.zip trong dataset "
              "/ internet cua kernel)")
    finally:
        try:
            px.stop()
        except Exception:
            pass
    br_expected = meta.get("browser_version")
    if br_expected and ver != br_expected:
        _fail(f"V5 BROWSER SA LECH: dataset={br_expected} bundle-used={ver} "
              "(browser la duoc dung thay - FAIL theo gate A5)")
    if txt != "ok":
        _fail(f"V6 smoke click/JS khong ranh: text_content={txt!r}")
    _log(f"V5 browser OK: {ver} (trung manifest)")
    _log(f"V6 smoke OK: goto(file://) + click(#btn) -> {txt!r}")
    _log(f"ALL GATE PASS t={time.time() - t0:.0f}s")
    return {"playwright": pw_actual, "browser_version": ver,
            "python": py_actual, "wheels_dir": whl_dir,
            "browsers_path": cache_dir, "manifest": meta_path,
            "bundle_root": bundle_root}


if __name__ == "__main__":  # smoke: python setup_playwright_offline.py (kernel offline)
    setup_playwright_offline()
