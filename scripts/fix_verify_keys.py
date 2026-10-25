"""fix_verify_keys.py - quet/tim key Kaggle hardcode (32 ky tu hex) trong file
va bao vi tri (da mask). Khong in key that ra man hinh.

Dung:
  python scripts/fix_verify_keys.py                 # quet thu muc scripts/
  python scripts/fix_verify_keys.py file1.py file2  # quet file cu the
  python scripts/fix_verify_keys.py --dir phase13-gui

Exit code: 0 = khong co key nao, 1 = CO key hardcode (phai sua ngay).
Cach sua dung: doc key tu env/HKCU\\Environment - xem scripts/kaggle_keys.py.
"""
import argparse
import os
import re

HEX32 = re.compile(r"\b[0-9a-f]{32}\b")
# Loai bo cac chuoi hex KHONG phai key (vd hash thu vien, md5 trong comment mau)
WHITE = re.compile(r"(example|dummy|sample|hash|sha|md5)", re.I)


def mask(s):
    return s[:6] + "..." + s[-4:]


def scan_file(path):
    hits = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                for m in HEX32.finditer(line):
                    if WHITE.search(line):
                        continue
                    hits.append((i, mask(m.group(0)),
                                 line.strip()[:90].replace(m.group(0), mask(m.group(0)))))
    except OSError as e:
        print("  doc loi %s: %r" % (path, e))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="file can quet (mac dinh: scripts/)")
    ap.add_argument("--dir", default="scripts", help="thuc muc quet khi khong chi dinh file")
    args = ap.parse_args()

    targets = list(args.files)
    if not targets:
        for root, _dirs, files in os.walk(args.dir):
            for fn in files:
                if fn.endswith((".py", ".ps1", ".md", ".json")):
                    targets.append(os.path.join(root, fn))

    total = 0
    for t in sorted(targets):
        hits = scan_file(t)
        if hits:
            print("CO KEY HARDCODE: %s" % t)
            for ln, mk, ctx in hits:
                print("   dong %-5s %s | %s" % (ln, mk, ctx))
            total += len(hits)
    if total:
        print("\nTONG %d cho xon key hardcode - sua bang env/kaggle_keys.py ngay" % total)
        print("SUA XONG chay lai de xac nhan exit 0.")
    else:
        print("SACH: khong tim thay key hardcode trong %d file" % len(targets))


if __name__ == "__main__":
    main()
