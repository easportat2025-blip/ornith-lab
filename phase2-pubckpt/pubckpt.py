"""Tai output train, giu lai checkpoint-1000 (ban tot, truoc khi NaN),
publish dataset gemma12b-adapter-r4. CPU."""
import json
import os
import shutil
import subprocess

WORK = "/kaggle/working"
PREV = os.path.join(WORK, "prev")
OUT = os.path.join(WORK, "adapter_r4")
OWNER = "khoadangnguye"
SLUG = "gemma12b-adapter-r4"


def log(m):
    print(f"[pubckpt] {m}", flush=True)


def sh(cmd):
    log(f"+ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print("STDOUT:" + (r.stdout or "")[-1500:], flush=True)
    print("STDERR:" + (r.stderr or "")[-800:], flush=True)
    if r.returncode != 0:
        raise SystemExit(f"FAILED({r.returncode}): {cmd}")
    if "dataset creation error" in (r.stdout or "").lower():
        raise SystemExit("DATASET-ERROR")
    return r.stdout or ""


os.makedirs(PREV, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
t, u, f = shutil.disk_usage(WORK)
log(f"disk free={f//2**30}G")
sh("kaggle kernels output khoadangnguye/gemma12b-phase2-lora "
   f"-p {PREV} --file-pattern \"adapter_model|adapter_config|run_info\"")
src = None
for root, _, files in os.walk(PREV):
    if "adapter_model.safetensors" in files and "checkpoint-1000" in root:
        src = root
        break
if not src:
    for root, _, files in os.walk(PREV):
        log(f"thay: {root} n={len(files)}")
    raise SystemExit("khong tim thay checkpoint-1000")
log(f"nguon: {src}")
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), os.path.join(OUT, f))
log(f"copy xong: {sorted(os.listdir(OUT))}")
shutil.rmtree(PREV, ignore_errors=True)
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "gemma12b adapter run4 ckpt1000",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
try:
    sh(f"kaggle datasets create -p {OUT}")
except SystemExit:
    sh(f"kaggle datasets version -p {OUT} -m 'refresh' --dir-mode zip")
out = sh(f"kaggle datasets files {OWNER}/{SLUG}")
if "safetensors" not in out:
    log("WARN: files chua san sang (dang processing), kiem tra lai sau")
log(f"PUBLISHED: {OWNER}/{SLUG}")
