# state

The real ops snapshot lives on the **`ops-state`** branch, not on `main`.
This directory is a placeholder for local/tracked examples.

`scripts/github_state.py` writes `state/current.json`, `state/jobs.json`, and
`state/heartbeat.json` to `ops-state`; `ops-heartbeat.yml` updates a GitHub issue
every 10 minutes so the lab is visible even when the local machine is off.
