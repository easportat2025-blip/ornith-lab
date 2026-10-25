"""dryrun_v22_data.py - kiem tra data mix cua v22 OFFLINE (mo phong load_ds_rows
cua kernel tren Kaggle: dataset base + zip duoc giai nen vao ext).

Kiem: dataset nao resolve duoc anh, bao nhieu row, va co row "hong co anh" khong.
"""
import io
import json
import os
import zipfile

CASES = [
    ("selfplay", "phase13-gui/selfplay_dataset", "traj.jsonl", "shots.zip"),
    ("train3d", "phase14-blender/train3d_dataset", "traj.jsonl", "shots.zip"),
    ("train3d-hard", "phase14-blender/train3d_hard_dataset", "traj.jsonl",
     "shots.zip"),
    ("train3d-bench", "phase14-blender/bench3d_dataset", "bench3d.jsonl",
     "shots.zip"),
]


def resolve(rel, base, ext):
    p = os.path.join(base, rel)
    if os.path.exists(p):
        return p
    cand = os.path.join(ext, rel)
    if os.path.exists(cand):
        return cand
    name = os.path.basename(rel)
    for root, _dirs, files in os.walk(ext):
        if name in files:
            return os.path.join(root, name)
    for root, _dirs, files in os.walk(base):
        if name in files:
            return os.path.join(root, name)
    return None


def kaggle_layout(base):
    """Mo phong Kaggle: file zip bi STRIP, noi dung giai nen vao <base>/<ten-zip>/."""
    ext = os.path.join(base, "_ext")
    os.makedirs(ext, exist_ok=True)
    for f in os.listdir(base):
        if f.endswith(".zip"):
            with zipfile.ZipFile(os.path.join(base, f)) as z:
                z.extractall(os.path.join(ext, f[:-4]))
    return ext


total = 0
for name, base, jf, zf in CASES:
    if not os.path.isdir(base):
        print("%-14s THIEU thu muc %s" % (name, base))
        continue
    rows = [json.loads(l) for l in
            io.open(os.path.join(base, jf), encoding='utf-8') if l.strip()]
    ext = kaggle_layout(base)
    ok = sum(1 for r in rows if resolve(r["image"], base, ext))
    # kiem tra theo loai action
    kinds = {}
    for r in rows:
        a = (r.get("action") or "").split(" ")[0]
        kinds[a] = kinds.get(a, 0) + 1
    print("%-14s %4d row | resolve %4d/%4d | action: %s"
          % (name, len(rows), ok, len(rows), kinds))
    assert ok == len(rows), "%s: %d anh khong resolve" % (name, len(rows) - ok)
    total += len(rows)
print("TONG data (tu phan kiem):", total)
print("DRYRUN DATA OK")
