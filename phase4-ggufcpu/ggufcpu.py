"""GGUF tren CPU: tai BF16 tu HF ve /tmp -> convert -> quant Q4_K_M
-> upload. Khong can GPU/merge. TOKEN doc tu env/HKCU, khong hardcode."""
import os
import shutil
import subprocess

TMP = "/tmp/gg"
BASE = os.path.join(TMP, "base")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
REPO = "himAgayem/gemma-4-12b-gamecraft-r4"
GGUF_NAME = "gemma-4-12b-gamecraft-r4-q4_k_m.gguf"


def log(m):
    print(f"[ggc] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:110]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print((r.stdout or "")[-1200:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1200:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:70]}")


os.makedirs(BASE, exist_ok=True)
t, u, f = shutil.disk_usage("/tmp")
log(f"tmp free={f//2**30}G")
sh("pip install -q huggingface_hub transformers safetensors gguf "
   "sentencepiece protobuf")

from huggingface_hub import HfApi, snapshot_download
api = HfApi(token=HF_TOKEN)
snapshot_download(REPO, local_dir=BASE, token=HF_TOKEN,
                  allow_patterns=["*.safetensors", "*.json",
                                  "*.jinja", "*.model", "README.md"])
log("tai BF16 xong")

# tokenizer smoke test truoc khi convert
import json
cfg = json.load(open(os.path.join(BASE, "tokenizer_config.json")))
log(f"extra_special_tokens={cfg.get('extra_special_tokens', 'KHONG CO')}")
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(BASE, trust_remote_code=False)
log(f"tokenizer load OK: {type(tok).__name__}")

sh("git clone --depth 1 https://github.com/ggerganov/llama.cpp /tmp/llama.cpp",
   timeout=1200)
sh("cmake -S /tmp/llama.cpp -B /tmp/llama.cpp/build "
   "-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DLLAMA_CURL=OFF",
   timeout=1800)
sh("cmake --build /tmp/llama.cpp/build --target llama-quantize -j4",
   timeout=3600)
log("build xong")
sh(f"python /tmp/llama.cpp/convert_hf_to_gguf.py {BASE} "
   f"--outfile {TMP}/f16.gguf --outtype f16", timeout=3600)
log("convert xong")
sh(f"/tmp/llama.cpp/build/bin/llama-quantize {TMP}/f16.gguf "
   f"{TMP}/{GGUF_NAME} Q4_K_M", timeout=3600)
log("quant xong")
os.remove(os.path.join(TMP, "f16.gguf"))
api.upload_file(path_or_fileobj=os.path.join(TMP, GGUF_NAME),
                path_in_repo=f"gguf/{GGUF_NAME}",
                repo_id=REPO, token=HF_TOKEN)
log(f"GGUF DONE: https://huggingface.co/{REPO}/blob/main/gguf/{GGUF_NAME}")
