"""Release r4: merge adapter vao base (CPU, bf16) -> save BF16 safetensors
-> upload HF public -> convert GGUF F16 -> quant Q4_K_M -> upload.
Stage het o /tmp (overlay rong), khong dung /kaggle/working.
TOKEN doc tu env/HKCU, khong hardcode.
"""
import gc
import glob
import json
import os
import shutil
import subprocess

TMP = "/tmp/rel"
BF16_DIR = os.path.join(TMP, "bf16")
GGUF_DIR = os.path.join(TMP, "gguf")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
REPO = "himAgayem/gemma-4-12b-gamecraft-r4"


def log(m):
    print(f"[rel] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:120]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print((r.stdout or "")[-1200:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-1200:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:80]}")


def find(fname, extra=""):
    for root, _, files in os.walk("/kaggle/input"):
        if fname in files and extra in root:
            return os.path.join(root, fname)
    return None


def finddir(fname, extra=""):
    p = find(fname, extra)
    return os.path.dirname(p) if p else None


os.makedirs(BF16_DIR, exist_ok=True)
os.makedirs(GGUF_DIR, exist_ok=True)
sh("pip install -q huggingface_hub gguf peft safetensors")
sh("pip uninstall -q -y torchao")  # tranh dispatch loi version peft/torchao

import torch
log(f"torch={torch.__version__} cuda={torch.cuda.is_available()}")
t, u, f = shutil.disk_usage("/tmp")
log(f"tmp free={f//2**30}G")

# 1. tim input
basedirs = [os.path.dirname(p) for p in
            sum([[os.path.join(r, f) for f in fs
                  if f == "model.safetensors"]
                 for r, _, fs in os.walk("/kaggle/input")], [])]
ad = finddir("adapter_model.safetensors", "adapter-r4")
log(f"base={basedirs} adapter={ad}")
assert basedirs and ad, "thieu input"

# 2. merge bf16 tren CPU
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained(
    basedirs[0], torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True, device_map="cpu", trust_remote_code=False)
tok = AutoTokenizer.from_pretrained(basedirs[0])
from peft import PeftModel
model = PeftModel.from_pretrained(model, ad)
model = model.merge_and_unload()
model.eval()
log("merge xong")
del ad
gc.collect()

# 3. save bf16 sharded + README + license note
model.save_pretrained(BF16_DIR, max_shard_size="4GB", safe_serialization=True)
tok.save_pretrained(BF16_DIR)
# Ghi de tokenizer GOC (file tu save lai loi format lam hong convert)
for _tf in glob.glob(os.path.join(basedirs[0], "tokenizer*")) + \
        glob.glob(os.path.join(basedirs[0], "*.jinja")):
    shutil.copy(_tf, os.path.join(BF16_DIR, os.path.basename(_tf)))
log("ghi de tokenizer goc xong")
readme = ("---\nlicense: apache-2.0\nbase_model: google/gemma-4-12b-it\n"
          "tags: [game-dev, blender, unity, code-generation, gemma]\n---\n"
          "# Gemma 4 12B GameCraft r4\n\n"
          "Fine-tune of `google/gemma-4-12b-it` for game code (Pygame/Unity) "
          "and Blender bpy 3D generation, trained with QLoRA on Kaggle.\n\n"
          "Own bench (60 tasks, greedy): base 97 -> **r4 136** "
          "(game 32, unity 57, bpy 47).\n\n"
          "## Files\n- BF16 safetensors here (full precision, fine-tune tiep).\n"
          "- `gguf/` : Q4_K_M quant for Ollama/LM Studio local use.\n\n"
          "## License\nApache 2.0 (ke thua tu Gemma 4). Thuong mai OK.\n")
open(os.path.join(BF16_DIR, "README.md"), "w").write(readme)
log("save bf16 xong")

# 4. upload BF16 public TRUOC (an toan: convert hong cung khong mat)
from huggingface_hub import HfApi
api = HfApi()
api.create_repo(REPO, private=False, exist_ok=True, token=HF_TOKEN)
existing = set(api.list_repo_files(REPO, token=HF_TOKEN))
if any(f.endswith(".safetensors") for f in existing):
    log("BF16 da co tren HF -> bo qua upload")
else:
    api.upload_folder(folder_path=BF16_DIR, repo_id=REPO, token=HF_TOKEN)
    log("upload BF16 xong")
# Luon day lai tokenizer goc (fix file save loi truoc do)
for _tf in glob.glob(os.path.join(BF16_DIR, "tokenizer*")) + \
        glob.glob(os.path.join(BF16_DIR, "*.jinja")):
    api.upload_file(path_or_fileobj=_tf,
                    path_in_repo=os.path.basename(_tf),
                    repo_id=REPO, token=HF_TOKEN)
log("day tokenizer goc xong")

# 3b. build llama.cpp quantize (doc lap, can truoc khi quant)
sh("git clone --depth 1 https://github.com/ggerganov/llama.cpp /tmp/llama.cpp",
   timeout=1200)
sh("cmake -S /tmp/llama.cpp -B /tmp/llama.cpp/build "
   "-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DLLAMA_CURL=OFF",
   timeout=1800)
sh("cmake --build /tmp/llama.cpp/build --target llama-quantize -j4", timeout=3600)
log("build quantize xong")
sh("pip install -q -r /tmp/llama.cpp/requirements.txt")
# convert BF16 -> F16 GGUF (can BF16 con tren disk)
sh(f"python /tmp/llama.cpp/convert_hf_to_gguf.py {BF16_DIR} "
   f"--outfile {GGUF_DIR}/f16.gguf --outtype f16", timeout=3600)
log("convert xong")

# 4b. ha transformers xuong 4.x cho convert (5.x loi tokenizer Gemma)
sh("pip install -q \"transformers<5\"")
gc.collect()

# 5. quant F16 -> Q4_K_M (chi can f16.gguf) roi xoa f16
sh(f"/tmp/llama.cpp/build/bin/llama-quantize {GGUF_DIR}/f16.gguf "
   f"{GGUF_DIR}/gemma-4-12b-gamecraft-r4-q4_k_m.gguf Q4_K_M", timeout=3600)
log("quant xong")
os.remove(os.path.join(GGUF_DIR, "f16.gguf"))

# 6. upload GGUF
api.upload_file(path_or_fileobj=os.path.join(
    GGUF_DIR, "gemma-4-12b-gamecraft-r4-q4_k_m.gguf"),
    path_in_repo="gguf/gemma-4-12b-gamecraft-r4-q4_k_m.gguf",
    repo_id=REPO, token=HF_TOKEN)
log("upload GGUF xong")
log(f"RELEASE DONE: https://huggingface.co/{REPO}")
