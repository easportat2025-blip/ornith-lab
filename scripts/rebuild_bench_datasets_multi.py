# -*- coding: utf-8 -*-
"""
rebuild_bench_datasets_multi.py - build zip dataset bench cho MOI slug dataset
dang duoc kernel mount, de 11 fix task co hieu luc.

Vi sao can script nay (rebuild_bench_datasets.py chi lam 1 staging/slug):
  Kernel nao mount dataset nao (doc tu kernel-metadata.json):
    B15.5 : khoadangnguye/ornith-gui-bench-v155   (v155, v155_v21, v155_v22, think0)
            dieniw/ornith-gui-bench-v155           (v155_B, v155_v22_B)
    B16-A : khoadangnguye/ornith-gui-bench-v16    (v16, v16_v22, v16_v21_think0)
            khoadangnguye/ornith-gui-bench-v16b   (v16_v21)
            dieniw/ornith-gui-bench-v16            (v16_v22_B)
            dieniw/ornith-gui-bench-v16b           (v16_B)
  => 6 dataset. Noi dung zip GIONG NHAU (top dir bench_v155/ + bench_v16/),
     chi dataset-metadata.json id khac.

Dung:
    python scripts/rebuild_bench_datasets_multi.py          # build + in lenh
    python scripts/rebuild_bench_datasets_multi.py --upload # build + lenh upload (can KAGGLE_KEY cua acc)
Upload can cho TUNG acc: dat KAGGLE_USERNAME/KAGGLE_KEY truoc khi chay.
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
P13 = os.path.join(ROOT, "phase13-gui")

# (nguon task, top dir, ten zip, slug dataset)
SUITES = [
    ("bench_v15/tasks_v15_5", "bench_v155", "bench_v155_bundle.zip",
     ["khoadangnguye/ornith-gui-bench-v155", "dieniw/ornith-gui-bench-v155"],
     "Ornith GUI bench B15.5 (T13-T18)"),
    ("bench_v15/tasks_v16_a", "bench_v16", "bench_v16_bundle.zip",
     ["khoadangnguye/ornith-gui-bench-v16", "khoadangnguye/ornith-gui-bench-v16b",
      "dieniw/ornith-gui-bench-v16", "dieniw/ornith-gui-bench-v16b"],
     "Ornith GUI bench B16-A (T19-T26)"),
]
EXTRA = ["bench_v155.py", "bench_v16.py", "checker.py", "checker_v16.py",
         "self_test_report.json", "dummy_actions_v155.json",
         "dummy_actions_v16.json", "dummy_run_result.json",
         "dummy_run_result_v16.json"]


def _hkcu(var):
    """Doc env cap user (HKCU\\Environment) - key acc A/B thuong nam o day
    (process env cua shell co the khong co)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        pass
    try:
        import subprocess as _sp
        p = _sp.run(["powershell", "-NoProfile", "-Command",
                     "[Environment]::GetEnvironmentVariable('%s','User')" % var],
                    capture_output=True, timeout=60)
        return ((p.stdout or b"").decode("utf-8", "replace") or "").strip()
    except Exception:
        return ""


def key_of(owner):
    var = "KAGGLE_KEY_A" if owner == "khoadangnguye" else "KAGGLE_KEY_B"
    return (os.environ.get(var, "") or _hkcu(var)
            or os.environ.get("KAGGLE_KEY", "") or _hkcu("KAGGLE_KEY"))


def build(src_rel, top, zipname, slug, title, stage_root):
    src = os.path.join(P13, src_rel.replace("/", os.sep))
    owner, name = slug.split("/")
    dst = os.path.join(stage_root, "%s__%s" % (owner, name))
    os.makedirs(dst, exist_ok=True)
    zp = os.path.join(dst, zipname)
    n = 0
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in EXTRA:
            p = os.path.join(src, rel)
            if os.path.exists(p):
                z.write(p, top + "/" + rel)
                n += 1
        tdir = os.path.join(src, "tasks")
        for f in sorted(os.listdir(tdir)):
            z.write(os.path.join(tdir, f), top + "/tasks/" + f)
            n += 1
    with zipfile.ZipFile(zp) as z:
        names = set(z.namelist())
    assert top + "/tasks/tasks.json" in names, "thieu tasks.json"
    meta = {"title": title, "id": slug, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(dst, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("  %-46s %2d file %6.1f KB -> %s"
          % (slug, n, os.path.getsize(zp) / 1024, os.path.relpath(dst, ROOT)))
    return dst, zp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="phase13-gui/bench_ds_staging")
    ap.add_argument("--upload", action="store_true")
    a = ap.parse_args()
    stage_root = os.path.join(ROOT, a.stage.replace("/", os.sep))
    os.makedirs(stage_root, exist_ok=True)
    print("=== build dataset bench (voi trang da fix) ===")
    cmds = []
    for src_rel, top, zipname, slugs, title in SUITES:
        for slug in slugs:
            dst, zp = build(src_rel, top, zipname, slug, title, stage_root)
            cmds.append("kaggle datasets version -p \"%s\" -m \"fix tasks\""
                        % os.path.relpath(dst, ROOT))
    print()
    print("=== LENH UPLOAD (chay theo thu tu) ===")
    for c in cmds:
        print(c)
    if a.upload:
        print("\n=== UPLOAD ===")
        for c in cmds:
            d = c.split("-p ")[1].split(" ")[0].strip('"')
            p = os.path.join(ROOT, d.replace("/", os.sep))
            meta = json.load(io.open(os.path.join(p, "dataset-metadata.json"),
                                  encoding="utf-8"))
            owner = meta["id"].split("/")[0]
            env = dict(os.environ)
            env["KAGGLE_USERNAME"] = owner
            key = key_of(owner)
            if not key:
                print("  !! thieu key cho %s - bo qua" % owner)
                continue
            env["KAGGLE_KEY"] = key
            env["PYTHONIOENCODING"] = "utf-8"
            r = subprocess.run(["kaggle", "datasets", "version", "-p", p,
                                "-m", "fix tasks"], capture_output=True,
                               env=env, timeout=900)
            print("  %-46s rc=%s %s" % (meta["id"], r.returncode,
                                         ((r.stdout or b"") +
                                          (r.stderr or b"")).decode(
                                             "utf-8", "replace")[-120:].strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
