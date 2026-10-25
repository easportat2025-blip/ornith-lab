# -*- coding: utf-8 -*-
"""store.py - JSON job registry for scripts/jobs.

ASCII-only source. Standard library only.

The registry is a single JSON document:

    {
      "version": 1,
      "updated": "2026-10-24T12:00:00Z",
      "jobs": {
        "job-20261024-120000-a1b2c3": { ... }
      }
    }

Every read-modify-write cycle runs under an OS file lock and writes through a
temporary file followed by os.replace().  That keeps the registry readable if
a keeper process is killed in the middle of an update.

Job fields (all always present after normalization):
    id, backend, account, session, script, args, status, created, started,
    finished, pid, log_path, artifacts, keepalive_until, attempts, error, meta

Statuses:
    pending, starting, running, fetching, done, failed, cancelled, lost

No credentials belong in this file.  Account tokens stay in the existing
scripts/colab_accounts/accN directories and are handled by the existing
colab_accounts / colab_run_task modules.
"""

import copy
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone

STATUSES = (
    "pending",
    "starting",
    "running",
    "fetching",
    "done",
    "failed",
    "cancelled",
    "lost",
)

ACTIVE_STATUSES = frozenset(("starting", "running", "fetching"))
TERMINAL_STATUSES = frozenset(("done", "failed", "cancelled", "lost"))

JOB_FIELDS = (
    "id",
    "backend",
    "account",
    "session",
    "script",
    "args",
    "status",
    "created",
    "started",
    "finished",
    "pid",
    "log_path",
    "artifacts",
    "keepalive_until",
    "attempts",
    "error",
    "meta",
)

STATE_VERSION = 1
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STATE_PATH = os.path.join(HERE, "state.json")

_STATUS_ALIASES = {
    "queued": "pending",
    "waiting": "pending",
    "launching": "starting",
    "leased": "starting",
    "active": "running",
    "in_progress": "running",
    "downloading": "fetching",
    "fetch": "fetching",
    "success": "done",
    "succeeded": "done",
    "completed": "done",
    "complete": "done",
    "error": "failed",
    "failure": "failed",
    "timeout": "failed",
    "canceled": "cancelled",
    "aborted": "cancelled",
    "dead": "lost",
    "missing": "lost",
}


class StoreError(Exception):
    """Raised for corrupt state, bad fields, or lock timeouts."""


def now_iso():
    """Current UTC time as an ISO-8601 string with a Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_plus(seconds):
    """UTC time `seconds` from now as an ISO-8601 string."""
    return datetime.fromtimestamp(time.time() + float(seconds),
                                  timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value):
    """Parse an ISO-8601 string or epoch number into epoch seconds.

    Returns None for empty or unparseable values.  Naive timestamps are
    treated as UTC, matching the format written by this module.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def _to_iso(value):
    """Normalize a timestamp to the registry's second-precision UTC format."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value),
                                      timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = str(value).strip()
    if not text:
        return None
    ts = parse_ts(text)
    if ts is None:
        return text
    return datetime.fromtimestamp(ts,
                                  timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_job_id():
    """Generate a short, sortable, unique job id."""
    return "job-%s-%s" % (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        uuid.uuid4().hex[:6],
    )


def _norm_status(value, default="pending"):
    if value is None:
        return default
    text = str(value).strip().lower()
    text = _STATUS_ALIASES.get(text, text)
    if text not in STATUSES:
        raise StoreError("invalid status %r (expected one of %s)"
                         % (value, ", ".join(STATUSES)))
    return text


def _status_set(value):
    """Turn a status name, alias, list, or set into a set of statuses.

    None or "all" means no filter (returns None).
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("", "all", "*"):
            return None
        if text in ("active", "in_flight"):
            return set(ACTIVE_STATUSES)
        if text in ("terminal", "finished", "complete"):
            return set(TERMINAL_STATUSES)
        return {_norm_status(text)}
    result = set()
    for item in value:
        part = _status_set(item)
        if part is None:
            return None
        result.update(part)
    return result


