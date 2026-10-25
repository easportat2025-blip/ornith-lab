# scripts/state

Runtime heartbeat/lease files live here and are **not committed** (except this README).

- `heartbeat.json` — written by `scripts/idle_ping.py` every 10 min (30 min when busy).
- `manual_active.json` — optional manual override for kernels pushed outside the watchdog:
  ```json
  {"items":[{"ref":"dieniw/ornith-gui-sft-v25b","status":"RUNNING",
             "since":"2026-10-24T08:00:00","note":"manual retry v2"}]}
  ```
  Entries expire after 6h; remove when the run finishes.
- `*.pid` — optional process markers.

These files contain no secrets. The GitHub `ops-state` branch gets a secret-free snapshot
from `scripts/github_state.py`.
