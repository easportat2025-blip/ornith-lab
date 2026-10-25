"""W2 smoke T4 v11: vllm 0.26.0 offline-safe + LoRA + tok/s vs HF 4bit.

Tu lieu (CPU-fetch): closure vllm 0.26.0 (KHONG co torch*, KHONG co torchcodec).
Rui ro: closure co nvidia_*_cu13 -> KHONG cho pip dung chung, se lam lech CUDA.
Cach: --no-deps cho tung goi, tu them phu thieu vong lap.
"""
import glob as _glob
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile as _zf


def log(m):
    print("[smoke] " + m, flush=True)


def sh(cmd, timeout=1800):
    print("$ " + cmd[:110], flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    tail = (r.stdout or "")[-400:]
    if tail:
        print(tail, flush=True)
    if r.returncode != 0:
        print("LOI rc=" + str(r.returncode) + ": "
              + (r.stderr or "")[-600:], flush=True)
        return False
    return True


def torch_ver():
    r = subprocess.run(
        "python -c \"import torch;print(torch.__version__)\"",
        shell=True, capture_output=True, text=True)
    return (r.stdout or "").strip()


# ---------- 1. wheels tu cpu-fetch ----------
SRC = None
for r_, _, fs in os.walk("/kaggle/input"):
    if any(f.startswith("vllm-") and f.endswith(".whl") for f in fs):
        SRC = r_
        break
assert SRC, "thieu wheels (check kernel_sources)"
# ban sao che loai nvidia cu13 + torch (tranh lech CUDA)
W = "/tmp/wmin"
shutil.rmtree(W, ignore_errors=True)
os.makedirs(W, exist_ok=True)
skip, n = [], 0
# KHONG cai: torch/torchvision/torchaudio/triton (giai phong torch), va cac
# wheel C-extension nang - chung ABITHE voi numpy cua image se lam hong
# ("cannot import name '_slice' from numpy._core.umath") lam vllm/transformers
# chet ngay trong process.
KILL = ("torch-", "torchaudio", "torchvision", "triton-", "numpy", "numba",
        "scipy", "tokenspeed", "tilelang", "quack_kernels",
        "cuda_", "cuda_bindings", "cuda_core", "cuda_pathfinder",
        "cuda_tile", "cuda_toolkit", "cutlass", "pynvvideocodec",
        "opencv_python", "agent_detector", "humming_kernels")
for f in _glob.glob(os.path.join(SRC, "*.whl")):
    b = os.path.basename(f)
    if ("nvidia_" in b and "cu13" in b) or b.startswith(KILL):
        skip.append(b.split("-")[0])
        continue
    os.symlink(f, os.path.join(W, b))
    n += 1
log(f"wheels={SRC} -> {W} ({n} usable, bo {len(skip)})")
log("torch truoc khi cai=" + torch_ver())

# ---------- 2. FA2 + LD_LIBRARY_PATH (nvidia libs cu12 san trong torch) ----------
import site
sp_libs = [p for p in (site.getsitepackages() or [])]
nvd = _glob.glob("/usr/local/lib/python3.13/dist-packages/nvidia/*/lib")
extra_ld = ":".join(sorted(set(nvd)))
if extra_ld:
    os.environ["LD_LIBRARY_PATH"] = (extra_ld + ":" +
                                     os.environ.get("LD_LIBRARY_PATH", ""))
    log("LD_LIBRARY_PATH +=" + extra_ld.replace(":", ":")[:200])
fa = _glob.glob(os.path.join(W, "flash_attn*.whl"))
if fa:
    sh(f"pip install --no-index --no-deps '{fa[0]}'")
sh("pip install -q -U bitsandbytes")
try:
    import flash_attn  # noqa: F401
    log("FA2 import OK")
except Exception as e:
    log("FA2 loi: " + str(e)[:150])

# ---------- 3. vllm: thu cu129 truoc, plain sau (ca hai --no-deps) ----------
VLLM_PKG = False
try:
    import site
    nvd = _glob.glob("/usr/local/lib/python3.13/dist-packages/nvidia/*/lib")
    if nvd:
        os.environ["LD_LIBRARY_PATH"] = (
            ":".join(sorted(set(nvd))) + ":" +
            os.environ.get("LD_LIBRARY_PATH", ""))
        log("LD_LIBRARY_PATH them " + str(len(nvd)) + " thu muc nvidia")
except Exception as e:
    log("LD loi: " + str(e)[:120])

cands = sorted(_glob.glob(os.path.join(W, "vllm*cu129*.whl"))) + \
    sorted(_glob.glob(os.path.join(W, "vllm-0.26*.whl")))
for whl in cands:
    log("thu cai " + os.path.basename(whl))
    sh(f"pip install --no-index --no-deps --find-links {W} '{whl}'")
    r = subprocess.run("python -c \"import vllm;print(vllm.__version__)\"",
                       shell=True, capture_output=True, text=True)
    if r.returncode == 0:
        VLLM_PKG = True
        log("vllm OK " + r.stdout.strip())
        break
    log("import fail: " + (r.stderr or "").strip().split("\n")[-1][:200])
    sh(f"pip uninstall -y vllm")

if VLLM_PKG:
    # Cai TOAN BO closure --no-deps (nhanh, het loi 'thieu module' don le).
    # BO wheel vllm plain (cu13) — xung dot voi vllm+cu129 da cai.
    req = os.path.join(W, "all.txt")
    picked = []
    for f in sorted(_glob.glob(os.path.join(W, "*.whl"))):
        b = os.path.basename(f)
        if b.startswith("vllm-") and "cu129" not in b:
            log("bo xung dot: " + b)
            continue
        picked.append(f)
    with open(req, "w") as fh:
        fh.write("\n".join(picked) + "\n")
    log(f"cai closure {len(picked)} wheels --no-deps")
    sh(f"pip install --no-index --no-deps -r {req}", timeout=2400)
    for _ in range(8):
        r = subprocess.run("python -c \"import vllm\"", shell=True,
                           capture_output=True, text=True)
        if r.returncode == 0:
            break
        miss = ""
        for ln in (r.stderr or "").split("\n"):
            if "ModuleNotFoundError" in ln:
                miss = ln.split("'")[1] if "'" in ln else ""
                break
        if not miss:
            log("import vllm loi khac:\n" + (r.stderr or "")[-400:])
            break
        log("thieu module=" + miss + " -> cai tu wheels")
        if not sh(f"pip install --no-index --no-deps --find-links {W} {miss}"):
            sh(f"pip install -q {miss}")
    VLLM_PKG = subprocess.run("python -c \"import vllm\"", shell=True,
                              capture_output=True).returncode == 0
log("VLLM_PKG=" + str(VLLM_PKG) + " torch=" + torch_ver())

# ---------- 3b. CHAN DOAN import (truoc khi tai model) ----------
def probe(code):
    r = subprocess.run("python -c " + json.dumps(code), shell=True,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


rc, so, se = probe("import transformers as t;print('tf',t.__version__)")
log("probe transformers: rc=" + str(rc) + " " + (so or se[-200:]))
if rc == 0:
    rc, so, se = probe("from transformers import AutoModelForCausalLM;"
                       "print('hf-auto OK')")
    log("probe hf-auto: rc=" + str(rc) + " " + (so or se[-300:]))
rc, so, se = probe("import numpy;print('np',numpy.__version__)")
log("probe numpy: rc=" + str(rc) + " " + (so or se[-150:]))
rc, so, se = probe("from vllm import LLM;print('vllm LLM OK')")
log("probe vllm.LLM: rc=" + str(rc) + " " + (so or se[-900:]))
if rc != 0:
    rc, so, se = probe("import vllm;print('vllm base OK')")
    log("probe vllm base: rc=" + str(rc) + " " + (so or se[-400:]))

# ---------- 4. inputs ----------
ad = None
for r_, _, fs in os.walk("/kaggle/input"):
    if "adapter_config.json" in fs:
        ad = r_
        break
log("adapter=" + str(ad))
from huggingface_hub import snapshot_download
orn = "/tmp/ornbase"
snapshot_download("ornith-ai/Ornith-1.5-9B", local_dir=orn,
                  allow_patterns=["*.safetensors", "*.json",
                                  "*.jinja", "*.model", "LICENSE*"],
                  max_workers=4)
log("base OK")

# ---------- 5. HF baseline TRUOC (vllm lam hong numpy ABI trong process) ----------
PROMPTS = ["Write a short Pygame maze game in Python:"] * 6
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers import BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(orn)
    m = AutoModelForCausalLM.from_pretrained(
        orn, quantization_config=BitsAndBytesConfig(load_in_4bit=True),
        device_map="auto")
    ids = tok(PROMPTS[0], return_tensors="pt").to(m.device)
    t0 = time.time()
    for _ in range(6):
        m.generate(**ids, max_new_tokens=64, do_sample=False,
                   pad_token_id=tok.eos_token_id)
    dt = time.time() - t0
    log(f"hf gen: ~384 tok / {dt:.1f}s = {384 / max(dt, .01):.1f} tok/s")
    del m
    import gc
    gc.collect()
    torch.cuda.empty_cache()
except Exception as e:
    import traceback as _tb2
    log("HF baseline LOI: " + str(e)[:200])
    log("TB-HF:\n" + "".join(_tb2.format_exc()[-1200:]))

# ---------- 6. vLLM gen + LoRA (sau HF) ----------
vllm_ok = False
if not VLLM_PKG:
    log("khong co package vllm -> chi test HF")
try:
    if not VLLM_PKG:
        raise RuntimeError("skip vllm")
    from vllm import LLM, SamplingParams
    t0 = time.time()
    llm = LLM(model=orn, dtype="float16", quantization="bitsandbytes",
              gpu_memory_utilization=0.9, max_model_len=1024,
              max_num_seqs=8, enforce_eager=True,
              enable_lora=True, max_loras=1)
    log(f"vllm load {time.time() - t0:.0f}s")
    sp = SamplingParams(max_tokens=64, temperature=0)
    t0 = time.time()
    outs = llm.generate(PROMPTS, sp)
    dt = time.time() - t0
    ntok = sum(len(o.outputs[0].token_ids) for o in outs)
    log(f"vllm gen: {ntok} tok / {dt:.1f}s = {ntok / max(dt, .01):.1f} tok/s")
    log("sample: " + outs[0].outputs[0].text[:180])
    vllm_ok = True
    if ad:
        try:
            from vllm.lora.request import LoRARequest
            o2 = llm.generate(PROMPTS[:1], sp,
                              lora_request=LoRARequest("o1", 1, ad))
            log("LoRA OK: " + o2[0].outputs[0].text[:180])
        except Exception as e:
            log("LoRA LOI: " + str(e)[:250])
    del llm
except Exception as e:
    import traceback as _tb
    log("vLLM THAT BAI: " + str(e)[:300])
    log("TB:\n" + "".join(_tb.format_exc()[-1800:]))

log("SMOKE DONE vllm_ok=" + str(vllm_ok))