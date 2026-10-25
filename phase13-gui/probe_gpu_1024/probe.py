import os
import platform
import sys
import time

print("PROBE_GPU start", time.strftime("%Y-%m-%d %H:%M:%S"))
print("python", sys.version)
print("platform", platform.platform())
try:
    import torch
    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("device", torch.cuda.get_device_name(0))
        print("capability", torch.cuda.get_device_capability(0))
except Exception as e:
    print("torch_error", type(e).__name__, e)
print("PROBE_GPU done")
