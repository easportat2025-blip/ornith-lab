# -*- coding: utf-8 -*-
"""colab_keeper.py - lease, monitor, keepalive, fetch, and release Colab jobs.

ASCII-only source.  Standard library only.

The keeper is deliberately a thin orchestrator around the existing runners:

    scripts/colab_run_task.py   (preferred: it performs the token swap)
    scripts/colab_exec_bg.py    (compatibility runner)

It launches a job through one of those scripts as a subprocess, then owns the
long poll loop itself so it can keep the session alive, detect a lost session,
fetch the log and artifacts, and stop the session when finished.

No credentials are read or written here.  Account switching uses the existing
scripts/colab_accounts.py swap_in/swap_out helpers; token files never enter the
job registry or keeper output.

Typical use:

    python scripts/jobs/colab_keeper.py --once
    python scripts/jobs/colab_keeper.py
    python scripts/jobs/colab_keeper.py --once --dry-run --job <job-id>
"""

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS_DIR)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from .store import (
        ACTIVE_STATUSES,
        TERMINAL_STATUSES,
        FileLock,
        JobStore,
        StoreError,
        iso_plus,
        now_iso,
        parse_ts,
    )
except ImportError:
    from store import (
        ACTIVE_STATUSES,
        TERMINAL_STATUSES,
        FileLock,
        JobStore,
        StoreError,
        iso_plus,
        now_iso,
        parse_ts,
    )

try:
    import colab_accounts as accounts
except Exception:  # pragma: no cover - doctor reports the real problem
    accounts = None

RUNNERS = {
    "run_task": os.path.join(SCRIPTS_DIR, "colab_run_task.py"),
    "exec_bg": os.path.join(SCRIPTS_DIR, "colab_exec_bg.py"),
}

DEFAULT_POLL = 60
DEFAULT_KEEPALIVE = 240
DEFAULT_MAX_RUNTIME = 6 * 3600
DEFAULT_LAUNCH_TIMEOUT = 1800
DEFAULT_DOWNLOAD_TIMEOUT = 1800
DEFAULT_IDLE = 30
DEFAULT_STALE_AFTER = 900
DEFAULT_RETRY_DELAY = 60
DEFAULT_DAILY_HOURS = 5.0
DEFAULT_ACCOUNTS = "1,2,3,4,5"

LOGS_DIR = os.path.join(HERE, "logs")
ARTIFACTS_DIR = os.path.join(HERE, "artifacts")
TMP_DIR = os.path.join(HERE, "tmp")
LOCKS_DIR = os.path.join(HERE, "locks")

REMOTE_LOG = "/content/out.log"
REMOTE_PID = "/content/job.pid"
REMOTE_EXIT = "/content/job.exit"

DEFAULT_FAIL_MARKERS = (
    "Traceback (most recent call last)",
    "SyntaxError:",
    "ModuleNotFoundError:",
    "ImportError:",
    "MemoryError",
    "CUDA out of memory",
    "RuntimeError: CUDA error",
    "Killed",
    "OOM killed",
)


class KeeperError(Exception):
    """Recoverable keeper failure."""


class SessionLost(KeeperError):
    """The Colab session or its kernel is no longer reachable."""


def log(message):
    print("[keeper] %s" % message, flush=True)


def _ensure_dirs():
    for path in (LOGS_DIR, ARTIFACTS_DIR, TMP_DIR, LOCKS_DIR):
        os.makedirs(path, exist_ok=True)


