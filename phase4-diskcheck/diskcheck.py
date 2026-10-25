import shutil
import subprocess

t, u, f = shutil.disk_usage("/kaggle/working")
print(f"[disk] working total={t//2**30}G used={u//2**30}G free={f//2**30}G",
      flush=True)
r = subprocess.run("df -h /kaggle/working /tmp; free -g",
                   shell=True, capture_output=True, text=True)
print(r.stdout, flush=True)
r = subprocess.run("which git cmake g++ make; python -c 'import torch; "
                   "print(torch.__version__)'",
                   shell=True, capture_output=True, text=True)
print(r.stdout, flush=True)
print("[disk] DONE", flush=True)
