# -*- coding: utf-8 -*-
"""
fix_v22_datasets.py - chuan bi 2 dataset lam kernel v22 chet (TASK-19/root-cause).

Vay do la gi:
  1) STAGE dataset 'khoadangnguye/ornith-gui-train3d-hard' (dang ton tai o
     hhjiji/... nen kernel v22 attach sai owner -> mount khong co -> FAIL).
  2) STAGE lai dataset 'ornith-policy-replay-data' (script post_policy_replay.ps1
     copy sai path 'out_policy_replay/...' thay vi 'out_policy_replay/replay/...'
     -> shots.zip KHONG duoc copy -> 0/332 row).
  3) VERIFY offline: mo phong DUNG loader cua kernel (load_ds_rows) tren staging
     -> bao 'N/N row resolve' truoc khi lenh Kaggle duoc chay.

KHONG push, KHONG dung key, KHONG sua file cua agent khac.
ASCII-only source.

Dung:
    python scripts/fix_v22_datasets.py --stage        # stage + verify + in lenh
    python scripts/fix_v22_datasets.py --verify-only   # chi verify staging hien co
"""
import argparse
import io
import json
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- (1) train3d-hard: staging co san, chi doi id -----------------------
T3DH_SRC = os.path.join(ROOT, "phase14-blender", "train3d_hard_dataset")
T3DH_STAGE = os.path.join(ROOT, "phase14-blender", "train3d_hard_dataset_accA")
T3DH_ID = "khoadangnguye/ornith-gui-train3d-hard"
T3DH_TITLE = "Ornith GUI train3D grounding hard"

# ---- (2) policy-replay: file that REALLY o out_policy_replay/replay/ ----
PR_SRC = os.path.join(ROOT, "phase13-gui", "out_policy_replay", "replay")
PR_STAGE = os.path.join(ROOT, "phase13-gui", "policy_replay_dataset")
PR_ID = "khoadangnguye/ornith-policy-replay-data"
PR_TITLE = "Ornith policy replay train data"


def log(m):
    print("[fix] " + str(m), flush=True)


def stage_train3d_hard():
    if not os.path.isdir(T3DH_SRC):
        log("KHONG thay %s" % T3DH_SRC)
        return False
    if os.path.isdir(T3DH_STAGE):
        shutil.rmtree(T3DH_STAGE)
    os.makedirs(T3DH_STAGE, exist_ok=True)
    # giong het dataset 'train3d' dang chay duoc: traj.jsonl + shots.zip + metadata
    for f in ("traj.jsonl", "shots.zip"):
        src = os.path.join(T3DH_SRC, f)
        if not os.path.exists(src):
            log("KHONG thay %s" % src)
            return False
        shutil.copy2(src, os.path.join(T3DH_STAGE, f))
    meta = {"title": T3DH_TITLE, "id": T3DH_ID,
            "licenses": [{"name": "other"}]}
    with io.open(os.path.join(T3DH_STAGE, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
    log("staged train3d-hard -> %s (id=%s)" % (T3DH_STAGE, T3DH_ID))
    return True


def stage_policy_replay():
    if not os.path.isdir(PR_SRC):
        log("KHONG thay %s (chua tai output policy-replay)" % PR_SRC)
        return False
    if os.path.isdir(PR_STAGE):
        shutil.rmtree(PR_STAGE)
    os.makedirs(PR_STAGE, exist_ok=True)
    for f in ("traj.jsonl", "shots.zip"):
        src = os.path.join(PR_SRC, f)
        if not os.path.exists(src):
            log("KHONG thay %s" % src)
            return False
        shutil.copy2(src, os.path.join(PR_STAGE, f))
    meta = {"title": PR_TITLE, "id": PR_ID, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(PR_STAGE, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        fh.write(json.dumps(meta, ensure_ascii=False, indent=1))
    log("staged policy-replay -> %s (id=%s)" % (PR_STAGE, PR_ID))
    return True


def simulate_loader(base, fname="traj.jsonl"):
    """Mo phong load_ds_rows cua kernel tren mot thu muc dataset da stage.

    Kernel: tim thu muc basename == slug, doc file .jsonl, unzip .zip vao ext,
    roi resolve tung dong 'image' theo: base/rel -> ext/rel -> basename trong ext.
    """
    import tempfile
    rows = []
    jf = os.path.join(base, fname)
    if not os.path.exists(jf):
        return None, "khong co %s" % fname
    with io.open(jf, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    ext = tempfile.mkdtemp(prefix="sim_ext_")
    for f in os.listdir(base):
        if f.endswith(".zip"):
            try:
                with zipfile.ZipFile(os.path.join(base, f)) as z:
                    z.extractall(ext)
            except Exception as e:
                return None, "unzip loi: %s" % e

    def resolve(rel):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
        p = os.path.join(ext, rel)
        if os.path.exists(p):
            return p
        name = os.path.basename(rel)
        for root, _d, files in os.walk(ext):
            if name in files:
                return os.path.join(root, name)
        return None

    ok = 0
    for r in rows:
        if resolve(r["image"]):
            ok += 1
    # kiem tra basename co bi trung giua cac thu muc con khong
    zmap = {}
    for root, _d, files in os.walk(ext):
        for f in files:
            if f.lower().endswith((".png", ".jpg")):
                zmap.setdefault(f, []).append(os.path.join(root, f))
    dups = {k: v for k, v in zmap.items() if len(v) > 1}
    shutil.rmtree(ext, ignore_errors=True)
    return (ok, len(rows)), dups


def verify(base, label):
    res, dups = simulate_loader(base)
    if res is None:
        log("VERIFY %s: FAIL (%s)" % (label, dups))
        return False
    ok, total = res
    log("VERIFY %s: %d/%d row resolve  |  basename trung: %d"
        % (label, ok, total, len(dups)))
    if dups:
        for k, v in list(dups.items())[:3]:
            log("   trung %s -> %s" % (k, v))
    return ok == total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()
    if a.stage:
        stage_train3d_hard()
        stage_policy_replay()
    ok1 = verify(T3DH_STAGE, "train3d-hard (staged)")
    ok2 = verify(PR_STAGE, "policy-replay (staged)")
    print()
    print("=== LENH KAGGLE (DeepSeek chay) ===")
    print("kaggle datasets create -p \"%s\"" % T3DH_STAGE)
    print("kaggle datasets version -p \"%s\" -m \"train3d-hard accA\"" % T3DH_STAGE)
    print("kaggle datasets version -p \"%s\" -m \"policy-replay + shots\"" % PR_STAGE)
    print()
    print("verify:", "OK" if (ok1 and ok2) else "CHECK")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
