import os
import platform
import sys
import time

print("PROBE_COMP start", time.strftime("%Y-%m-%d %H:%M:%S"))
print("python", sys.version)
print("platform", platform.platform())
print("cwd", os.getcwd())
for root in ("/kaggle/input", "/kaggle/input/arc-prize-2026-arc-agi-3"):
    try:
        print("LIST", root, sorted(os.listdir(root))[:30])
    except Exception as e:
        print("LIST_ERR", root, type(e).__name__, e)
print("PROBE_COMP done")
