# AGENTS.md — protocol for AI agents

This file is the public, sanitized operating protocol. The private `agent.md`
(local only) is not a source of truth for this repository.

## Read first

1. `README.md` — architecture and quick start.
2. `docs/HANDOFF.md` — latest state, blockers, next move.
3. `docs/ENVIRONMENT.md` — workflows, self-dispatch, troubleshooting.
4. `configs/kaggle_queue.json` — what is queued.
5. GitHub issue `[ops] kaggle watchdog` — latest kernel status and outputs.
6. `ops-state` branch → `state/current.json` — machine-readable ops state.

If these disagree, trust the newest timestamp, then the GitHub issue/state over
prose docs.

## Hard rules

- **Never commit secrets.** Use environment variables, HKCU on Windows, GitHub
  Actions secrets, or HF secrets. Never write a key to disk, a kernel, a dataset
  card, an issue, or a log.
- **Never train on B17.** B17 is the holdout benchmark. Curate v26+ from
  B15/B16/capability-similar failures, not from B17 tasks.
- **New kernel → new slug.** The watchdog only auto-pushes targets whose state
  is `pending` and whose Kaggle status is `MISSING`. It never re-pushes an
  existing `ERROR`/`COMPLETE` kernel on every tick.
- **Do not run a local watchdog 24/7.** GitHub Actions (`ops-tick` +
  `kaggle-watchdog`) is the loop. Local scripts are for inspection and manual
  runs.
- **Do not commit large artifacts.** Adapters, outputs, screenshots, zips, and
  datasets go to HF/Kaggle; commit only manifests and links.
- **Do not delete unfamiliar work.** Inspect first; the user may have created it.
- **Rotate any credential that appears in chat/logs/issues.** Record the incident
  in `docs/HANDOFF.md` without the value.

## Ops loop

```
kaggle-watchdog completes
  -> ops-tick waits 600s
  -> dispatches kaggle-watchdog (+ heartbeat)
  -> repeat
```

The `*/10` schedule is a backup seed. To stop the loop, disable `ops-tick` in
GitHub Actions. To seed it manually, dispatch `ops-tick` with
`delay_seconds=0`, or dispatch `kaggle-watchdog` directly.

The watchdog:
- polls every queue target;
- downloads small JSON/MD/TXT results for `COMPLETE` kernels into
  `state/results/` (max 2 MB each);
- updates the issue and `ops-state`;
- auto-pushes the first `pending` + `MISSING` kernel when nothing is active.

## Before pushing

```powershell
python scripts\secret_scan.py
python -m compileall -q scripts tests
python -m pytest -q
python -m unittest discover -s scripts\jobs -p "test_*.py" -v
```

If `git push` over HTTPS hangs, use the Git Data API:

```powershell
$env:GH_TOKEN = "<token>"
python scripts\github_push_files.py --repo easportat2025-blip/ornith-lab `
  --branch main --message "ops: ..." <files>
```

The API script uses the current remote `main` HEAD as the parent, so fetch first
if you need to see the latest commit. It never stores the token.

## After a milestone

1. Update `docs/HANDOFF.md` (state, metrics, blockers, next move).
2. Update `configs/kaggle_queue.json` (done/active/pending, new slug).
3. Run the checks above.
4. Push `main`; let `ci.yml` and `hf-sync.yml` run.
5. Confirm the watchdog issue and `ops-state` updated.
6. If a gate failed, keep the branch/artifacts and write a post-mortem; do not
   merge a regression.

## Useful commands

```powershell
python scripts\ops_status.py          # queue + state + secret presence
python scripts\check_secrets.py       # set/missing only
python scripts\kaggle_watchdog_ci.py  # one watchdog poll (needs Kaggle env)
python scripts\hf_code_sync.py --dry-run
python scripts\hf_chat_sync.py --dry-run --files docs/HANDOFF.md README.md
```

## Handoff checklist

- [ ] Latest metrics and gate result are in `docs/HANDOFF.md`.
- [ ] Queue state matches Kaggle (`done` / `active` / `pending`).
- [ ] B17 remains holdout-only.
- [ ] No secrets or large artifacts staged.
- [ ] CI green; `hf-sync` green or explicitly skipped.
- [ ] Watchdog issue shows the expected active kernel.
- [ ] Next action is a single, concrete command or decision.
