"""Tai r6 adapter tu train output, publish slug MOI sach (r6b).
CPU, RAM 30GB."""
import json
import os
import shutil
import subprocess

WORK = "/kaggle/working"
PREV = os.path.join(WORK, "prev")
OUT = os.path.join(WORK, "adapter_r6b")
OWNER = "khoadangnguye"
SLUG = "gemma12b-adapter-r6b"


def log(m):
    print(f"[pubr6b] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:100]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print("STDOUT:" + (r.stdout or "")[-1500:], flush=True)
    print("STDERR:" + (r.stderr or "")[-800:], flush=True)
    if r.returncode != 0:
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:60]}")
    if "dataset creation error" in (r.stdout or "").lower():
        raise SystemExit("DATASET-ERROR")
    return r.stdout or ""


os.makedirs(PREV, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
sh("kaggle kernels output khoadangnguye/gemma12b-phase2-lora "
   f"-p {PREV} --file-pattern \"lora-r6\"")
src = None
for root, _, files in os.walk(PREV):
    if "adapter_model.safetensors" in files and "lora-r6" in root:
        sz = os.path.getsize(os.path.join(root, "adapter_model.safetensors"))
        log(f"thay {root} adapter {sz} bytes")
        if sz > 10**9:
            src = root
            break
if not src:
    raise SystemExit("khong tim thay adapter r6 day du (>1GB)")
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), os.path.join(OUT, f))
log(f"copy xong: {sorted(os.listdir(OUT))}")
shutil.rmtree(PREV, ignore_errors=True)
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "gemma12b adapter run6 b",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
sh(f"kaggle datasets create -p {OUT}")
out = sh(f"kaggle datasets files {OWNER}/{SLUG}")
if "safetensors" not in out:
    log("WARN: files chua san sang, kiem tra lai sau")
log(f"PUBLISHED: {OWNER}/{SLUG}")
