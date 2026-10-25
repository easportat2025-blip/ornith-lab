"""Public toan bo dataset acc A (isPrivate=false)."""
import json
import os
import shutil
import subprocess

USER = "khoadangnguye"
BASE = r"C:\Users\Admin\Desktop\New folder\data\pubmeta"
REFS = [
    "gemma12b-gamedata", "gemma12b-tools", "gemma12b-wheels",
    "viable-wheels-vllm-full", "gemma12b-adapter-r1", "checkpoinr6",
    "sft18-adapter", "viable-pkg-model", "sft18-gpu", "sft18-tpu",
    "viable-wheels-vllm121", "viable-wheels-vllm12", "viable-rl-mega-offline",
    "viable-bench-data", "evalplus-offline",
    "khoadangnguyeviable-rl-step200-ckpt", "arc-agi-1-eval", "saraz-bundle",
    "evo-ai-src", "gemma12b-gamedata-r6", "gemma12b-adapter-aux7k",
    "gemma12b-adapter-main8k", "gemma12b-probe-tiny", "gemma12b-gamedata-r5",
    "gemma12b-llamatools", "gemma12b-adapter-r4", "gemma12b-gamedata-r4",
    "gemma12b-adapter-r3",
]


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r


os.makedirs(BASE, exist_ok=True)
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
ok, fail = [], []
for slug in REFS:
    ref = f"{USER}/{slug}"
    d = os.path.join(BASE, slug)
    os.makedirs(d, exist_ok=True)
    try:
        api.dataset_metadata(ref, d)
        mf = os.path.join(d, "dataset-metadata.json")
        meta = json.load(open(mf, encoding="utf-8"))
        info = meta.get("info") or meta
        info["isPrivate"] = False
        if "info" in meta:
            meta["info"] = info
        else:
            meta = info
        json.dump(meta, open(mf, "w", encoding="utf-8"), indent=2)
        api.dataset_metadata_update(ref, d)
        ok.append(slug)
        print(f"PUBLIC OK: {slug}", flush=True)
    except Exception as e:
        fail.append((slug, f"{type(e).__name__}: {e}"))
        print(f"FAIL {slug}: {e}", flush=True)
print(f"\nXONG: ok={len(ok)} fail={len(fail)}")
for s, e in fail:
    print(f"  - {s}: {e}")
shutil.rmtree(BASE, ignore_errors=True)
