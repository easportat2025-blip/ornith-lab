# -*- coding: utf-8 -*-
"""
verify_dataset_fixes.py - kiem tra dataset bench tren Kaggle (zip) da CHUA
ban fix task hay chua.

Dung ngay sau khi `kaggle datasets version`:
    python scripts/verify_dataset_fixes.py --acc A
    python scripts/verify_dataset_fixes.py --acc B --suite b16a

Tai khoan kieu:
  A: khoadangnguye/ornith-gui-bench-v155   (B15.5)  + khoadangnguye/ornith-gui-bench-v16b
  B: dieniw/ornith-gui-bench-v155           (B15.5)  + dieniw/ornith-gui-bench-v16b
Key lay tu env (KAGGLE_KEY_A / KAGGLE_KEY_B) - KHONG ghi key vao file.

Exit 0 = moi dataset deu co fix can co; 1 = con thieu.
"""
import argparse
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile

# marker: (ten file trong dataset, chuoi bat buoc phai co)
FIXES = {
    "b155": [
        ("t13_wizard.html", "revalidate",
         "T13 validate lai loi khi go/blur"),
        ("t14_alerts.html", "feed.focus()",
         "T14 tu focus feed (model bam End duoc)"),
        ("t15_dialog.html", "terms.focus()",
         "T15 tu focus panel terms"),
        ("t16_clipboard2.html", "Copied: ",
         "T16 phan hoi khi copy thanh cong"),
        ("t17_reorder.html", "UP</button>",
         "T17 nut UP/DOWN (de model thay) + target 1 swap"),
    ],
    "b16a": [
        ("t19_wizardsum.html", "Remember the number, then press Next",
         "T19 status huong dan + phan hoi khi bam vao so"),
        ("t22_keynav.html", "Wrong cell - move with the arrow keys",
         "T22 cho phep chon bang click"),
        ("t23_undoredo.html", "Current values:",
         "T23 hien trang thai that cua 3 field"),
        ("t24_multifilter.html", "Filters applied:",
         "T24 hien filter da ap + loi cu the"),
        ("t26_distractorlist.html", "Target item:",
         "T26 hien muc tieu tren man hinh"),
    ],
}
# nhung thu KHONG duoc xuat hien (lo dap an)
FORBIDDEN = ["Wrong, expected", "it rejects you while the count is wrong"]

DATASETS = {
    "A": [("khoadangnguye/ornith-gui-bench-v155", "b155"),
          ("khoadangnguye/ornith-gui-bench-v16b", "b16a")],
    "B": [("dieniw/ornith-gui-bench-v155", "b155"),
          ("dieniw/ornith-gui-bench-v16b", "b16a")],
}


def dl(slug, acc, tmp):
    user = "khoadangnguye" if acc == "A" else "dieniw"
    key = os.environ.get("KAGGLE_KEY_A" if acc == "A" else "KAGGLE_KEY_B", "")
    env = dict(os.environ)
    env["KAGGLE_USERNAME"] = user
    env["KAGGLE_KEY"] = key
    env["PYTHONUTF8"] = "1"
    d = os.path.join(tmp, "%s_%s" % (acc, slug.replace("/", "_")))
    os.makedirs(d, exist_ok=True)
    p = subprocess.run(["kaggle", "datasets", "download", slug, "-p", d, "--force"],
                       capture_output=True, env=env, timeout=900)
    zs = [f for f in os.listdir(d) if f.endswith(".zip")]
    if p.returncode != 0 or not zs:
        print("  !! tai that bai: %s" % slug)
        return None
    return os.path.join(d, zs[0])


def check_zip(zp, suite):
    z = zipfile.ZipFile(zp)
    names = z.namelist()
    blob = {}
    for n in names:
        if n.endswith((".html", ".json")):
            blob[n] = z.read(n).decode("utf-8", "replace")
    bad = []
    for fname, marker, desc in FIXES[suite]:
        hit = [n for n, s in blob.items()
               if n.endswith(fname) and marker in s]
        if not hit:
            bad.append("THIEU fix: %s (%s) - can '%s'" % (fname, desc, marker))
        else:
            print("     ok  %-24s %s" % (fname, desc))
    for bad_marker in FORBIDDEN:
        for n, s in blob.items():
            if bad_marker in s:
                bad.append("VAN CON: '%s' trong %s" % (bad_marker, n))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acc", default="A", choices=["A", "B"])
    ap.add_argument("--suite", default=None, choices=[None, "b155", "b16a"])
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix="verifyfix_")
    total = 0
    for slug, suite in DATASETS[a.acc]:
        if a.suite and suite != a.suite:
            continue
        print("=== %s (%s)" % (slug, suite))
        zp = dl(slug, a.acc, tmp)
        if not zp:
            total += 1
            continue
        bad = check_zip(zp, suite)
        for b in bad:
            print("     !! %s" % b)
        total += len(bad)
    print("=" * 60)
    print("TONG van cong: %d" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
