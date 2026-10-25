# -*- coding: utf-8 -*-
r"""
login_colab_acc.py - DANG NHAP TAI KHOAN GOOGLE COLAB (TU DONG, khong can chon).

Lam gi (tu dong het):
  1) tim acc chua co token (acc1, acc2, ...)
  2) giu token cua acc hien tai, xoa token global => CLI bat buoc mo luong OAuth
  3) chay CLI va BAT URL trong output => TU MO TRINH DUyet (webbrowser)
  4) user cap quyen tren trinh duyet; Google hien code => DAN VAO TERMINAL
     (Enter) - CLI doc code tu stdin
  5) CLI luu token vao token.json global -> script COPY vao accN/token.json
     va khoi phuc token cua acc truoc do

Lenh:
    python scripts\login_colab_acc.py            # acc tiep theo, tu dong
    python scripts\login_colab_acc.py --status   # xem trang thai
    python scripts\login_colab_acc.py --reset    # xoa token sai (neu can)
ASCII-only source.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")
COLAB = os.path.join(os.path.dirname(sys.executable), "colab.exe")
if not os.path.exists(COLAB):
    COLAB = "colab"
GLOBAL_TOKEN = os.path.join(os.path.expanduser("~"), ".config", "colab-cli",
                            "token.json")
URL_RE = re.compile(r"https://accounts\.google\.com/\S+")


def acc_dir(i):
    return os.path.join(ACC_ROOT, "acc%d" % i)


def acc_token(i):
    return os.path.join(acc_dir(i), "token.json")


def has_token(i):
    p = acc_token(i)
    if not os.path.exists(p):
        return False
    try:
        return bool(json.load(io.open(p, encoding="utf-8")))
    except Exception:
        return os.path.getsize(p) > 50


def next_acc(n_max=8):
    for i in range(1, n_max + 1):
        if os.path.isdir(acc_dir(i)) and not has_token(i):
            return i
    return None


def _swap_in(i):
    backup = None
    if os.path.exists(GLOBAL_TOKEN):
        backup = GLOBAL_TOKEN + ".bak_login"
        shutil.copy2(GLOBAL_TOKEN, backup)
    if has_token(i):
        shutil.copy2(acc_token(i), GLOBAL_TOKEN)
    elif os.path.exists(GLOBAL_TOKEN):
        os.remove(GLOBAL_TOKEN)          # bat buoc CLI mo luong OAuth
    return backup


def _swap_out(backup):
    if backup and os.path.exists(backup):
        shutil.copy2(backup, GLOBAL_TOKEN)
        try:
            os.remove(backup)
        except Exception:
            pass


def acc_browser(i):
    """Cau hinh browser cho acc i: {"chrome_profile": "Profile 2"} =>
    mo URL trong DUNG profile Chrome (mac dinh webbrowser.open luon mo profile
    mac dinh => 5 lan login ra 1 acc!)."""
    p = os.path.join(acc_dir(i), "browser.json")
    if os.path.exists(p):
        try:
            return json.load(io.open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def with_login_hint(url, email):
    """THAY THAY login_hint cua CLI (CLI ghim san acc dau tien) bang email
    cua acc -> Google chon DUNG tai khoan. Append se bi loi 400."""
    if not email:
        return url
    import urllib.parse as _up
    parts = _up.urlsplit(url)
    q = [(k, v) for k, v in _up.parse_qsl(parts.query, keep_blank_values=True)
         if k != "login_hint"]
    q.append(("login_hint", email))
    return _up.urlunsplit((parts.scheme, parts.netloc, parts.path,
                            _up.urlencode(q), parts.fragment))


def open_url(url, cfg):
    """Mo URL cho acc i (da thay login_hint => Google chon dung tai khoan)."""
    em = (cfg or {}).get("email")
    if em:
        url = with_login_hint(url, em)
    prof = (cfg or {}).get("chrome_profile")
    if prof:
        for exe in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
            if os.path.exists(exe):
                try:
                    subprocess.Popen([exe, "--profile-directory=" + prof, url])
                    return True
                except Exception:
                    pass
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def cli_plain(i, args, timeout=1800):
    """Chay CLI voi token acc i. Neu can OAuth: bat URL + TU MO TRINH DUyet."""
    d = acc_dir(i)
    os.makedirs(d, exist_ok=True)
    s = os.path.join(d, "sessions.json")
    if not os.path.exists(s):
        io.open(s, "w", encoding="utf-8", newline="\n").write("{}")
    backup = _swap_in(i)
    opened = {"url": None}

    def reader(pipe):
        buf = ""
        for raw in iter(pipe.readline, b""):
            line = raw.decode("utf-8", "replace").rstrip()
            m = URL_RE.search(line)
            if m and not opened["url"]:
                opened["url"] = m.group(0)
                prof = (acc_browser(i) or {}).get("chrome_profile")
                em = (acc_browser(i) or {}).get("email")
                print("", flush=True)
                u2 = with_login_hint(m.group(0), em)
                print("  >>> DUNG URL NAY (login_hint da thay cho acc%d):" % i,
                      flush=True)
                print("  " + u2, flush=True)
                print("  >>> Chrome %s | %s" % (prof or "(mac dinh)",
                                                em or "(chua co email)"),
                      flush=True)
                print("  >>> TRINH DUYET se mo tu dong. Chon DUNG tai khoan"
                      " tren man hinh Google (neu acc da bi bôi den, bam"
                      " 'Use another account').", flush=True)
                print("", flush=True)
                open_url(u2, acc_browser(i))
                continue          # KHONG in URL goc (khong co login_hint)
            print(line, flush=True)

    cmd = [COLAB, "--config", s, "-c", os.path.join(d, "oauth.json")] + list(args)
    # 22/10: CLI log ra ky tu '->' => cp1252 crash (UnicodeEncodeError) =>
    # ep UTF-8 cho subprocess CLI
    cenv = dict(os.environ)
    cenv["PYTHONIOENCODING"] = "utf-8"
    cenv["PYTHONUTF8"] = "1"
    old_tok = None
    if os.path.exists(GLOBAL_TOKEN):
        try:
            old_tok = io.open(GLOBAL_TOKEN, encoding="utf-8").read()
        except Exception:
            old_tok = None
    new_tok = None
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=None, env=cenv)
        t = threading.Thread(target=reader, args=(p.stdout,), daemon=True)
        t.start()
        p.wait(timeout=timeout)
        t.join(timeout=5)
        if os.path.exists(GLOBAL_TOKEN):
            try:
                new_tok = io.open(GLOBAL_TOKEN, encoding="utf-8").read()
            except Exception:
                new_tok = None
        # token co THAY DOI khong? (neu khong => OAuth flow khong chay =>
        # browser van dang nhap acc truoc do -> se ra trung acc)
        changed = (new_tok is not None and new_tok != old_tok
                   and len(new_tok.strip()) > 50)
        return p.returncode, opened["url"], changed
    except subprocess.TimeoutExpired:
        print("  [warn] het thoi gian chờ", flush=True)
        return 124, opened["url"], False
    finally:
        _swap_out(backup)


def tok_hash(i):
    """Hash cua refresh_token - DUNG DE PHAT HIEN TRUNG ACC (cung tai khoan
    Google se cho CUNG refresh_token => khong phai acc rieng!)."""
    import hashlib
    p = acc_token(i)
    if not os.path.exists(p):
        return None
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        rt = str(d.get("refresh_token", ""))
        return hashlib.md5(rt.encode()).hexdigest()[:10] if rt else None
    except Exception:
        return None


def check_dups():
    """Bao cao acc nao TRUNG nhau (cung mot tai khoan Google)."""
    h2ids = {}
    for i in range(1, 9):
        h = tok_hash(i)
        if h:
            h2ids.setdefault(h, []).append(i)
    print("=== kiem tra trung acc ===")
    for h, ids in h2ids.items():
        if len(ids) > 1:
            print("  !! TRUNG: hash %s -> acc %s  (cung 1 tai khoan Google!)"
                  % (h, ids))
        else:
            print("  acc%-2d hash %s (rieng)" % (ids[0], h))
    if not h2ids:
        print("  (chua acc nao co token)")
    return h2ids


def do_login(i, tries=4, wait=180):
    """Thu acc i toi da 'tries' lan (MOI LAN MOT URL MOI + MOT CUA SO TRINH
    DUYET MOI). Het so lan => tra ve False (main loop chuyen acc ke tiep)."""
    d = acc_dir(i)
    os.makedirs(d, exist_ok=True)
    s = os.path.join(d, "sessions.json")
    if not os.path.exists(s):
        io.open(s, "w", encoding="utf-8", newline="\n").write("{}")
    for attempt in range(1, tries + 1):
        print("=" * 70)
        print(" COLAB ACC %d - LAN %d/%d  (moi lan: URL moi + cua so moi)"
              % (i, attempt, tries))
        print("=" * 70)
        print(" >> DAN MA CODE: chuyen sang TAB CHROME vua mo (trang Google")
        print("    hien MOT CHUOI nhu '4/0AXlqoi4Ccmi5zMEYpjocc...' )")
        print("    -> COPY CHUOI DO (khong phai dong huong dan trong chat!)")
        print("    -> DAN VAO DONG 'Enter the authorization code:' -> Enter")
        print(" >> Het %ds neu khong dan ma => thu LAN %d" % (wait, attempt + 1))
        print("-" * 70, flush=True)
        rc, url, changed = cli_plain(i, ["usage"], timeout=wait)
        if os.path.exists(GLOBAL_TOKEN) and os.path.getsize(GLOBAL_TOKEN) > 50 \
                and changed:
            shutil.copy2(GLOBAL_TOKEN, acc_token(i))
            print("\n  -> OK acc%d da co token" % i)
            h = tok_hash(i)
            dup = [j for j in range(1, 9) if j != i and tok_hash(j) == h and h]
            if dup:
                print("  !!! TRUNG voi acc%s (cung tai khoan Google)" % dup)
            return True
        if not changed:
            print("  [!] OAuth flow khong chay (token khong doi) - thu lai lan sau",
                  flush=True)
        else:
            print("  [!] chua nhan duoc ma (het %ds)" % wait, flush=True)
    print("\n  -> acc%d het %d lan thu -> chuyen acc ke tiep" % (i, tries))
    return False


def main():
    args = sys.argv[1:]
    if "--status" in args:
        show_status()
        return 0
    if "--check" in args:
        check_dups()
        return 0
    if "--reset" in args:
        reset()
        return 0
    wait = 300
    if "--wait" in args:
        wait = int(sys.argv[sys.argv.index("--wait") + 1])
    tries = 4
    if "--tries" in args:
        tries = int(sys.argv[sys.argv.index("--tries") + 1])
    rounds = 2
    if "--rounds" in args:
        rounds = int(sys.argv[sys.argv.index("--rounds") + 1])
    # vong: xoa het cac acc chua co token -> thu tung acc (tries lan moi acc)
    for rnd in range(1, rounds + 1):
        todo = [i for i in range(1, 9)
                if os.path.isdir(acc_dir(i)) and not has_token(i)]
        if not todo:
            break
        print("\n### VONG %d: %d acc can dang nhap: %s\n"
              % (rnd, len(todo), todo))
        for i in todo:
            ok = do_login(i, tries=tries, wait=wait)
            if ok:
                print("  acc tiep theo: %s" % (next_acc() or "(het)"))
    print("\n=== ket qua ===")
    check_dups()
    return 0


def show_status():
    print("=== trang thai ===")
    for i in range(1, 9):
        if not os.path.isdir(acc_dir(i)):
            continue
        mark = "DA DANG NHAP" if has_token(i) else "chua co token"
        extra = ""
        if has_token(i):
            b = _swap_in(i)
            try:
                p = subprocess.run([COLAB, "--config",
                                    os.path.join(acc_dir(i), "sessions.json"),
                                    "-c", os.path.join(acc_dir(i), "oauth.json"),
                                    "usage"], capture_output=True, text=True,
                                   timeout=180)
                extra = ((p.stdout or "") + (p.stderr or "")).strip(
                ).replace("\n", " | ")[:130]
            except Exception as e:
                extra = str(e)[:60]
            finally:
                _swap_out(b)
        print("  acc%-2d %-14s %s" % (i, mark, extra))
    print("\n  acc tiep theo: %s" % (next_acc() or "(het)"))


def reset():
    for i in range(1, 9):
        p = acc_token(i)
        if os.path.exists(p):
            os.remove(p)
            print("  da xoa token acc%d" % i)


def main():
    args = sys.argv[1:]
    if "--status" in args:
        show_status()
        return 0
    if "--check" in args:
        check_dups()
        return 0
    if "--reset" in args:
        reset()
        return 0
    nxt = next_acc()
    if nxt is None:
        print("Tat ca acc da co token. Dung --status de xem.")
        return 0
    print("Tu tim thay acc chua co token: acc%d" % nxt)
    return do_login(nxt)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
