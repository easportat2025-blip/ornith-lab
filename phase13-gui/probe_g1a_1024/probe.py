import os
import time

print("PROBE_G1A start", time.strftime("%Y-%m-%d %H:%M:%S"))
print("LIST /kaggle/input", sorted(os.listdir("/kaggle/input"))[:20])
print("PROBE_G1A done")
