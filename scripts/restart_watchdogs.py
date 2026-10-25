"""restart_watchdogs.py - khoi dong LAI 2 watchdog (acc A + acc B) doc lap.

Key truyen qua env luc chay (KHONG ghi vao file):
    $env:KAGGLE_KEY_A = "<key acc A>"; $env:KAGGLE_KEY_B = "<key acc B>"
    python scripts/restart_watchdogs.py

Moi watchdog: process DETACHED (tiep khi user dong session) + log rieng.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LOGDIR = os.path.join(ROOT, "scripts", "logs")
os.makedirs(LOGDIR, exist_ok=True)

KEY_A = os.environ.get("KAGGLE_KEY_A", "")
KEY_B = os.environ.get("KAGGLE_KEY_B", "")
if not KEY_A or not KEY_B:
    print("THIEU env KAGGLE_KEY_A / KAGGLE_KEY_B - bo qua")
    sys.exit(1)

DETACH = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED_PROCESS|NO_WINDOW

# --- dung watchdog cu ---
out = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
     "Where-Object { $_.CommandLine -match 'watchdog\\.py' } | "
     "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
    capture_output=True, text=True, creationflags=0x08000000)
print("dung watchdog cu:", (out.stdout or "").strip()[:200])
time.sleep(2)

JOBS = [
    ("A", {
        "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
        "KAGGLE_USERNAME": "khoadangnguye", "KAGGLE_KEY": KEY_A,
        "GPU_QUEUE": os.path.join(ROOT, "scripts", "gpu_queue.json"),
        "WATCH_TARGETS": os.path.join(ROOT, "scripts", "watchdog_targets.json"),
        "WATCH_STATE": os.path.join(ROOT, "scripts", "watchdog_state.json"),
        "WATCH_LOG": os.path.join(LOGDIR, "watchdog.log"),
    }),
    ("B", {
        "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
        "KAGGLE_USERNAME": "dieniw", "KAGGLE_KEY": KEY_B,
        "GPU_QUEUE": os.path.join(ROOT, "scripts", "gpu_queue_B.json"),
        "WATCH_TARGETS": os.path.join(ROOT, "scripts", "watchdog_targets_B.json"),
        "WATCH_STATE": os.path.join(ROOT, "scripts", "watchdog_state_B.json"),
        "WATCH_LOG": os.path.join(LOGDIR, "watchdog_B.log"),
    }),
]

for name, extra in JOBS:
    env = dict(os.environ)
    env.update(extra)
    log = open(os.path.join(LOGDIR, "watchdog%s.log" % name), "a",
               encoding="utf-8")
    p = subprocess.Popen([PY, os.path.join(ROOT, "scripts", "watchdog.py")],
                         cwd=ROOT, env=env, stdout=log,
                         stderr=subprocess.STDOUT, creationflags=DETACH)
    print("watchdog %s started pid %d" % (name, p.pid))
    time.sleep(1)
print("OK")
