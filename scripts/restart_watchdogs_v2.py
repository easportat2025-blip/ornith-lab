# -*- coding: utf-8 -*-
"""
restart_watchdogs_v2.py - khoi dong LAI 2 watchdog (acc A + acc B) bang watchdog_v2.py.

Ban sao cua scripts/restart_watchdogs.py (DO NOT sua file cua agent chinh):
  - tu dung 2 watchdog doc lap, process DETACHED (song song voi user dong session)
  - log rieng cho tung acc
  - KHONG ghi key vao file: key chi doc tu env luc chay
  - dung watchdog_v2.py (co batch status, backoff, lock, --check)

Dung:
    $env:KAGGLE_KEY_A = "<key acc A>"; $env:KAGGLE_KEY_B = "<key acc B>"
    python scripts/restart_watchdogs_v2.py

    # xem config truoc khi chay (khong can network):
    python scripts/watchdog_v2.py --check
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


def stop_running():
    """Dung watchdog_v.py (v1 + v2). Regex phai khop ca 'watchdog_v2.py'."""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -match 'watchdog(_v2)?\\.py' } | "
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
        "WATCH_LOCK": os.path.join(ROOT, "scripts", "watchdog_A.lock"),
    }),
    ("B", {
        "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
        "KAGGLE_USERNAME": "dieniw", "KAGGLE_KEY": KEY_B,
        "GPU_QUEUE": os.path.join(ROOT, "scripts", "gpu_queue_B.json"),
        "WATCH_TARGETS": os.path.join(ROOT, "scripts", "watchdog_targets_B.json"),
        "WATCH_STATE": os.path.join(ROOT, "scripts", "watchdog_state_B.json"),
        "WATCH_LOG": os.path.join(LOGDIR, "watchdog_B.log"),
        "WATCH_LOCK": os.path.join(ROOT, "scripts", "watchdog_B.lock"),
    }),
]

SCRIPT = os.path.join(ROOT, "scripts", "watchdog_v2.py")

if __name__ == "__main__":
    stop_running()
    for name, extra in JOBS:
        env = dict(os.environ)
        env.update(extra)
        log = open(os.path.join(LOGDIR, "watchdog%s.log" % name), "a",
                   encoding="utf-8")
        p = subprocess.Popen([PY, SCRIPT], cwd=ROOT, env=env, stdout=log,
                             stderr=subprocess.STDOUT, creationflags=DETACH)
        print("watchdog v2 %s started pid %d" % (name, p.pid))
        time.sleep(1)
    print("OK - log: scripts/logs/watchdog.log, scripts/logs/watchdog_B.log")
