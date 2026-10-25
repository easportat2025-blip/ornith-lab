"""Lay loop_soup tu output loop Ornith, publish dataset.
CPU."""
import json
import os
import shutil
import subprocess

WORK = "/kaggle/working"
OUT = os.path.join(WORK, "soupo1")
OWNER = "dieniw"
SLUG = "ornith-adapter-o1"


def log(m):
    print(f"[pubsoup] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:100]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print("STDOUT:" + (r.stdout or "")[-1200:], flush=True)
    print("STDERR:" + (r.stderr or "")[-800:], flush=True)
    if r.returncode != 0:
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:60]}")
    if "dataset creation error" in (r.stdout or "").lower():
        raise SystemExit("DATASET-ERROR")
    return r.stdout or ""


os.makedirs(OUT, exist_ok=True)
src = None
for root, _, files in os.walk("/kaggle/input"):
    if "adapter_model.safetensors" in files and "loop_soup" in root:
        sz = os.path.getsize(os.path.join(root, "adapter_model.safetensors"))
        log(f"thay {root} {sz // 2**20}MB")
        if sz > 10**8:
            src = root
            break
if not src:
    raise SystemExit("khong thay soup day du")
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), os.path.join(OUT, f))
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "ornith adapter o1 loop soup",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
sh(f"kaggle datasets create -p {OUT}")
out = sh(f"kaggle datasets files {OWNER}/{SLUG}")
if "safetensors" not in out:
    log("WARN: files chua san sang, kiem tra lai sau")
log(f"PUBLISHED: {OWNER}/{SLUG}")
