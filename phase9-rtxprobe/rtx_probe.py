"""Probe: kernel_sources co mount tren RTX khong."""
import os
for r, ds, fs in os.walk("/kaggle/input"):
    print(f"IN: {r} dirs={len(ds)} nfiles={len(fs)} "
          f"{sorted(fs)[:5]}", flush=True)
print("PROBE DONE", flush=True)
