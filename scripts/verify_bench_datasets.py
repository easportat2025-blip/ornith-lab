"""verify_bench_datasets.py - kiem tra dataset bench tren Kaggle co DUNG ban
da sua khong (T13: revalidate khi goi/blur; B16: khong lo dap an).

Dung: python scripts/verify_bench_datasets.py
"""
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile

TMP = os.path.join(os.environ.get("TEMP", "."), "verify_bench_ds")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kaggle_keys import kaggle_env  # key lay tu HKCU\Environment, khong hardcode
ACC = ["A", "B"]
DS = [
    ("A", "khoadangnguye/ornith-gui-bench-v155", "B15.5"),
    ("A", "khoadangnguye/ornith-gui-bench-v16b", "B16"),
    ("B", "dieniw/ornith-gui-bench-v155", "B15.5"),
    ("B", "dieniw/ornith-gui-bench-v16b", "B16"),
    ("B", "dieniw/ornith-gui-bench-v16", "B16 (slug CU)"),
]


def download(slug, acc):
    user, key = kaggle_env(acc)
    if not key:
        print("  [SKIP] acc %s: thieu key env (KAGGLE_KEY_%s)" % (acc, acc))
        return None
    env = dict(os.environ)
    env["KAGGLE_USERNAME"] = user
    env["KAGGLE_KEY"] = key
    env["PYTHONUTF8"] = "1"
    d = os.path.join(TMP, acc)
    os.makedirs(d, exist_ok=True)
    p = subprocess.run(["kaggle", "datasets", "download", slug, "-p", d,
                        "--force"], capture_output=True, env=env, timeout=900)
    if p.returncode != 0 or not os.path.isdir(d):
        return None
    zs = [f for f in os.listdir(d) if f.endswith(".zip")]
    return os.path.join(d, zs[0]) if zs else None


def check(zp):
    out = {"t13_fixed": None, "b16_leak": []}
    try:
        z = zipfile.ZipFile(zp)
    except Exception as e:
        out["error"] = str(e)[:80]
        return out
    for n in z.namelist():
        if not n.endswith(".html"):
            continue
        s = z.read(n).decode("utf-8", "replace")
        if "t13_wizard" in n:
            out["t13_fixed"] = ("revalidate" in s and "blur" in s)
        if re.search(r"expected", s, re.I):
            out["b16_leak"].append(os.path.basename(n))
    return out


print("=== kiem tra dataset bench tren Kaggle ===")
for acc, slug, label in DS:
    zp = download(slug, acc)
    if not zp:
        print("  %-3s %-46s (%-13s) -> TAI LAI THAT BAI" % (acc, slug, label))
        continue
    r = check(zp)
    t13 = r.get("t13_fixed")
    leak = r.get("b16_leak") or []
    verdict = "OK"
    if t13 is False:
        verdict = "HTML CU (T13 chua sua)"
    if leak:
        verdict += " | LO DAP AN: " + ",".join(leak)
    print("  %-3s %-46s (%-13s) -> T13_fix=%s | %s" % (
        acc, slug, label, t13, verdict))
