# -*- coding: utf-8 -*-
"""Health check and self-healing re-seed for the GitHub ops loop.

The normal loop is:

    kaggle-watchdog completed
      -> ops-tick (sleep delay_seconds)
      -> dispatch kaggle-watchdog
      -> ...

This script is the independent fallback. It reads ``configs/ops.json``, asks
the GitHub API for the latest runs of ``ops-tick`` and ``kaggle-watchdog``, and
dispatches a fresh watchdog and/or ops-tick timer when the loop looks stale.
``ops-tick`` skips a duplicate watchdog when one is already active, so
dispatching both is safe and restores the self-dispatch timer.

It never prints or writes secrets. The token is read from ``GITHUB_TOKEN``.

Usage:
  GITHUB_TOKEN=... python scripts/ops_health.py --redispatch
  python scripts/ops_health.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "ops.json")
API = "https://api.github.com"
DEFAULT_STALE_MINUTES = 25
WORKFLOWS = ("ops-tick.yml", "kaggle-watchdog.yml", "ops-heartbeat.yml")
ACTIVE_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def parse_iso(value):
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def age_minutes(created_at, now=None):
    parsed = parse_iso(created_at)
    if parsed is None:
        return None
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    return round((now - parsed).total_seconds() / 60.0, 2)


def is_active(run):
    return bool(run) and str(run.get("status") or "").lower() in ACTIVE_STATUSES


def decide_actions(runs, enabled=True, stale_minutes=DEFAULT_STALE_MINUTES):
    """Return the dispatches needed to re-seed the loop.

    If the watchdog is stale, dispatch it directly. If ops-tick is stale,
    dispatch ops-tick with delay 0 so it can restore the self-dispatch timer;
    ops-tick skips a duplicate watchdog when one is already active. Dispatching
    both is safe because ops-tick checks the active watchdog first.
    """
    if not enabled:
        return []
    watchdog = runs.get("kaggle-watchdog.yml") or {}
    tick = runs.get("ops-tick.yml") or {}
    if is_active(watchdog) or is_active(tick):
        return []
    wd_age = watchdog.get("age_minutes")
    tick_age = tick.get("age_minutes")
    actions = []
    if wd_age is None or wd_age > stale_minutes:
        actions.append({
            "workflow": "kaggle-watchdog.yml",
            "reason": "watchdog stale or missing",
            "inputs": {"auto_push": "true"},
        })
    if tick_age is None or tick_age > stale_minutes:
        actions.append({
            "workflow": "ops-tick.yml",
            "reason": "ops-tick stale or missing; re-seed timer",
            "inputs": {"delay_seconds": "0"},
        })
    return actions


def _request(method, url, token, payload=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API + url,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "ornith-ops-health",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw.decode("utf-8")) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            body = {"message": raw.decode("utf-8", "replace")[:300]}
        return exc.code, body
    except Exception as exc:
        return 0, {"message": "%s: %s" % (type(exc).__name__, exc)}


def latest_run(repo, workflow, token, ref="main"):
    workflow_q = urllib.parse.quote(workflow, safe="")
    url = "/repos/%s/actions/workflows/%s/runs?per_page=1&branch=%s" % (
        repo, workflow_q, urllib.parse.quote(ref, safe=""))
    status, data = _request("GET", url, token)
    if status != 200:
        return None, "HTTP %s: %s" % (status, str(data.get("message", ""))[:200])
    runs = data.get("workflow_runs") or []
    if not runs:
        return None, "no runs"
    run = runs[0]
    return {
        "id": run.get("id"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "html_url": run.get("html_url"),
        "age_minutes": age_minutes(run.get("created_at")),
    }, ""


def dispatch(repo, workflow, token, ref="main", inputs=None):
    payload = {"ref": ref}
    if inputs:
        payload["inputs"] = inputs
    elif workflow == "kaggle-watchdog.yml":
        payload["inputs"] = {"auto_push": "true"}
    status, data = _request(
        "POST",
        "/repos/%s/actions/workflows/%s/dispatches" % (
            repo, urllib.parse.quote(workflow, safe="")),
        token,
        payload,
    )
    return status in (200, 201, 204), status, str(data.get("message", ""))[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--ref", default=os.environ.get("GITHUB_REF_NAME", "main"))
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--out", default=os.path.join(ROOT, "state", "loop_health.json"))
    ap.add_argument("--redispatch", action="store_true",
                    help="dispatch kaggle-watchdog when the loop is stale")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; never dispatch")
    ap.add_argument("--stale-minutes", type=int, default=0,
                    help="override loop.stale_after_minutes (0 = use config)")
    args = ap.parse_args()

    cfg = load_json(args.config, {})
    loop = cfg.get("loop") or {}
    upgrade = cfg.get("upgrade") or {}
    enabled = loop.get("enabled", True) is not False
    stale = args.stale_minutes or int(loop.get("stale_after_minutes",
                                               DEFAULT_STALE_MINUTES))
    repo = args.repo
    ref = args.ref or "main"
    token = os.environ.get("GITHUB_TOKEN", "")

    errors = []
    runs = {}
    if not repo:
        errors.append("GITHUB_REPOSITORY is empty")
    if not token:
        errors.append("GITHUB_TOKEN is empty")
    if repo and token:
        for workflow in WORKFLOWS:
            run, error = latest_run(repo, workflow, token, ref)
            if error:
                errors.append("%s: %s" % (workflow, error))
            runs[workflow] = run or {"error": error or "no run"}
    else:
        for workflow in WORKFLOWS:
            runs[workflow] = {"error": "not checked"}

    actions = (decide_actions(runs, enabled=enabled, stale_minutes=stale)
               if repo and token else [])
    for idx, action in enumerate(actions):
        action["dispatched"] = False
        action["rc"] = None
        if not (args.redispatch and not args.dry_run and repo and token):
            continue
        ok, rc, message = dispatch(repo, action["workflow"], token, ref,
                                   inputs=action.get("inputs"))
        action["dispatched"] = bool(ok)
        action["rc"] = rc
        if message:
            action["message"] = message
        if not ok:
            errors.append("dispatch %s: HTTP %s %s" % (
                action["workflow"], rc, message))
        # Give the first dispatch a moment to appear as queued before the
        # second dispatch checks for an active watchdog.
        if idx < len(actions) - 1:
            time.sleep(3)

    summary = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": repo,
        "ref": ref,
        "enabled": enabled,
        "upgrade_mode": bool(upgrade.get("mode", False)),
        "stale_minutes": stale,
        "redispatch": bool(args.redispatch and not args.dry_run),
        "dry_run": bool(args.dry_run),
        "runs": runs,
        "actions": actions,
        "errors": errors,
    }

    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print("== ops health ==")
    print("repo=%s ref=%s enabled=%s upgrade_mode=%s stale=%sm" % (
        repo or "?", ref, enabled, summary["upgrade_mode"], stale))
    for workflow in WORKFLOWS:
        run = runs.get(workflow) or {}
        if run.get("error"):
            print("%-20s ERROR %s" % (workflow, run["error"]))
        else:
            print("%-20s %-10s %-8s age=%sm %s" % (
                workflow, run.get("status", "?"),
                run.get("conclusion") or "-",
                run.get("age_minutes"), run.get("html_url", "")))
    if not actions:
        print("actions: none (loop fresh or disabled)")
    for action in actions:
        print("action: %s (%s) dispatched=%s rc=%s" % (
            action["workflow"], action["reason"],
            action["dispatched"], action["rc"]))
    for error in errors:
        print("error:", error)
    print("wrote", out_path)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        lines = ["### ops health", "",
                 "- repo: `%s`" % (repo or "?"),
                 "- enabled: `%s` · upgrade_mode: `%s` · stale: `%sm`" % (
                     enabled, summary["upgrade_mode"], stale),
                 "", "| workflow | status | conclusion | age |",
                 "|---|---|---|---|"]
        for workflow in WORKFLOWS:
            run = runs.get(workflow) or {}
            lines.append("| `%s` | %s | %s | %s |" % (
                workflow, run.get("status", run.get("error", "?")),
                run.get("conclusion") or "-",
                ("%sm" % run["age_minutes"])
                if run.get("age_minutes") is not None else "-"))
        lines.append("")
        if actions:
            lines.append("Actions:")
            for action in actions:
                lines.append("- `%s`: %s (dispatched=%s rc=%s)" % (
                    action["workflow"], action["reason"],
                    action["dispatched"], action["rc"]))
        else:
            lines.append("Actions: none.")
        if errors:
            lines.append("")
            lines.append("Errors:")
            for error in errors:
                lines.append("- %s" % error)
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
