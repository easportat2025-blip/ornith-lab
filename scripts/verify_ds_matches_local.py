"""verify_ds_matches_local.py - so hash TUNG file giua dataset tren Kaggle va
thu muc local (phat hien dataset stale/mot phan).

Dung: python scripts/verify_ds_matches_local.py <slug> <local_dir> <top_dir>
VD:  python scripts/verify_ds_matches_local.py khoadangnguye/ornith-gui-bench-v155 phase13-gui/bench_v15/tasks_v15_5 bench_v155
"""
import hashlib
import io
import os
import subprocess
import sys
import zipfile

slug = sys.argv[1]
local_dir = sys.argv[2]
top = sys.argv[3] if len(sys.argv) > 3 else ""

acc = "B" if slug.startswith("dieniw/") else "A"
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kaggle_keys import kaggle_env  # key lay tu HKCU\Environment, khong hardcode
user, key = kaggle_env(acc)
if not key:
    sys.exit("thieu key env KAGGLE_KEY_%s (doc HKCU\\Environment)" % acc)
env = dict(os.environ)
env["KAGGLE_USERNAME"] = user
env["KAGGLE_KEY"] = key
env["PYTHONUTF8"] = "1"

d = os.path.join(os.environ.get("TEMP", "."), "dsmatch")
os.makedirs(d, exist_ok=True)
p = subprocess.run(["kaggle", "datasets", "download", slug, "-p", d, "--force"],
                   capture_output=True, env=env, timeout=900)
zs = [f for f in os.listdir(d) if f.endswith(".zip")]
if not zs:
    print("tai that bai:", (p.stdout or b"")[-200:], (p.stderr or b"")[-200:])
    sys.exit(1)
z = zipfile.ZipFile(os.path.join(d, zs[0]))


def h(b):
    return hashlib.sha1(b).hexdigest()[:12]


same = diff = missing = 0
diffs = []
for n in z.namelist():
    rel = n.split(top + "/", 1)[1] if top and n.startswith(top + "/") else n
    lp = os.path.join(local_dir, rel.replace("/", os.sep))
    if not os.path.exists(lp):
        missing += 1
        diffs.append("THIEU LOCAL: " + rel)
        continue
    a = h(z.read(n))
    b = h(io.open(lp, "rb").read())
    if a == b:
        same += 1
    else:
        diff += 1
        diffs.append("KHAC: %s (ds=%s local=%s)" % (rel, a, b))
print("%-46s -> giong %d, khac %d, thieu %d" % (slug, same, diff, missing))
for x in diffs[:20]:
    print("   ", x)
if not diffs:
    print("   -> dataset TRUNG VOI LOCAL 100%")
