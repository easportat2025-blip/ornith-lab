"""W1 CPU-fetch: tai wheels vLLM + flash-attn ve /kaggle/working/wheels.
GPU kernels gan qua kernel_sources (khong can dataset)."""
import os
import subprocess
import sys

W = "/kaggle/working/wheels"
os.makedirs(W, exist_ok=True)

def sh(cmd, timeout=3600):
    print("$ " + cmd[:120], flush=True)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    tail = (r.stdout or "")[-400:]
    if tail:
        print(tail, flush=True)
    if r.returncode != 0:
        print("LOI rc=" + str(r.returncode) + ": "
              + (r.stderr or "")[-800:], flush=True)
        return False
    return True


print("CPU python=" + sys.version.replace("\n", " "), flush=True)
sh("pip --version")

# Xoa sach dir cu (tranh lan wheel vllm 0.31) + pin vllm 0.26.0
# (ban moi nhat giu torch==2.11.0 khop image GPU)
sh(f"rm -rf {W} && mkdir -p {W}")

# 1. vLLM 0.26.0 closure (abi3 wheel + deps; torch da co tren GPU se skip)
sh(f"pip download --dest {W} vllm==0.26.0")

# torchcodec (dep cung vllm 0.26, pip closure bo sot) + xem torch image CPU
sh(f"pip download --dest {W} torchcodec")
sh("python -c \"import torch; print('CPU-torch='+torch.__version__)\" 2>&1 "
   "| tail -1")

# 2. einops (dep cua flash-attn, phong khi --no-deps bo sot)
sh(f"pip download --dest {W} einops")

# 2b. bitsandbytes (can 4bit; RTX offline khong co PyPI)
sh(f"pip download --dest {W} bitsandbytes")

# 3. flash-attn FA2 cho torch2.11/cu128/cp313 tu Astral index
ok_fa = sh(f"pip download --no-deps --dest {W} --index-url "
           f"https://wheels.astral.sh/simple/cu128/ flash-attn")

# 4. Fallback: mo asset mjun0812 prebuilds qua GitHub API
if not ok_fa:
    print("Astral that bai -> thu mjun0812 prebuilds", flush=True)
    try:
        import json
        import urllib.request
        req = urllib.request.Request(
            "https://api.github.com/repos/mjun0812/"
            "flash-attention-prebuild-wheels/releases?per_page=30",
            headers={"User-Agent": "kaggle-fetch"})
        rels = json.load(urllib.request.urlopen(req, timeout=60))
        hit = None
        for rel in rels:
            for a in rel.get("assets", []):
                n = a.get("name", "")
                if ("cu128" in n and "torch2.11" in n and "cp313" in n
                        and n.endswith("linux_x86_64.whl")):
                    hit = a.get("browser_download_url")
                    break
            if hit:
                break
        print("asset tim duoc: " + str(hit), flush=True)
        if hit:
            out = os.path.join(W, hit.split("/")[-1])
            urllib.request.urlretrieve(hit, out)
            print("tai xong: " + out, flush=True)
    except Exception as e:
        print("fallback that bai: " + str(e)
              + " (bo qua FA, vLLM van chay)", flush=True)

sh(f"ls -la {W} && du -sh {W}")
# XOA torch* khoi closure: GPU giu torch goc (2.11+cu128),
# keo torch la tu image CPU se gay lech CUDA nhu smoke v2
sh(f"rm -f {W}/torch*.whl {W}/torchaudio* {W}/torchvision* "
   f"&& ls {W} | grep -ci torch; ls -la {W} && du -sh {W}")

# 5. vLLM variant theo CUDA: +cu129 link libcudart.so.12 (co san trong
# torch cu128) — wheel plain tren PyPI link libcudart.so.13 (image thieu).
import urllib.request as _u
_V = "0.26.0"
_URL = (f"https://github.com/vllm-project/vllm/releases/download/v{_V}/"
        f"vllm-{_V}+cu129-cp38-abi3-manylinux_2_28_x86_64.whl")
_out = os.path.join(W, os.path.basename(_URL))
try:
    print("tai " + _URL, flush=True)
    _u.urlretrieve(_URL, _out)
    print("OK " + _out + " " + str(os.path.getsize(_out)), flush=True)
except Exception as e:
    print("tai cu129 that bai: " + str(e), flush=True)
print("FETCH DONE", flush=True)
