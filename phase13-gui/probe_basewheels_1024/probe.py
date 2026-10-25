import os
import time

print("PROBE_BASEWHEELS start", time.strftime("%Y-%m-%d %H:%M:%S"))
for root in ("/kaggle/input", "/kaggle/input/datasets"):
    try:
        print("LIST", root, sorted(os.listdir(root))[:50])
    except Exception as e:
        print("LIST_ERR", root, type(e).__name__, e)
print("PROBE_BASEWHEELS done")
