"""Publish adapter run 1 (gemma12b-lora-r1) tu kernel output
thanh dataset rieng de phase sau attach.
Chay tren Kaggle CPU."""
import json
import os
import shutil
import subprocess

WORK = "/kaggle/working"
OUT = os.path.join(WORK, "adapter_r1")
OWNER = "khoadangnguye"
SLUG = "gemma12b-adapter-r1"


def log(m):
    print(f"[pubr1] {m}", flush=True)


def sh(cmd):
    log(f"+ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print((r.stdout or "")[-1500:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1500:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd}")
    if "dataset creation error" in (r.stdout or "").lower():
        raise SystemExit("DATASET-ERROR")


os.makedirs(OUT, exist_ok=True)
src = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "adapter_model.safetensors" in files and "run_info.json" in files:
        if "lora-r1" in root or "lora_r1" in root or "r1" in os.path.basename(root):
            src = root
            break
if not src:
    # liet ke de debug roi dung
    for root, dirs, files in os.walk("/kaggle/input"):
        log(f"thay: {root} files={len(files)}")
    raise SystemExit("khong tim thay adapter r1 trong kernel output")
log(f"nguon: {src}")
for f in os.listdir(src):
    shutil.copy(os.path.join(src, f), os.path.join(OUT, f))
log(f"copy xong: {sorted(os.listdir(OUT))}")
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "gemma12b adapter run1",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
try:
    sh(f"kaggle datasets create -p {OUT}")
except SystemExit:
    sh(f"kaggle datasets version -p {OUT} -m 'refresh r1' --dir-mode zip")
log(f"PUBLISHED: {OWNER}/{SLUG}")
