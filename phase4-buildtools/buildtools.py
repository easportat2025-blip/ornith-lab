"""Clone + build llama-quantize + tai gguf wheel -> dataset llamatools.
De RTX offline dung (khong can mang). CPU."""
import json
import os
import shutil
import subprocess

WORK = "/kaggle/working"
OUT = os.path.join(WORK, "llamatools")
OWNER = "khoadangnguye"
SLUG = "gemma12b-llamatools"


def log(m):
    print(f"[tools] {m}", flush=True)


def sh(cmd, timeout=3600):
    log(f"+ {cmd[:100]}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    print((r.stdout or "")[-800:], flush=True)
    if r.returncode != 0:
        print((r.stderr or "")[-800:], flush=True)
        raise SystemExit(f"FAILED({r.returncode}): {cmd[:60]}")


os.makedirs(OUT, exist_ok=True)
sh("git clone --depth 1 https://github.com/ggerganov/llama.cpp /tmp/llama.cpp",
   timeout=1200)
sh("cmake -S /tmp/llama.cpp -B /tmp/llama.cpp/build "
   "-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DLLAMA_CURL=OFF",
   timeout=1800)
sh("cmake --build /tmp/llama.cpp/build --target llama-quantize -j4",
   timeout=3600)
QB = None
for root, _, files in os.walk("/tmp/llama.cpp/build"):
    for f in files:
        if "quantize" in f:
            p = os.path.join(root, f)
            log(f"thay {p} {os.path.getsize(p)} bytes")
            if os.path.getsize(p) > 5000000 and QB is None:
                QB = p
assert QB, "khong thay binary llama-quantize that (>5MB)"
shutil.copy(QB, os.path.join(OUT, "llama-quantize"))
shutil.copy("/tmp/llama.cpp/convert_hf_to_gguf.py",
            os.path.join(OUT, "convert_hf_to_gguf.py"))
sh(f"pip download --dest {OUT} --no-deps gguf")
names = sorted(os.listdir(OUT))
log(f"files={names}")
qb = os.path.join(OUT, "llama-quantize")
assert os.path.getsize(qb) > 5000000, f"binary nhe bat thuong: {os.path.getsize(qb)}"
assert any("convert_hf" in f for f in names)
assert any("gguf-" in f and f.endswith(".whl") for f in names)
with open(os.path.join(OUT, "dataset-metadata.json"), "w") as f:
    json.dump({"title": "gemma12b llama quant tools",
               "id": f"{OWNER}/{SLUG}",
               "licenses": [{"name": "CC0-1.0"}]}, f, indent=2)
try:
    sh(f"kaggle datasets create -p {OUT}")
except SystemExit:
    sh(f"kaggle datasets version -p {OUT} -m 'fix binary that' --dir-mode zip")
out = sh(f"kaggle datasets files {OWNER}/{SLUG}")
if "llama-quantize" not in out:
    raise SystemExit("VERIFY FAIL")
log(f"PUBLISHED: {OWNER}/{SLUG}")
