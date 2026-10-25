"""Chia base Ornith 19GB thanh 4 dataset ~5GB (RTX chi mount duoc nho).

PRIVATE KERNEL - chua key acc B. XOA kernel + ROTATE key sau khi xong.
Buoc: HF download base -> /tmp -> copy tung shard + file nho -> datasets create.
"""
import json
import os
import shutil
import subprocess
import time

# CRED (private kernel, xoa + rotate sau)
os.environ["KAGGLE_USERNAME"] = "dieniw"
os.environ["KAGGLE_KEY"] = "5d786fc357fb840ab273b159aca88038"


def log(m):
    print("[split] " + m, flush=True)


def sh(cmd, timeout=5400):
    print("$ " + cmd[:100], flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    tail = (r.stdout or "")[-300:]
    if tail:
        print(tail, flush=True)
    if r.returncode != 0:
        print("LOI rc=" + str(r.returncode) + ": "
              + (r.stderr or "")[-500:], flush=True)
        return False
    return True


sh("pip install -q kaggle huggingface_hub")
from huggingface_hub import snapshot_download

SRC = "/tmp/ornbase"
for attempt in range(3):
    try:
        snapshot_download("ornith-ai/Ornith-1.5-9B", local_dir=SRC,
                          allow_patterns=["*.safetensors", "*.json",
                                          "*.jinja", "*.model", "LICENSE*"],
                          max_workers=4)
        break
    except Exception as e:
        log(f"tai lan {attempt + 1} loi: {e}")
        time.sleep(60)

shards = sorted(f for f in os.listdir(SRC)
                if f.startswith("model-") and f.endswith(".safetensors"))
assert len(shards) == 4, f"shards={shards}"
small = [f for f in os.listdir(SRC)
         if f.endswith((".json", ".jinja", ".model"))
         or f.startswith("LICENSE")]
log(f"shards={shards} small={small}")

for k, shname in enumerate(shards, start=1):
    d = f"/tmp/s{k}"
    os.makedirs(d, exist_ok=True)
    log(f"s{k}: copy {shname} ...")
    shutil.copy(os.path.join(SRC, shname), os.path.join(d, shname))
    if k == 1:
        for f in small:
            shutil.copy(os.path.join(SRC, f), os.path.join(d, f))
    meta = {"id": f"dieniw/ornbase-s{k}", "title": f"ornbase-s{k}",
            "licenses": [{"name": "CC0-1.0"}]}
    open(os.path.join(d, "dataset-metadata.json"), "w").write(
        json.dumps(meta))
    ok = False
    for att in range(3):
        if sh(f"kaggle datasets create -p {d} -u", timeout=5400):
            ok = True
            break
        log(f"s{k} upload lan {att + 1} that bai, thu lai")
        time.sleep(30)
    log(f"s{k}: {'OK' if ok else 'THAT BAI SAU 3 LAN'}")
    shutil.rmtree(d, ignore_errors=True)  # don /tmp ngay

log("SPLIT DONE")
