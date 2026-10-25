# -*- coding: utf-8 -*-
r"""
read_profile_emails.py - doc EMAIL cua tung Chrome profile (tu file
Preferences) roi dien vao scripts/colab_accounts/accN/browser.json
=> URL OAuth co login_hint => Google chon DUNG tai khoan (het loi 5 acc = 1 acc).

Dung:
    python scripts\read_profile_emails.py            # xem + dien (khong ghi)
    python scripts\read_profile_emails.py --write    # dien thuc te vao file
ASCII-only source.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")
UD = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome",
                  "User Data")
EMAIL_RE = re.compile(r'"email"\s*:\s*"([^"@]+@[^"]+)"')


def profiles():
    out = []
    if not os.path.isdir(UD):
        return out
    for d in sorted(os.listdir(UD)):
        if not (d == "Default" or d.startswith("Profile ")):
            continue
        p = os.path.join(UD, d, "Preferences")
        if not os.path.exists(p):
            continue
        emails = []
        try:
            raw = io.open(p, encoding="utf-8", errors="replace").read()
            for m in EMAIL_RE.finditer(raw):
                e = m.group(1)
                if e not in emails:
                    emails.append(e)
        except Exception:
            pass
        # ten hien thi
        name = ""
        try:
            ls = json.load(io.open(os.path.join(UD, "Local State"),
                                   encoding="utf-8"))
            name = (ls.get("profile", {}).get("info_cache", {})
                    .get(d, {}).get("name", ""))
        except Exception:
            pass
        out.append((d, name, emails))
    return out


def main():
    write = "--write" in sys.argv
    profs = profiles()
    print("=== profile Chrome -> email ===")
    for d, name, emails in profs:
        print("  %-11s %-12s %s" % (d, name, emails[0] if emails
                                    else "(khong doc duoc email)"))
    if not write:
        print("\n(them --write de dien vao browser.json)")
        return 0
    # gan acc1..N theo thu tu profile
    n = 0
    for i, (d, name, emails) in enumerate(profs, start=1):
        if not emails:
            continue
        acc_dir = os.path.join(ACC_ROOT, "acc%d" % i)
        os.makedirs(acc_dir, exist_ok=True)
        bp = os.path.join(acc_dir, "browser.json")
        cfg = {}
        if os.path.exists(bp):
            try:
                cfg = json.load(io.open(bp, encoding="utf-8"))
            except Exception:
                cfg = {}
        cfg["chrome_profile"] = d
        cfg["email"] = emails[0]
        io.open(bp, "w", encoding="utf-8", newline="\n").write(json.dumps(
            cfg, ensure_ascii=False, indent=1))
        print("  acc%-2d -> %-11s %s" % (i, d, emails[0]))
        n += 1
    print("\nda dien %d acc. Bay chay: python scripts\\login_colab_acc.py"
          % n)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
