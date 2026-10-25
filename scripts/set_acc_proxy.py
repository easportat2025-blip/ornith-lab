# -*- coding: utf-8 -*-
r"""
set_acc_proxy.py - gan PROXY RIENG cho tung acc Google Colab.

Moi acc = 1 file scripts/colab_accounts/accN/proxy.json:
    {"https_proxy": "socks5h://user:pass@HOST:PORT", "http_proxy": "..."}
=> scripts/colab_cpu_worker.py + login_colab_acc.py doc vao env khi goi CLI
=> moi acc ra mot IP khac nhau (tranh Google flag khi nhieu acc cung IP).

Dung:
    python scripts\set_acc_proxy.py 1 socks5 user:pass@1.2.3.4:1081
    python scripts\set_acc_proxy.py 1 http   user:pass@1.2.3.4:8081
    python scripts\set_acc_proxy.py 1 clear
    python scripts\set_acc_proxy.py --show
ASCII-only source.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")


def pfile(i):
    return os.path.join(ACC_ROOT, "acc%d" % i, "proxy.json")


def build(kind, cred_host):
    if kind in ("socks5", "socks5h"):
        scheme = "socks5h"
    elif kind == "http":
        scheme = "http"
    else:
        raise SystemExit("kind phai la socks5 | http")
    url = "%s://%s" % (scheme, cred_host)
    return {"https_proxy": url, "http_proxy": url, "all_proxy": url}


def main():
    a = sys.argv[1:]
    if not a or a[0] == "--show":
        for i in range(1, 9):
            p = pfile(i)
            if os.path.exists(p):
                d = json.load(io.open(p, encoding="utf-8"))
                print("  acc%-2d %s" % (i, d.get("https_proxy")))
            else:
                print("  acc%-2d (chua gan proxy)" % i)
        return 0
    if a[0] == "--clear":
        for i in range(1, 9):
            p = pfile(i)
            if os.path.exists(p):
                os.remove(p)
                print("  da xoa proxy acc%d" % i)
        return 0
    i = int(a[0])
    if len(a) < 2:
        print("dung: set_acc_proxy.py <acc> <socks5|http|clear> [user:pass@host:port]")
        return 2
    kind = a[1]
    if kind == "clear":
        p = pfile(i)
        if os.path.exists(p):
            os.remove(p)
        print("  acc%d: xoa proxy" % i)
        return 0
    if len(a) < 3:
        print("  thieu thong tin proxy (user:pass@host:port)")
        return 2
    d = os.path.join(ACC_ROOT, "acc%d" % i)
    os.makedirs(d, exist_ok=True)
    cfg = build(kind, a[2])
    io.open(pfile(i), "w", encoding="utf-8", newline="\n").write(
        json.dumps(cfg, ensure_ascii=False, indent=1))
    print("  acc%d -> %s" % (i, cfg["https_proxy"]))
    print("  (file: %s)" % pfile(i))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
