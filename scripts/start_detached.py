"""start_detached.py - khoi dong watcher/worker nhu PROCESS TACH ROI (Windows),
de chung song khi user dong session opencode (harness background se bi kill).

Dung:  python scripts/start_detached.py
"""
import os
import subprocess
import time
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LOGDIR = os.path.join(ROOT, "scripts", "logs")
os.makedirs(LOGDIR, exist_ok=True)

JOBS = [
    ("watchdog", [PY, os.path.join(ROOT, "scripts", "watchdog.py")],
     {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}),
    ("space_sync", [PY, os.path.join(ROOT, "scripts", "space_sync_loop.py")],
     {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
      "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
      "SPACE_SYNC_INTERVAL": os.environ.get("SPACE_SYNC_INTERVAL", "180")}),
    ("agent_md_watch", [PY, os.path.join(ROOT, "scripts", "watch_agent_md.py")],
     {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "WATCH_LOOP": "1"}),
]


def main():
    # 1) dung process cu (theo command line) TRUOC khi start lai
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object { $_.CommandLine -match 'watchdog.py|space_sync_loop.py|"
         "watch_agent_md.py' } | ForEach-Object { Stop-Process -Id "
         "$_.ProcessId -Force; $_.ProcessId }"],
        capture_output=True, text=True, creationflags=0x08000000)
    print("da dung process cu:", (out.stdout or "").strip() or "(khong co)")
    time.sleep(2)

    # 2) start lai voi flags khong tao cua so (kaggle.exe con cung khong bat)
    for name, cmd, extra in JOBS:
        if name == "space_sync" and not extra.get("HF_TOKEN"):
            print("bo qua", name, "(thieu HF_TOKEN)")
            continue
        env = dict(os.environ)
        env.update(extra)
        log = open(os.path.join(LOGDIR, name + ".log"), "a", encoding="utf-8")
        p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log,
                             stderr=subprocess.STDOUT,
                             creationflags=(0x00000008 | 0x00000200 |
                                            0x08000000))
        # 0x8 DETACHED_PROCESS, 0x200 CREATE_NEW_PROCESS_GROUP,
        # 0x08000000 CREATE_NO_WINDOW -> kaggle.exe con KHONG bat cua so den
        print("started %-16s pid %s -> scripts/logs/%s.log" % (name, p.pid, name))


if __name__ == "__main__":
    main()
