# -*- coding: utf-8 -*-
"""
publish_traj_r2.py - DUNG LAI dataset traj R2 (972 row) cho acc A.

Vay do gi (22/10):
  - `scripts/upload_traj_flat.py` STAGE 816 PNG RỜI vao thu muc => Kaggle CLI
    BO QUA thu muc con khi upload => dataset chi con traj.jsonl, KHONG co
    anh => loader khong resolve duoc anh => drop het row => traj_rows = 0
    => 5 run SFT v23b CHET voi thong bao "traj is still the OLD version
    (0 rows) - R2 not uploaded" (guard cua @MiMo -> fail loud, dung noi dung).
  - Ban R2 (972 row) chi con o dataset tren Kaggle, ma dataset do da bi
    thay bang ban 0 row; staging cuc bo cung bi don.

Cach khoi phuc (deterministic):
  1) doc base 816 row (traj_local_staging/traj.jsonl) + 816 anh (traj_images.zip)
  2) bo sung 156 row DONE cho 156 episode chua ket thuc bang DONE
     (DUNG logic cua phase13-gui/traj_done_aug.py) => 972 row / 216 DONE
  3) STAGE = traj.jsonl + traj_images.zip (PNG o GOC zip) + dataset-metadata.json
     => CLI upload ca file (khong bo qua thu muc) => loader giai nen zip roi
     resolve ext/<ten>.png = dung duong dan trong row
  4) VERIFY theo DUNG logic loader (base/rel -> ext/rel -> basename trong ext)

Dung:
    python scripts/publish_traj_r2.py            # build + verify (offline)
    python scripts/publish_traj_r2.py --upload   # + upload len Kaggle (key acc A)
ASCII-only source. Doc key tu HKCU (khong ghi key vao file).
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
BASE_JSONL = os.path.join(P13, "traj_local_staging", "traj.jsonl")
BASE_ZIP = os.path.join(P13, "traj_zip_staging", "traj_images.zip")
STAGE = os.path.join(P13, "traj_ds_staging", "khoadangnguye__ornith-gui-traj")
SLUG = "khoadangnguye/ornith-gui-traj"
DONE_SUFFIX = " When you are done, say DONE."
STEP_RE = re.compile(r"^(.*)_s(\d+)\.png$")


def log(m):
    print("[traj] %s" % m, flush=True)


def read_jsonl(p):
    out = []
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def is_done(r):
    return (r.get("action") or "").strip().upper().startswith("DONE")


def group(rows):
    eps = {}
    for r in rows:
        m = STEP_RE.match(r.get("image") or "")
        key = m.group(1) if m else (r.get("image") or "")
        eps.setdefault(key, []).append(r)
    for k in eps:
        eps[k].sort(key=lambda r: int(STEP_RE.match(r["image"]).group(2))
                    if STEP_RE.match(r.get("image") or "") else 0)
    return eps


def build():
    rows = read_jsonl(BASE_JSONL)
    log("base: %d row" % len(rows))
    eps = group(rows)
    added = []
    for key, rs in eps.items():
        last = rs[-1]
        if is_done(last):
            continue
        ins = (last.get("instruction") or "").strip()
        if not ins.endswith(DONE_SUFFIX.strip()):
            ins = ins + DONE_SUFFIX
        added.append({"image": last.get("image"), "instruction": ins,
                      "action": "DONE"})
    aug = rows + added
    log("aug: %d row (%d goc + %d DONE moi) | episode: %d"
        % (len(aug), len(rows), len(added), len(eps)))
    n_done = sum(1 for r in aug if is_done(r))
    log("row DONE: %d (%.1f%%)" % (n_done, 100.0 * n_done / max(1, len(aug))))

    # ---- staging: jsonl + ZIP (PNG o goc) + metadata
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE, exist_ok=True)
    with io.open(os.path.join(STAGE, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in aug:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    if not os.path.exists(BASE_ZIP):
        log("!! thieu %s" % BASE_ZIP)
        return None
    shutil.copy2(BASE_ZIP, os.path.join(STAGE, "traj_images.zip"))
    meta = {"title": "Ornith GUI traj (R2: %d row, %d DONE)" % (len(aug), n_done),
            "id": SLUG, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    log("staging: %s" % os.path.relpath(STAGE, ROOT))
    return aug, n_done


def verify_loader(aug):
    """Mo phong DUNG logic loader cua kernel (base/rel -> ext/rel -> basename)."""
    import tempfile
    with zipfile.ZipFile(os.path.join(STAGE, "traj_images.zip")) as z:
        names = set(z.namelist())
    base = os.path.join(STAGE, "traj.jsonl")
    tmp = tempfile.mkdtemp(prefix="loadext_")
    with zipfile.ZipFile(os.path.join(STAGE, "traj_images.zip")) as z:
        z.extractall(tmp)
    ok = miss = 0
    for r in aug:
        rel = r.get("image") or ""
        p1 = os.path.join(STAGE, rel.replace("/", os.sep))
        p2 = os.path.join(tmp, rel.replace("/", os.sep))
        if os.path.exists(p1):
            ok += 1
        elif os.path.exists(p2):
            ok += 1
        else:
            miss += 1
    shutil.rmtree(tmp, ignore_errors=True)
    log("resolve theo logic loader: %d/%d row (thieu %d)" % (ok, len(aug), miss))
    return miss == 0


def upload():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["KAGGLE_USERNAME"] = "khoadangnguye"
    key = os.environ.get("KAGGLE_KEY_A", "")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v, _t = winreg.QueryValueEx(k, "KAGGLE_KEY_A")
                key = str(v).strip()
        except Exception:
            key = ""
    if not key:
        log("!! thieu key acc A (KAGGLE_KEY_A / HKCU)")
        return 2
    env["KAGGLE_KEY"] = key
    cmd = ("kaggle datasets version -p \"%s\" -m \"R2: %d row + anh trong zip\""
           % (STAGE, sum(1 for _ in io.open(os.path.join(STAGE, "traj.jsonl"),
                                          encoding="utf-8") if _.strip())))
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=3600)
    log("upload: rc=%s | %s" % (p.returncode,
                                 ((p.stdout or "") + (p.stderr or ""))[-200:]))
    return 0 if p.returncode == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(BASE_JSONL):
        log("!! thieu base %s" % BASE_JSONL)
        return 2
    res = build()
    if not res:
        return 3
    aug, n_done = res
    if not verify_loader(aug):
        log("=> FAIL: co row khong resolve duoc anh")
        return 1
    print("| chi so | gia tri |")
    print("|---|---|")
    print("| rows | %d |" % len(aug))
    print("| episodes | %d |" % len(group(aug)))
    print("| row DONE | %d (%.1f%%) |" % (n_done, 100.0 * n_done / max(1, len(aug))))
    if a.upload:
        return upload()
    print()
    print("LENH UPLOAD (can key acc A):")
    print("  python scripts/publish_traj_r2.py --upload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
