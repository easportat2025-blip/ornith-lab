"""So tensor 3 adapter: giong/khac nhau bao nhieu (giai thich diem y het)."""
import os
import subprocess


def log(m):
    print("[cmp] " + m, flush=True)


subprocess.run("pip install -q safetensors numpy", shell=True)
from safetensors import safe_open


def find(tag):
    for r, _, fs in os.walk("/kaggle/input"):
        if "adapter_model.safetensors" in fs and tag in r:
            return os.path.join(r, "adapter_model.safetensors")
    return None


paths = {}
for tag in ("adapter-o1", "adapter-loop1", "adapter-ab1"):
    p = find(tag)
    paths[tag] = p
    log(f"{tag} -> {p} "
        f"{os.path.getsize(p) / 2**20:.0f}MB" if p else f"{tag} MISSING")
assert all(paths.values()), "thieu adapter"


def load(p):
    d = {}
    with safe_open(p, framework="np") as f:
        for k in f.keys():
            d[k] = f.get_tensor(k)
    return d


import numpy as np
mods = {t: load(p) for t, p in paths.items()}
names = list(mods)
log(f"so tensor: {[(t, len(mods[t])) for t in names]}")
base_keys = set(mods[names[0]].keys())
for t in names[1:]:
    log(f"{t} keys giong o1: {set(mods[t].keys()) == base_keys}")
pairs = [("adapter-o1", "adapter-loop1"), ("adapter-o1", "adapter-ab1"),
         ("adapter-loop1", "adapter-ab1")]
for a, b in pairs:
    ma, mb = mods[a], mods[b]
    common = [k for k in ma if k in mb]
    log(f"{a} vs {b}: chung {len(common)} tensor")
    diffs = []
    for k in common[:40]:
        x, y = ma[k].astype("float64"), mb[k].astype("float64")
        if x.shape != y.shape:
            log(f"  {k}: SHAPE KHAC {x.shape} vs {y.shape}")
            continue
        md = float(np.abs(x - y).max())
        diffs.append(md)
    import statistics
    log(f"  max|diff| 40 tensor dau: max={max(diffs):.4f} "
        f"mean={statistics.mean(diffs):.4f} "
        f"~0 -> WEIGHTS GIONG NHAU" if max(diffs) < 1e-6
        else f"  -> WEIGHTS KHAC NHAU (max diff {max(diffs):.4f})")
log("CMP DONE")
