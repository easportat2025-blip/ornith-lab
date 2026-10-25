# -*- coding: utf-8 -*-
"""
colab_accounts.py - quan ly NHIEU tai khoan Google Colab (nhieu CLI config).

Ly do (22/10): acc Kaggle A het quota (0/30h) => can GPU thay the.
User co ~5 acc Google, moi acc ~5h GPU/ngay => ~25h GPU/ngay.

Moi acc = 1 thu muc config rieng:
    <root>/<acc>/sessions.json   (token + session state)
    <root>/<acc>/oauth.json      (client OAuth config)
Dung lenh CLI voi:  colab --config <root>/<acc>/sessions.json -c <root>/<acc>/oauth.json <cmd>

Lenh:
    python scripts/colab_accounts.py init [N]        # tao config dir cho N acc (mac dinh 5)
    python scripts/colab_accounts.py login 1 2 3     # mo luong dang nhap (trinh duyet cho tung acc)
    python scripts/colab_accounts.py status          # quota + session + trang thai tung acc
    python scripts/colab_accounts.py run 1 --gpu T4  # cap session tren acc 1
    python scripts/colab_accounts.py stop 1          # dung session acc 1
ASCII-only source.
"""
import io
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")
COLAB = os.path.join(os.path.dirname(sys.executable), "colab.exe")
if not os.path.exists(COLAB):
    COLAB = "colab"


def cfg_dir(i):
    return os.path.join(ACC_ROOT, "acc%d" % i)


# Token OAuth cua CLI: DUONG DAN HARDCODE global
# (~/.config/colab-cli/token.json - xem auth.py:54) => de chay nhieu acc ta
# phai SWAP token: copy token cua acc vao global truoc, copy global ve acc sau.
GLOBAL_TOKEN = os.path.join(os.path.expanduser("~"), ".config", "colab-cli",
                            "token.json")


def _tok_path(i):
    return os.path.join(cfg_dir(i), "token.json")


def swap_in(i):
    """Dua token cua acc i vao cho vi tri global. Tra ve token global goc."""
    backup = None
    if os.path.exists(GLOBAL_TOKEN):
        backup = GLOBAL_TOKEN + ".bak.multi"
        shutil.copy2(GLOBAL_TOKEN, backup)
    src = _tok_path(i)
    if os.path.exists(src):
        os.makedirs(os.path.dirname(GLOBAL_TOKEN), exist_ok=True)
        shutil.copy2(src, GLOBAL_TOKEN)
    return backup


def swap_out(backup):
    if backup and os.path.exists(backup):
        shutil.copy2(backup, GLOBAL_TOKEN)
        try:
            os.remove(backup)
        except Exception:
            pass


def cli(i, *args, timeout=600):
    """Chay lenh CLI voi config cua acc i (va token cua acc i)."""
    d = cfg_dir(i)
    cmd = [COLAB, "--config", os.path.join(d, "sessions.json"),
           "-c", os.path.join(d, "oauth.json")] + list(args)
    backup = swap_in(i)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT (co the dang mo trinh duyet de dang nhap)"
    except Exception as e:
        return 1, "ERR %s" % e
    finally:
        swap_out(backup)


def init(n=5):
    os.makedirs(ACC_ROOT, exist_ok=True)
    for i in range(1, n + 1):
        d = cfg_dir(i)
        os.makedirs(d, exist_ok=True)
        s = os.path.join(d, "sessions.json")
        if not os.path.exists(s):
            io.open(s, "w", encoding="utf-8", newline="\n").write("{}")
        print("  acc%-2d -> %s" % (i, d))
    print("\n=> Buoc tiep theo: python scripts/colab_accounts.py login %s"
          % " ".join(str(i) for i in range(1, n + 1)))
    print("   (mo trinh duyet cho TUNG acc va dang nhap bang acc do)")


def login(ids):
    """Dang nhap 1 acc: can user LOG OUT khoi Google (hoac dung cua so
    rieng) truoc khi chay lenh nay => CLI mo trinh duyet, user chon acc do.
    Token sau do duoc COPY vao accN/token.json de dung lai nhanh."""
    for i in ids:
        print("\n=== acc%d: yeu cau dang nhap (trinh duyet) ===" % i)
        print("   NHAC: hay logout Google truoc, roi chay lai lenh nay.")
        rc, out = cli(i, "usage", timeout=900)
        print("  rc=%s %s" % (rc, out[:300]))
        # luu token global hien tai vao accN (neu vua dang nhap acc moi)
        if os.path.exists(GLOBAL_TOKEN):
            shutil.copy2(GLOBAL_TOKEN, _tok_path(i))
            print("  -> token da luu cho acc%d (%s)" % (i, _tok_path(i)))
        else:
            print("  -> khong thay token global (chua dang nhap?)")


def status(n=5):
    for i in range(1, n + 1):
        if not os.path.isdir(cfg_dir(i)):
            continue
        rc, out = cli(i, "usage", timeout=180)
        rc2, out2 = cli(i, "sessions", timeout=180)
        print("--- acc%d ---" % i)
        print("  usage: %s" % out.replace("\n", " | ")[:180])
        print("  sessions: %s" % (out2.replace("\n", " | ")[:180] or "(none)"))


def run(i, gpu="T4", name=None):
    s = name or ("orn-%s" % gpu.lower())
    rc, out = cli(i, "new", "-s", s, "--gpu", gpu, timeout=900)
    print("  acc%d new %s: rc=%s %s" % (i, s, rc, out[:200]))
    return rc == 0


def stop(i):
    rc, out = cli(i, "stop", timeout=600)
    print("  acc%d stop: rc=%s %s" % (i, rc, out[:160]))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "init":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        init(n)
    elif cmd == "login":
        ids = [int(x) for x in sys.argv[2:]] or [1]
        login(ids)
    elif cmd == "status":
        n = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 5
        status(n)
    elif cmd == "run":
        i = int(sys.argv[2])
        gpu = "T4"
        if "--gpu" in sys.argv:
            gpu = sys.argv[sys.argv.index("--gpu") + 1]
        run(i, gpu)
    elif cmd == "stop":
        stop(int(sys.argv[2]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
