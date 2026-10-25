import os
import platform
import sys
import time

print("PROBE_CPU start", time.strftime("%Y-%m-%d %H:%M:%S"))
print("python", sys.version)
print("platform", platform.platform())
print("cwd", os.getcwd())
print("files", sorted(os.listdir("."))[:20])
print("PROBE_CPU done")
