"""r6 -> GGUF bang Unsloth (khong llama.cpp).
Merge PEFT -> Unsloth load full -> save_pretrained_gguf q4_k_m
-> upload repo PRIVATE. T4 online. TOKEN doc tu env/HKCU, khong hardcode."""
import gc
import glob
import os
import shutil
import subprocess

TMP = "/tmp/rel6"
MDIR = os.path.join(TMP, "merged")
GDIR = os.path.join(TMP, "ggufout")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
REPO = "himAgayem/gamecraft-r6-test"


def log(m):
    print(f"[r6gguf] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:100]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print((r.stdout or "")[-1200:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1200:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:80]}")


os.makedirs(MDIR, exist_ok=True)
os.makedirs(GDIR, exist_ok=True)
os.chdir("/tmp")  # unsloth ghi F16 trung gian o CWD -> can /tmp rong


def finddir(fname, extra=""):
    for root, _, files in os.walk("/kaggle/input"):
        if fname in files and extra in root:
            return root
    return None


wh = None
for root, _, files in os.walk("/kaggle/input"):
    if any("unsloth" in f and f.endswith(".whl") for f in files):
        wh = root
        break
assert wh, "thieu wheels"
sh(f"pip install --no-index --no-deps --find-links {wh} "
   f"unsloth unsloth_zoo trl bitsandbytes")
sh("pip uninstall -q -y torchao")  # tranh dispatch loi version peft/torchao
sh("pip install -q huggingface_hub")

import torch
basedirs = [os.path.dirname(p) for p in
            sum([[os.path.join(r, f) for f in fs
                  if f == "model.safetensors"]
                 for r, _, fs in os.walk("/kaggle/input")], [])]
ad = finddir("adapter_model.safetensors", "adapter-r6b")
log(f"base={basedirs} adapter={ad}")
assert basedirs and ad, "thieu input"

# 1. merge PEFT tren base FP16 FULL (khong 4-bit -> dequantize that).
# 24GB chia 2xT4 + offload CPU/disk.
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
model = AutoModelForCausalLM.from_pretrained(
    basedirs[0], torch_dtype=torch.float16, device_map="auto",
    max_memory={0: "14GiB", 1: "14GiB", "cpu": "60GiB"},
    offload_folder="/tmp/offload", low_cpu_mem_usage=True)
tok = AutoTokenizer.from_pretrained(basedirs[0])
model = PeftModel.from_pretrained(model, ad).merge_and_unload()
gc.collect()
torch.cuda.empty_cache()
model.save_pretrained(MDIR, safe_serialization=True)
tok.save_pretrained(MDIR)
# de tokenizer GOC (fix loi convert/unsloth)
for tf in glob.glob(os.path.join(basedirs[0], "tokenizer*")) + \
        glob.glob(os.path.join(basedirs[0], "*.jinja")):
    shutil.copy(tf, os.path.join(MDIR, os.path.basename(tf)))
# XOA quantization_config ke thua tu base 4-bit (khong la Unsloth
# tuong weights van 4-bit va tu choi export) + verify ~24GB fp16
import json as _json
_cfg = os.path.join(MDIR, "config.json")
_dc = _json.load(open(_cfg, encoding="utf-8"))
_dc.pop("quantization_config", None)
_json.dump(_dc, open(_cfg, "w", encoding="utf-8"), indent=2)
_sz = sum(os.path.getsize(os.path.join(MDIR, f)) for f in
          os.listdir(MDIR) if f.endswith(".safetensors"))
log(f"merged safetensors size={_sz // 2**30}G (can ~24G)")
assert _sz > 20 * 2**30, "weights chua dequantize dung!"
del model
gc.collect()
torch.cuda.empty_cache()
log("merge + save xong")

# 2. Unsloth load full + export GGUF
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MDIR, max_seq_length=1024, dtype=None,
    load_in_4bit=False, load_in_8bit=False, device_map="auto")
model.save_pretrained_gguf(GDIR, tokenizer,
                           quantization_method="q4_k_m")
ggufs = []
for root, _, files in os.walk("/tmp"):
    for f in files:
        if f.endswith(".gguf"):
            ggufs.append(os.path.join(root, f))
log(f"gguf files={ggufs}")
assert ggufs, "khong thay file gguf"
del model
gc.collect()
torch.cuda.empty_cache()

# 3. upload PRIVATE
from huggingface_hub import HfApi
api = HfApi()
api.create_repo(REPO, private=True, exist_ok=True, token=HF_TOKEN)
api.upload_file(path_or_fileobj=ggufs[0],
                path_in_repo=os.path.basename(ggufs[0]),
                repo_id=REPO, token=HF_TOKEN)
log(f"GGUF DONE (private): https://huggingface.co/{REPO}")
