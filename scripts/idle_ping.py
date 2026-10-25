# -*- coding: utf-8 -*-
"""idle_ping.py - 10-minute status heartbeat when no work is active.

Reads the local job registry and Kaggle watchdog state, then posts a compact
presence event to the headless OpenChat API and writes
scripts/state/heartbeat.json. If work is active it backs off to 30 minutes.

Examples:
  python scripts/idle_ping.py --once --dry-run
  python scripts/idle_ping.py --once
  python scripts/idle_ping.py                 # loop forever
  python scripts/idle_ping.py --interval 600 --busy-interval 1800

No secrets are read or written. ASCII-only source on purpose.
"""
import argparse
import atexit
import io
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_FILE = os.path.join(ROOT, "scripts", "jobs", "state.json")
WATCHDOG_FILE = os.path.join(ROOT, "scripts", "watchdog_state_B.json")
QUEUE_FILE = os.path.join(ROOT, "scripts", "gpu_queue_B.json")
QUEUE_STATE = os.path.join(ROOT, "scripts", "gpu_queue_B_state.json")
MANUAL_FILE = os.path.join(ROOT, "scripts", "state", "manual_active.json")
STATE_DIR = os.path.join(ROOT, "scripts", "state")
STATE_FILE = os.path.join(STATE_DIR, "heartbeat.json")
PID_FILE = os.path.join(STATE_DIR, "idle_ping.pid")
LOG_FILE = os.path.join(ROOT, "scripts", "logs", "idle_ping.log")
DEFAULT_URL = os.environ.get("OC_CHAT_URL", "http://127.0.0.1:8788").rstrip("/")
ACTIVE = ("pending", "starting", "running", "fetching", "leased")
ACTIVE_WD = ("QUEUED", "RUNNING", "PENDING", "STARTING", "PUSHED")


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def log(msg):
    line = "[idle_ping %s] %s" % (now_iso(), msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with io.open(LOG_FILE, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def read_json(path, default=None):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def job_snapshot():
    raw = read_json(JOBS_FILE, None)
    if raw is None:
        return {"ok": False, "total": 0, "active": [],
                "counts": {}, "path": os.path.relpath(JOBS_FILE, ROOT)}
    jobs = raw.get("jobs") if isinstance(raw, dict) else raw
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    if not isinstance(jobs, list):
        jobs = []
    active = []
    counts = {}
    for j in jobs:
        if not isinstance(j, dict):
            continue
        st = str(j.get("status") or "unknown").lower()
        counts[st] = counts.get(st, 0) + 1
        if st in ACTIVE:
            active.append({"id": j.get("id") or "", "backend": j.get("backend") or "",
                           "account": j.get("account") or "",
                           "session": j.get("session") or "", "status": st})
    return {"ok": True, "total": len(jobs), "active": active,
            "counts": counts, "path": os.path.relpath(JOBS_FILE, ROOT)}


def _old_push(qv, hours=48):
    """True when queue metadata proves the kernel was pushed long ago."""
    if not isinstance(qv, dict):
        return False
    if qv.get("pushed") is False and int(qv.get("attempts") or 0) >= 10:
        return True
    stamp = qv.get("pushed_at") or ""
    if not stamp:
        return False
    try:
        t = time.mktime(time.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S"))
        return (time.time() - t) > hours * 3600
    except Exception:
        return False


def watchdog_snapshot():
    raw = read_json(WATCHDOG_FILE, {})
    qstate = read_json(QUEUE_STATE, {}) or {}
    active = []
    if isinstance(raw, dict):
        for k, v in raw.items():
            st = str(v or "").upper()
            if st not in ACTIVE_WD:
                continue
            if _old_push(qstate.get(k)):
                continue
            active.append({"ref": k, "status": st})
    return {"active": active, "path": os.path.relpath(WATCHDOG_FILE, ROOT)}


def manual_snapshot():
    raw = read_json(MANUAL_FILE, {}) or {}
    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        items = []
    active = []
    now = time.time()
    for it in items:
        if not isinstance(it, dict):
            continue
        st = str(it.get("status") or "RUNNING").upper()
        if st not in ACTIVE_WD:
            continue
        since = it.get("since") or ""
        try:
            t = time.mktime(time.strptime(since[:19], "%Y-%m-%dT%H:%M:%S"))
            if now - t > 6 * 3600:
                continue
        except Exception:
            pass
        active.append({"ref": it.get("ref") or "", "status": st,
                       "note": it.get("note") or ""})
    return {"active": active, "path": os.path.relpath(MANUAL_FILE, ROOT)}


def queue_snapshot():
    raw = read_json(QUEUE_FILE, [])
    if isinstance(raw, dict):
        raw = raw.get("items") or raw.get("queue") or []
    if not isinstance(raw, list):
        raw = []
    paused = 0
    for item in raw:
        if isinstance(item, dict) and item.get("pause"):
            paused += 1
    return {"total": len(raw), "paused": paused}


def build_state():
    js = job_snapshot()
    wd = watchdog_snapshot()
    manual = manual_snapshot()
    q = queue_snapshot()
    active = len(js["active"]) + len(wd["active"]) + len(manual["active"])
    idle = active == 0
    detail = ("jobs=%d/%d active=%d kaggle_active=%d manual=%d "
              "queue=%d paused=%d") % (
        len(js["active"]), js["total"], len(js["active"]),
        len(wd["active"]), len(manual["active"]), q["total"], q["paused"])
    return {
        "ts": time.time(), "iso": now_iso(), "host": socket.gethostname(),
        "pid": os.getpid(), "idle": idle,
        "status": "idle" if idle else "busy",
        "active": active, "detail": detail,
        "jobs": js, "watchdog": wd, "manual": manual, "queue": q,
        "note": "no active job" if idle else "work in progress",
    }


def post_ping(state, url, timeout=8):
    body = {
        "agent": "heartbeat", "status": state["status"],
        "job": (state["jobs"]["active"][0].get("id")
                if state["jobs"]["active"] else ""),
        "detail": state["detail"], "host": state["host"],
        "pid": state["pid"],
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url + "/api/ping", data=data, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return True, raw[:500]
    except urllib.error.HTTPError as e:
        return False, "HTTP %s: %s" % (e.code, e.read()[:300])
    except Exception as e:
        return False, str(e)[:300]


def write_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, STATE_FILE)


def one_cycle(url, dry_run=False):
    state = build_state()
    ok = None
    err = ""
    if not dry_run:
        write_state(state)
        ok, err = post_ping(state, url)
    log("%s | %s | openchat=%s%s" % (
        state["status"], state["detail"],
        "dry-run" if dry_run else ("ok" if ok else "FAIL"),
        "" if not err else (" (" + err[:120] + ")")))
    return state, ok, err


def write_pid():
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with io.open(PID_FILE, "w", encoding="ascii") as fh:
            fh.write(str(os.getpid()))
        atexit.register(clear_pid)
    except Exception:
        pass


def clear_pid():
    try:
        with io.open(PID_FILE, encoding="ascii") as fh:
            if fh.read().strip() == str(os.getpid()):
                os.remove(PID_FILE)
    except Exception:
        pass


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--interval", type=int, default=600,
                    help="idle interval seconds (default 600)")
    ap.add_argument("--busy-interval", type=int, default=1800,
                    help="busy interval seconds (default 1800)")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cycles", type=int, default=0)
    args = ap.parse_args(argv)
    write_pid()

    cycles = 0
    while True:
        state, _, _ = one_cycle(args.url, args.dry_run)
        cycles += 1
        if args.once or (args.max_cycles and cycles >= args.max_cycles):
            return 0
        time.sleep(max(30, args.busy_interval if not state["idle"]
                       else args.interval))


if __name__ == "__main__":
    sys.exit(main())
