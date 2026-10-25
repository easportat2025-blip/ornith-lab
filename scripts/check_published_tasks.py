# -*- coding: utf-8 -*-
"""
check_published_tasks.py - kiem dataset DA PUBLISH tren Kaggle co dung PHIEN BAN
mong doi chua, chi can 1 file + 1 chuoi dac trung.

Vi sao can: 22/10, run bench-v16-v22 v2 chay tren TASK CU (detect_task_fixes:
PROOF_OLD) ⇒ nguyen do la dataset CHUA duoc version lai. Khong co cach nao
nhin thay tu log ⇒ phai kiem truc tiep noi dung da publish.

Dung (vi du kiem dataset B16-A da co fix "Current values: f1 = " cua T23):
    python scripts/check_published_tasks.py khoadangnguye/ornith-gui-bench-v16b \
        --file "bench_v16/tasks/t23_undoredo.html" --marker "Current values: f1 = "
    python scripts/check_published_tasks.py <owner/slug> --file <f> --marker <m> --acc A
ASCII-only source. Doc-only (tai 1 file) - KHONG sua gi tren Kaggle.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def acc_env(acc, owner=""):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    var = {"A": "KAGGLE_KEY_A", "B": "KAGGLE_KEY_B"}.get((acc or "").upper(),
                                                        "KAGGLE_KEY")
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
        # PHAI set USERNAME theo acc: CLI dung cap (key, username) - dung key
        # cua acc A nhung username cua acc khac => 403.
        if (acc or "").upper() == "A":
            env["KAGGLE_USERNAME"] = "khoadangnguye"
        elif (acc or "").upper() == "B":
            env["KAGGLE_USERNAME"] = "dieniw"
        elif owner:
            env["KAGGLE_USERNAME"] = owner
    return env


def remote_files(dataset, env):
    """-> {ten file: size} tu 'kaggle datasets files' (1 API call)."""
    p = subprocess.run(["kaggle", "datasets", "files", dataset],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=600)
    if p.returncode != 0:
        return None
    out = {}
    for line in (p.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and "." in parts[0] and \
                parts[0].lower() not in ("name", "size", "creationdate"):
            try:
                out[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return out


def check_sizes(dataset, staging, env, zip_top=None):
    """So kich thuoc file giua staging LOCAL va dataset DA PUBLISH.

    Dataset 'stale' (chua version lai) se lech size file => phat hien
    khong can tai file, chi 1 API call/dataset.
    """
    sp = os.path.join(ROOT, staging.replace("/", os.sep))
    if not os.path.isdir(sp):
        print("khong co staging local: %s" % staging)
        return None
    local = {}
    zips = [f for f in os.listdir(sp) if f.endswith(".zip")]
    if zips:
        # staging dang gom 1 file ZIP; Kaggle publish se GIAI NEN => so sanh
        # phan ben trong zip voi danh sach file tren remote.
        import zipfile
        zp = os.path.join(sp, zips[0])
        try:
            with zipfile.ZipFile(zp) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    local[info.filename] = info.file_size
        except Exception as e:
            print("khong doc duoc zip: %s" % e)
            return None
    else:
        for root, _d, files in os.walk(sp):
            for f in files:
                if f == "dataset-metadata.json":
                    continue
                p = os.path.join(root, f)
                rel = os.path.relpath(p, sp).replace("\\", "/")
                if zip_top:
                    rel = "%s/%s" % (zip_top, rel)
                try:
                    local[rel] = os.path.getsize(p)
                except OSError:
                    pass
    rem = remote_files(dataset, env)
    if rem is None:
        print("khong doc duoc file list cua %s (403?)" % dataset)
        return None
    if not local:
        print("staging local rong: %s" % staging)
        return None
    # file trong zip: ten co top-dir => bo top-dir de doi chieu
    diff = []
    missing = []
    for rel, sz in sorted(local.items()):
        key = rel
        if key not in rem and zip_top and key.startswith(zip_top + "/"):
            key = key[len(zip_top) + 1:]
        if key not in rem:
            missing.append(rel)
        elif rem[key] != sz:
            diff.append((rel, sz, rem[key]))
    same = len(local) - len(diff) - len(missing)
    print("%-46s so sanh %d file: giong %d | KHAC kich thuoc %d | thieu %d"
          % (dataset, len(local), same, len(diff), len(missing)))
    for rel, a, b in diff[:8]:
        print("   KHAC: %-44s local=%d remote=%d" % (rel, a, b))
    for rel in missing[:8]:
        print("   THIEU tren remote: %s" % rel)
    return not diff and not missing


BENCH_DATASETS = [
    ("khoadangnguye/ornith-gui-bench-v155",
     "phase13-gui/bench_ds_staging/khoadangnguye__ornith-gui-bench-v155", "bench_v155"),
    ("dieniw/ornith-gui-bench-v155",
     "phase13-gui/bench_ds_staging/dieniw__ornith-gui-bench-v155", "bench_v155"),
    ("khoadangnguye/ornith-gui-bench-v16",
     "phase13-gui/bench_ds_staging/khoadangnguye__ornith-gui-bench-v16", "bench_v16"),
    ("khoadangnguye/ornith-gui-bench-v16b",
     "phase13-gui/bench_ds_staging/khoadangnguye__ornith-gui-bench-v16b", "bench_v16"),
    ("dieniw/ornith-gui-bench-v16",
     "phase13-gui/bench_ds_staging/dieniw__ornith-gui-bench-v16", "bench_v16"),
    ("dieniw/ornith-gui-bench-v16b",
     "phase13-gui/bench_ds_staging/dieniw__ornith-gui-bench-v16b", "bench_v16"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset", nargs="?", help="owner/slug")
    ap.add_argument("--all-bench", action="store_true",
                    help="so kich thuoc CUA 6 dataset bench voi staging local")
    ap.add_argument("--file", required=False,
                    help="file trong dataset (vd bench_v16/tasks/t23_undoredo.html)")
    ap.add_argument("--marker", required=False,
                    help="chuoi dac trung phai CO trong phien ban moi")
    ap.add_argument("--staging", default=None,
                    help="so kich thuoc voi staging LOCAL (thay cho --file/--marker)")
    ap.add_argument("--zip-top", default=None,
                    help="ten top-dir trong zip (vd bench_v155)")
    ap.add_argument("--acc", default=None, help="A | B | (mac dinh: key hien tai)")
    ap.add_argument("--expect", choices=["present", "absent"], default="present",
                    help="mong doi marker co (present) hay khong (absent - de kiem "
                         "ban CU)")
    a = ap.parse_args()
    env = acc_env(a.acc, a.dataset.split("/")[0] if a.dataset and "/" in a.dataset else "")

    # ---- che do batch: 6 dataset bench
    if a.all_bench:
        bad = 0
        for ds, st, top in BENCH_DATASETS:
            owner = ds.split("/")[0]
            # dataset private: phai dung key CUA CHINH owner (va username dung
            # theo owner) => acc nao khong doc duoc => 403.
            if owner == "khoadangnguye":
                env_d = acc_env("A", owner)
            elif owner == "dieniw":
                env_d = acc_env("B", owner)
            else:
                env_d = acc_env(a.acc, owner)
            ok = check_sizes(ds, st, env_d, top)
            if ok is None:
                bad += 1
                continue
            if not ok:
                bad += 1
        print("=" * 60)
        print("=> %d/6 dataset bench KHOP staging local (da version dung)"
              % (6 - bad))
        print("   Neu >0, chay 'python scripts/rebuild_bench_datasets_multi.py "
              "--upload' roi chay lai lenh nay")
        return 0 if bad == 0 else 1

    if not a.dataset:
        print("can owner/slug, hoac --all-bench")
        return 2

    # ---- che do so kich thuoc (nhanh, 1 API call/dataset)
    if a.staging:
        ok = check_sizes(a.dataset, a.staging, env, a.zip_top)
        if ok is None:
            return 2
        print("=> %s" % ("DUNG phien ban mong doi" if ok else
                          "SAI: dataset tren Kaggle CHUA khop staging local "
                          "(chua version lai / hoac sai noi dung)"))
        return 0 if ok else 1

    if not a.file or not a.marker:
        print("can --file + --marker, hoac --staging")
        return 2
    tmp = tempfile.mkdtemp(prefix="dscheck_")
    cmd = ["kaggle", "datasets", "download", a.dataset, "-f", a.file, "-p", tmp,
           "--unzip"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=600)
    if p.returncode != 0:
        print("TAI THAT BAI (rc=%s): %s" % (p.returncode,
              ((p.stdout or "") + (p.stderr or ""))[-300:].strip()))
        return 2
    found = None
    for root, _d, files in os.walk(tmp):
        for f in files:
            path = os.path.join(root, f)
            try:
                c = io.open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if a.marker in c:
                found = path
                break
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    if found:
        print("CO marker %r trong %s" % (a.marker, a.file))
        ok = (a.expect == "present")
        print("=> %s" % ("DUNG phien ban mong doi" if ok else
                          "SAI: marker da co nhung ban mong doi KHONG co marker"))
        return 0 if ok else 1
    print("KHONG co marker %r trong %s" % (a.marker, a.file))
    ok = (a.expect == "absent")
    print("=> %s" % ("DUNG phien ban CU (mong doi)" if ok else
                      "SAI: dataset CHUA duoc version lai (van la phien ban CU)"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
