# -*- coding: utf-8 -*-
"""
kernel_cancel.py - huy 1 kernel run dang chay tren Kaggle (CLI khong co lenh).

Dung API noi bo: POST /api/i/kernels.KernelsService/KernelsCancel
Body thu cac shape: {"kernelId": id} / {"kernelSlug": "owner/slug"}
Key lay tu HKCU:\\Environment (KAGGLE_KEY_A / KAGGLE_KEY_B) - KHONG ghi key vao file.

Usage:
    python scripts/kernel_cancel.py khoadangnguye/ornith-gui-sft-v23b
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://www.kaggle.com/api/i/kernels.KernelsService/"


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def key_of(owner):
    var = "KAGGLE_KEY_A" if owner == "khoadangnguye" else "KAGGLE_KEY_B"
    return (os.environ.get(var) or hkcu(var) or hkcu("KAGGLE_KEY") or "")


def call(slug, endpoint, body):
    owner = slug.split("/")[0]
    key = key_of(owner)
    url = BASE + endpoint
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-XSRF-TOKEN", "")
    req.add_header("Cookie", "Kaggle_ApiKey=%s" % key)
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("X-Kaggle-Authorization", "Bearer %s" % key)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)


def find_id(slug):
    """Lay numeric id cua kernel tu API list (public endpoint)."""
    owner = slug.split("/")[0]
    key = key_of(owner)
    url = ("https://www.kaggle.com/api/v1/kernels/list?user=%s&search=%s"
           % (owner, slug.split("/")[-1]))
    req = urllib.request.Request(url)
    req.add_header("Cookie", "Kaggle_ApiKey=%s" % key)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        for k in d or []:
            if (k.get("ref") or "").lower() == slug.lower():
                return k.get("id"), k.get("lastRunTime"), k.get("totalRunTimeSeconds")
    except Exception as e:
        print("  list loi:", e)
    return None, None, None


def main():
    if len(sys.argv) < 2:
        print("dung: kernel_cancel.py <owner/slug>")
        return 2
    slug = sys.argv[1]
    kid, lrt, trt = find_id(slug)
    print("[cancel] %s id=%s lastRunTime=%s" % (slug, kid, lrt))
    attempts = [
        ("KernelsCancel", {"kernelSlug": slug}),
        ("KernelsCancel", {"kernelId": kid}),
        ("KernelCancel", {"kernelId": kid}),
    ]
    for ep, body in attempts:
        if body.get("kernelId") is None and not body.get("kernelSlug"):
            continue
        code, txt = call(slug, ep, body)
        print("  %-14s %-22s -> %s %s" % (ep, json.dumps(body)[:22], code,
                                           (txt or "")[:140].replace("\n", " ")))
        if code == 200:
            print("[cancel] OK")
            return 0
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
