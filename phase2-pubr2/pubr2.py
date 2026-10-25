"""Tai output kernel train qua download API (khong mount),
giu lai dung thu muc gemma12b-lora-r2, publish dataset.
Chay CPU, offline (khong can internet)."""
import json
import os
import shutil
import subprocess

WORK = "/kaggle/working"
PREV = os.path.join(WORK, "prev")
OUT = os.path.join(WORK, "adapter_r2")
OWNER = "khoadangnguye"
SLUG = "gemma12b-adapter-r2"


def log(m):
    print(f"[pubr2] {m}", flush=True)


def sh(cmd):
    log(f"+ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1500:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd}")
    if "dataset creation error" in (r.stdout or "").lower():
        raise SystemExit("DATASET-ERROR")


os.makedirs(PREV, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
t, u, f = shutil.disk_usage(WORK)
log(f"disk free={f//2**30}G")
sh("kaggle kernels output khoadangnguye/gemma12b-phase2-lora "
   f"-p {PREV} --file-pattern "
   "\"adapter_model|adapter_config|run_info|tokenizer|chat_template|"
   "generation_config|processor_config\"")
src = None
for root, _, files in os.walk(PREV):
    if "adapter_model.safetensors" in files and "lora-r2" in root:
        src = root
        break
if not src:
    for root, _, files in os.walk(PREV):
        log(f"thay: {root} n={len(files)}")
    raise SystemExit("khong tim thay lora-r2")
log(f"nguon: {src}")
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), os.path.join(OUT, f))
log(f"copy xong: {sorted(os.listdir(OUT))}")
shutil.rmtree(PREV, ignore_errors=True)
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "gemma12b adapter run2",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
try:
    sh(f"kaggle datasets create -p {OUT}")
except SystemExit:
    sh(f"kaggle datasets version -p {OUT} -m 'refresh r2' --dir-mode zip")
log(f"PUBLISHED: {OWNER}/{SLUG}")
