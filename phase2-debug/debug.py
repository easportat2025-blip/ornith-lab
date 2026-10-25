import os

base = "/kaggle/input"
print("[debug] input exists:", os.path.isdir(base))
if os.path.isdir(base):
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d)
        print("[debug] entry:", d)
        if os.path.isdir(p):
            try:
                files = sorted(os.listdir(p))
            except Exception as e:
                print("[debug]  !", e)
                continue
            print("[debug]  n_files:", len(files))
            for f in files[:15]:
                print("[debug]   -", f)
print("[debug] DONE")
