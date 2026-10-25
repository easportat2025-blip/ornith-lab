import os
import time

print("PROBE_BASE4 start", time.strftime("%Y-%m-%d %H:%M:%S"))
for root in ("/kaggle/input",):
    try:
        print("LIST", root, sorted(os.listdir(root))[:50])
    except Exception as e:
        print("LIST_ERR", root, type(e).__name__, e)
for name in ("ornbase-s1", "ornbase-s2", "ornbase-s3", "ornbase-s4"):
    p = os.path.join("/kaggle/input", name)
    try:
        print("DS", name, "files", sorted(os.listdir(p))[:10])
    except Exception as e:
        print("DS_ERR", name, type(e).__name__, e)
print("PROBE_BASE4 done")
