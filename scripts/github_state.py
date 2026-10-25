# -*- coding: utf-8 -*-
"""github_state.py - push a secret-free ops snapshot to GitHub (ops-state).

Reads local job/watchdog/heartbeat state and writes:
  state/current.json
  state/jobs.json
  state/heartbeat.json
to an orphan-ish branch (default: ops-state) via the GitHub Contents API.

Token lookup order: GITHUB_TOKEN, GH_TOKEN, HKCU\\Environment.
Repo lookup: --repo, GITHUB_REPO, configs/github.json.
Never prints or writes the token. ASCII-only source on purpose.

Examples:
  python scripts/github_state.py --dry-run
  python scripts/github_state.py --once
  python scripts/github_state.py --loop 600
"""
import argparse
import base64
import io
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "configs", "github.json")
JOBS = os.path.join(ROOT, "scripts", "jobs", "state.json")
HEART = os.path.join(ROOT, "scripts", "state", "heartbeat.json")
WATCHDOG = os.path.join(ROOT, "scripts", "watchdog_state_B.json")
QUEUE = os.path.join(ROOT, "scripts", "gpu_queue_B.json")
QUEUE_STATE = os.path.join(ROOT, "scripts", "gpu_queue_B_state.json")
MANUAL = os.path.join(ROOT, "scripts", "state", "manual_active.json")
API = "https://api.github.com"


def env_or_hkcu(name):
    v = os.environ.get(name)
    if v:
        return v.strip()
    if os.name != "nt":
        return ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _ = winreg.QueryValueEx(k, name)
            return str(v or "").strip()
    except Exception:
        return ""


def read_json(path, default=None):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode("ascii", "replace").strip()
    except Exception:
        return ""


def job_summary():
    raw = read_json(JOBS, None)
    if raw is None:
        return {"ok": False, "total": 0, "active": 0, "counts": {}}
    jobs = raw.get("jobs") if isinstance(raw, dict) else raw
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    if not isinstance(jobs, list):
        jobs = []
    counts = {}
    active = 0
    for j in jobs:
        if not isinstance(j, dict):
            continue
        st = str(j.get("status") or "unknown").lower()
        counts[st] = counts.get(st, 0) + 1
        if st in ("pending", "starting", "running", "fetching", "leased"):
            active += 1
    return {"ok": True, "total": len(jobs), "active": active,
            "counts": counts}


def _old_push(qv, hours=48):
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


def watchdog_summary():
    raw = read_json(WATCHDOG, {})
    qstate = read_json(QUEUE_STATE, {}) or {}
    active = []
    if isinstance(raw, dict):
        for k, v in raw.items():
            st = str(v or "").upper()
            if st not in ("QUEUED", "RUNNING", "PENDING", "STARTING", "PUSHED"):
                continue
            if _old_push(qstate.get(k)):
                continue
            active.append({"ref": k, "status": st})
    return {"active": active, "count": len(active)}


def manual_summary():
    raw = read_json(MANUAL, {}) or {}
    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        items = []
    active = []
    now = time.time()
    for it in items:
        if not isinstance(it, dict):
            continue
        st = str(it.get("status") or "RUNNING").upper()
        if st not in ("QUEUED", "RUNNING", "PENDING", "STARTING", "PUSHED"):
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
    return {"active": active, "count": len(active)}


def queue_summary():
    raw = read_json(QUEUE, [])
    if isinstance(raw, dict):
        raw = raw.get("items") or raw.get("queue") or []
    if not isinstance(raw, list):
        raw = []
    return {"total": len(raw)}


def snapshot():
    heart = read_json(HEART, {}) or {}
    js = job_summary()
    wd = watchdog_summary()
    manual = manual_summary()
    q = queue_summary()
    return {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "git_commit": git_head(),
        "active_jobs": js["active"] + wd["count"] + manual["count"],
        "jobs": js,
        "watchdog": wd,
        "manual": manual,
        "queue": q,
        "heartbeat": {
            "status": heart.get("status", "unknown"),
            "idle": heart.get("idle"),
            "detail": heart.get("detail", ""),
            "iso": heart.get("iso", ""),
        },
        "source": "github_state.py",
    }


