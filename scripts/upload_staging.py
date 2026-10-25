# -*- coding: utf-8 -*-
"""
upload_staging.py - upload 1 staging dataset len Kaggle bang key dung cua acc,
roi VERIFY file that tren remote (bat loi "dataset rong").

Viet sau khi kernel bench-v22 CRASH: Kaggle da BO QUA dataset khong ton tai
khi push ("could not be added to the kernel: [...]") van bao "successfully
pushed" => kernel chay nhung THIEU adapter LoRA => assert lora fail giua run,
mat ca slot GPU.

Nhiem vu cua script:
  1. doc id trong <staging>/dataset-metadata.json
  2. chon key dung theo owner (KAGGLE_KEY_A / KAGGLE_KEY_B)
  3. 'kaggle datasets create' -> neu da ton tai thi 'kaggle datasets version'
  4. doi 'READY'
  5. VERIFY: 'kaggle datasets files <owner>/<slug>' phai LIET KE du file
     (adapter_config.json, ...) - dataset rong/rong file = FAIL

Dung:
    python scripts/upload_staging.py phase13-gui/lora_v22_dataset
    python scripts/upload_staging.py phase13-gui/lora_v22_dataset --check
    python scripts/upload_staging.py phase13-gui/lora_v22_dataset --acc A
ASCII-only source. KHONG ghi key vao file.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS = 0x08000000 if os.name == "nt" else 0

# owner -> ten env var chua key cua acc do
OWNER_KEY = {
    "khoadangnguye": "KAGGLE_KEY_A",
    "dieniw": "KAGGLE_KEY_B",
    "hhjiji": "KAGGLE_KEY",
}
ACC_KEY = {"A": "KAGGLE_KEY_A", "B": "KAGGLE_KEY_B", "C": "KAGGLE_KEY",
           "ME": "KAGGLE_KEY"}


def kaggle(args, env, timeout=3600):
    try:
        p = subprocess.run(["kaggle"] + args, capture_output=True, env=env,
                           timeout=timeout, creationflags=FLAGS)
    except Exception as e:
        return 1, "", str(e)
    return (p.returncode,
            (p.stdout or b"").decode("utf-8", "replace"),
            (p.stderr or b"").decode("utf-8", "replace"))


def _hkcu(var):
    """Doc env cap user (HKCU\\Environment) - key cua acc A/B thuong nam o day
    (process env cua shell co the khong co)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        pass
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetEnvironmentVariable('%s','User')" % var],
            capture_output=True, timeout=60, creationflags=FLAGS)
        return ((p.stdout or b"").decode("utf-8", "replace") or "").strip()
    except Exception:
        return ""


def key_for(owner, acc=None):
    if acc:
        var = ACC_KEY.get(acc.upper(), "")
        # C: env cua process co the giu key CU sau khi user doi HKCU
        # => uu tien registry de tranh dung nham key.
        if acc.upper() == "C":
            return _hkcu(var) or os.environ.get(var, "")
        v = os.environ.get(ACC_KEY.get(acc.upper(), ""), "") or _hkcu(
            ACC_KEY.get(acc.upper(), ""))
        return v
    var = OWNER_KEY.get(owner, "KAGGLE_KEY")
    if owner == "hhjiji":
        return (_hkcu(var) or os.environ.get(var, "")
                or _hkcu("KAGGLE_KEY"))
    return (os.environ.get(var, "") or _hkcu(var)
            or os.environ.get("KAGGLE_KEY", "") or _hkcu("KAGGLE_KEY"))


