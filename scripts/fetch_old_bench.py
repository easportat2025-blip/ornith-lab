# -*- coding: utf-8 -*-
"""
fetch_old_bench.py - tai dataset bench o PHIEN BAN CU (version) va dua len
slug MOI de chay "model moi tren task CU" (o thu nghiem 2x2).

Vi sao can: v22 tang +50 diem tren B15.5 nhung do CHUNG 2 nguyen nhan (sua
loi sinh + sua task) => KHONG quy duoc cho task fix. Thu nghiem 2x2 can
them 1 o: **model v22 tren task B15.5 CU** => tach duoc phan nao do loi sinh,
phan nao do sua task.
=> dataset version CU van con tren Kaggle (version history) => tai version do
va upload lai duoi slug moi (vd ...-bench-v155-old) de kernel mount vao.

Dung (can key cua acc chu dataset):
    python scripts/fetch_old_bench.py khoadangnguye/ornith-gui-bench-v155 \
        --version 1 --new-slug khoadangnguye/ornith-gui-bench-v155-old
ASCII-only source. KHONG ghi key vao file.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS = 0x08000000 if os.name == "nt" else 0
API = "https://www.kaggle.com/api/v1/datasets/download"


def acc_env(owner):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    var = ("KAGGLE_KEY_A" if owner == "khoadangnguye"
           else "KAGGLE_KEY_B" if owner == "dieniw" else "KAGGLE_KEY")
    key = os.environ.get(var, "")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v, _t = winreg.QueryValueEx(k, var)
                key = str(v).strip()
        except Exception:
            key = ""
    if key:
        env["KAGGLE_KEY"] = key
    env["KAGGLE_USERNAME"] = owner
    return env, bool(key)


def download_version(owner, slug, version, out_dir):
    """Tai 1 version cu the cua dataset. -> (ok, thong bao)"""
    env, has_key = acc_env(owner)
    if not has_key:
        return False, "thieu key cho acc '%s'" % owner
    url = "%s/%s/%s/%d" % (API, owner, slug, version)
    import base64
    import urllib.request
    token = base64.b64encode(("%s:%s" % (owner, env["KAGGLE_KEY"]))
                             .encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + token})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
    except Exception as e:
        return False, "tai version %d that bai: %s" % (version, str(e)[:160])
    os.makedirs(out_dir, exist_ok=True)
    zp = os.path.join(out_dir, "%s_v%d.zip" % (slug, version))
    with open(zp, "wb") as fh:
        fh.write(data)
    return True, "tai duoc %s (%d byte)" % (os.path.basename(zp), len(data))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", help="owner/slug cua dataset can version CU")
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--new-slug", default=None,
                    help="slug MOI de upload (mac dinh: <slug>-old)")
    ap.add_argument("--out", default="phase13-gui/old_bench_ds")
    a = ap.parse_args()
    if "/" not in a.dataset:
        print("dataset phai dang owner/slug")
        return 2
    owner, slug = a.dataset.split("/", 1)
    new_slug = a.new_slug or (slug + "-old")
    out_root = os.path.join(ROOT, a.out.replace("/", os.sep))
    dl_dir = os.path.join(out_root, "dl")
    stage = os.path.join(out_root, "%s__%s" % (owner, new_slug))
    os.makedirs(dl_dir, exist_ok=True)

    print("=== tai version %d cua %s ===" % (a.version, a.dataset))
    ok, msg = download_version(owner, slug, a.version, dl_dir)
    print("  ", msg)
    if not ok:
        print("HUONG DAN: hay tai thu cong vao Kaggle UI (Versions -> download) "
              "roi chay lai lenh nay voi --skip-download")
        return 3

    # giai nen + dua ra staging voi id MOI
    if os.path.isdir(stage):
        shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)
    zps = [f for f in os.listdir(dl_dir) if f.endswith(".zip")]
    if not zps:
        print("khong co file zip nao de giai nen")
        return 4
    with zipfile.ZipFile(os.path.join(dl_dir, zps[0])) as z:
        z.extractall(stage)
    meta = {"title": "Ornith GUI bench %s (PHIEN BAN CU - doi chieu)" % slug,
            "id": "%s/%s" % (owner, new_slug),
            "licenses": [{"name": "other"}]}
    with io.open(os.path.join(stage, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    n = sum(len(fs) for _r, _d, fs in os.walk(stage))
    print("staging: %s (%d file)" % (os.path.relpath(stage, ROOT), n))
    print()
    print("=== LENH TIEP (can key acc '%s') ===" % owner)
    print("  kaggle datasets create -p \"%s\"   # hoac 'version' neu da ton tai"
          % os.path.relpath(stage, ROOT))
    print("  # roi them slug moi vao dataset_sources cua kernel bench va push lai")
    print("  # => do 'model v22 tren task CU' = o thu nghiem 2x2 con thieu")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
