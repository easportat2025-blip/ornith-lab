"""check_acc_quota.py - check quota GPU/TPU cua cac account Kaggle tren may
(key chi doc tu file, KHONG in ra).

Tren may: ~/.kaggle/kaggle*.json (nhieu acc) + env KAGGLE_USERNAME/KEY.
"""
import glob
import io
import json
import os
import re
import subprocess

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"
ENV["KAGGLE_CONFIG_DIR"] = os.path.expanduser("~/.kaggle")


def quota(username, key):
    env = dict(ENV)
    env["KAGGLE_USERNAME"] = username
    env["KAGGLE_KEY"] = key
    try:
        p = subprocess.run(["kaggle", "quota"], capture_output=True, env=env,
                           timeout=120, creationflags=0x08000000)
        out = (p.stdout or b"").decode("utf-8", "replace")
        err = (p.stderr or b"").decode("utf-8", "replace")
        g = re.search(r"GPU\s+([\d.]+)h\s+([\d.]+)h\s+([\d.]+)h\s+(\S+)", out)
        t = re.search(r"TPU\s+([\d.]+)h\s+([\d.]+)h\s+([\d.]+)h\s+(\S+)", out)
        if g:
            return ("GPU used=%s rem=%s/%s reset=%s | TPU %s" %
                    (g.group(1), g.group(2), g.group(3), g.group(4),
                     (t.group(2) + "/" + t.group(3) + " reset " + t.group(4))
                     if t else "?"))
        return "ERR " + (err or out).strip()[:90]
    except Exception as e:
        return "EXC " + str(e)[:80]


def main():
    seen = {}
    for f in glob.glob(os.path.expanduser("~/.kaggle/kaggle*.json")) + \
            glob.glob(os.path.expanduser("~/Downloads/kaggle.json")):
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        u = d.get("username")
        k = d.get("key")
        if u and k:
            seen.setdefault(u, (k, os.path.basename(f)))
    # account tu env
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        seen.setdefault(os.environ["KAGGLE_USERNAME"],
                        (os.environ["KAGGLE_KEY"], "env"))
    for u, (k, src) in sorted(seen.items()):
        print("%-22s [%s] %s" % (u, src, quota(u, k)))


if __name__ == "__main__":
    main()
