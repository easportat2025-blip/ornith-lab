# -*- coding: utf-8 -*-
r"""
colab_login_watch.py - DANG NHAP COLAB THEO CHE DO "NGUOI DUNG GUI MA, AGENT DAN".

Cach hoat dong:
  1) Voi tung acc: chay CLI voi stdin=PIPE, in URL (da thay login_hint) va
     TU MO TRINH DUYET (Chrome profile dung cua acc)
  2) Script CHO file scripts/colab_code.txt - khi nguoi dung gui ma trong chat
     (hoac tu dan), agent ghi ma vao file do
  3) Script doc file -> day vao stdin cua CLI -> CLI doi ma -> luu token
  4) Het ma -> acc tiep theo

Yeu cau: file scripts/colab_code.txt chi chua MA (chuoi nhu 4/0AXlqoi4...)
ASCII-only source.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")
COLAB = os.path.join(os.path.dirname(sys.executable), "colab.exe")
if not os.path.exists(COLAB):
    COLAB = "colab"
GLOBAL_TOKEN = os.path.join(os.path.expanduser("~"), ".config", "colab-cli",
                            "token.json")
CODE_FILE = os.path.join(ROOT, "scripts", "colab_code.txt")
URL_RE = __import__("re").compile(r"https://accounts\.google\.com/\S+")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    from login_colab_acc import (with_login_hint, open_url, acc_dir, acc_token,
                                 has_token, tok_hash)
except Exception as e:                                   # noqa: E402
    print("import loi: %s" % e)
    raise


def log(m):
    print("[login] %s" % m, flush=True)


def read_code():
    if not os.path.exists(CODE_FILE):
        return None
    try:
        t = io.open(CODE_FILE, encoding="utf-8", errors="replace").read().strip()
    except Exception:
        return None
    return t or None


def clear_code():
    try:
        if os.path.exists(CODE_FILE):
            os.remove(CODE_FILE)
    except Exception:
        pass


def login_one(i, wait=600):
    """1 acc: mo trinh duyet, cho ma qua CODE_FILE, luu token."""
    d = acc_dir(i)
    os.makedirs(d, exist_ok=True)
    s = os.path.join(d, "sessions.json")
    if not os.path.exists(s):
        io.open(s, "w", encoding="utf-8", newline="\n").write("{}")
    cfg = {}
    bp = os.path.join(d, "browser.json")
    if os.path.exists(bp):
        try:
            cfg = json.load(io.open(bp, encoding="utf-8"))
        except Exception:
            cfg = {}
    em = cfg.get("email")
    prof = cfg.get("chrome_profile")

    # token cu -> lui ra, xoa global => CLI bat buoc chay OAuth flow
    backup = None
    if os.path.exists(GLOBAL_TOKEN):
        backup = GLOBAL_TOKEN + ".bak_watch"
        shutil.copy2(GLOBAL_TOKEN, backup)
    if has_token(i):
        shutil.copy2(acc_token(i), GLOBAL_TOKEN)
    elif os.path.exists(GLOBAL_TOKEN):
        os.remove(GLOBAL_TOKEN)

    cenv = dict(os.environ)
    cenv["PYTHONIOENCODING"] = "utf-8"
    cenv["PYTHONUTF8"] = "1"
    cmd = [COLAB, "--config", s, "-c", os.path.join(d, "oauth.json"), "usage"]
    log("=== ACC %d | profile=%s | email=%s ===" % (i, prof, em))
    log("Dang mo trinh duyet... hay copy MA trong tab Chrome va gui lai cho toi")
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, env=cenv)

    url_seen = {"u": None, "t": 0}

    def reader():
        for raw in iter(p.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip()
            m = URL_RE.search(line)
            if m and not url_seen["u"]:
                url_seen["u"] = m.group(0)
                u2 = with_login_hint(url_seen["u"], em)
                log("URL (login_hint=%s):" % em)
                log("  " + u2)
                open_url(u2, cfg)
                continue
            if line.strip():
                log("  | " + line[:160])

    threading.Thread(target=reader, daemon=True).start()

    t0 = time.time()
    sent = False
    while time.time() - t0 < wait:
        time.sleep(3)
        if p.poll() is not None and not sent:
            break
        code = read_code()
        if code and not sent:
            log("Nhan duoc ma (do dai %d) -> day vao CLI" % len(code))
            try:
                p.stdin.write((code + "\n").encode("utf-8", "replace"))
                p.stdin.flush()
            except Exception as e:
                log("ghi stdin loi: %s" % e)
            sent = True
            clear_code()
        if sent and p.poll() is not None:
            break
    try:
        p.terminate()
    except Exception:
        pass
    ok = False
    if os.path.exists(GLOBAL_TOKEN) and os.path.getsize(GLOBAL_TOKEN) > 50:
        shutil.copy2(GLOBAL_TOKEN, acc_token(i))
        ok = True
        log("OK acc%d da co token" % i)
        h = tok_hash(i)
        dup = [j for j in range(1, 9) if j != i and tok_hash(j) == h and h]
        if dup:
            log("!!! TRUNG voi acc%s" % dup)
    else:
        log("acc%d chua duoc (het %ds / ma khong dung)" % (i, wait))
    if backup and os.path.exists(backup):
        shutil.copy2(backup, GLOBAL_TOKEN)
        try:
            os.remove(backup)
        except Exception:
            pass
    clear_code()
    return ok


def main():
    wait = 900
    if "--wait" in sys.argv:
        wait = int(sys.argv[sys.argv.index("--wait") + 1])
    ids = []
    for a in sys.argv[1:]:
        if a.isdigit():
            ids.append(int(a))
    if not ids:
        ids = [i for i in range(1, 9)
               if os.path.isdir(acc_dir(i)) and not has_token(i)]
    log("cac acc se thu: %s (moi acc cho toi toi da %ds)" % (ids, wait))
    log("HAY GUI MA (chuoi 4/0AXlqoi4...) - toi se dan vao CLI")
    for i in ids:
        if login_one(i, wait):
            break
    log("xong. Token da luu: %s" % [i for i in ids if has_token(i)])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
