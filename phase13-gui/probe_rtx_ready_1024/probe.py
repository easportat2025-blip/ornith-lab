import os
import time

print("PROBE_RTX_READY start", time.strftime("%Y-%m-%d %H:%M:%S"))
try:
    import torch
    print("cuda", torch.cuda.is_available(), torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print("gpu", i, torch.cuda.get_device_name(i))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:300])
print("inputs", sorted(os.listdir("/kaggle/input"))[:10])
print("PROBE_RTX_READY done")
