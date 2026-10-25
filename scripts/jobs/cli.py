# -*- coding: utf-8 -*-
"""cli.py - headless command line for the scripts/jobs registry.

ASCII-only source.  Standard library only.

Commands:
    submit, list, status, logs, cancel, reap, keepalive, doctor

Global option:
    --state PATH    registry path (default scripts/jobs/state.json)

Every command supports --json for machine-readable output.  The CLI never
reads token files; doctor only checks that they exist and have non-zero size.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from . import colab_keeper as keeper
    from . import store as job_store
except ImportError:
    import colab_keeper as keeper
    import store as job_store

STATUSES = job_store.STATUSES
ACTIVE_STATUSES = job_store.ACTIVE_STATUSES
TERMINAL_STATUSES = job_store.TERMINAL_STATUSES
StoreError = job_store.StoreError

SECRET_KEY = re.compile(
    r"(?i)(token|secret|password|passwd|api[_-]?key|oauth|credential)")


def _reconfigure():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _store(args):
    return job_store.JobStore(getattr(args, "state", None))


def _json_dump(value):
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _err(message):
    print(message, file=sys.stderr)


def _short(value, width):
    text = "" if value is None else str(value)
    if len(text) <= width:
        return text
    return text[:max(0, width - 3)] + "..."


def _stamp(value):
    text = "" if value is None else str(value)
    return text.replace("T", " ").replace("Z", "")


def _duration(job):
    started = job_store.parse_ts(job.get("started"))
    if started is None:
        return "-"
    finished = job_store.parse_ts(job.get("finished"))
    if finished is None:
        finished = time.time()
    seconds = max(0, int(finished - started))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return "%dh%02dm" % (hours, minutes)
    if minutes:
        return "%dm%02ds" % (minutes, secs)
    return "%ds" % secs


def _table(jobs):
    if not jobs:
        print("no jobs")
        return
    print("%-28s %-9s %-5s %-14s %-19s %-7s %s" % (
        "ID", "STATUS", "ACC", "SESSION", "CREATED", "RUNTIME", "SCRIPT"))
    for job in jobs:
        print("%-28s %-9s %-5s %-14s %-19s %-7s %s" % (
            _short(job.get("id"), 28),
            _short(job.get("status"), 9),
            _short(job.get("account"), 5),
            _short(job.get("session"), 14),
            _short(_stamp(job.get("created")), 19),
            _duration(job),
            _short(os.path.basename(str(job.get("script") or "")), 40),
        ))
        if job.get("error"):
            print("  error: %s" % _short(job.get("error"), 160))


def _parse_meta(pairs):
    meta = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise StoreError("--meta expects KEY=VALUE, got %r" % pair)
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise StoreError("--meta key is empty")
        if SECRET_KEY.search(key):
            raise StoreError(
                "refusing secret-like meta key %r; use an environment "
                "variable outside the registry" % key)
        parsed = value
        if value in ("true", "false", "null") or value[:1] in "[{\"":
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = value
        elif re.match(r"^-?\d+$", value):
            try:
                parsed = int(value)
            except ValueError:
                parsed = value
        meta[key] = parsed
    return meta


def _parse_artifact(value):
    kind = "file"
    text = value.strip()
    if text.startswith("dir:"):
        kind = "dir"
        text = text[4:]
    local = None
    if "::" in text:
        text, local = text.split("::", 1)
    if not text:
        raise StoreError("--artifact remote path is empty")
    return {"remote": text, "local": local, "kind": kind,
            "ok": None, "size": None, "error": None}


def cmd_submit(args):
    script = os.path.abspath(args.script)
    if not os.path.exists(script):
        _err("script not found: %s" % script)
        return 2
    if args.session and args.account is None:
        _err("--session requires an explicit --account")
        return 2
    if args.runner not in ("auto", "run_task", "exec_bg"):
        _err("invalid --runner %s" % args.runner)
        return 2

    meta = _parse_meta(args.meta)
    meta.update({
        "wait": int(args.wait),
        "runner": args.runner,
        "poll": int(args.poll),
        "keepalive_every": int(args.keepalive_every),
        "max_runtime": int(args.max_runtime),
        "max_attempts": int(args.max_attempts),
        "require_artifacts": bool(args.require_artifacts),
        "keep_session": bool(args.keep_session),
        "no_launch": bool(args.no_launch),
        "script_args": list(args.arg or []),
    })
    if args.gpu:
        meta["gpu"] = args.gpu
    if args.success_marker:
        meta["success_marker"] = args.success_marker
    if args.wait > 0:
        meta["runner_downloads"] = True

    artifacts = [_parse_artifact(item) for item in (args.artifact or [])]
    payload = {
        "id": args.job_id,
        "backend": args.backend,
        "account": args.account,
        "session": args.session,
        "script": script,
        "args": list(args.arg or []),
        "status": "pending",
        "artifacts": artifacts,
        "meta": meta,
    }
    if args.dry_run:
        if args.json:
            _json_dump({"dry_run": True, "job": payload})
        else:
            print("dry-run: would submit %s" % (args.job_id or "<new id>"))
            print("script: %s" % script)
            print("meta: %s" % json.dumps(meta, sort_keys=True))
        return 0

    store = _store(args)
    job = store.create(
        job_id=args.job_id,
        backend=args.backend,
        account=args.account,
        session=args.session,
        script=script,
        args=list(args.arg or []),
        status="pending",
        artifacts=artifacts,
        meta=meta,
    )
    if args.json:
        _json_dump(job)
    else:
        print("submitted %s" % job["id"])
        print("next: python scripts/jobs/colab_keeper.py --once --job %s"
              % job["id"])
    return 0


def cmd_list(args):
    store = _store(args)
    limit = None if args.limit == 0 else args.limit
    jobs = store.list(status=args.status, limit=limit,
                      account=args.account, backend=args.backend)
    if args.json:
        _json_dump(jobs)
    else:
        _table(jobs)
    return 0


def cmd_status(args):
    store = _store(args)
    if args.job:
        job = store.get(args.job)
        if job is None:
            _err("job not found: %s" % args.job)
            return 1
        if args.json:
            _json_dump(job)
            return 0
        print("id:       %s" % job["id"])
        print("status:   %s" % job["status"])
        print("backend:  %s" % job["backend"])
        print("account:  %s" % job["account"])
        print("session:  %s" % job["session"])
        print("script:   %s" % job["script"])
        print("created:  %s" % job["created"])
        print("started:  %s" % job["started"])
        print("finished: %s" % job["finished"])
        print("runtime:  %s" % _duration(job))
        print("attempts: %s" % job["attempts"])
        print("pid:      %s" % job["pid"])
        print("log:      %s" % job["log_path"])
        print("keepalive:%s" % job["keepalive_until"])
        print("error:    %s" % job["error"])
        print("artifacts:")
        for artifact in job.get("artifacts") or []:
            print("  %s -> %s (%s, %s bytes)"
                  % (artifact.get("remote"), artifact.get("local"),
                     artifact.get("ok"), artifact.get("size")))
        print("meta:")
        for key in sorted(job.get("meta") or {}):
            print("  %s: %s" % (key, job["meta"][key]))
        return 0

    counts = store.counts()
    active = store.list(status=ACTIVE_STATUSES, oldest_first=True)
    recent = store.list(limit=10)
    if args.json:
        _json_dump({"state": store.path, "counts": counts,
                    "active": active, "recent": recent})
        return 0
    print("state: %s" % store.path)
    print("counts: %s" % " ".join("%s=%d" % (key, counts[key])
                                  for key in STATUSES))
    print("\nactive:")
    _table(active)
    print("\nrecent:")
    _table(recent)
    return 0


def _read_lines(path, tail):
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 512 * 1024))
            data = handle.read().decode("utf-8", "replace")
    except OSError as exc:
        raise StoreError("cannot read log %s: %s" % (path, exc))
    lines = data.splitlines()
    if tail and tail > 0:
        lines = lines[-tail:]
    return lines


def cmd_logs(args):
    store = _store(args)
    job = store.get(args.job)
    if job is None:
        _err("job not found: %s" % args.job)
        return 1
    path = job.get("log_path")
    if not path:
        _err("job %s has no log_path yet (status %s)"
             % (args.job, job["status"]))
        return 1
    if args.path_only:
        if args.json:
            _json_dump({"id": job["id"], "log_path": path})
        else:
            print(path)
        return 0
    if not os.path.exists(path):
        _err("log file missing: %s" % path)
        return 1
    if args.follow and args.json:
        _err("--follow cannot be combined with --json")
        return 2
    lines = _read_lines(path, args.tail)
    if args.json:
        _json_dump({"id": job["id"], "log_path": path, "lines": lines})
        return 0
    for line in lines:
        print(line)
    if not args.follow:
        return 0

    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            while True:
                chunk = handle.read()
                if chunk:
                    sys.stdout.write(chunk.decode("utf-8", "replace"))
                    sys.stdout.flush()
                time.sleep(max(1, int(args.interval)))
    except KeyboardInterrupt:
        return 0


def cmd_cancel(args):
    store = _store(args)
    result = keeper.cancel_job(store, args.job, dry_run=args.dry_run,
                               local_only=args.local_only)
    if args.json:
        _json_dump(result)
    else:
        print("%s: %s" % (result.get("id"), result.get("status")
                          or result.get("error")))
    return 0 if result.get("ok") else 1


def cmd_reap(args):
    store = _store(args)
    lost = keeper.reap_stale(store, stale_after=args.stale_after,
                             dry_run=args.dry_run)
    pruned = []
    if not args.no_prune:
        pruned = store.prune(older_than=args.prune_days * 86400,
                             dry_run=args.dry_run)
    if args.json:
        _json_dump({"dry_run": args.dry_run, "lost": lost, "pruned": pruned})
        return 0
    if lost:
        for item in lost:
            print("lost %s: %s" % (item["id"], item["error"]))
    else:
        print("no stale active jobs")
    if args.no_prune:
        print("prune: skipped")
    else:
        print("pruned %d old terminal job(s)%s"
              % (len(pruned), " (dry-run)" if args.dry_run else ""))
        for job_id in pruned:
            print("  %s" % job_id)
    return 0


def cmd_keepalive(args):
    store = _store(args)
    if not args.job and not args.all:
        _err("use --job ID or --all")
        return 2
    if args.job:
        job_ids = [args.job]
    else:
        job_ids = [job["id"] for job in store.list(
            status=ACTIVE_STATUSES, oldest_first=True)]
    results = [keeper.keepalive_job(store, job_id, dry_run=args.dry_run)
               for job_id in job_ids]
    if args.json:
        _json_dump(results)
    else:
        if not results:
            print("no active jobs")
        for item in results:
            if item.get("ok"):
                print("%s: ok keepalive_until=%s"
                      % (item.get("id"), item.get("keepalive_until")))
            else:
                print("%s: FAILED %s" % (item.get("id"),
                                         item.get("error")))
    return 0 if all(item.get("ok") for item in results) else 1


def _account_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(
            SCRIPTS_DIR, "colab_accounts", "acc*"))):
        if not os.path.isdir(path):
            continue
        name = os.path.basename(path)
        token = os.path.join(path, "token.json")
        sessions = os.path.join(path, "sessions.json")
        oauth = os.path.join(path, "oauth.json")
        try:
            token_size = os.path.getsize(token) if os.path.exists(token) else 0
        except OSError:
            token_size = 0
        rows.append({
            "account": name,
            "dir": path,
            "token": token_size > 0,
            "token_size": token_size,
            "sessions": os.path.exists(sessions),
            "oauth": os.path.exists(oauth),
        })
    return rows


def cmd_doctor(args):
    store = _store(args)
    errors = []
    warnings = []
    checks = {}

    checks["python"] = sys.version.split()[0]
    if sys.version_info < (3, 8):
        errors.append("Python 3.8 or newer is required")

    state_exists = os.path.exists(store.path)
    checks["state_path"] = store.path
    checks["state_exists"] = state_exists
    counts = {status: 0 for status in STATUSES}
    try:
        state = store.load()
        counts = {status: 0 for status in STATUSES}
        for job in state["jobs"].values():
            counts[job["status"]] = counts.get(job["status"], 0) + 1
        checks["state_jobs"] = len(state["jobs"])
    except StoreError as exc:
        errors.append("state: %s" % exc)
        checks["state_jobs"] = None

    directory = os.path.dirname(os.path.abspath(store.path))
    writable = False
    try:
        os.makedirs(directory, exist_ok=True)
        fd, probe = tempfile.mkstemp(prefix=".doctor-", dir=directory)
        os.close(fd)
        os.remove(probe)
        writable = True
    except OSError as exc:
        errors.append("state directory is not writable: %s" % exc)
    checks["state_writable"] = writable

    try:
        with job_store.FileLock(store.lock_path, timeout=2):
            lock_ok = True
    except StoreError as exc:
        lock_ok = False
        errors.append("lock: %s" % exc)
    checks["lock_ok"] = lock_ok

    runners = {}
    for name, path in keeper.RUNNERS.items():
        exists = os.path.exists(path)
        runners[name] = {"path": path, "exists": exists}
        if not exists:
            errors.append("missing runner: %s" % path)
    checks["runners"] = runners

    colab_path = None
    if keeper.accounts is not None:
        colab_path = keeper.accounts.COLAB
    if not colab_path:
        colab_path = shutil.which("colab")
    checks["colab"] = colab_path
    if not colab_path or not os.path.exists(colab_path):
        if shutil.which("colab"):
            checks["colab"] = shutil.which("colab")
        else:
            errors.append("colab executable not found")
    if args.probe and checks.get("colab"):
        try:
            proc = subprocess.run([checks["colab"], "version"],
                                  capture_output=True, text=True,
                                  timeout=30)
            checks["colab_version"] = ((proc.stdout or "")
                                       + (proc.stderr or "")).strip()[:300]
            if proc.returncode != 0:
                warnings.append("colab version returned %s"
                                % proc.returncode)
        except Exception as exc:
            warnings.append("colab version probe failed: %s" % exc)

    account_rows = _account_rows()
    checks["accounts"] = account_rows
    if not account_rows:
        warnings.append("no scripts/colab_accounts/acc* directories")
    for row in account_rows:
        if not row["token"]:
            warnings.append("%s has no non-empty token.json" % row["account"])
        if not row["sessions"]:
            warnings.append("%s has no sessions.json" % row["account"])

    stale = keeper.reap_stale(store, stale_after=args.stale_after,
                              dry_run=True)
    checks["stale_active"] = stale
    for item in stale:
        warnings.append("stale active job %s: %s"
                        % (item["id"], item["error"]))

    checks["counts"] = counts
    checks["env"] = {
        "JOBS_STATE": os.environ.get("JOBS_STATE"),
        "JOBS_COLAB_ACCOUNTS": os.environ.get("JOBS_COLAB_ACCOUNTS"),
        "JOBS_DAILY_HOURS": os.environ.get("JOBS_DAILY_HOURS"),
    }
    report = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }
    if args.json:
        _json_dump(report)
    else:
        print("ok: %s" % report["ok"])
        print("state: %s (%d job(s))" % (store.path,
                                         checks.get("state_jobs") or 0))
        print("counts: %s" % " ".join("%s=%d" % (key, counts[key])
                                      for key in STATUSES))
        print("colab: %s" % checks.get("colab"))
        print("accounts: %d" % len(account_rows))
        for row in account_rows:
            print("  %s token=%s sessions=%s oauth=%s"
                  % (row["account"], row["token"], row["sessions"],
                     row["oauth"]))
        if errors:
            print("errors:")
            for item in errors:
                print("  %s" % item)
        if warnings:
            print("warnings:")
            for item in warnings:
                print("  %s" % item)
    return 0 if not errors else 1


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", default=argparse.SUPPRESS,
                        help="registry path")
    parser = argparse.ArgumentParser(
        description="Headless job registry for Colab keeper jobs.")
    parser.add_argument("--state", default=None,
                        help="state.json path (default scripts/jobs/state.json)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("submit", parents=[common],
                       help="queue a job")
    p.add_argument("--script", required=True)
    p.add_argument("--account", type=int)
    p.add_argument("--session")
    p.add_argument("--backend", default="colab")
    p.add_argument("--runner", default="auto",
                   choices=("auto", "run_task", "exec_bg"))
    p.add_argument("--wait", type=int, default=0,
                   help="runner wait seconds (0 means keeper-managed)")
    p.add_argument("--poll", type=int, default=keeper.DEFAULT_POLL)
    p.add_argument("--keepalive-every", type=int,
                   default=keeper.DEFAULT_KEEPALIVE)
    p.add_argument("--max-runtime", type=int,
                   default=keeper.DEFAULT_MAX_RUNTIME)
    p.add_argument("--max-attempts", type=int, default=1)
    p.add_argument("--gpu", help="pre-lease a GPU session, e.g. T4")
    p.add_argument("--artifact", action="append", default=[],
                   help="remote file, dir:/remote/dir, or remote::local")
    p.add_argument("--arg", action="append", default=[],
                   help="recorded script argument (runners do not forward it)")
    p.add_argument("--meta", action="append", default=[],
                   help="extra meta KEY=VALUE")
    p.add_argument("--success-marker",
                   help="require this string in the log to mark done")
    p.add_argument("--require-artifacts", action="store_true")
    p.add_argument("--keep-session", action="store_true")
    p.add_argument("--no-launch", action="store_true",
                   help="attach to a job already running on the VM")
    p.add_argument("--job-id")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("list", parents=[common], help="list jobs")
    p.add_argument("--status")
    p.add_argument("--account", type=int)
    p.add_argument("--backend")
    p.add_argument("--limit", type=int, default=20,
                   help="0 means all")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("status", parents=[common],
                       help="show one job or a summary")
    p.add_argument("job", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("logs", parents=[common], help="print a job log")
    p.add_argument("job")
    p.add_argument("--tail", type=int, default=80,
                   help="number of lines (0 means all)")
    p.add_argument("--follow", action="store_true")
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--path-only", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_logs)

    p = sub.add_parser("cancel", parents=[common], help="cancel a job")
    p.add_argument("job")
    p.add_argument("--local-only", action="store_true",
                   help="do not kill the remote pid or stop the session")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_cancel)

    p = sub.add_parser("reap", parents=[common],
                       help="mark stale jobs lost and prune old records")
    p.add_argument("--stale-after", type=int,
                   default=keeper.DEFAULT_STALE_AFTER)
    p.add_argument("--prune-days", type=float, default=7.0)
    p.add_argument("--no-prune", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_reap)

    p = sub.add_parser("keepalive", parents=[common],
                       help="ping active sessions")
    p.add_argument("--job")
    p.add_argument("--all", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_keepalive)

    p = sub.add_parser("doctor", parents=[common],
                       help="check runners, state, accounts, and locks")
    p.add_argument("--probe", action="store_true",
                   help="run 'colab version' (no authentication)")
    p.add_argument("--stale-after", type=int,
                   default=keeper.DEFAULT_STALE_AFTER)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_doctor)

    return parser


def main(argv=None):
    _reconfigure()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except StoreError as exc:
        _err("store error: %s" % exc)
        return 2
    except KeyboardInterrupt:
        _err("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