def _pid_alive(pid):
    """Return True when a local process with this pid is still running."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                ok = ctypes.windll.kernel32.GetExitCodeProcess(
                    handle, ctypes.byref(code))
                return bool(ok) and code.value == STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


_SECRET_1 = re.compile(
    r"(?i)(access_token|refresh_token|id_token|client_secret|password|"
    r"api[_-]?key)(\s*[:=]\s*)([^\s,;\"']+)")
_SECRET_2 = re.compile(r"(?i)(authorization:\s*bearer\s+)(\S+)")


def _redact(text):
    """Remove obvious credential assignments before writing a log."""
    if not text:
        return text
    text = _SECRET_1.sub(lambda m: m.group(1) + m.group(2) + "<redacted>",
                         text)
    text = _SECRET_2.sub(lambda m: m.group(1) + "<redacted>", text)
    return text


def _kill_tree(pid):
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=20,
                           creationflags=0x08000000)
            return
        except Exception:
            pass
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
            return
        except Exception:
            pass
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception:
        pass


def _run_process(cmd, timeout, cwd=None, env=None):
    """Run a command and capture merged output.

    Returns (returncode, output, timed_out).  On timeout the whole process
    tree is killed so a stuck colab.exe cannot keep the keeper alive.
    """
    kwargs = {
        "cwd": cwd,
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    try:
        output, _ = proc.communicate(timeout=timeout)
        return proc.returncode, output or "", False
    except subprocess.TimeoutExpired:
        _kill_tree(proc.pid)
        try:
            output, _ = proc.communicate(timeout=15)
        except Exception:
            output = ""
        return 124, output or "", True


def _append_text(path, text):
    if not text:
        return
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(_redact(text))
        if not text.endswith("\n"):
            handle.write("\n")
        handle.flush()


def _read_tail(path, max_bytes=262144):
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            return handle.read().decode("utf-8", "replace")
    except OSError:
        return ""


def _write_script(name, source):
    _ensure_dirs()
    path = os.path.join(TMP_DIR, "%s_%d.py" % (name, os.getpid()))
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(source)
        if not source.endswith("\n"):
            handle.write("\n")
    return path


def _account_list():
    raw = os.environ.get("JOBS_COLAB_ACCOUNTS", DEFAULT_ACCOUNTS)
    result = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if value > 0 and value not in result:
            result.append(value)
    return result or [1, 2, 3, 4, 5]


def _account_token_ok(account):
    if accounts is None:
        return True
    try:
        path = os.path.join(accounts.cfg_dir(int(account)), "token.json")
    except Exception:
        return False
    try:
        return os.path.exists(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def _runtime_seconds(job):
    started = parse_ts(job.get("started"))
    if started is None:
        return 0.0
    finished = parse_ts(job.get("finished"))
    if finished is None:
        finished = time.time()
    return max(0.0, finished - started)


def _usage_seconds(store, account, window=86400):
    """Rolling usage for one account, clipped to the window."""
    now = time.time()
    since = now - float(window)
    total = 0.0
    for job in store.list():
        if str(job.get("account")) != str(account):
            continue
        started = parse_ts(job.get("started"))
        if started is None:
            continue
        finished = parse_ts(job.get("finished")) or now
        if finished < since:
            continue
        total += max(0.0, finished - max(started, since))
    return total


def _account_conflict(store, job, account, session):
    """Reject a lease that would share an account or session with a live job."""
    for other in store.list(status=ACTIVE_STATUSES):
        if other["id"] == job["id"]:
            continue
        if session and other.get("session") == session:
            return "session %s is already leased by %s" % (
                session, other["id"])
        if account is not None and str(other.get("account")) == str(account):
            return "account %s already has active job %s" % (
                account, other["id"])
    return None


def _select_account(store, job, daily_hours=None, dry_run=False):
    """Choose the least-used account with no active job.

    Returns (account, reason).  account is None when no capacity is available.
    """
    if daily_hours is None:
        try:
            daily_hours = float(os.environ.get("JOBS_DAILY_HOURS",
                                               DEFAULT_DAILY_HOURS))
        except ValueError:
            daily_hours = DEFAULT_DAILY_HOURS

    explicit = job.get("account")
    if explicit is not None:
        if not dry_run and not _account_token_ok(explicit):
            return None, ("account %s has no token.json; run "
                          "colab_accounts.py login %s" % (explicit, explicit))
        return explicit, "explicit account %s" % explicit

    active = store.list(status=ACTIVE_STATUSES)
    busy = {}
    for other in active:
        key = str(other.get("account"))
        busy[key] = busy.get(key, 0) + 1

    candidates = []
    reasons = []
    for account in _account_list():
        key = str(account)
        used_hours = _usage_seconds(store, account) / 3600.0
        if busy.get(key):
            reasons.append("acc%s busy" % account)
            continue
        if daily_hours and daily_hours > 0 and used_hours >= daily_hours:
            reasons.append("acc%s at %.1fh/%.1fh" % (
                account, used_hours, daily_hours))
            continue
        if not dry_run and not _account_token_ok(account):
            reasons.append("acc%s no token" % account)
            continue
        candidates.append((used_hours, account))

    if not candidates:
        return None, ("no account capacity (%s)" %
                      (", ".join(reasons) or "no accounts configured"))

    candidates.sort()
    used_hours, account = candidates[0]
    return account, "acc%s selected (%.1fh used in 24h)" % (
        account, used_hours)


def _session_name(job):
    if job.get("session"):
        return str(job["session"])
    return "jobs-%s" % uuid.uuid4().hex[:8]


def _lease(store, job, dry_run=False):
    """Return (account, session, reason) without writing to the registry."""
    account = job.get("account")
    session = job.get("session")
    if session and account is None:
        return None, None, ("session %s requires an explicit --account"
                            % session)
    if account is None:
        account, reason = _select_account(store, job, dry_run=dry_run)
        if account is None:
            return None, None, reason
    else:
        reason = "explicit account %s" % account
    if not session:
        session = _session_name(job)
    conflict = _account_conflict(store, job, account, session)
    if conflict:
        return None, None, conflict
    return account, session, reason


def _colab_cli(account, *args, **kwargs):
    """Run the colab CLI for one account, with a short token-swap window.

    The existing colab_accounts module owns token backup/restore.  A global
    keeper lock serializes these calls because the upstream CLI stores its
    OAuth token at one hard-coded path.  This limits control-plane
    parallelism, not the number of jobs running on the VMs.
    """
    timeout = kwargs.pop("timeout", 300)
    dry_run = kwargs.pop("dry_run", False)
    if kwargs:
        raise KeeperError("unexpected kwargs: %s" % sorted(kwargs))
    if dry_run:
        return 0, "DRY-RUN: colab %s" % " ".join(str(item) for item in args)
    if accounts is None:
        raise KeeperError("cannot import scripts/colab_accounts.py")
    if not _account_token_ok(account):
        raise KeeperError(
            "account %s has no token.json; run colab_accounts.py login %s"
            % (account, account))

    _ensure_dirs()
    config_dir = accounts.cfg_dir(int(account))
    cmd = [accounts.COLAB, "--config",
           os.path.join(config_dir, "sessions.json")]
    oauth = os.path.join(config_dir, "oauth.json")
    if os.path.exists(oauth):
        cmd += ["-c", oauth]
    cmd += [str(item) for item in args]

    with FileLock(os.path.join(LOCKS_DIR, "colab.lock"), timeout=120):
        backup = accounts.swap_in(int(account))
        try:
            return _run_process(cmd, timeout=timeout)
        finally:
            accounts.swap_out(backup)


CHECK_SOURCE = r'''
import json
import os

def _stat(path):
    try:
        return os.path.getsize(path), os.path.getmtime(path)
    except Exception:
        return -1, 0

payload = {
    "alive": False,
    "pid": None,
    "size": 0,
    "mtime": 0,
    "exit_code": None,
}
try:
    pid = int(open("/content/job.pid").read().strip())
    payload["pid"] = pid
    os.kill(pid, 0)
    payload["alive"] = True
except Exception:
    pass
size, mtime = _stat("/content/out.log")
payload["size"] = size
payload["mtime"] = mtime
try:
    payload["exit_code"] = int(open("/content/job.exit").read().strip())
except Exception:
    pass
print("KEEPER_JSON=" + json.dumps(payload))
'''


PING_SOURCE = r'''
print("KEEPER_PING")
'''


KILL_SOURCE = r'''
import os
import signal

try:
    pid = int(open("/content/job.pid").read().strip())
    os.kill(pid, signal.SIGKILL)
    print("KEEPER_KILLED=%d" % pid)
except Exception as exc:
    print("KEEPER_KILL_ERR=%s" % exc)
'''


LOG_SOURCE = r'''
import os

path = "/content/out.log"
if not os.path.exists(path):
    print("KEEPER_LOG_MISSING")
else:
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - 200000))
        data = handle.read()
    print("KEEPER_LOG_BEGIN")
    print(data.decode("utf-8", "replace"))
    print("KEEPER_LOG_END")
'''


def _ensure_session(job, dry_run=False):
    """Pre-create a GPU session when meta.gpu is set.

    The legacy runners create a CPU session themselves.  For GPU jobs the
    keeper leases the session first, then the runner attaches to it.
    """
    meta = job.get("meta") or {}
    gpu = meta.get("gpu")
    if not gpu or meta.get("no_launch"):
        return
    account = job.get("account")
    session = job.get("session")
    if account is None or not session:
        raise KeeperError("gpu lease requires account and session")
    rc, out, _timed = _colab_cli(account, "status", "-s", session,
                                 timeout=300, dry_run=dry_run)
    text = (out or "").lower()
    if rc == 0 and "not found" not in text:
        log("session %s already exists on acc%s" % (session, account))
        return
    log("leasing %s session %s on acc%s" % (gpu, session, account))
    rc, out, timed_out = _colab_cli(account, "new", "-s", session,
                                    "--gpu", str(gpu), timeout=900,
                                    dry_run=dry_run)
    if timed_out or rc != 0:
        raise KeeperError("GPU lease failed rc=%s: %s"
                          % (rc, (out or "")[-400:]))
    log("session %s ready" % session)


def build_runner_cmd(job, wait=None):
    """Build the argv for the existing runner subprocess.

    account/session/script/wait are always passed through.  Artifact
    --download flags are passed through when meta.runner_downloads is true,
    or when a positive runner wait means the runner will own the fetch.
    """
    meta = job.get("meta") or {}
    runner = str(meta.get("runner") or "run_task").lower()
    if runner in ("auto", ""):
        runner = "run_task"
    if runner not in RUNNERS:
        raise KeeperError("unknown runner %r (expected run_task or exec_bg)"
                          % runner)
    script = job.get("script")
    if not script:
        raise KeeperError("job has no script")
    if not os.path.isabs(script):
        script = os.path.join(ROOT, script)
    if not os.path.exists(script):
        raise KeeperError("script not found: %s" % script)
    account = job.get("account")
    session = job.get("session")
    if account is None or not session:
        raise KeeperError("runner requires account and session")

    if wait is None:
        try:
            wait = int(meta.get("wait", 0))
        except (TypeError, ValueError):
            wait = 0

    if runner == "run_task":
        cmd = [sys.executable, RUNNERS["run_task"], str(account), str(session),
               script, "--wait", str(wait)]
        if meta.get("no_launch"):
            cmd.append("--no-launch")
        pass_downloads = bool(meta.get("runner_downloads")) or wait > 0
        if pass_downloads:
            for artifact in job.get("artifacts") or []:
                remote = artifact.get("remote") if isinstance(artifact, dict) \
                    else artifact
                if remote:
                    cmd += ["--download", str(remote)]
        return cmd

    return [sys.executable, RUNNERS["exec_bg"], str(session), script,
            "--wait", str(wait), "--acc", str(account)]


def _runner_log_path(job):
    return os.path.join(LOGS_DIR, "%s.runner.log" % job["id"])


def _run_runner(cmd, job, timeout):
    """Run a legacy runner under the global token/launcher lock.

    colab_run_task.py performs its own short token swaps.  colab_exec_bg.py
    does not, so the keeper swaps the token around that whole subprocess.
    Holding the same lock used by _colab_cli prevents another keeper from
    interleaving a token swap with the runner.
    """
    meta = job.get("meta") or {}
    runner = str(meta.get("runner") or "run_task").lower()
    if runner in ("auto", ""):
        runner = "run_task"
    _ensure_dirs()
    with FileLock(os.path.join(LOCKS_DIR, "colab.lock"), timeout=120):
        if runner == "exec_bg":
            if accounts is None:
                raise KeeperError("cannot import scripts/colab_accounts.py")
            backup = accounts.swap_in(int(job["account"]))
            try:
                return _run_process(cmd, timeout=timeout, cwd=ROOT)
            finally:
                accounts.swap_out(backup)
        return _run_process(cmd, timeout=timeout, cwd=ROOT)


def _launch(store, job, args):
    """Launch through an existing runner and transition to running."""
    meta = job.get("meta") or {}
    if meta.get("no_launch"):
        log("%s: --no-launch, attaching to an existing VM job" % job["id"])
        return store.update(job["id"], status="running",
                            started=job.get("started") or now_iso(),
                            meta={"launch_rc": 0, "launch_mode": "no_launch"})

    _ensure_session(job, dry_run=False)
    cmd = build_runner_cmd(job)
    runner_log = _runner_log_path(job)
    _append_text(runner_log, "\n=== attempt %d at %s ===\n$ %s\n"
                 % (job.get("attempts") or 0, now_iso(),
                    subprocess.list2cmdline(cmd)))

    timeout = args.launch_timeout or int(
        meta.get("launch_timeout") or DEFAULT_LAUNCH_TIMEOUT)
    rc, output, timed_out = _run_runner(cmd, job, timeout)
    _append_text(runner_log, output)
    log("%s: launch rc=%s%s" % (job["id"], rc,
                                " (timeout)" if timed_out else ""))

    if timed_out:
        return _retry_or_fail(store, job,
                              "launch timed out after %ss" % timeout,
                              retryable=True,
                              meta={"runner_log": runner_log})
    if rc != 0:
        return _retry_or_fail(store, job,
                              "launch failed rc=%s: %s"
                              % (rc, (output or "")[-500:]),
                              retryable=True,
                              meta={"runner_log": runner_log,
                                    "launch_rc": rc})

    text = (output or "").lower()
    if "allocation refused" in text or (
            "quota" in text and "exceeded" in text):
        return _retry_or_fail(store, job,
                              "Colab refused the allocation: %s"
                              % (output or "")[-500:],
                              retryable=True,
                              meta={"runner_log": runner_log,
                                    "launch_rc": rc})

    return store.update(
        job["id"], status="running",
        started=job.get("started") or now_iso(),
        meta={"runner_log": runner_log, "launch_rc": rc,
              "launch_finished": now_iso(),
              "runner": (job.get("meta") or {}).get("runner", "run_task")})


def _parse_check_output(output):
    payload = None
    for line in (output or "").splitlines():
        if "KEEPER_JSON=" in line:
            text = line.split("KEEPER_JSON=", 1)[1].strip()
            try:
                payload = json.loads(text)
            except ValueError:
                payload = None
            if payload is not None:
                break
    if payload is None:
        match = re.search(r"ALIVE=([01])\s+SIZE=(-?\d+)", output or "")
        if match:
            payload = {
                "alive": match.group(1) == "1",
                "pid": None,
                "size": int(match.group(2)),
                "mtime": 0,
                "exit_code": None,
            }
    if not isinstance(payload, dict):
        raise KeeperError("cannot parse remote check output: %s"
                          % (output or "")[-500:])
    payload["alive"] = bool(payload.get("alive"))
    try:
        payload["size"] = int(payload.get("size", 0))
    except (TypeError, ValueError):
        payload["size"] = 0
    try:
        payload["mtime"] = float(payload.get("mtime", 0) or 0)
    except (TypeError, ValueError):
        payload["mtime"] = 0.0
    if payload.get("pid") is not None:
        try:
            payload["pid"] = int(payload["pid"])
        except (TypeError, ValueError):
            payload["pid"] = None
    if payload.get("exit_code") is not None:
        try:
            payload["exit_code"] = int(payload["exit_code"])
        except (TypeError, ValueError):
            payload["exit_code"] = None
    return payload


def _remote_check(job, dry_run=False):
    account = job.get("account")
    session = job.get("session")
    path = _write_script("check", CHECK_SOURCE)
    rc, output, timed_out = _colab_cli(
        account, "exec", "-s", session, "-f", path, "--timeout", "120",
        timeout=180, dry_run=dry_run)
    if dry_run:
        return {"alive": True, "pid": 0, "size": 0, "mtime": 0,
                "exit_code": None, "dry_run": True}
    if timed_out:
        raise KeeperError("remote check timed out")
    lower = (output or "").lower()
    if "not found" in lower or "session lost" in lower or "lost session" in lower:
        raise SessionLost((output or "")[-500:])
    if rc != 0 and "KEEPER_JSON=" not in (output or ""):
        raise KeeperError("remote check rc=%s: %s"
                          % (rc, (output or "")[-500:]))
    return _parse_check_output(output)


def _ping(job, dry_run=False):
    account = job.get("account")
    session = job.get("session")
    path = _write_script("ping", PING_SOURCE)
    rc, output, timed_out = _colab_cli(
        account, "exec", "-s", session, "-f", path, "--timeout", "60",
        timeout=120, dry_run=dry_run)
    if dry_run:
        return True
    lower = (output or "").lower()
    if "not found" in lower or "session lost" in lower:
        raise SessionLost((output or "")[-500:])
    if timed_out or rc != 0:
        raise KeeperError("keepalive ping rc=%s: %s"
                          % (rc, (output or "")[-300:]))
    if "KEEPER_PING" not in (output or ""):
        raise KeeperError("keepalive ping produced no marker")
    return True


def _read_remote_log(job):
    path = _write_script("readlog", LOG_SOURCE)
    rc, output, _timed = _colab_cli(
        job.get("account"), "exec", "-s", job.get("session"), "-f", path,
        "--timeout", "120", timeout=180)
    if rc != 0:
        return None
    if "KEEPER_LOG_MISSING" in (output or ""):
        return ""
    if "KEEPER_LOG_BEGIN" not in (output or ""):
        return None
    body = output.split("KEEPER_LOG_BEGIN", 1)[1]
    body = body.rsplit("KEEPER_LOG_END", 1)[0]
    return body.lstrip("\r\n")


def _download(job, remote, local, timeout=None, kind="file"):
    """Download one remote path.  Returns (ok, message)."""
    timeout = timeout or DEFAULT_DOWNLOAD_TIMEOUT
    local = os.path.abspath(local)
    parent = os.path.dirname(local)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if kind == "dir":
        if os.path.isdir(local):
            shutil.rmtree(local, ignore_errors=True)
        rc, output, timed_out = _colab_cli(
            job.get("account"), "download", "-s", job.get("session"),
            remote, local, timeout=timeout)
        if timed_out:
            return False, "download timed out after %ss" % timeout
        if os.path.exists(local):
            return True, (output or "")[-300:]
        return False, "rc=%s %s" % (rc, (output or "")[-300:])

    part = local + ".part"
    try:
        if os.path.exists(part):
            os.remove(part)
    except OSError:
        pass
    rc, output, timed_out = _colab_cli(
        job.get("account"), "download", "-s", job.get("session"),
        remote, part, timeout=timeout)
    if timed_out:
        try:
            os.remove(part)
        except OSError:
            pass
        return False, "download timed out after %ss" % timeout
    if os.path.exists(part) and os.path.getsize(part) > 0:
        try:
            os.replace(part, local)
        except OSError as exc:
            return False, "cannot move download into place: %s" % exc
        return True, (output or "")[-300:]
    try:
        if os.path.exists(part):
            os.remove(part)
    except OSError:
        pass
    return False, "rc=%s %s" % (rc, (output or "")[-300:])


def _path_size(path):
    if not os.path.exists(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def _failure_scan(log_path, meta):
    """Return (failed, reason) based on markers in the tail of the log."""
    text = _read_tail(log_path)
    success_marker = meta.get("success_marker")
    if success_marker:
        if str(success_marker) in text:
            return False, None
        return True, "success marker not found: %s" % success_marker
    if meta.get("ignore_fail_markers"):
        return False, None
    markers = meta.get("fail_markers") or DEFAULT_FAIL_MARKERS
    if isinstance(markers, str):
        markers = [markers]
    for marker in markers:
        if marker and str(marker) in text:
            return True, "failure marker in log: %s" % marker
    return False, None


def _mark(store, job, status, error=None, meta=None):
    fields = {"status": status}
    if error is not None:
        fields["error"] = error
    if status in TERMINAL_STATUSES:
        fields["finished"] = now_iso()
    if meta:
        return store.update(job["id"], meta=meta, **fields)
    return store.update(job["id"], **fields)


def _retry_or_fail(store, job, error, retryable=False, meta=None):
    """Return a retried job to pending, or mark it failed."""
    current = store.get(job["id"])
    if current is None:
        return "lost"
    if current["status"] in TERMINAL_STATUSES:
        return current["status"]

    meta = dict(meta or {})
    meta["last_error"] = error
    try:
        max_attempts = int((current.get("meta") or {}).get("max_attempts", 1))
    except (TypeError, ValueError):
        max_attempts = 1
    attempts = int(current.get("attempts") or 0)
    if retryable and attempts < max_attempts:
        fields = {
            "status": "pending",
            "error": error,
            "finished": None,
            "keepalive_until": None,
        }
        lower = error.lower()
        if ("session" in lower or "not found" in lower
                or "lost" in lower):
            fields["session"] = None
        if "quota" in lower or "allocation" in lower:
            if not (current.get("meta") or {}).get("explicit_account"):
                fields["account"] = None
            fields["session"] = None
        meta["retry_at"] = iso_plus(
            int((current.get("meta") or {}).get("retry_delay",
                                                DEFAULT_RETRY_DELAY)))
        meta["keeper_pid"] = None
        meta["keeper_host"] = None
        updated = store.update(current["id"], meta=meta, **fields)
        log("%s: retry scheduled (%s/%s): %s"
            % (current["id"], attempts, max_attempts, error))
        return updated["status"]

    meta["failure_reason"] = error
    _mark(store, current, "failed", error=error, meta=meta)
    log("%s: failed: %s" % (current["id"], error))
    return "failed"


def _fetch(store, job, args):
    """Download the log and artifacts, then decide done/failed/cancelled."""
    current = store.get(job["id"]) or job
    meta = dict(current.get("meta") or {})
    if current["status"] == "cancelled" or meta.get("cancel_requested"):
        return "cancelled"

    latest = store.get(job["id"])
    if latest is None:
        return "lost"
    if latest["status"] == "cancelled" or \
            (latest.get("meta") or {}).get("cancel_requested"):
        return "cancelled"
    store.update(job["id"], status="fetching",
                 meta={"fetch_started": now_iso()})
    log_path = os.path.join(LOGS_DIR, "%s.log" % job["id"])
    download_timeout = args.download_timeout or int(
        meta.get("download_timeout") or DEFAULT_DOWNLOAD_TIMEOUT)

    log_ok, log_message = _download(
        current, REMOTE_LOG, log_path, timeout=download_timeout, kind="file")
    log_fallback = False
    if not log_ok:
        remote_text = _read_remote_log(current)
        if remote_text is not None:
            with open(log_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(remote_text)
                if not remote_text.endswith("\n"):
                    handle.write("\n")
            log_ok = True
            log_fallback = True
            log_message = "downloaded via exec fallback"
    if not log_ok:
        log("%s: log download failed: %s" % (job["id"], log_message))

    artifacts = []
    artifact_errors = []
    for artifact in current.get("artifacts") or []:
        entry = dict(artifact)
        remote = entry.get("remote")
        if not remote:
            continue
        remote = str(remote)
        kind = str(entry.get("kind") or "file")
        local = entry.get("local")
        if not local:
            base = os.path.basename(remote.rstrip("/")) or "artifact"
            local = os.path.join(ARTIFACTS_DIR, job["id"], base)
        elif not os.path.isabs(local):
            local = os.path.join(ARTIFACTS_DIR, job["id"], local)
        ok, message = _download(current, remote, local,
                                timeout=download_timeout, kind=kind)
        entry["local"] = os.path.abspath(local)
        entry["ok"] = bool(ok)
        entry["size"] = _path_size(local) if ok else 0
        entry["error"] = None if ok else message
        artifacts.append(entry)
        if not ok:
            artifact_errors.append("%s: %s" % (remote, message))
            log("%s: artifact failed: %s" % (job["id"], remote))

    meta.update({
        "fetch_finished": now_iso(),
        "log_fallback": log_fallback,
        "log_message": log_message,
        "artifact_errors": artifact_errors,
        "runtime_sec": int(_runtime_seconds(current)),
    })
    if not log_ok:
        meta["log_error"] = log_message

    failure = None
    exit_code = meta.get("last_exit_code")
    if exit_code is not None and int(exit_code) != 0:
        failure = "remote job exit code %s" % exit_code
    if failure is None and not log_ok and not meta.get("allow_missing_log"):
        failure = "log download failed: %s" % log_message
    if failure is None and log_ok:
        failed, reason = _failure_scan(log_path, meta)
        if failed:
            failure = reason
    if failure is None and meta.get("require_artifacts") and artifact_errors:
        failure = "required artifact(s) failed: %s" % "; ".join(artifact_errors)

    store.update(job["id"], log_path=log_path, artifacts=artifacts, meta=meta)
    latest = store.get(job["id"])
    if latest is not None and (
            latest["status"] == "cancelled"
            or (latest.get("meta") or {}).get("cancel_requested")):
        return "cancelled"
    if failure:
        meta["failure_reason"] = failure
        _mark(store, current, "failed", error=failure, meta=meta)
        return "failed"
    _mark(store, current, "done", error=None, meta=meta)
    log("%s: done (log %s, %d artifact(s))"
        % (job["id"], log_path, len(artifacts)))
    return "done"


def _monitor(store, job, args):
    """Poll until the remote pid exits, the session is lost, or time is up."""
    meta = dict(job.get("meta") or {})
    try:
        poll = int(args.poll or meta.get("poll") or DEFAULT_POLL)
    except (TypeError, ValueError):
        poll = DEFAULT_POLL
    try:
        keepalive = int(args.keepalive_every
                        or meta.get("keepalive_every") or DEFAULT_KEEPALIVE)
    except (TypeError, ValueError):
        keepalive = DEFAULT_KEEPALIVE
    try:
        max_runtime = int(args.max_runtime
                          or meta.get("max_runtime") or DEFAULT_MAX_RUNTIME)
    except (TypeError, ValueError):
        max_runtime = DEFAULT_MAX_RUNTIME

    started = parse_ts(job.get("started")) or time.time()
    attempt_started = parse_ts(meta.get("attempt_started")) or started
    deadline = attempt_started + max_runtime
    last_size = meta.get("last_size")
    last_mtime = meta.get("last_mtime")
    last_change = parse_ts(meta.get("last_change")) or time.time()
    last_ping = parse_ts(meta.get("last_ping")) or 0.0
    errors = 0
    first = True

    while True:
        current = store.get(job["id"])
        if current is None:
            return "lost"
        if current["status"] == "cancelled" or \
                (current.get("meta") or {}).get("cancel_requested"):
            _stop_remote(current, dry_run=False)
            return "cancelled"

        now = time.time()
        if now >= deadline:
            _stop_remote(current, dry_run=False)
            return _retry_or_fail(
                store, current,
                "maximum runtime exceeded (%ss)" % max_runtime,
                retryable=False,
                meta={"runtime_sec": int(now - started),
                      "attempt_runtime_sec": int(now - attempt_started)})

        if not first:
            sleep_for = max(1.0, min(float(poll), deadline - time.time()))
            time.sleep(sleep_for)
        first = False

        try:
            check = _remote_check(current)
            errors = 0
        except SessionLost as exc:
            return _retry_or_fail(store, current,
                                  "session lost: %s" % exc,
                                  retryable=True)
        except KeeperError as exc:
            errors += 1
            store.update(job["id"], meta={
                "last_poll": now_iso(),
                "poll_error": str(exc)[-500:],
                "poll_errors": errors,
            })
            log("%s: poll error %d/3: %s" % (job["id"], errors, exc))
            if errors >= 3:
                return _retry_or_fail(store, current,
                                      "lost contact with session: %s" % exc,
                                      retryable=True)
            continue

        now = time.time()
        changed = (check.get("size") != last_size
                   or check.get("mtime") != last_mtime)
        if changed:
            last_change = now
        last_size = check.get("size")
        last_mtime = check.get("mtime")

        meta_update = {
            "last_poll": now_iso(),
            "last_size": check.get("size"),
            "last_mtime": check.get("mtime"),
            "last_alive": bool(check.get("alive")),
            "remote_pid": check.get("pid"),
            "last_exit_code": check.get("exit_code"),
            "runtime_sec": int(max(0.0, now - started)),
            "keepalive_until": iso_plus(max(keepalive * 2, 300)),
            "last_change": datetime.fromtimestamp(
                last_change, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        store.update(job["id"], meta=meta_update)
        meta.update(meta_update)

        if check.get("exit_code") is not None:
            latest = store.get(job["id"])
            if latest is not None and (
                    latest["status"] == "cancelled"
                    or (latest.get("meta") or {}).get("cancel_requested")):
                return "cancelled"
            store.update(job["id"], status="fetching")
            return "fetching"
        if not check.get("alive"):
            pid = check.get("pid")
            size = check.get("size") or 0
            if pid is None and size <= 0 and (now - attempt_started) < 120:
                log("%s: waiting for pid file" % job["id"])
                continue
            latest = store.get(job["id"])
            if latest is not None and (
                    latest["status"] == "cancelled"
                    or (latest.get("meta") or {}).get("cancel_requested")):
                return "cancelled"
            store.update(job["id"], status="fetching")
            return "fetching"

        if (not changed) and (now - last_change) >= keepalive \
                and (now - last_ping) >= keepalive:
            try:
                _ping(current)
                last_ping = now
                count = int(meta.get("keepalive_count") or 0) + 1
                meta["keepalive_count"] = count
                store.update(job["id"], meta={
                    "last_ping": now_iso(),
                    "keepalive_count": count,
                    "keepalive_until": iso_plus(max(keepalive * 2, 300)),
                })
                log("%s: keepalive ping (log quiet %ds)"
                    % (job["id"], int(now - last_change)))
            except SessionLost as exc:
                return _retry_or_fail(store, current,
                                      "session lost during keepalive: %s" % exc,
                                      retryable=True)
            except KeeperError as exc:
                log("%s: keepalive failed (will retry): %s" % (job["id"], exc))


def _stop_remote(job, dry_run=False):
    """Kill the remote pid, if any.  Does not stop the session."""
    if not job.get("account") or not job.get("session"):
        return
    try:
        check = _remote_check(job, dry_run=dry_run)
    except (SessionLost, KeeperError):
        return
    if not check.get("alive") or not check.get("pid"):
        return
    path = _write_script("kill", KILL_SOURCE)
    try:
        rc, output, _timed = _colab_cli(
            job.get("account"), "exec", "-s", job.get("session"), "-f", path,
            "--timeout", "60", timeout=120, dry_run=dry_run)
        log("%s: remote kill rc=%s %s"
            % (job["id"], rc, (output or "").strip()[:120]))
    except (SessionLost, KeeperError) as exc:
        log("%s: remote kill skipped: %s" % (job["id"], exc))


def _release(store, job, args):
    """Stop the Colab session unless the job asked to keep it."""
    current = store.get(job["id"]) or job
    meta = dict(current.get("meta") or {})
    if args.keep_session or meta.get("keep_session"):
        return
    if meta.get("released"):
        return
    if not current.get("account") or not current.get("session"):
        return
    try:
        rc, output, timed_out = _colab_cli(
            current.get("account"), "stop", "-s", current.get("session"),
            timeout=600)
        update = {
            "released": True,
            "released_at": now_iso(),
            "release_rc": rc,
        }
        if timed_out or rc != 0:
            update["release_error"] = (output or "")[-400:]
            log("%s: release rc=%s %s" % (job["id"], rc,
                                          (output or "")[-160:]))
        else:
            log("%s: session %s released" % (job["id"],
                                             current.get("session")))
        store.update(job["id"], meta=update)
    except (KeeperError, StoreError) as exc:
        log("%s: release failed: %s" % (job["id"], exc))
        try:
            store.update(job["id"], meta={"release_error": str(exc)[-400:]})
        except StoreError:
            pass


def process_job(store, job, args):
    """Run one job through launch, monitor, fetch, and release."""
    job_id = job["id"]
    result = job["status"]
    try:
        current = store.get(job_id)
        if current is None:
            return "lost"
        if current["status"] == "cancelled":
            return "cancelled"
        if current["status"] == "pending":
            return "pending"
        if current["status"] == "starting":
            launched = _launch(store, current, args)
            if isinstance(launched, str):
                return launched
            current = launched
            result = current["status"]
        if result == "running":
            result = _monitor(store, current, args)
            if result != "fetching":
                return result
        if result == "fetching":
            return _fetch(store, current, args)
        return result
    except Exception as exc:
        detail = traceback.format_exc()
        log("%s: keeper exception: %s" % (job_id, exc))
        try:
            _retry_or_fail(store, job, "keeper exception: %s" % exc,
                           retryable=False,
                           meta={"traceback": detail[-4000:]})
        except Exception:
            pass
        return "failed"
    finally:
        try:
            current = store.get(job_id)
            if current is not None:
                _release(store, current, args)
        except Exception as exc:
            log("%s: release cleanup error: %s" % (job_id, exc))


def _claim_fields(job, account, session, reason):
    return {
        "status": "starting",
        "account": account,
        "session": session,
        "started": job.get("started") or now_iso(),
        "keepalive_until": iso_plus(300),
        "meta": {
            "keeper_pid": os.getpid(),
            "keeper_host": socket.gethostname(),
            "keeper_started": now_iso(),
            "attempt_started": now_iso(),
            "lease_reason": reason,
            "explicit_account": job.get("account") is not None,
        },
    }


def claim_next(store, args):
    """Claim the oldest pending job with account capacity."""
    now = time.time()
    reason = "no pending jobs"
    for job in store.list(status="pending", oldest_first=True):
        meta = job.get("meta") or {}
        retry_at = parse_ts(meta.get("retry_at"))
        if retry_at is not None and retry_at > now:
            reason = "next retry at %s" % meta.get("retry_at")
            continue
        account, session, lease_reason = _lease(store, job, dry_run=False)
        if account is None:
            reason = lease_reason
            continue
        claimed = store.claim(
            job["id"], from_statuses=("pending",),
            increment={"attempts": 1},
            **_claim_fields(job, account, session, lease_reason))
        if claimed is not None:
            log("%s: claimed acc%s session %s (%s)"
                % (job["id"], account, session, lease_reason))
            return claimed, lease_reason
        reason = "lost claim race"
    return None, reason


def claim_specific(store, job_id, args):
    """Claim one explicit job, including an active job (adoption)."""
    job = store.get(job_id)
    if job is None:
        return None, "job not found: %s" % job_id
    if job["status"] in TERMINAL_STATUSES:
        return job, "job is already %s" % job["status"]
    if job["status"] == "pending":
        account, session, reason = _lease(store, job, dry_run=False)
        if account is None:
            return None, reason
        claimed = store.claim(
            job["id"], from_statuses=("pending",),
            increment={"attempts": 1},
            **_claim_fields(job, account, session, reason))
        return claimed, reason
    claimed = store.claim(
        job["id"], from_statuses=ACTIVE_STATUSES,
        meta={"keeper_pid": os.getpid(),
              "keeper_host": socket.gethostname(),
              "adopted": True,
              "adopted_at": now_iso()})
    return claimed, "adopted active job"


def adopt_active(store, args):
    """Adopt an active job whose keeper is gone (same host pid check)."""
    if not args.adopt:
        return None
    host = socket.gethostname()
    for job in store.list(status=ACTIVE_STATUSES, oldest_first=True):
        meta = job.get("meta") or {}
        keeper_pid = meta.get("keeper_pid")
        keeper_host = meta.get("keeper_host")
        if keeper_host == host and _pid_alive(keeper_pid):
            continue
        claimed = store.claim(
            job["id"], from_statuses=ACTIVE_STATUSES,
            meta={"keeper_pid": os.getpid(),
                  "keeper_host": host,
                  "adopted": True,
                  "adopted_at": now_iso()})
        if claimed is not None:
            log("%s: adopted stale %s job" % (job["id"], job["status"]))
            return claimed
    return None


def reap_stale(store, stale_after=DEFAULT_STALE_AFTER, dry_run=False):
    """Mark active jobs with a stale keeper heartbeat as lost."""
    now = time.time()
    host = socket.gethostname()
    lost = []
    for job in store.list(status=ACTIVE_STATUSES, oldest_first=True):
        meta = job.get("meta") or {}
        keeper_pid = meta.get("keeper_pid")
        keeper_host = meta.get("keeper_host")
        if keeper_host == host and _pid_alive(keeper_pid):
            continue
        reference = (parse_ts(meta.get("keepalive_until"))
                     or parse_ts(job.get("started"))
                     or parse_ts(job.get("created")) or 0)
        if now - reference < float(stale_after):
            continue
        error = ("keeper heartbeat stale for %ds (last keepalive %s)"
                 % (int(now - reference),
                    meta.get("keepalive_until") or job.get("started")
                    or job.get("created")))
        lost.append({"id": job["id"], "status": job["status"],
                     "error": error})
        if not dry_run:
            try:
                _mark(store, job, "lost", error=error,
                      meta={"reaped": True, "reaped_at": now_iso()})
            except StoreError:
                pass
    return lost


def keepalive_job(store, job_id, dry_run=False):
    """Ping one active session and refresh its keepalive deadline."""
    job = store.get(job_id)
    if job is None:
        return {"id": job_id, "ok": False, "error": "job not found"}
    if job["status"] not in ACTIVE_STATUSES:
        return {"id": job_id, "ok": False,
                "error": "job is %s, not active" % job["status"]}
    if dry_run:
        return {"id": job_id, "ok": True, "dry_run": True,
                "account": job.get("account"), "session": job.get("session")}
    try:
        _ping(job)
    except SessionLost as exc:
        _mark(store, job, "lost", error="session lost: %s" % exc,
              meta={"last_ping": now_iso()})
        return {"id": job_id, "ok": False, "lost": True, "error": str(exc)}
    except KeeperError as exc:
        return {"id": job_id, "ok": False, "error": str(exc)}
    updated = store.update(job_id, meta={
        "last_ping": now_iso(),
        "keepalive_until": iso_plus(600),
        "keepalive_count": int((job.get("meta") or {}).get(
            "keepalive_count") or 0) + 1,
    })
    return {"id": job_id, "ok": True, "keepalive_until":
            updated.get("keepalive_until")}


def cancel_job(store, job_id, dry_run=False, local_only=False):
    """Cancel a job.  Remote kill/stop is attempted unless local_only."""
    job = store.get(job_id)
    if job is None:
        return {"id": job_id, "ok": False, "error": "job not found"}
    if job["status"] in TERMINAL_STATUSES:
        return {"id": job_id, "ok": True, "status": job["status"],
                "message": "already terminal"}
    if dry_run:
        return {"id": job_id, "ok": True, "dry_run": True,
                "status": job["status"], "remote": not local_only}

    if job["status"] == "pending":
        updated = store.update(
            job_id, status="cancelled", error="cancelled by user",
            meta={"cancel_requested": True, "cancel_finished": now_iso()})
        return {"id": job_id, "ok": True, "status": updated["status"]}

    store.update(job_id, meta={"cancel_requested": True,
                               "cancel_requested_at": now_iso()})
    cancel_error = None
    if not local_only:
        try:
            _stop_remote(job)
        except Exception as exc:
            cancel_error = str(exc)
        try:
            _release(store, job, argparse.Namespace(keep_session=False))
        except Exception as exc:
            cancel_error = cancel_error or str(exc)
    updated = store.update(
        job_id, status="cancelled", error="cancelled by user",
        meta={"cancel_finished": now_iso(),
              "cancel_error": cancel_error})
    return {"id": job_id, "ok": True, "status": updated["status"],
            "cancel_error": cancel_error}


def plan_job(store, args):
    """Build a dry-run plan without mutating state or calling Colab."""
    job = None
    if args.job:
        job = store.get(args.job)
        if job is None:
            result = {"job": None, "error": "job not found: %s" % args.job}
            _print_plan(result, args)
            return 1
    else:
        pending = store.list(status="pending", oldest_first=True, limit=1)
        active = store.list(status=ACTIVE_STATUSES, oldest_first=True, limit=1)
        job = pending[0] if pending else (active[0] if active else None)
    if job is None:
        result = {"job": None, "error": "no pending or active jobs"}
        _print_plan(result, args)
        return 0

    account = job.get("account")
    session = job.get("session")
    reason = "existing lease"
    if job["status"] == "pending":
        account, session, reason = _lease(store, job, dry_run=True)
    planned = dict(job)
    planned["account"] = account
    planned["session"] = session
    meta = planned.get("meta") or {}
    commands = {}
    if account is not None and session:
        if meta.get("gpu"):
            commands["lease"] = ["colab", "new", "-s", session,
                                 "--gpu", str(meta.get("gpu"))]
        try:
            commands["launch"] = build_runner_cmd(planned)
        except KeeperError as exc:
            commands["launch_error"] = str(exc)
        commands["poll"] = ["colab", "exec", "-s", session, "-f",
                            "<scripts/jobs/tmp/check.py>", "--timeout", "120"]
        commands["keepalive"] = ["colab", "exec", "-s", session, "-f",
                                 "<scripts/jobs/tmp/ping.py>",
                                 "--timeout", "60"]
        commands["fetch_log"] = [
            "colab", "download", "-s", session, REMOTE_LOG,
            os.path.join(LOGS_DIR, "%s.log" % job["id"])]
        fetch_artifacts = []
        for artifact in job.get("artifacts") or []:
            remote = artifact.get("remote") if isinstance(artifact, dict) \
                else artifact
            if not remote:
                continue
            base = os.path.basename(str(remote).rstrip("/")) or "artifact"
            fetch_artifacts.append([
                "colab", "download", "-s", session, str(remote),
                os.path.join(ARTIFACTS_DIR, job["id"], base)])
        commands["fetch_artifacts"] = fetch_artifacts
        commands["release"] = ["colab", "stop", "-s", session]
    result = {
        "job": job["id"],
        "status": job["status"],
        "account": account,
        "session": session,
        "lease_reason": reason,
        "runner": meta.get("runner", "run_task"),
        "poll_seconds": int(meta.get("poll") or DEFAULT_POLL),
        "keepalive_seconds": int(meta.get("keepalive_every")
                                 or DEFAULT_KEEPALIVE),
        "commands": commands,
    }
    _print_plan(result, args)
    return 0


def _print_plan(result, args):
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    if result.get("error"):
        log(result["error"])
        return
    log("dry-run plan for %s (status %s)"
        % (result.get("job"), result.get("status")))
    log("account=%s session=%s (%s)"
        % (result.get("account"), result.get("session"),
           result.get("lease_reason")))
    for name, command in (result.get("commands") or {}).items():
        if isinstance(command, list) and command and isinstance(
                command[0], list):
            for item in command:
                log("%s: %s" % (name, subprocess.list2cmdline(item)))
        elif isinstance(command, list):
            log("%s: %s" % (name, subprocess.list2cmdline(command)))
        else:
            log("%s: %s" % (name, command))


def run_forever(store, args):
    if args.dry_run:
        return plan_job(store, args)

    if args.job:
        job, reason = claim_specific(store, args.job, args)
        if job is None:
            log(reason)
            return 1
        if job["status"] in TERMINAL_STATUSES:
            log("%s is already %s" % (job["id"], job["status"]))
            return 0
        result = process_job(store, job, args)
        log("%s -> %s" % (job["id"], result))
        return 0

    while True:
        try:
            lost = reap_stale(store, stale_after=args.stale_after)
            for item in lost:
                log("reaped %s as lost: %s" % (item["id"], item["error"]))
        except Exception as exc:
            log("reap error: %s" % exc)

        job = adopt_active(store, args)
        reason = "adopted"
        if job is None:
            job, reason = claim_next(store, args)
        if job is None:
            if args.once:
                log("no work: %s" % reason)
                return 0
            time.sleep(max(1, int(args.idle)))
            continue

        result = process_job(store, job, args)
        log("%s -> %s" % (job["id"], result))
        if args.once:
            return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Lease and monitor Colab jobs from the JSON registry.")
    parser.add_argument("--state", help="state.json path (default: scripts/jobs/state.json)")
    parser.add_argument("--job", help="process one job id")
    parser.add_argument("--once", action="store_true",
                        help="process at most one job, then exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan; do not call Colab or write state")
    parser.add_argument("--json", action="store_true",
                        help="JSON output for --dry-run")
    parser.add_argument("--poll", type=int, help="poll interval seconds")
    parser.add_argument("--keepalive-every", type=int,
                        help="quiet-job keepalive interval seconds")
    parser.add_argument("--max-runtime", type=int,
                        help="maximum runtime seconds")
    parser.add_argument("--idle", type=int, default=DEFAULT_IDLE,
                        help="idle sleep seconds when no job is ready")
    parser.add_argument("--launch-timeout", type=int,
                        help="runner launch timeout seconds")
    parser.add_argument("--download-timeout", type=int,
                        help="artifact download timeout seconds")
    parser.add_argument("--stale-after", type=int,
                        default=DEFAULT_STALE_AFTER,
                        help="seconds before a missing heartbeat is lost")
    parser.add_argument("--no-adopt", action="store_true",
                        help="do not resume active jobs from dead keepers")
    parser.add_argument("--keep-session", action="store_true",
                        help="do not stop the Colab session after the job")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    args.adopt = not args.no_adopt

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    store = JobStore(args.state)
    try:
        return run_forever(store, args)
    except StoreError as exc:
        print("store error: %s" % exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
