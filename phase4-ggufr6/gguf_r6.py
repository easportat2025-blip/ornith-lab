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
sh("pip install -q huggingface_hub")

import torch
basedirs = [os.path.dirname(p) for p in
            sum([[os.path.join(r, f) for f in fs
                  if f == "model.safetensors"]
                 for r, _, fs in os.walk("/kaggle/input")], [])]
ad = finddir("adapter_model.safetensors", "adapter-r6")
log(f"base={basedirs} adapter={ad}")
assert basedirs and ad, "thieu input"

# 1. merge PEFT (fp16, offload CPU neu can)
from transformers import AutoModelForCausalLM, AutoTokenizer, \
    BitsAndBytesConfig
from peft import PeftModel
bnb = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True)
base_q = AutoModelForCausalLM.from_pretrained(
    basedirs[0], quantization_config=bnb, device_map="auto")
tok = AutoTokenizer.from_pretrained(basedirs[0])
model = PeftModel.from_pretrained(base_q, ad).merge_and_unload()
del base_q
gc.collect()
torch.cuda.empty_cache()
model.save_pretrained(MDIR, safe_serialization=True)
tok.save_pretrained(MDIR)
# de tokenizer GOC (fix loi convert/unsloth)
for tf in glob.glob(os.path.join(basedirs[0], "tokenizer*")) + \
        glob.glob(os.path.join(basedirs[0], "*.jinja")):
    shutil.copy(tf, os.path.join(MDIR, os.path.basename(tf)))
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
