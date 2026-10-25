"""Tai Ornith-1.5-9B safetensors tu HF ve /tmp, publish dataset.
De train run O1+. CPU, internet ON."""
import json
import os
import shutil
import subprocess

TMP = "/tmp/orn"
OUT = os.path.join(TMP, "base")
OWNER = "khoadangnguye"
SLUG = "ornith-15-9b-base"
REPO = "ornith-ai/Ornith-1.5-9B"


def log(m):
    print(f"[ornbase] {m}", flush=True)


def sh(cmd, timeout=7200):
    log(f"+ {cmd[:100]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print((r.stdout or "")[-1000:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1000:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:60]}")


os.makedirs(OUT, exist_ok=True)
sh("pip install -q huggingface_hub")
from huggingface_hub import snapshot_download
snapshot_download(REPO, local_dir=OUT,
                  allow_patterns=["*.safetensors", "*.json", "*.jinja",
                                  "*.model", "LICENSE*"],
                  max_workers=4)
names = sorted(os.listdir(OUT))
log(f"files={names}")
import glob
sfs = glob.glob(os.path.join(OUT, "*.safetensors"))
tot = sum(os.path.getsize(p) for p in sfs)
log(f"safetensors {len(sfs)} files, tong {tot // 2**30}G")
assert tot > 15 * 2**30, "thieu weights!"
cfg = json.load(open(os.path.join(OUT, "config.json"), encoding="utf-8"))
log("co vision_config=" + str("vision_config" in cfg))
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "ornith 15 9b base for sft",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
sh(f"kaggle datasets create -p {OUT}")
try:
    out = sh(f"kaggle datasets files {OWNER}/{SLUG}")
    if "safetensors" not in out:
        log("WARN: files chua san sang (dang processing)")
except SystemExit:
    log("WARN: verify loi (co the processing), kiem tra ngoai sau")
log(f"PUBLISHED?: {OWNER}/{SLUG}")
