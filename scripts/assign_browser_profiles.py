# -*- coding: utf-8 -*-
r"""
assign_browser_profiles.py - gan Chrome PROFILE khac nhau cho tung acc Colab,
de moi acc dang nhap bang 1 tai khoan Google KHAC NHAU (fix loi: 5 lan login
ra 1 acc vi webbrowser.open luon mo profile mac dinh).

Tu dong doc danh sach profile Chrome (Local State -> profile.info_cache) va
 gan acc1..N theo thu tu, roi in bang canh tac nguoi dung.

Dung:
    python scripts\assign_browser_profiles.py            # tu gan + in bang
    python scripts\assign_browser_profiles.py --auto      # tu gan theo thu tu
    python scripts\assign_browser_profiles.py 1 Profile 2 # gan acc1 = Profile 2
    python scripts\assign_browser_profiles.py --show      # xem bang hien tai
ASCII-only source.
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")
CHROME_UD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google",
                         "Chrome", "User Data")


def chrome_profiles():
    out = []
    ls = os.path.join(CHROME_UD, "Local State")
    if os.path.exists(ls):
        try:
            d = json.load(io.open(ls, encoding="utf-8"))
            info = d.get("profile", {}).get("info_cache", {})
            for k in sorted(info.keys()):
                out.append((k, info[k].get("name", "?")))
        except Exception:
            pass
    if not out and os.path.isdir(CHROME_UD):
        for d in sorted(os.listdir(CHROME_UD)):
            if d == "Default" or d.startswith("Profile "):
                out.append((d, "(khong doc ten)"))
    return out


def assign(acc, profile):
    d = os.path.join(ACC_ROOT, "acc%d" % acc)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "browser.json")
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(
        {"chrome_profile": profile}, ensure_ascii=False, indent=1))
    print("  acc%-2d -> Chrome %s" % (acc, profile))


def show():
    print("=== gan browser profile hien tai ===")
    for i in range(1, 9):
        d = os.path.join(ACC_ROOT, "acc%d" % i, "browser.json")
        if os.path.exists(d):
            c = json.load(io.open(d, encoding="utf-8"))
            print("  acc%-2d -> %s" % (i, c.get("chrome_profile")))
    print("\n=== cac profile Chrome co san ===")
    for k, n in chrome_profiles():
        print("  %-12s %s" % (k, n))


def main():
    a = sys.argv[1:]
    if "--show" in a:
        show()
        return 0
    if a and a[0].isdigit():
        assign(int(a[0]), a[1])
        return 0
    profs = chrome_profiles()
    if not profs:
        print("khong tim thay profile Chrome")
        return 1
    print("=== gan tu dong acc1..N theo thu tu profile ===")
    for i, (k, n) in enumerate(profs, start=1):
        assign(i, k)
    print("\nBang:")
    for i, (k, n) in enumerate(profs, start=1):
        print("  acc%-2d = %-11s (%s)" % (i, k, n))
    print("\n=> Bay gio chay: python scripts\\login_colab_acc.py")
    print("   (moi acc se mo trinh duyet DUNG profile cua no)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
