"""Soup: trung binh weights 2 adapters (main8k + aux7k, cung r128).
CPU 30GB RAM du suc. Output soup50."""
import json
import os
import shutil

WORK = "/kaggle/working"
OUT = os.path.join(WORK, "soup50")
RATIO_MAIN = 0.5


def log(m):
    print(f"[soup] {m}", flush=True)


def find_adapter(tag):
    for root, _, files in os.walk("/kaggle/input"):
        if "adapter_model.safetensors" in files and tag in root:
            return os.path.join(root, "adapter_model.safetensors"), root
    return None, None


os.makedirs(OUT, exist_ok=True)
fa_path, fa_dir = find_adapter("main8k")
fb_path, fb_dir = find_adapter("aux7k")
log(f"A={fa_path}")
log(f"B={fb_path}")
assert fa_path and fb_path, "thieu adapter input"

import torch
from safetensors.torch import load_file, save_file

ta = load_file(fa_path, device="cpu")
tb = load_file(fb_path, device="cpu")
assert set(ta.keys()) == set(tb.keys()), "keys khac nhau"
log(f"tensors={len(ta)}")
out = {k: (ta[k].float() * RATIO_MAIN +
           tb[k].float() * (1 - RATIO_MAIN)).to(ta[k].dtype)
       for k in ta}
n_tensors = len(out)
save_file(out, os.path.join(OUT, "adapter_model.safetensors"))
del ta, tb, out
shutil.copy(os.path.join(fa_dir, "adapter_config.json"),
            os.path.join(OUT, "adapter_config.json"))
json.dump({"a": "main-ckpt8000", "b": "aux-ckpt7000",
           "ratio_a": RATIO_MAIN, "n_tensors": n_tensors},
          open(os.path.join(OUT, "soup_info.json"), "w"), indent=2)
log("SOUP DONE")
