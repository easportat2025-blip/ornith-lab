"""Phase M: tai base Ornith 19GB ve /kaggle/working/ornbase (1 lan duy nhat).
Kernel RTX offline gan output nay qua kernel_sources (khoi mount dataset,
khoi download). CPU + internet la du."""
import os
import subprocess
import time


def log(m):
    print("[maker] " + m, flush=True)


OUT = "/kaggle/working/ornbase"
os.makedirs(OUT, exist_ok=True)
for attempt in range(4):
    try:
        import subprocess as _s
        _s.run("pip install -q huggingface_hub", shell=True, check=False)
        from huggingface_hub import snapshot_download
        snapshot_download("ornith-ai/Ornith-1.5-9B", local_dir=OUT,
                          allow_patterns=["*.safetensors", "*.json",
                                          "*.jinja", "*.model", "LICENSE*"],
                          max_workers=4)
        break
    except Exception as e:
        log(f"lan {attempt + 1} loi: {e} -> doi 120s")
        time.sleep(120)
else:
    raise SystemExit("tai base that bai sau 4 lan")

total = 0
names = []
for r, _, fs in os.walk(OUT):
    for f in fs:
        p = os.path.join(r, f)
        total += os.path.getsize(p)
        names.append(f)
log(f"files={len(names)} total={total / 2**30:.2f}GB")
have = [n for n in names if n == "model.safetensors"]
log("shards=" + str(sorted(
    n for n in names if n.startswith("model-") and n.endswith(".safetensors"))))
assert any(n.startswith("model-") for n in names), "thieu shards!"
log("MAKER DONE")
