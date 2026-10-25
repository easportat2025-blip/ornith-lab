# -*- coding: utf-8 -*-
r"""
host_train_data.py - tai dataset train tu Kaggle (acc B, fallback acc A) va
HOST len HF dataset repo PUBLIC (kkouadn/ornith-colab-data) de may Colab
tai bang wget (khong can token, tranh endpoint 'colab upload' 500).

Dung:
    python scripts\host_train_data.py
ASCII-only source. Key doc tu HKCU (KHONG ghi key vao file).
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(os.environ.get("TEMP", "."), "hostdata")
HF_REPO = "kkouadn/ornith-colab-data"

# (ten dataset tren Kaggle, ten file .zip tren HF)
WANT = [
    ("ornith-gui-synth-recipe", "ornith-gui-synth-recipe.zip"),
    ("ornith-gui-train3d", "ornith-gui-train3d.zip"),
    ("ornith-gui-train3d-hard", "ornith-gui-train3d-hard.zip"),
    ("ornith-gui-real-ui", "ornith-gui-real-ui.zip"),
    ("ornith-gui-real-fixtures", "ornith-gui-real-fixtures.zip"),
    ("ornith-gui-traj", "ornith-gui-traj.zip"),
    ("ornith-policy-replay-data", "ornith-policy-replay-data.zip"),
    ("gui-selfplay", "gui-selfplay.zip"),
]


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def key(owner):
    var = "KAGGLE_KEY_A" if owner == "khoadangnguye" else "KAGGLE_KEY_B"
    return os.environ.get(var) or hkcu(var) or ""


def kaggle_dl(owner, name, dest):
    env = dict(os.environ)
    env["KAGGLE_USERNAME"] = owner
    env["KAGGLE_KEY"] = key(owner)
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run(["kaggle", "datasets", "download",
                        "%s/%s" % (owner, name), "-p", dest, "--force"],
                       capture_output=True, text=True, env=env, timeout=1800)
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    return p.returncode, out


def host(files):
    from huggingface_hub import HfApi
    toks = [t for t in (os.environ.get("HF_TOKEN"), hkcu("HF_TOKEN"),
                        os.environ.get("HF_TOKEN_2"), hkcu("HF_TOKEN_2")) if t]
    for tok in toks:
        api = HfApi(token=tok)
        try:
            api.create_repo(HF_REPO, repo_type="dataset", exist_ok=True,
                            private=False)
            for f in files:
                api.upload_file(path_or_fileobj=f,
                                path_in_repo=os.path.basename(f),
                                repo_id=HF_REPO, repo_type="dataset",
                                commit_message="host %s" % os.path.basename(f),
                                token=tok)
                print("    host OK  %s (%.2f MB)"
                      % (os.path.basename(f),
                         os.path.getsize(f) / 1e6))
            return True
        except Exception as e:
            print("    token loi: %s" % str(e)[:120])
    return False


def main():
    os.makedirs(TMP, exist_ok=True)
    got = []
    for name, zipname in WANT:
        p = os.path.join(TMP, zipname)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            print("  da co: %s" % zipname)
            got.append(p)
            continue
        ok = False
        for owner in ("dieniw", "khoadangnguye"):
            rc, out = kaggle_dl(owner, name, TMP)
            if os.path.exists(p) and os.path.getsize(p) > 1000:
                print("  tai %-30s tu %s (%.2f MB)"
                      % (name, owner, os.path.getsize(p) / 1e6))
                got.append(p)
                ok = True
                break
            print("  tai %-30s that bai (%s): %s"
                  % (name, owner, out.strip()[-90:]))
            time.sleep(3)
        if not ok:
            print("  !! bo qua %s" % name)
    print("\n=== host len HF public ===")
    if not got:
        print("  khong co file nao de host")
        return 1
    if not host(got):
        print("  !! host that bai")
        return 1
    print("\nURL (wget tren VM):")
    for f in got:
        print("  https://huggingface.co/datasets/%s/resolve/main/%s"
              % (HF_REPO, os.path.basename(f)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
