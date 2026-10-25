"""ferry_dataset.py - chuyen dataset tu acc nguon sang acc dich (dataset private
theo acc: acc khac khong mount duoc).

QUAN TRONG (3 bai hoc):
 1. kaggle CLI tra exit code 0 KE CA khi API loi (403) -> phai kiem CHUOI output.
 2. kaggle CLI BO QUA thu muc khi upload dataset -> phai upload dang ZIP.
 3. CLI download dataset tra ve 1 file .zip chua giai nen -> upload NGUYEN file zip
    do (Kaggle tu giai nen -> giu dung cau truc goc, khong gom lai 2 lan).

Key nguon doc tu HKCU:\\Environment (user env) neu khong truyen env -> tranh
shell bi pollution.

Dung: python scripts/ferry_dataset.py <slug> [<slug> ...]
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"
FLAGS = 0x08000000 if os.name == "nt" else 0
ERR_MARK = ("403", "401", "404", "forbidden", "not found", "must be")


def kaggle(args, env):
    p = subprocess.run(["kaggle"] + args, capture_output=True, env=env,
                       timeout=7200, creationflags=FLAGS)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


def ok(out, err):
    low = (out + "\n" + err).lower()
    for m in ("upload successful", "dataset version", "successfully",
              "is being created", "creating"):
        if m in low:
            return True
    for m in ERR_MARK:
        if m in low:
            return False
    return False


def src_creds():
    u = os.environ.get("ACC_SRC_USERNAME")
    k = os.environ.get("ACC_SRC_KEY")
    if u and k:
        return u, k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as rk:
            def val(n):
                try:
                    return winreg.QueryValueEx(rk, n)[0]
                except OSError:
                    return None
            return val("KAGGLE_USERNAME"), val("KAGGLE_KEY")
    except Exception:
        return None, None


def main():
    slugs = sys.argv[1:]
    if not slugs:
        print("dung: ferry_dataset.py <slug>...")
        return 1
    su, sk = src_creds()
    du, dk = os.environ["KAGGLE_USERNAME"], os.environ["KAGGLE_KEY"]
    if not su or not sk:
        print("khong lay duoc credential acc nguon")
        return 1
    print("nguon=%s -> dich=%s" % (su, du))
    env_src = dict(ENV)
    env_src["KAGGLE_USERNAME"], env_src["KAGGLE_KEY"] = su, sk
    env_dst = dict(ENV)
    env_dst["KAGGLE_USERNAME"], env_dst["KAGGLE_KEY"] = du, dk
    n_ok = 0
    for slug in slugs:
        tmp = tempfile.mkdtemp(prefix="ferry_")
        try:
            rc, out, err = kaggle(["datasets", "download", "%s/%s" % (su, slug),
                                   "-p", tmp, "--force"], env_src)
            names = os.listdir(tmp) if os.path.isdir(tmp) else []
            zips = [f for f in names if f.endswith(".zip")]
            if not names:
                print("[%s] download that bai: %s" % (slug, (err or out)[-160:]))
                continue
            if zips:
                # giu nguyen zip (Kaggle tu giai nen -> dung cau truc goc)
                for f in names:
                    if f in zips or f == "dataset-metadata.json":
                        continue
                    p = os.path.join(tmp, f)
                    if os.path.isdir(p):
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        os.remove(p)
                print("  -> giu 1 zip: %s (%d KB)" %
                      (zips[0], os.path.getsize(os.path.join(tmp, zips[0])) // 1024))
            meta = {"title": slug, "id": "%s/%s" % (du, slug),
                    "licenses": [{"name": "other"}]}
            with open(os.path.join(tmp, "dataset-metadata.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(meta, fh)
            rc, out, err = kaggle(["datasets", "create", "-p", tmp], env_dst)
            if not ok(out, err):
                rc, out, err = kaggle(["datasets", "version", "-p", tmp, "-m",
                                       "ferry %s" % slug], env_dst)
            if not ok(out, err):
                print("[%s] upload that bai: %s" % (slug, (err or out)[-200:]))
                continue
            print("[%s] -> %s/%s OK" % (slug, du, slug))
            n_ok += 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("ferry xong: %d/%d" % (n_ok, len(slugs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