def env_for(owner, acc=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["KAGGLE_USERNAME"] = owner
    k = key_for(owner, acc)
    if k:
        env["KAGGLE_KEY"] = k
    return env, bool(k)


def remote_files(owner, slug, env):
    """-> (list ten file | None, status string)

    FIX 23/10: CLI mac dinh chi tra 20 file/trang -> verify tuong dataset
    "chi co 20 file" (hoac 1 file) trong khi that ra 531. Nay phan trang
    bang --format json + Next Page Token.
    None = KHONG kiem duoc (403/404/timeout/rc!=0) -> khong ket luan.
    """
    ref = "%s/%s" % (owner, slug)
    files = []
    token = ""
    raw = ""
    for _ in range(30):
        cmd = ["datasets", "files", ref, "--page-size", "200",
               "--format", "json"]
        if token:
            cmd += ["--page-token", token]
        rc, out, err = kaggle(cmd, env, timeout=120)
        raw = out + err
        if rc != 0:
            return None, ("KHONG DOC DUOC (rc=%s) %s"
                          % (rc, raw.strip()[-140:].replace("\n", " ")))
        low = raw.lower()
        if "403" in low or "forbidden" in low or "404" in low:
            return None, ("KHONG DOC DUOC (403/404) - dataset co the chua ton tai "
                          "hoac private cho acc khac")
        i, j = out.find("["), out.rfind("]")
        if i < 0 or j < i:
            return None, ("KHONG DOC DUOC (output khong phai JSON): %s"
                          % raw.strip()[-140:].replace("\n", " "))
        try:
            batch = json.loads(out[i:j + 1])
        except Exception as e:
            return None, "KHONG DOC DUOC (JSON loi: %s)" % e
        if not batch:
            break
        files.extend(f.get("name") or "" for f in batch)
        token = ""
        for line in out.splitlines():
            if line.startswith("Next Page Token ="):
                token = line.split("=", 1)[1].strip()
        if not token:
            break
    if not files:
        return [], ("dataset RONG? (0 file) raw: %s"
                    % raw.strip()[-160:].replace("\n", " "))
    return files, "ok (%d file)" % len(files)


def stage_for_upload(p):
    """Kaggle CLI bo qua thu muc con (dir-mode=skip).

    => zip tung thu muc con thanh <ten>.zip (noi dung giu tien to <ten>/).
    Kaggle giai nen zip thanh <ten>/<ten>/... ; loader cua kernel resolve
    theo basename nen van dung. Tra ve (staging_dir, tmp_dir|None).
    """
    subdirs = [d for d in os.listdir(p)
               if os.path.isdir(os.path.join(p, d))]
    if not subdirs:
        return p, None
    tmp = tempfile.mkdtemp(prefix="kaggle_up_")
    for f in os.listdir(p):
        s = os.path.join(p, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(tmp, f))
    for d in subdirs:
        zp = os.path.join(tmp, d + ".zip")
        n = 0
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            rootd = os.path.join(p, d)
            for base, _dirs, fs in os.walk(rootd):
                for f in fs:
                    full = os.path.join(base, f)
                    rel = os.path.relpath(full, rootd).replace("\\", "/")
                    z.write(full, d + "/" + rel)
                    n += 1
        print("  zip %-24s %4d file  %6.1f MB"
              % (d, n, os.path.getsize(zp) / 1048576.0))
    return tmp, tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("staging")
    ap.add_argument("--check", action="store_true",
                    help="chi verify remote, khong upload")
    ap.add_argument("--acc", default=None, help="A | B | ME (ep key)")
    ap.add_argument("--wait", type=int, default=40)
    a = ap.parse_args()

    p = a.staging if os.path.isabs(a.staging) else os.path.join(
        ROOT, a.staging.replace("/", os.sep))
    mp = os.path.join(p, "dataset-metadata.json")
    if not os.path.exists(mp):
        print("FAIL: khong co dataset-metadata.json trong %s" % p)
        return 2
    # dataset-metadata.json co the co BOM (PowerShell Set-Content -Encoding utf8)
    meta = json.load(io.open(mp, encoding="utf-8-sig"))
    slug = meta.get("id") or ""
    if "/" not in slug:
        print("FAIL: id khong hop le: %r" % slug)
        return 2
    owner = slug.split("/")[0]
    print("staging : %s" % os.path.relpath(p, ROOT))
    print("slug    : %s" % slug)
    n_local = sum(len(fs) for _b, _d, fs in os.walk(p)) - 1
    print("file local: %d" % n_local)

    env, has_key = env_for(owner, a.acc)
    if not has_key:
        print("!! KHONG co key cho acc '%s' (can %s) - bo qua upload"
              % (owner, OWNER_KEY.get(owner, "KAGGLE_KEY")))
        return 3

    updir, tmp = stage_for_upload(p)
    try:
        if not a.check:
            print("=== upload ===")
            rc, out, err = kaggle(["datasets", "create", "-p", updir], env)
            blob = (out + err)
            if rc != 0 or "already" in blob.lower() or "403" in blob.lower():
                print("  create rc=%s (%s) -> thu version"
                      % (rc, blob.strip()[-90:].replace("\n", " ")))
                rc, out, err = kaggle(["datasets", "version", "-p", updir, "-m",
                                       "upload %s" % time.strftime("%d/%m %H:%M")],
                                      env)
                blob = (out + err)
                print("  version rc=%s %s" % (rc, blob.strip()[-120:].replace("\n", " ")))
            else:
                print("  create rc=%s %s" % (rc, blob.strip()[-120:].replace("\n", " ")))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    files = None
    if not a.check:
        print("=== wait READY (theo so file) ===")
        for i in range(1, max(1, a.wait) + 1):
            files, status = remote_files(owner, slug, env)
            print("  [%2d] %s" % (i, status))
            if files and len(files) >= 2:
                break
            time.sleep(15)

    print("=== VERIFY file remote ===")
    if files is None:
        files, status = remote_files(owner, slug, env)
    else:
        status = "ok (%d file)" % len(files)
    print("  %s -> %s" % (slug, status))
    if files is None:
        print("  !! khong doc duoc danh sach file. Neu day la acc khac: "
              "dung key cua acc '%s' de verify" % owner)
        return 4
    if not files:
        print("  !! FAIL: dataset RONG (0 file) - kernel se mount ma khong co "
              "gi -> bo qua adapter/du lieu")
        return 5
    for f in sorted(files)[:20]:
        print("   - %s" % f)
    print("OK: %d file tren remote" % len(files))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