def load_config():
    raw = read_json(CONFIG, {}) or {}
    repo = os.environ.get("GITHUB_REPO") or raw.get("repo") or ""
    branch = os.environ.get("GITHUB_STATE_BRANCH") or raw.get("branch") or "ops-state"
    return repo.strip(), branch.strip()


def api(method, path, token, body=None, timeout=20):
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ornith-lab-state",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            obj = json.loads(raw)
        except Exception:
            obj = {"message": raw[:300]}
        return e.code, obj
    except Exception as e:
        return 0, {"message": str(e)[:300]}


def ensure_branch(repo, branch, token):
    code, info = api("GET", "/repos/" + repo, token)
    if code != 200:
        return False, "repo GET failed: %s %s" % (code, info.get("message", ""))
    default = info.get("default_branch") or "main"
    code, ref = api("GET", "/repos/%s/git/ref/heads/%s" % (repo, branch), token)
    if code == 200:
        return True, ""
    if code not in (404, 409):
        return False, "ref GET failed: %s %s" % (code, ref.get("message", ""))
    code, base = api("GET", "/repos/%s/git/ref/heads/%s" % (repo, default), token)
    if code != 200:
        return False, "default ref failed: %s" % code
    sha = (base.get("object") or {}).get("sha")
    if not sha:
        return False, "default branch sha missing"
    code, out = api("POST", "/repos/%s/git/refs" % repo, token,
                    {"ref": "refs/heads/" + branch, "sha": sha})
    if code in (201, 200):
        return True, ""
    return False, "branch create failed: %s %s" % (code, out.get("message", ""))


def put_file(repo, branch, path, content, token, message):
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    code, cur = api("GET", "/repos/%s/contents/%s?ref=%s" % (
        repo, path, branch), token)
    body = {"message": message, "content": b64, "branch": branch}
    if code == 200 and cur.get("sha"):
        body["sha"] = cur["sha"]
    code, out = api("PUT", "/repos/%s/contents/%s" % (repo, path), token, body)
    if code in (200, 201):
        return True, ""
    return False, "%s %s" % (code, out.get("message", ""))


def push(snap, repo, branch, token, dry_run=False):
    files = {
        "state/current.json": json.dumps(snap, ensure_ascii=False, indent=2) + "\n",
        "state/jobs.json": json.dumps(snap.get("jobs", {}), ensure_ascii=False,
                                      indent=2) + "\n",
        "state/heartbeat.json": json.dumps(snap.get("heartbeat", {}),
                                           ensure_ascii=False, indent=2) + "\n",
    }
    if dry_run:
        print(json.dumps({"repo": repo, "branch": branch,
                          "files": list(files)}, ensure_ascii=False))
        print(files["state/current.json"])
        return True
    ok, err = ensure_branch(repo, branch, token)
    if not ok:
        print("[github_state] " + err, file=sys.stderr)
        return False
    stamp = snap.get("iso", "")
    for path, content in files.items():
        ok, err = put_file(repo, branch, path, content, token,
                           "ops: %s %s" % (stamp, path))
        if not ok:
            print("[github_state] PUT %s failed: %s" % (path, err),
                  file=sys.stderr)
            return False
    print("[github_state] pushed %s@%s (%d files)" % (repo, branch, len(files)))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="")
    ap.add_argument("--branch", default="")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    repo, branch = load_config()
    repo = args.repo or repo
    branch = args.branch or branch
    token = env_or_hkcu("GITHUB_TOKEN") or env_or_hkcu("GH_TOKEN")
    if not args.dry_run and (not repo or not token):
        print("[github_state] need GITHUB_TOKEN (HKCU/env) and repo "
              "(--repo or configs/github.json)", file=sys.stderr)
        return 2
    snap = snapshot()
    if args.dry_run:
        push(snap, repo or "OWNER/REPO", branch, token, dry_run=True)
        return 0
    while True:
        ok = push(snapshot(), repo, branch, token)
        if args.once or not args.loop:
            return 0 if ok else 1
        time.sleep(max(60, args.loop))


if __name__ == "__main__":
    sys.exit(main())
