# -*- coding: utf-8 -*-
"""
copy_ds_a_to_b.py - copy dataset tu acc A (khoadangnguye) sang acc B (dieniw).

Ly do (22/10): acc A het quota GPU (30.08h/30h, reset 24/10) => khong push
duoc kernel train => chuyen pipeline sang acc B (con 12.38h). Nhung dataset
cua A la PRIVATE => acc B khong mount duoc (Kagle silent bo qua, van bao
"successfully pushed") => phai copy thu cong.

Cach copy (1 dataset):
  1) `kaggle datasets download` -> 1 file zip (da gom ca thu muc con)
  2) unzip tam -> lay file .jsonl (sau nhat) -> copy ra TOP-LEVEL staging
     (loader doc base/<fname>.jsonl; nam trong zip thi loader khong thay)
  3) staging = <fname>.jsonl + <slug>.zip + dataset-metadata.json
     (2 file -> CLI khong hang; anh giai nen trong ext/ -> loader resolve
      duoc bang basename walk - da patch trong kernel_v24)
  4) `kaggle datasets create` voi key B + verify READY

Usage:
    python scripts/copy_ds_a_to_b.py                 # copy 8 dataset train
    python scripts/copy_ds_a_to_b.py <slug> [...]    # copy tuy chon
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, "phase13-gui", "ds_copy_tmp")
STAGE = os.path.join(ROOT, "phase13-gui", "ds_copy_stage")

DEFAULT = [
    "ornith-gui-traj",
    "ornith-gui-real-ui",
    "ornith-gui-real-fixtures",
    "gui-selfplay",
    "ornith-gui-train3d",
    "ornith-gui-train3d-hard",
    "ornith-policy-replay-data",
    "ornith-gui-synth-recipe",
]
TITLE = {
    "ornith-gui-traj": "Ornith GUI traj R2 (972 row)",
    "ornith-gui-real-ui": "Ornith GUI real UI (792 row)",
    "ornith-gui-real-fixtures": "Ornith GUI real fixtures (42 row)",
    "gui-selfplay": "Ornith GUI selfplay",
    "ornith-gui-train3d": "Ornith GUI train 3D",
    "ornith-gui-train3d-hard": "Ornith GUI train 3D hard",
    "ornith-policy-replay-data": "Ornith policy replay data",
    "ornith-gui-synth-recipe": "Ornith synth recipe (loop recovery)",
}


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def env_for(owner):
    var = "KAGGLE_KEY_A" if owner == "khoadangnguye" else "KAGGLE_KEY_B"
    key = os.environ.get(var) or hkcu(var) or hkcu("KAGGLE_KEY") or ""
    e = dict(os.environ)
    e["KAGGLE_USERNAME"] = owner
    e["KAGGLE_KEY"] = key
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def run(cmd, env, timeout=3600):
    p = subprocess.run(cmd, capture_output=True, env=env, timeout=timeout,
                       creationflags=0x08000000 if os.name == "nt" else 0)
    return p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode(
        "utf-8", "replace")


def copy_one(name):
    envA = env_for("khoadangnguye")
    envB = env_for("dieniw")
    os.makedirs(TMP, exist_ok=True)
    dl = os.path.join(TMP, name)
    shutil.rmtree(dl, ignore_errors=True)
    os.makedirs(dl, exist_ok=True)
    rc, out = run(["kaggle", "datasets", "download",
                   "khoadangnguye/" + name, "-p", dl, "--force"], envA)
    zips = [f for f in os.listdir(dl) if f.lower().endswith(".zip")]
    if not zips:
        print("  !! download fail %s: %s" % (name, out.strip()[-160:]))
        return False
    zp = os.path.join(dl, zips[0])
    mb = os.path.getsize(zp) / 1e6
    # tim .jsonl sau nhat trong zip
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        js = [n for n in names if n.lower().endswith(".jsonl")]
        if not js:
            print("  !! khong co .jsonl trong %s" % name)
            return False
        js.sort(key=lambda n: (n.count("/"), n))
        jname = os.path.basename(js[0])
        # staging
        sd = os.path.join(STAGE, "dieniw__" + name)
        shutil.rmtree(sd, ignore_errors=True)
        os.makedirs(sd, exist_ok=True)
        with z.open(js[0]) as src, io.open(os.path.join(sd, jname), "wb") as dst:
            shutil.copyfileobj(src, dst)
        shutil.copy2(zp, os.path.join(sd, zips[0]))
        nrows = sum(1 for _ in io.open(os.path.join(sd, jname), encoding="utf-8",
                                       errors="replace"))
        meta = {"title": TITLE.get(name, ("Ornith " + name)[:48]),
                "id": "dieniw/" + name,
                "licenses": [{"name": "other"}]}
        io.open(os.path.join(sd, "dataset-metadata.json"), "w",
                encoding="utf-8", newline="\n").write(
            json.dumps(meta, ensure_ascii=False, indent=1))
    print("  %-30s zip %.1fMB | %s: %d row | stage %d file"
          % (name, mb, jname, nrows, len(os.listdir(sd))))
    rc, out = run(["kaggle", "datasets", "create", "-p", sd], envB)
    if rc != 0:
        rc, out = run(["kaggle", "datasets", "version", "-p", sd, "-m",
                       "copy from accA"], envB)
    ok = "Upload successful" in out or "successfully" in out.lower() or rc == 0
    print("     upload rc=%s %s" % (rc, out.strip()[-110:].replace("\n", " ")))
    return ok


def main():
    names = sys.argv[1:] or DEFAULT
    os.makedirs(STAGE, exist_ok=True)
    print("=== copy dataset A -> B ===")
    for n in names:
        try:
            copy_one(n)
        except Exception as e:
            print("  !! loi %s: %s" % (n, e))
        time.sleep(4)
    print("\n=== verify READY ===")
    envB = env_for("dieniw")
    for n in names:
        rc, out = run(["kaggle", "datasets", "status", "dieniw/" + n], envB,
                      timeout=180)
        st = "ready" if "ready" in out.lower() else out.strip()[-60:]
        print("  dieniw/%-30s %s" % (n, st))
        time.sleep(3)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
