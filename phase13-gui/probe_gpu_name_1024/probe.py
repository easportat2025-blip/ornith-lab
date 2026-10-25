import os
import time

print("PROBE_GPU_NAME start", time.strftime("%Y-%m-%d %H:%M:%S"))
try:
    import torch
    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
    print("device_count", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print("gpu", i, torch.cuda.get_device_name(i))
        p = torch.cuda.get_device_properties(i)
        print("vram_gb", round(p.total_memory / 1024**3, 1))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:300])
print("PROBE_GPU_NAME done")
