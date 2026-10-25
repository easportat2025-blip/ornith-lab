import importlib
import time

print("PROBE_IMPORTS start", time.strftime("%Y-%m-%d %H:%M:%S"))
for name in ["torch", "transformers", "peft", "trl", "bitsandbytes",
             "unsloth", "unsloth_zoo", "accelerate", "datasets", "vllm"]:
    try:
        m = importlib.import_module(name)
        print("OK", name, getattr(m, "__version__", ""))
    except Exception as e:
        print("MISSING", name, type(e).__name__, str(e)[:120])
print("PROBE_IMPORTS done")
