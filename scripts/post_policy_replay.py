"""post_policy_replay.py - dong goi du lieu policy-replay thanh dataset (acc A).

Input : output cua kernel policy-replay (replay/traj.jsonl + replay/<suite>/shots/*.png)
Output: dataset <owner>/<id> voi traj.jsonl + shots.zip (anh TOP-LEVEL, Kaggle giai nen
        ra <ds>/shots/<ten>.png -> khop "image": "shots/<ten>.png").
"""
import argparse
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


def kaggle(args):
    p = subprocess.run(["kaggle"] + args, capture_output=True, env=ENV,
                       timeout=3600, creationflags=FLAGS)
    return ((p.stdout or b"").decode("utf-8", "replace"),
            (p.stderr or b"").decode("utf-8", "replace"))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="phase13-gui/out_policy_replay")
    ap.add_argument("--id", default="khoadangnguye/ornith-policy-replay-data")
    ap.add_argument("--title", default="Ornith policy replay train data")
    a = ap.parse_args()
    base = os.path.join(a.out, "replay")
    if not os.path.isdir(base):
        base = a.out
    tj = os.path.join(base, "traj.jsonl")
    cands = sorted(glob.glob(os.path.join(a.out, "**", "traj.jsonl"),
                             recursive=True), key=lambda p: -os.path.getsize(p))
    if not cands:
        print("khong thay traj.jsonl")
        return 1
    tj = cands[0]
    rows = [json.loads(l) for l in io.open(tj, encoding="utf-8") if l.strip()]
    print("traj: %s (%d row)" % (tj, len(rows)))
    tmp = tempfile.mkdtemp(prefix="pr_")
    try:
        # ANH phai nam FLAT o cap goc staging: `kaggle datasets create` BO QUA
        # thu muc con (bài học #1) -> shots/ se bi mat. Row se tro toi
        # "<ten>.png" va loader resolve bang basename (walk).
        sdir = tmp
        os.makedirs(sdir, exist_ok=True)
        zips = sorted(glob.glob(os.path.join(a.out, "**", "shots.zip"),
                                recursive=True), key=lambda p: -os.path.getsize(p))
        n_zip = 0
        for zp in zips:
            try:
                with zipfile.ZipFile(zp) as z:
                    for nm in z.namelist():
                        if nm.lower().endswith(".png"):
                            with z.open(nm) as src, open(
                                    os.path.join(sdir, os.path.basename(nm)),
                                    "wb") as dst:
                                shutil.copyfileobj(src, dst)
                            n_zip += 1
                break
            except Exception as e:
                print("zip loi %s: %s" % (zp, e))
        for p in glob.glob(os.path.join(a.out, "**", "shots", "*.png"),
                           recursive=True):
            dst = os.path.join(sdir, os.path.basename(p))
            if not os.path.exists(dst):
                shutil.copy2(p, dst)
        n_shot = len([f for f in os.listdir(sdir) if f.lower().endswith(".png")])
        print("anh: %d (tu zip %d)" % (n_shot, n_zip))
        if n_shot == 0:
            print("KHONG CO ANH -> dataset se khong dung duoc")
            return 1
        with io.open(os.path.join(tmp, "traj.jsonl"), "w", encoding="utf-8",
                     newline="\n") as fh:
            for r in rows:
                r = dict(r)
                r["image"] = os.path.basename(r["image"])
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        meta = {"title": a.title, "id": a.id, "licenses": [{"name": "other"}]}
        json.dump(meta, io.open(os.path.join(tmp, "dataset-metadata.json"), "w",
                                 encoding="utf-8"), ensure_ascii=False)
        out, err = kaggle(["datasets", "create", "-p", tmp])
        if not ok(out, err):
            out, err = kaggle(["datasets", "version", "-p", tmp, "-m",
                               "policy replay %s" % time.strftime("%H:%M")])
        if not ok(out, err):
            print("upload that bai:", (err or out)[-250:])
            return 1
        print("OK ->", a.id)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    import time
    sys.exit(main())
