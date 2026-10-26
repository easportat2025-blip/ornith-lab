# -*- coding: utf-8 -*-
"""Kaggle watchdog for GitHub Actions (no local process needed).

Reads configs/kaggle_queue.json, polls each kernel, prints a summary, optionally
downloads small result files to state/results/, and optionally pushes the next
pending kernel when nothing is running.

Secrets come from environment only:
  KAGGLE_USERNAME, KAGGLE_KEY

This script never writes credentials to disk.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "configs", "kaggle_queue.json")
STATE = os.path.join(ROOT, "state", "current.json")
RESULTS = os.path.join(ROOT, "state", "results")
FLAGS = 0x08000000 if os.name == "nt" else 0

ACTIVE = {"RUNNING", "QUEUED", "STARTING", "PENDING"}
DEFAULT_RESULT_PATTERN = (
    r"(?i)(result|summary|gate|manifest|metrics|report|eval|bench|b17)"
    r".*\.(json|md|txt)$"
)
MAX_RESULT_BYTES = 2 * 1024 * 1024


def run(args, timeout=180):
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        p = subprocess.run(["kaggle"] + args, capture_output=True, env=env,
                           timeout=timeout, creationflags=FLAGS)
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
            (p.stderr or b"").decode("utf-8", "replace")
    except Exception as e:
        return 1, "", "%s: %s" % (type(e).__name__, e)


def kernel_status(ref):
    rc, out, err = run(["kernels", "status", ref], timeout=90)
    blob = out + err
    m = re.search(r"KernelWorkerStatus\.([A-Z_]+)", blob)
    if m:
        return m.group(1)
    if "404" in blob or "not found" in blob.lower():
        return "MISSING"
    return "UNKNOWN"


def kernel_logs(ref, tail=80):
    rc, out, err = run(["kernels", "logs", ref], timeout=180)
    blob = (out + err).strip()
    if not blob:
        return []
    try:
        rows = json.loads(blob)
        lines = []
        for row in rows:
            data = row.get("data", "")
            for line in str(data).splitlines():
                if line.strip():
                    lines.append(line.rstrip())
        return lines[-tail:]
    except Exception:
        return blob.splitlines()[-tail:]


def push_kernel(path):
    full = path if os.path.isabs(path) else os.path.join(ROOT, path)
    rc, out, err = run(["kernels", "push", "-p", full], timeout=600)
    return rc, (out + err).strip()


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def download_results(ref, pattern=DEFAULT_RESULT_PATTERN,
                     max_bytes=MAX_RESULT_BYTES):
    """Download only small JSON/MD/TXT result files for one kernel.

    Kaggle's --file-pattern regex keeps the transfer small; the size guard also
    deletes anything unexpectedly large before state is committed to ops-state.
    """
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "__", ref).strip("_") or "kernel"
    outdir = os.path.join(RESULTS, safe)
    os.makedirs(outdir, exist_ok=True)
    rc, out, err = run(["kernels", "output", ref, "-p", outdir,
                        "--file-pattern", pattern, "-q"], timeout=300)
    kept = []
    for base, _dirs, files in os.walk(outdir):
        for name in files:
            path = os.path.join(base, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size > max_bytes:
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            kept.append({
                "path": os.path.relpath(path, ROOT).replace("\\", "/"),
                "bytes": size,
            })
    kept.sort(key=lambda x: x["path"])
    return rc, (out + err).strip()[-500:], kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto-push", action="store_true",
                    help="push the first pending target when nothing is active")
    ap.add_argument("--download-results", action="store_true",
                    help="download small result files for COMPLETE kernels")
    ap.add_argument("--result-pattern", default=DEFAULT_RESULT_PATTERN,
                    help="regex passed to kaggle kernels output --file-pattern")
    ap.add_argument("--results-max-bytes", type=int, default=MAX_RESULT_BYTES,
                    help="delete downloaded result files larger than this")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    if not os.environ.get("KAGGLE_USERNAME") or not os.environ.get("KAGGLE_KEY"):
        print("WARN: KAGGLE_USERNAME/KAGGLE_KEY missing; watchdog skipped.")
        print("      Add them as GitHub Actions secrets (see docs/SECRETS.md).")
        return 0

    queue = load_json(QUEUE, {"targets": []})
    targets = queue.get("targets", [])
    results = []
    active = []
    pending = []

    for t in targets:
        ref = t["ref"]
        st = kernel_status(ref)
        item = {"ref": ref, "path": t.get("path", ""), "kind": t.get("kind", ""),
                "state": t.get("state", ""), "status": st}
        if st in ACTIVE:
            active.append(item)
        elif st == "COMPLETE":
            item["state"] = "done"
            if a.download_results:
                rc, blob, kept = download_results(
                    ref, a.result_pattern, a.results_max_bytes)
                item["outputs"] = kept
                item["output_rc"] = rc
                if blob:
                    item["output_tail"] = blob
        elif t.get("state") == "pending" and st == "MISSING":
            # Only auto-create a kernel that does not exist yet. Never re-push
            # an existing ERROR/COMPLETE kernel on every 10-minute tick.
            pending.append(item)
        elif st in ("ERROR", "CANCELLED"):
            item["state"] = "failed"
            item["log_tail"] = kernel_logs(ref, 40)
        elif st == "MISSING":
            item["state"] = "failed"
        results.append(item)

    pushed = None
    if a.auto_push and not active and pending:
        nxt = pending[0]
        rc, blob = push_kernel(nxt["path"])
        pushed = {"ref": nxt["ref"], "rc": rc, "output": blob[-800:]}
        if rc == 0:
            nxt["status"] = "PUSHED"

    state = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "host": "github-actions",
        "account": queue.get("account", ""),
        "active": [x["ref"] for x in active],
        "results": results,
        "pushed": pushed,
        "download_results": a.download_results,
    }
    state_path = a.out or STATE
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)

    print("== Kaggle watchdog ==")
    for x in results:
        print("%-42s %-10s %s" % (x["ref"], x["status"], x["state"]))
        for o in x.get("outputs", []):
            print("  output %-60s %d bytes" % (o["path"], o["bytes"]))
    if pushed:
        print("pushed:", pushed["ref"], "rc=", pushed["rc"])
        if pushed["output"]:
            print(pushed["output"])
    if not results:
        print("queue is empty")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## Kaggle watchdog\n\n")
            f.write("| kernel | status | state | outputs |\n|---|---|---|---|\n")
            for x in results:
                f.write("| `%s` | %s | %s | %d |\n" % (
                    x["ref"], x["status"], x["state"],
                    len(x.get("outputs", []))))
            if pushed:
                f.write("\nPushed: `%s` (rc=%s)\n" % (pushed["ref"], pushed["rc"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
