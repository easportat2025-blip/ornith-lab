#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
colab_stage.py - STAGE (cache) tai nguyen len Google Drive trong Colab VM
de cac lan sau khong phai tai lai 18GB.

Chay trong Colab:
    colab new -s orn-stage --gpu T4
    colab drivemount -s orn-stage
    colab exec -s orn-stage -f scripts/colab_stage.py

Cache:
    /content/drive/ornith-cache/base/     <- model base (4 shard ~18GB)
    /content/drive/ornith-cache/wheels/   <- wheels (unsloth/trl/peft...)
    /content/drive/ornith-cache/data/     <- dataset zips (jsonl + anh)

ASCII-only source.
"""
import os
import subprocess
import sys
import time

CACHE = "/content/drive/ornith-cache"
BASE_ID = os.environ.get("ORNITH_BASE_ID", "ornith-ai/Ornith-1.5-9B")
T0 = time.time()


def log(m):
    print("[stage] %s (t=%.0fs)" % (m, time.time() - T0), flush=True)


def sh(cmd, timeout=7200):
    log("run: %s" % cmd[:110])
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    out = ((p.stdout or "") + (p.stderr or ""))[-400:]
    log("rc=%s %s" % (p.returncode, out.replace("\n", " ")[:200]))
    return p.returncode == 0


def main():
    if not os.path.isdir("/content/drive"):
        log("!! chua mount Drive -> chay 'colab drivemount -s <session>' truoc")
        return 1
    for sub in ("base", "wheels", "data"):
        os.makedirs(os.path.join(CACHE, sub), exist_ok=True)
    log("cache dir: %s" % CACHE)

    # 1) model base tu HF (public -> khong can token)
    base_dir = os.path.join(CACHE, "base")
    need = not any(f.endswith(".safetensors") for f in os.listdir(base_dir))
    if need:
        log("tai model base %s (~18GB, can 10-25 phut)..." % BASE_ID)
        sh("pip install -q -U 'huggingface_hub[hf_transfer]'")
        sh("HF_HUB_ENABLE_HF_TRANSFER=1 python -c \""
           "from huggingface_hub import snapshot_download;"
           "snapshot_download(repo_id='%s', local_dir='%s',"
           " max_workers=4, ignore_patterns=['*.pth','original/*','*.gguf'])\""
           % (BASE_ID, base_dir), timeout=7200)
    else:
        log("model base da co trong cache")
    try:
        fs = sorted(os.listdir(base_dir))
        log("base files (%d): %s" % (len(fs), ", ".join(fs[:10])))
    except Exception as e:
        log("doc base loi: %s" % e)

    # 2) wheels: unsloth + trl + peft (cho GRPO)
    wdir = os.path.join(CACHE, "wheels")
    if not os.listdir(wdir):
        log("tai wheels (unsloth/trl/peft/datasets/accelerate/bitsandbytes)...")
        sh("mkdir -p %s && cd %s && pip download -q --dest . "
           "unsloth unsloth_zoo trl peft datasets accelerate bitsandbytes "
           "transformers pillow qwen-vl-utils" % wdir, timeout=5400)
    log("wheels: %d file" % len(os.listdir(wdir)))

    # 3) bao cao
    log("HOAN TAT - dung /content/drive/ornith-cache o cac lan sau")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