def _norm_account(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return text


def _listify(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [item for item in value]
    return [value]


def _norm_artifacts(value):
    """Normalize artifacts to a list of dicts.

    A plain string becomes {"remote": str, "local": None, "kind": "file",
    "ok": None, "size": None, "error": None}.  Existing dicts keep unknown
    keys so callers can attach upload metadata.
    """
    if value is None:
        return []
    if isinstance(value, (str, dict)):
        value = [value]
    result = []
    for item in value:
        if isinstance(item, dict):
            entry = copy.deepcopy(item)
            if "remote" not in entry:
                entry["remote"] = entry.get("path")
            entry.setdefault("local", None)
            entry.setdefault("kind", "file")
            entry.setdefault("ok", None)
            entry.setdefault("size", None)
            entry.setdefault("error", None)
        else:
            entry = {
                "remote": str(item),
                "local": None,
                "kind": "file",
                "ok": None,
                "size": None,
                "error": None,
            }
        result.append(entry)
    return result


def _norm_meta(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return copy.deepcopy(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return {"legacy_meta": value}
        if isinstance(parsed, dict):
            return parsed
        return {"legacy_meta": parsed}
    return {"legacy_meta": value}


def _empty_state():
    return {"version": STATE_VERSION, "updated": now_iso(), "jobs": {}}


def _normalize_job(raw, job_id=None):
    """Return a job dict with every required field and sane types."""
    if not isinstance(raw, dict):
        raise StoreError("job record must be an object, got %r" % type(raw))
    job = copy.deepcopy(raw)
    jid = job.get("id") or job_id or new_job_id()
    jid = str(jid)

    status = _norm_status(job.get("status"), "pending")
    created = _to_iso(job.get("created")) or now_iso()

    attempts = job.get("attempts", 0)
    try:
        attempts = int(attempts)
    except (TypeError, ValueError):
        attempts = 0

    pid = job.get("pid")
    if pid is not None:
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            pid = None

    out = {
        "id": jid,
        "backend": str(job.get("backend") or "colab"),
        "account": _norm_account(job.get("account")),
        "session": str(job["session"]) if job.get("session") else None,
        "script": str(job["script"]) if job.get("script") else None,
        "args": _listify(job.get("args")),
        "status": status,
        "created": created,
        "started": _to_iso(job.get("started")),
        "finished": _to_iso(job.get("finished")),
        "pid": pid,
        "log_path": str(job["log_path"]) if job.get("log_path") else None,
        "artifacts": _norm_artifacts(job.get("artifacts")),
        "keepalive_until": _to_iso(job.get("keepalive_until")),
        "attempts": attempts,
        "error": str(job["error"]) if job.get("error") else None,
        "meta": _norm_meta(job.get("meta")),
    }

    # Preserve fields written by newer versions instead of dropping them.
    for key, value in job.items():
        if key not in out:
            out[key] = copy.deepcopy(value)
    return out


def _normalize_state(raw):
    """Accept old or partial state shapes and return the canonical shape.

    Supported legacy shapes:
      - {"jobs": {id: job}}
      - {"jobs": [job, ...]}
      - [job, ...]
      - a single job object
    """
    if raw is None:
        return _empty_state()
    extra = {}
    if isinstance(raw, list):
        jobs_raw = raw
    elif isinstance(raw, dict):
        extra = {k: v for k, v in raw.items() if k != "jobs"}
        if "jobs" in raw:
            jobs_raw = raw["jobs"]
        elif "id" in raw and "status" in raw:
            jobs_raw = [raw]
        else:
            jobs_raw = []
    else:
        raise StoreError("state root must be an object or list, got %r"
                         % type(raw))

    jobs = {}
    if isinstance(jobs_raw, dict):
        for key, value in jobs_raw.items():
            job = _normalize_job(value, job_id=key)
            jobs[job["id"]] = job
    elif isinstance(jobs_raw, list):
        for value in jobs_raw:
            job = _normalize_job(value)
            jobs[job["id"]] = job
    elif jobs_raw is None:
        jobs = {}
    else:
        raise StoreError("state jobs must be an object or list, got %r"
                         % type(jobs_raw))

    version = extra.get("version", STATE_VERSION)
    try:
        version = int(version)
    except (TypeError, ValueError):
        version = STATE_VERSION
    state = {
        "version": version,
        "updated": _to_iso(extra.get("updated")) or now_iso(),
        "jobs": jobs,
    }
    for key, value in extra.items():
        if key not in state:
            state[key] = copy.deepcopy(value)
    return state


def _dump_state(state):
    state = copy.deepcopy(state)
    state["version"] = STATE_VERSION
    state["updated"] = now_iso()
    return json.dumps(state, indent=2, ensure_ascii=True) + "\n"


def _read_state(path):
    if not os.path.exists(path):
        return _empty_state()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except ValueError as exc:
        raise StoreError("corrupt state file %s: %s" % (path, exc))
    except OSError as exc:
        raise StoreError("cannot read state file %s: %s" % (path, exc))
    return _normalize_state(raw)


def _atomic_write(path, text):
    """Write text to path atomically, with retries for Windows file locks."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".state-", suffix=".tmp",
                                    dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(5):
            try:
                os.replace(tmp_path, path)
                tmp_path = None
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class FileLock(object):
    """Small cross-platform advisory file lock.

    Windows uses msvcrt.locking on the first byte; POSIX uses fcntl.flock.
    The lock is held for the lifetime of the context manager.
    """

    def __init__(self, path, timeout=30.0):
        self.path = path
        self.timeout = float(timeout)
        self._handle = None

    def __enter__(self):
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        self._handle = open(self.path, "a+b")
        self._handle.seek(0, os.SEEK_END)
        if self._handle.tell() == 0:
            self._handle.write(b"\0")
            self._handle.flush()
        deadline = time.time() + self.timeout
        while True:
            try:
                self._handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._handle.fileno(),
                                   msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._handle.fileno(),
                                fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.time() >= deadline:
                    try:
                        self._handle.close()
                    finally:
                        self._handle = None
                    raise StoreError("timeout waiting for lock %s"
                                     % self.path)
                time.sleep(0.05)

    def __exit__(self, exc_type, exc_value, traceback):
        if self._handle is None:
            return False
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
        return False


def _apply_update(job, fields, meta=None, replace_meta=False):
    """Mutate a normalized job with update fields.  Caller holds the lock."""
    if not isinstance(fields, dict):
        raise StoreError("update fields must be a dict")
    fields = dict(fields)
    fields.pop("id", None)
    unknown = [key for key in fields if key not in JOB_FIELDS]
    if unknown:
        raise StoreError("unknown job field(s): %s" % ", ".join(sorted(unknown)))

    if "status" in fields:
        status = _norm_status(fields["status"], job.get("status", "pending"))
        fields["status"] = status
        if status in TERMINAL_STATUSES and "finished" not in fields:
            if not job.get("finished"):
                fields["finished"] = now_iso()
        if status in ("starting", "running") and "started" not in fields:
            if not job.get("started"):
                fields["started"] = now_iso()

    if meta is not None:
        if "meta" in fields:
            raise StoreError("pass meta once (argument or field)")
        if not isinstance(meta, dict):
            raise StoreError("meta must be a dict")
        if replace_meta:
            merged = copy.deepcopy(meta)
        else:
            merged = copy.deepcopy(job.get("meta") or {})
            merged.update(copy.deepcopy(meta))
        fields["meta"] = merged

    for key, value in fields.items():
        if key in ("created", "started", "finished", "keepalive_until"):
            value = _to_iso(value)
        elif key == "args":
            value = _listify(value)
        elif key == "artifacts":
            value = _norm_artifacts(value)
        elif key == "attempts":
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise StoreError("attempts must be an integer")
        elif key == "pid":
            if value is not None:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    raise StoreError("pid must be an integer or null")
        elif key == "account":
            value = _norm_account(value)
        elif key in ("error", "script", "session", "backend", "log_path"):
            value = str(value) if value is not None else None
        elif key == "meta":
            value = _norm_meta(value)
        job[key] = value
    return job


class JobStore(object):
    """Thread-safe and process-safe JSON job registry."""

    def __init__(self, path=None, lock_timeout=None):
        chosen = path or os.environ.get("JOBS_STATE") or DEFAULT_STATE_PATH
        self.path = os.path.abspath(chosen)
        self.lock_path = self.path + ".lock"
        if lock_timeout is None:
            lock_timeout = os.environ.get("JOBS_LOCK_TIMEOUT", "30")
        self.lock_timeout = float(lock_timeout)

    def _lock(self):
        return FileLock(self.lock_path, self.lock_timeout)

    def load(self):
        """Return a deep copy of the whole canonical state document."""
        with self._lock():
            return copy.deepcopy(_read_state(self.path))

    def save(self, state):
        """Replace the whole state document (normalized) atomically."""
        with self._lock():
            normalized = _normalize_state(state)
            _atomic_write(self.path, _dump_state(normalized))
            return copy.deepcopy(normalized)

    def create(self, job_id=None, **fields):
        """Create a job and return a deep copy.  Status defaults to pending."""
        if "id" in fields:
            supplied = str(fields.pop("id"))
            if job_id is not None and str(job_id) != supplied:
                raise StoreError("conflicting job ids: %r and %r"
                                 % (job_id, supplied))
            job_id = supplied
        with self._lock():
            state = _read_state(self.path)
            jid = str(job_id) if job_id else new_job_id()
            if jid in state["jobs"]:
                raise StoreError("job already exists: %s" % jid)
            fields["id"] = jid
            job = _normalize_job(fields, job_id=jid)
            state["jobs"][jid] = job
            _atomic_write(self.path, _dump_state(state))
            return copy.deepcopy(job)

    def update(self, job_id, meta=None, replace_meta=False, **fields):
        """Update one job and return a deep copy.

        Passing a terminal status without `finished` fills it automatically.
        `meta` is merged into the existing meta dict unless replace_meta=True.
        """
        with self._lock():
            state = _read_state(self.path)
            job = state["jobs"].get(str(job_id))
            if job is None:
                raise StoreError("job not found: %s" % job_id)
            _apply_update(job, fields, meta=meta, replace_meta=replace_meta)
            state["jobs"][str(job_id)] = job
            _atomic_write(self.path, _dump_state(state))
            return copy.deepcopy(job)

    def claim(self, job_id, from_statuses=("pending",), increment=None,
              meta=None, **fields):
        """Compare-and-set a job.

        Returns the updated job, or None when the current status is not in
        `from_statuses` (another keeper won the race).  `increment` is a dict
        of integer field deltas, normally {"attempts": 1}.
        """
        allowed = _status_set(from_statuses)
        with self._lock():
            state = _read_state(self.path)
            key = str(job_id)
            job = state["jobs"].get(key)
            if job is None:
                return None
            if allowed is not None and job["status"] not in allowed:
                return None
            if increment:
                for name, delta in increment.items():
                    if name != "attempts":
                        raise StoreError("only attempts may be incremented")
                    try:
                        job[name] = int(job.get(name) or 0) + int(delta)
                    except (TypeError, ValueError):
                        raise StoreError("attempts must be an integer")
            _apply_update(job, fields, meta=meta)
            state["jobs"][key] = job
            _atomic_write(self.path, _dump_state(state))
            return copy.deepcopy(job)

    def get(self, job_id):
        """Return one job as a deep copy, or None."""
        with self._lock():
            state = _read_state(self.path)
            job = state["jobs"].get(str(job_id))
            return copy.deepcopy(job) if job is not None else None

    def list(self, status=None, limit=None, account=None, backend=None,
             session=None, oldest_first=False):
        """List jobs, newest first by default.

        status may be a name, alias, list, or set.  limit=None means all;
        limit=0 means none.
        """
        allowed = _status_set(status)
        with self._lock():
            state = _read_state(self.path)
            jobs = list(state["jobs"].values())

        if allowed is not None:
            jobs = [job for job in jobs if job["status"] in allowed]
        if account is not None:
            jobs = [job for job in jobs
                    if str(job.get("account")) == str(account)]
        if backend is not None:
            wanted = str(backend).lower()
            jobs = [job for job in jobs
                    if str(job.get("backend") or "").lower() == wanted]
        if session is not None:
            jobs = [job for job in jobs
                    if str(job.get("session")) == str(session)]

        jobs.sort(key=lambda item: (parse_ts(item.get("created")) or 0,
                                    item["id"]),
                  reverse=not oldest_first)
        if limit is not None:
            jobs = jobs[:max(0, int(limit))]
        return copy.deepcopy(jobs)

    def increment(self, job_id, field="attempts", delta=1):
        """Atomically increment a numeric job field (currently attempts)."""
        if field != "attempts":
            raise StoreError("only attempts may be incremented")
        with self._lock():
            state = _read_state(self.path)
            key = str(job_id)
            job = state["jobs"].get(key)
            if job is None:
                raise StoreError("job not found: %s" % job_id)
            try:
                job[field] = int(job.get(field) or 0) + int(delta)
            except (TypeError, ValueError):
                raise StoreError("%s must be an integer" % field)
            state["jobs"][key] = job
            _atomic_write(self.path, _dump_state(state))
            return copy.deepcopy(job)

    def prune(self, older_than=7 * 86400, statuses=None, dry_run=False):
        """Delete old terminal jobs.  Returns the removed job ids.

        Age is measured from `finished`, falling back to `created`.
        Active jobs are never removed unless their status is explicitly
        included in `statuses`.
        """
        allowed = _status_set(statuses) if statuses is not None \
            else set(TERMINAL_STATUSES)
        cutoff = time.time() - float(older_than)
        with self._lock():
            state = _read_state(self.path)
            removed = []
            for key, job in list(state["jobs"].items()):
                if allowed is not None and job["status"] not in allowed:
                    continue
                reference = (parse_ts(job.get("finished"))
                             or parse_ts(job.get("created")) or 0)
                if reference < cutoff:
                    removed.append(key)
            if removed and not dry_run:
                for key in removed:
                    state["jobs"].pop(key, None)
                _atomic_write(self.path, _dump_state(state))
        return removed

    def counts(self):
        """Return a status -> count dict covering every known status."""
        result = {status: 0 for status in STATUSES}
        with self._lock():
            state = _read_state(self.path)
        for job in state["jobs"].values():
            result[job["status"]] = result.get(job["status"], 0) + 1
        return result

    def delete(self, job_id):
        """Delete one job record.  Returns True if it existed."""
        with self._lock():
            state = _read_state(self.path)
            key = str(job_id)
            existed = key in state["jobs"]
            if existed:
                state["jobs"].pop(key, None)
                _atomic_write(self.path, _dump_state(state))
            return existed


_DEFAULT_STORE = None


def default_store():
    """Return a lazily-created JobStore for the default state path."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = JobStore()
    return _DEFAULT_STORE


def create(**kwargs):
    return default_store().create(**kwargs)


def update(job_id, **kwargs):
    return default_store().update(job_id, **kwargs)


def get(job_id):
    return default_store().get(job_id)


def list_jobs(**kwargs):
    return default_store().list(**kwargs)


def prune(**kwargs):
    return default_store().prune(**kwargs)


__all__ = [
    "STATUSES",
    "ACTIVE_STATUSES",
    "TERMINAL_STATUSES",
    "JOB_FIELDS",
    "STATE_VERSION",
    "DEFAULT_STATE_PATH",
    "StoreError",
    "FileLock",
    "JobStore",
    "now_iso",
    "iso_plus",
    "parse_ts",
    "new_job_id",
    "default_store",
    "create",
    "update",
    "get",
    "list_jobs",
    "prune",
]
