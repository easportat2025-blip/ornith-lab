"""Export GGUF Q4_K_M bang Unsloth tren T4 (khong dung llama.cpp).
Tai merged BF16 tu HF repo -> load 4bit -> export gguf -> upload.
TOKEN doc tu env/HKCU, khong hardcode."""
import os
import subprocess

WORK = "/kaggle/working"
GGUF_DIR = "/tmp/gguf"  # /kaggle/working chi 19GB, unsloth can ~46GB
HF_TOKEN = os.environ.get("HF_TOKEN", "")
REPO = "himAgayem/gemma-4-12b-gamecraft-r4"
GGUF_NAME = "gemma-4-12b-gamecraft-r4-q4_k_m.gguf"


def log(m):
    print(f"[gguf] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:100]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print((r.stdout or "")[-1200:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1200:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:80]}")


os.makedirs(GGUF_DIR, exist_ok=True)
os.chdir("/tmp")  # unsloth ghi file trung gian o CWD -> can /tmp rong


def find_wheels():
    for root, _, files in os.walk("/kaggle/input"):
        if any("unsloth" in f and f.endswith(".whl") for f in files):
            return root
    return None


wheels = find_wheels()
log(f"wheels={wheels}")
if wheels:
    sh(f"pip install --no-index --no-deps --find-links {wheels} "
       f"unsloth unsloth_zoo trl bitsandbytes")
sh("pip install -q huggingface_hub")

import torch
log(f"cuda={torch.cuda.is_available()} "
    f"gpus={torch.cuda.device_count()}")
from unsloth import FastLanguageModel
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=REPO, max_seq_length=1024, dtype=None,
    load_in_4bit=False, load_in_8bit=False,  # full precision de export
    device_map="auto")  # chẻ 2xT4 (24GB > 16GB 1 card)
log("load xong tu HF")
model.save_pretrained_gguf(GGUF_DIR, tokenizer,
                           quantization_method="q4_k_m")
log(f"export xong: {sorted(os.listdir(GGUF_DIR))}")

from huggingface_hub import HfApi
api = HfApi()
gguf_files = []
for root, _, files in os.walk("/tmp"):
    for f in files:
        if f.endswith(".gguf"):
            gguf_files.append(os.path.join(root, f))
log(f"tim thay gguf: {gguf_files}")
assert gguf_files, "khong thay file gguf"
gguf_path = gguf_files[0]
api.upload_file(path_or_fileobj=gguf_path,
                path_in_repo=f"gguf/{os.path.basename(gguf_path)}",
                repo_id=REPO, token=HF_TOKEN)
log(f"GGUF DONE: https://huggingface.co/{REPO}/blob/main/gguf/"
    f"{os.path.basename(gguf_path)}")
