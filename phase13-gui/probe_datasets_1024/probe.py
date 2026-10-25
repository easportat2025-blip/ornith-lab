import os
import time

print("PROBE_DATASETS start", time.strftime("%Y-%m-%d %H:%M:%S"))
roots = ["/kaggle/input", "/kaggle/input/competitions"]
for root in roots:
    try:
        names = sorted(os.listdir(root))
        print("LIST", root, len(names), names[:50])
    except Exception as e:
        print("LIST_ERR", root, type(e).__name__, e)
for base, dirs, files in os.walk("/kaggle/input"):
    depth = base.count(os.sep) - "/kaggle/input".count(os.sep)
    if depth > 2:
        dirs[:] = []
        continue
    print("DIR", base, "dirs", len(dirs), "files", len(files))
print("PROBE_DATASETS done")
