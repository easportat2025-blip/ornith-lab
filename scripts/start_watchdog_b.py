"""start_watchdog_b.py - start watchdog thu 2 cho acc B (dieniw) voi queue B."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LOGDIR = os.path.join(ROOT, "scripts", "logs")
os.makedirs(LOGDIR, exist_ok=True)

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUTF8"] = "1"
env["GPU_QUEUE"] = os.path.join(ROOT, "scripts", "gpu_queue_B.json")
env["WATCH_TARGETS"] = os.path.join(ROOT, "scripts", "watchdog_targets_B.json")
env["WATCH_STATE"] = os.path.join(ROOT, "scripts", "watchdog_state_B.json")
env["WATCH_LOG"] = os.path.join(ROOT, "scripts", "logs", "watchdog_B.log")
env["KAGGLE_USERNAME"] = "dieniw"
env["KAGGLE_KEY"] = os.environ.get("KAGGLE_KEY_B", "")

if not env["KAGGLE_KEY"]:
    print("thieu KAGGLE_KEY_B (key acc B) - bo qua")
    sys.exit(1)

# dung watchdog B cu (neu co)
subprocess.run(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                "Where-Object { $_.CommandLine -match 'watchdog.py' -and "
                "$_.CommandLine -notmatch 'space_sync' } | ForEach-Object { "
                "if ($_.CommandLine -notmatch 'KAGGLE') { } }"],
               capture_output=True, text=True, creationflags=0x08000000)

log = open(os.path.join(LOGDIR, "watchdog_B.log"), "a", encoding="utf-8")
p = subprocess.Popen([PY, os.path.join(ROOT, "scripts", "watchdog.py")],
                     cwd=ROOT, env=env, stdout=log,
                     stderr=subprocess.STDOUT,
                     creationflags=(0x00000008 | 0x00000200 | 0x08000000))
print("watchdog B started pid", p.pid, "-> scripts/logs/watchdog_B.log")
