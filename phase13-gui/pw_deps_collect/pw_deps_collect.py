"""pw_deps_collect.py — thu thập system deps (apt) mà playwright install-deps
cài, đóng gói thành deps_out/ + deps_out.zip để replay OFFLINE trong kernel
bench (copy vào / rồi ldconfig).

Chạy: CPU + internet ON (không cần GPU, không attach competition).
  - ldd truoc/sau -> danh sach lib thieu
  - thu launch truoc (ghi loi), install-deps, launch lai
  - diff dpkg-query -W truoc/sau -> package moi -> dpkg -L -> copy file
  - zip lai (/kaggle/working/deps_out.zip + deps_out/)
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

OUT = "/kaggle/working"
T0 = time.time()
LOG = []


def log(msg):
    print("[deps] " + str(msg), flush=True)
    LOG.append(str(msg))


def sh(cmd, t=900):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=t)
    return r.returncode, r.stdout or "", r.stderr or ""


def dpkg_list():
    rc, out, _ = sh("dpkg-query -W -f='${Package}\\n'")
    return set(out.split())


# ---------- find bundle ----------
bundle = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "bundle_manifest.json" in files:
        bundle = root
        break
assert bundle, "khong thay bundle_manifest.json trong /kaggle/input"
log("bundle root: " + bundle)

# ---------- V2: pip install wheels (offline) ----------
wheels = os.path.join(bundle, "wheels")
rc, out, err = sh(f"/usr/bin/python3 -m pip install --no-index --find-links {wheels} playwright", t=300)
log(f"pip install rc={rc} tail={(out or err)[-200:]}")
import playwright  # noqa: E402
log("playwright ver: " + getattr(playwright, "__version__", "?"))

# ---------- copy browsers to /tmp + chmod (giong snippet v4) ----------
cache_src = None
for root, dirs, files in os.walk(bundle):
    if any(d.startswith("chromium") for d in dirs) or any(
            d == "ms-playwright" for d in dirs):
        if "ms-playwright" in dirs:
            cache_src = os.path.join(root, "ms-playwright")
            break
        if any(d.startswith("chromium") for d in dirs):
            cache_src = root
            break
assert cache_src, "khong thay cache ms-playwright"
log("cache_src: " + cache_src)
dst = "/tmp/pw-browsers"
if os.path.exists(dst):
    shutil.rmtree(dst)
os.makedirs(dst, exist_ok=True)
rc, out, err = sh(f"cp -a {cache_src}/. {dst}/", t=600)
log(f"cp rc={rc} err={err[-120:]}")
sh(f"chmod -R u+x {dst}")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = dst

hs = (dst + "/chromium_headless_shell-1248/chrome-headless-shell-linux64/"
      "chrome-headless-shell")
ch = dst + "/chromium-1248/chrome-linux/chrome"
log("exists hs=%s ch=%s" % (os.path.exists(hs), os.path.exists(ch)))


def ldd_missing(binpath):
    if not os.path.exists(binpath):
        return ["<no file: %s>" % binpath]
    rc, out, err = sh("ldd " + binpath + " 2>&1", t=120)
    return [l.strip() for l in (out + err).splitlines() if "not found" in l]


miss_before = {}
for name, bp in (("headless_shell", hs), ("chrome", ch)):
    miss_before[name] = ldd_missing(bp)
log("MISSING BEFORE:\n" + json.dumps(miss_before, indent=1))


def try_launch(label, exec_path=None, extra_args=()):
    from playwright.sync_api import sync_playwright
    px = sync_playwright().start()
    res = {"label": label}
    try:
        kw = {"headless": True, "args": ["--no-sandbox", *extra_args]}
        if exec_path:
            kw["executable_path"] = exec_path
        b = px.chromium.launch(**kw)
        res["version"] = b.version
        pg = b.new_page()
        pg.goto("data:text/html,<html><body><button id='btn' "
                "onclick=\"this.textContent='ok'\">x</button></body></html>")
        pg.click("#btn")
        res["click_text"] = pg.text_content("#btn")
        b.close()
        res["ok"] = True
    except Exception as e:  # noqa: BLE001
        res["ok"] = False
        res["error"] = f"{type(e).__name__}: {str(e)[:1200]}"
    finally:
        try:
            px.stop()
        except Exception:
            pass
    return res


launches = [try_launch("hs_default"),
            try_launch("hs_shm", extra_args=["--disable-dev-shm-usage"]),
            try_launch("chrome_full", exec_path=ch)]
for l in launches:
    log("LAUNCH " + json.dumps(l, ensure_ascii=False)[:900])

# ---------- dpkg snapshot BEFORE ----------
pk_before = dpkg_list()
log("dpkg count before: %d" % len(pk_before))

# ---------- install-deps (internet) ----------
rc, out, err = sh("/usr/bin/python3 -m playwright install-deps chromium", t=1200)
log(f"install-deps rc={rc}")
log("install-deps out tail: " + (out or "")[-700:])
log("install-deps err tail: " + (err or "")[-300:])

pk_after = dpkg_list()
newpk = sorted(pk_after - pk_before)
log("NEW PACKAGES (%d): %s" % (len(newpk), json.dumps(newpk)))

miss_after = {}
for name, bp in (("headless_shell", hs), ("chrome", ch)):
    miss_after[name] = ldd_missing(bp)
log("MISSING AFTER:\n" + json.dumps(miss_after, indent=1))

launch_after = try_launch("hs_after_deps")
log("LAUNCH AFTER " + json.dumps(launch_after, ensure_ascii=False)[:900])

# ---------- collect files from new packages ----------
skip_prefix = ("/usr/share/doc", "/usr/share/man", "/usr/share/locale",
               "/usr/share/lintian", "/usr/share/icons", "/usr/share/applications",
               "/usr/share/apport", "/usr/share/bug")
files = []
for p in newpk:
    rc, lst, _ = sh(f"dpkg -L {p} 2>/dev/null")
    for f in lst.splitlines():
        f = f.strip()
        if not f.startswith("/") or f == "/":
            continue
        if f.startswith(skip_prefix):
            continue
        if os.path.isdir(f) and not os.path.islink(f):
            continue
        if os.path.isfile(f) or os.path.islink(f):
            files.append(f)
# unique keep order
seen = set()
dep_files = [f for f in files if not (f in seen or seen.add(f))]
log("dep files: %d" % len(dep_files))

root_out = os.path.join(OUT, "deps_out")
if os.path.exists(root_out):
    shutil.rmtree(root_out)
n = 0
tot = 0
fails = 0
for f in dep_files:
    rel = f.lstrip("/")
    tgt = os.path.join(root_out, rel)
    os.makedirs(os.path.dirname(tgt), exist_ok=True)
    try:
        if os.path.islink(f):
            if os.path.lexists(tgt):
                os.remove(tgt)
            os.symlink(os.readlink(f), tgt)
        else:
            shutil.copy2(f, tgt)
        n += 1
        tot += os.path.getsize(f)
    except Exception as e:  # noqa: BLE001
        fails += 1
        log("copy fail %s: %s" % (f, e))
log("copied %d files %.1f MB (fails=%d)" % (n, tot / 1e6, fails))

# zip
zpath = os.path.join(OUT, "deps_out.zip")
if os.path.exists(zpath):
    os.remove(zpath)
rc, out, err = sh(f"cd {root_out} && zip -qry {zpath} . && ls -l {zpath}")
if rc != 0 or not os.path.exists(zpath):
    log("zip cmd fail rc=%s -> dung python" % rc)
    shutil.make_archive(os.path.join(OUT, "deps_out"), "zip", root_out)
zs = os.path.getsize(zpath) if os.path.exists(zpath) else -1
log("deps_out.zip: %.1f MB" % (zs / 1e6))

result = {
    "t_sec": round(time.time() - T0, 1),
    "bundle": bundle, "cache_src": cache_src,
    "missing_before": miss_before, "missing_after": miss_after,
    "launches": launches, "launch_after": launch_after,
    "new_pkgs": newpk, "ndep_files": n, "dep_mb": round(tot / 1e6, 1),
    "zip_mb": round(zs / 1e6, 1),
}
with io.open(os.path.join(OUT, "pw_deps_result.json"), "w",
             encoding="utf-8") as f:
    f.write(json.dumps(result, indent=1, ensure_ascii=False))
log("DONE t=%.0fs" % result["t_sec"])
