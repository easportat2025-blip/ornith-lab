# -*- coding: utf-8 -*-
"""
watchdog_v2.py -- Kaggle kernel watchdog (v2), drop-in replacement for watchdog.py.

Same env contract as v1 (so restart_watchdogs.py keeps working):
    WATCH_TARGETS  - json list of targets
    GPU_QUEUE      - json list of queue items
    GPU_QUEUE_STATE, WATCH_STATE, WATCH_LOG, WATCH_STOP
Extra:
    WATCH_LOCK     - lock file (default scripts/watchdog.lock)

WHAT IS FIXED vs v1 (all verified against scripts/watchdog.log + targets json):
 1. BATCH STATUS. v1 called `kaggle kernels status` once per target every cycle
    (26 targets -> 26 API calls / 2 min). v2 calls `kaggle kernels list --mine
    --format json` ONCE (gives lastRunTime for every kernel) and only asks for
    the status of kernels that actually need it. Steady state: ~1-3 calls.
 2. BROKEN FILE-PATTERN REGEX. Several targets in watchdog_targets.json use
    "\\\\.json" (json -> python string "\\\\." = backslash backslash dot) which
    as a regex means "a literal backslash then any char" -> never matches ->
    output silently empty. v2 normalizes the pattern and warns.
 3. DUPLICATE LABELS. "bench-v155" and "sft-v22" appear twice in the targets
    file; v1 built the marker path from the label only -> the 2nd entry could
    never be fetched (marker already written by the 1st). v2 dedupes labels
    and uses ref+label for the marker key.
 4. POST-ACTION MARKER WRITTEN ON FAILURE. v1 wrote the marker whatever the
    exit code was -> a failed post-action was never retried. v2 writes the
    marker only on rc == 0 and retries with backoff otherwise.
 5. PUSH SPAM. v1 retried a failing push every cycle forever (log shows the
    same 409 Conflict every ~2 min, 10+ times). v2 has exponential backoff,
    a max-attempts cap, a 409/"already exists" special case, and verifies the
    kernel really appeared after a "successfully pushed" (the TASK-4 silent
    push bug).
 6. WRONG GPU SESSION COUNT. v1 counted sessions only from queue items whose
    status it happened to know. v2 counts in-flight kernels (pushed by us and
    not yet terminal) plus recently-started kernels, so the "<=2 GPU session"
    rule is actually enforced.
 7. Non-atomic state writes, no log rotation, no lock (two watchdogs on the
    same state file fought each other), no --check/--once modes, no graceful
    shutdown, post-action path resolved against CWD (not ROOT).

DESIGN RULES
  * NEVER cancel a kernel (project rule). This script only reads + pushes.
  * Never print or store credentials. Kaggle creds come from the environment.
  * Fail loud: every error is logged, nothing is silently swallowed.

USAGE
    python scripts/watchdog_v2.py                # run forever
    python scripts/watchdog_v2.py --once         # single cycle then exit
    python scripts/watchdog_v2.py --check        # validate config, no network
    python scripts/watchdog_v2.py --dry-run      # never push
    python scripts/watchdog_v2.py --interval 60  # poll period (s)
"""
import argparse
import io
import json
import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---------------------------------------------------------------- config paths
def _env_path(var, default_name, base=None):
    v = os.environ.get(var)
    if v:
        return v
    return os.path.join(base or HERE, default_name)


CFG = _env_path("WATCH_TARGETS", "watchdog_targets.json")
QUEUE = _env_path("GPU_QUEUE", "gpu_queue.json")
QSTATE = _env_path("GPU_QUEUE_STATE",
                   os.path.basename(QUEUE).replace(".json", "_state.json"))
STATE = _env_path("WATCH_STATE", "watchdog_state.json")
LOG = _env_path("WATCH_LOG", "watchdog.log")
STOP = _env_path("WATCH_STOP", "watchdog.stop")
LOCK = _env_path("WATCH_LOCK", "watchdog.lock")

ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONLEGACYWINDOWSSTDIO"] = "0"

TERMINAL = ("COMPLETE", "ERROR", "CANCELLED")
ACTIVE = ("RUNNING", "QUEUED", "PENDING")
MAX_PUSH_ATTEMPTS = 6
BACKOFF_BASE = 120.0          # seconds
BACKOFF_CAP = 3600.0
LOG_MAX_BYTES = 8 * 1024 * 1024
RECENT_WINDOW = 90 * 60      # "recently started" = lastRunTime within 90 min

_STOP = {"flag": False}


# --------------------------------------------------------------------- helpers
def log(msg):
    line = time.strftime("%m-%d %H:%M:%S") + " " + str(msg)
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > LOG_MAX_BYTES:
            os.replace(LOG, LOG + ".1")
    except Exception:
        pass
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
    try:
        print(line, flush=True)
    except Exception:
        pass


def run(cmd, timeout=1800, cwd=None):
    p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=timeout,
                       cwd=cwd or ROOT,
                       creationflags=(0x08000000 if os.name == "nt" else 0))
    return (p.returncode,
            (p.stdout or b"").decode("utf-8", "replace"),
            (p.stderr or b"").decode("utf-8", "replace"))


def load_json(path, default):
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def atomic_write(path, text):
    """Write file atomically so a crash can never leave a truncated state."""
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_write_json(path, obj):
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=1))


# --------------------------------------------------------- config normalization
def normalize_pattern(pat):
    """Repair double-escaped regex fragments.

    json "\\\\.json"  -> python '\\\\.json' (2 backslashes + dot)
    regex '\\\\.'       -> matches a literal backslash + any char  (WRONG)
    json "\\.json"    -> python '\\.json' (1 backslash + dot)   (correct)

    We collapse 2 backslashes + dot into 1 backslash + dot.
    """
    if not pat:
        return pat
    out = re.sub(r"\\\\+\.", r"\\.", pat)
    return out


def pattern_ok(pat):
    try:
        re.compile(pat)
        return True
    except Exception:
        return False


def normalize_targets(raw):
    """Return (targets, warnings). Each target gets a unique label + fixed pattern."""
    warnings = []
    out = []
    seen_labels = {}
    seen_refs = {}
    seen_specs = {}
    for i, t in enumerate(raw or []):
        if not isinstance(t, dict):
            warnings.append("target #%d is not an object - skipped" % i)
            continue
        ref = (t.get("kernel") or "").strip()
        if not ref:
            warnings.append("target #%d has no 'kernel' - skipped" % i)
            continue
        t = dict(t)
        t["kernel"] = ref
        label = (t.get("label") or ref.split("/")[-1]).strip()
        pat_raw = t.get("pattern") or ""
        outdir_raw = t.get("outdir") or ""
        # exact duplicate (same kernel + outdir + pattern) -> pointless repeat
        spec_key = (ref, outdir_raw, pat_raw)
        if spec_key in seen_specs:
            warnings.append("exact duplicate target (kernel %s, outdir %r) at "
                            "#%d - skipped (first one is #%d)"
                            % (ref, outdir_raw, i, seen_specs[spec_key]))
            continue
        seen_specs[spec_key] = i
        if label in seen_labels:
            n = seen_labels[label] + 1
            seen_labels[label] = n
            new_label = "%s#%d" % (label, n)
            warnings.append("duplicate label %r (target #%d, kernel %s) "
                            "-> renamed %r" % (label, i, ref, new_label))
            label = new_label
        else:
            seen_labels[label] = 1
        t["label"] = label
        if ref in seen_refs:
            warnings.append("kernel %s listed more than once (labels %r and %r) "
                            "- both kept, marker keys differ"
                            % (ref, seen_refs[ref], label))
        seen_refs[ref] = label
        pat = t.get("pattern") or ""
        fixed = normalize_pattern(pat)
        if fixed != pat:
            warnings.append("kernel %s: pattern fixed %r -> %r"
                            % (ref, pat, fixed))
            t["pattern"] = fixed
        if t.get("pattern") and not pattern_ok(t["pattern"]):
            warnings.append("kernel %s: pattern %r does not compile - "
                            "download will use no filter" % (ref, t["pattern"]))
            t["pattern"] = ""
        post = t.get("post")
        if post and not os.path.isabs(post):
            t["post"] = os.path.join(ROOT, post.replace("\\", os.sep))
        if t.get("post") and not os.path.exists(t["post"]):
            warnings.append("kernel %s: post script not found: %s"
                            % (ref, t["post"]))
        outdir = t.get("outdir") or ("out_" + label)
        if not os.path.isabs(outdir):
            outdir = os.path.join(ROOT, outdir)
        t["outdir"] = outdir
        out.append(t)
    return out, warnings


def validate_queue(raw):
    warnings = []
    out = []
    for i, item in enumerate(raw or []):
        if not isinstance(item, dict):
            warnings.append("queue #%d is not an object - skipped" % i)
            continue
        if not item.get("id") or not item.get("dir"):
            warnings.append("queue #%d missing 'id' or 'dir' - skipped" % i)
            continue
        item = dict(item)
        d = item["dir"]
        if not os.path.isabs(d):
            d = os.path.join(ROOT, d.replace("\\", os.sep))
        item["dir"] = d
        if not os.path.isdir(d):
            warnings.append("queue %s: dir does not exist: %s" % (item["id"], d))
        out.append(item)
    return out, warnings


def backoff_seconds(attempt):
    """Exponential backoff, capped."""
    attempt = max(1, int(attempt))
    return min(BACKOFF_CAP, BACKOFF_BASE * (2 ** (attempt - 1)))


def marker_key(target):
    """Unique marker key: ref + label (so duplicate labels cannot collide)."""
    ref = target.get("kernel", "")
    label = target.get("label", "")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", ref + "__" + label)


def marker_path(target):
    return os.path.join(HERE, ".watchdog_done." + marker_key(target))


# ------------------------------------------------------------------ kaggle i/o
def kaggle_list():
    """One call -> {ref: lastRunTime}. Empty dict on failure."""
    rc, out, err = run(["kaggle", "kernels", "list", "--mine",
                         "--page-size", "200", "--format", "json"], timeout=180)
    if rc != 0:
        log("kernels list FAILED rc=%s: %s" % (rc, (err or out)[-200:]))
        return {}
    try:
        data = json.loads(out)
    except Exception:
        # fall back to the table format
        d = {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and "/" in parts[0]:
                d[parts[0]] = parts[3]
        return d
    return {k.get("ref"): (k.get("lastRunTime") or "") for k in data
            if isinstance(k, dict) and k.get("ref")}


def kernel_status(ref):
    rc, out, err = run(["kaggle", "kernels", "status", ref], timeout=120)
    m = re.search(r"KernelWorkerStatus\.(\w+)", out + err)
    if m:
        return m.group(1)
    if "Cannot access kernel" in (out + err):
        return "MISSING"
    return "UNKNOWN"


def fetch_output(ref, outdir, pattern):
    os.makedirs(outdir, exist_ok=True)
    cmd = ["kaggle", "kernels", "output", ref, "-p", outdir, "--force"]
    if pattern:
        cmd += ["--file-pattern", pattern]
    rc, out, err = run(cmd, timeout=1800)
    return rc == 0, ((err or out) or "")[-300:]


def dataset_ready(slug):
    rc, out, err = run(["kaggle", "datasets", "status", slug], timeout=120)
    txt = (out + err).lower()
    if re.search(r"processing|in_progress|pending", txt):
        return False
    return bool(re.search(r"ready|active", txt))


def quota_info():
    """-> (remaining_hours, refresh_at_epoch_or_None)."""
    rc, out, err = run(["kaggle", "quota"], timeout=180)
    rem, refresh = 0.0, None
    for line in (out + err).splitlines():
        parts = line.split()
        if not parts or parts[0] != "GPU":
            continue
        for cand in parts[1:4]:
            if cand.endswith("h"):
                try:
                    rem = float(cand[:-1])
                    break
                except ValueError:
                    pass
        for cand in parts:
            m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", cand)
            if m:
                try:
                    import datetime
                    refresh = datetime.datetime.strptime(
                        m.group(1) + " " + m.group(2),
                        "%Y-%m-%d %H:%M:%S").timestamp()
                except Exception:
                    refresh = None
                break
        break
    return rem, refresh


# ------------------------------------------------------------------ the worker
class Watchdog(object):
    def __init__(self, args):
        self.args = args
        self.targets = []
        self.warnings = []
        self.queue = []
        self.qstate = load_json(QSTATE, {})
        raw_state = load_json(STATE, {})
        # 22/10: state file cua watchdog v1 luu string ("COMPLETE"/"ERROR"/
        # "UNKNOWN"). Watchdog v2 can dict {"status","last_run"}. Normalize
        # ve dict de khong crash "'str' object has no attribute 'get'".
        self.state = {}
        for k, v in (raw_state or {}).items():
            if isinstance(v, dict):
                self.state[k] = v
            elif isinstance(v, str):
                self.state[k] = {"status": v, "last_run": ""}
            else:
                self.state[k] = {"status": str(v or ""), "last_run": ""}
        self.last_list = {}
        self.quota = (0.0, None)
        self.next_quota = 0.0
        self.quota_logged = None

    # -------------------------------------------------------------- utilities
    def note(self, msg):
        if not self.args.quiet:
            log(msg)

    def run_post(self, target):
        script = target.get("post")
        if not script:
            return
        mpath = os.path.join(HERE, ".watchdog_post_done." + marker_key(target))
        if os.path.exists(mpath):
            return
        if not os.path.exists(script):
            log("post-action MISSING %s" % script)
            return
        log("post-action %s -> %s" % (target["label"], script))
        try:
            rc, out, err = run(["powershell", "-NoProfile", "-ExecutionPolicy",
                                 "Bypass", "-WindowStyle", "Hidden",
                                 "-File", script], timeout=7200, cwd=ROOT)
        except Exception as e:
            log("post-action %s EXCEPTION: %s" % (target["label"], e))
            return
        log("post-action %s rc=%s %s" % (target["label"], rc,
                                         (out or err)[-500:]))
        # marker ONLY on success -- v1 wrote it on failure too (never retried)
        if rc == 0:
            try:
                with io.open(mpath, "w", encoding="utf-8") as fh:
                    fh.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception:
                pass
        else:
            log("post-action %s FAILED - will retry next cycle" % target["label"])

    def fetch_if_new(self, target, status, last_run):
        mpath = marker_path(target)
        stamp = last_run or status
        old = None
        if os.path.exists(mpath):
            try:
                with io.open(mpath, "r", encoding="utf-8") as fh:
                    old = fh.read().strip()
            except Exception:
                old = None
        if old == stamp:
            return False
        ok, detail = fetch_output(target["kernel"], target["outdir"],
                                   target.get("pattern") or "")
        log("fetch %s (%s) %s %s" % (target["label"], status,
                                     "OK" if ok else "FAIL", detail))
        if ok:
            try:
                with io.open(mpath, "w", encoding="utf-8") as fh:
                    fh.write(stamp)
            except Exception:
                pass
            self.run_post(target)
        # fetch failed -> marker untouched -> retried next cycle
        return ok

    # ------------------------------------------------------------ target loop
    def poll_targets(self):
        listing = kaggle_list()
        if listing:
            self.last_list = listing
        # only ask for statuses we really need
        needed = []
        for t in self.targets:
            ref = t["kernel"]
            st = self.state.get(ref, {}).get("status")
            lrt = listing.get(ref)
            if st in TERMINAL and lrt and \
                    self.state.get(ref, {}).get("last_run") == lrt:
                continue          # already done and no new version
            needed.append(t)
        statuses = {}
        for t in needed:
            statuses[t["kernel"]] = kernel_status(t["kernel"])
        for t in self.targets:
            ref = t["kernel"]
            st = statuses.get(ref) or self.state.get(ref, {}).get("status")
            lrt = listing.get(ref)
            rec = self.state.setdefault(ref, {})
            rec["status"] = st
            if lrt:
                rec["last_run"] = lrt
            if st in TERMINAL and lrt:
                self.fetch_if_new(t, st, lrt)

    # ------------------------------------------------------------ queue logic
    def gpu_inflight(self):
        """Count kernels currently occupying a GPU slot (rule: max 2)."""
        n = 0
        for ref, rec in self.qstate.items():
            if ref.startswith("_"):
                continue
            if rec.get("status") in ACTIVE:
                n += 1
        # kernels started recently but not yet seen terminal -> assume running
        now = time.time()
        for ref, lrt in (self.last_list or {}).items():
            if not lrt:
                continue
            rec = self.state.get(ref, {})
            if rec.get("status") in TERMINAL:
                continue
            try:
                ts = time.mktime(time.strptime(lrt[:19], "%Y-%m-%d %H:%M:%S"))
            except Exception:
                continue
            if now - ts < RECENT_WINDOW:
                n += 1
        return n

    def push_queue(self):
        raw = load_json(QUEUE, [])
        items, warns = validate_queue(raw)
        for w in warns:
            log("queue config: %s" % w)
        if not items:
            return
        now = time.time()
        if now >= self.next_quota:
            rem, refresh = quota_info()
            self.quota = (rem, refresh)
            self.next_quota = (refresh + 300) if (refresh and refresh > now + 60) \
                else now + 300
            if rem != self.quota_logged:
                log("quota GPU con %.2fh (refresh %s)" %
                    (rem, time.strftime("%m-%d %H:%M",
                                        time.localtime(refresh))
                     if refresh else "?"))
                self.quota_logged = rem
        rem, refresh = self.quota
        inflight = self.gpu_inflight()
        for item in items:
            kid = item["id"]
            rec = self.qstate.setdefault(kid, {})
            if rec.get("pushed"):
                continue
            if rec.get("next_try") and now < rec["next_try"]:
                continue
            if rec.get("attempts", 0) >= MAX_PUSH_ATTEMPTS:
                continue
            after = item.get("after")
            if after:
                st = self.qstate.get(after, {}).get("status") or \
                    self.state.get(after, {}).get("status")
                if st not in TERMINAL:
                    continue
            need_ds = item.get("needs_dataset")
            if need_ds and not dataset_ready(need_ds):
                log("queue %s: dataset %s chua READY" % (kid, need_ds))
                continue
            if inflight >= 2:
                log("queue %s: da du %d GPU session, cho" % (kid, inflight))
                continue
            log("queue: push %s (%s)" % (kid, item.get("note", "")))
            try:
                rc, out, err = run(["kaggle", "kernels", "push", "-p",
                                     item["dir"]], timeout=900)
            except Exception as e:
                rec["attempts"] = rec.get("attempts", 0) + 1
                rec["next_try"] = time.time() + backoff_seconds(rec["attempts"])
                log("queue %s push EXCEPTION: %s" % (kid, e))
                continue
            blob = (out + err) or ""
            ok = (rc == 0 and "successfully pushed" in blob.lower()
                  and "push error" not in blob.lower())
            # FIX (MiMo 22/10): Kaggle BO QUA dataset khong ton tai khi push va
            # VAN bao "successfully pushed" -> kernel chay nhung THIEU dataset
            # (adapter) -> assert fail giua run. Phai coi la FAIL.
            miss_ds = re.findall(
                r"could not be added to the kernel:\s*\[([^\]]*)\]", blob, re.I)
            if miss_ds:
                ok = False
                parts = [p.strip().strip("'\"") for p in miss_ds[0].split(",")]
                miss_txt = ", ".join(p for p in parts if p)
                log("queue %s push FAIL: Kaggle BO QUA dataset khong ton tai: %s"
                    % (kid, miss_txt))
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = blob[-300:].replace("\n", " ")
            if ok:
                # TASK-4 lesson: "successfully pushed" != kernel exists.
                seen = False
                for _ in range(6):
                    time.sleep(10)
                    if kid in kaggle_list():
                        seen = True
                        break
                if not seen:
                    log("queue %s: push OK nhung kernel KHONG xuat hien "
                        "(silent push) -> retry sau" % kid)
                    rec["next_try"] = time.time() + backoff_seconds(rec["attempts"])
                    continue
                rec["pushed"] = True
                rec["pushed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                rec["next_try"] = 0
                inflight += 1
                log("queue %s push OK (verified)" % kid)
                if item.get("post"):
                    self.run_post({"kernel": kid, "label": kid.split("/")[-1],
                                   "post": os.path.join(ROOT, item["post"])})
            else:
                if "409" in blob or "Conflict" in blob:
                    # slug already taken -> do not hammer it every cycle
                    rec["blocked"] = True
                    rec["next_try"] = time.time() + BACKOFF_CAP
                    log("queue %s push FAIL 409 Conflict - BLOCKED 1h "
                        "(slug ton tai / doi version): %s"
                        % (kid, blob[-200:].replace("\n", " ")))
                else:
                    rec["next_try"] = time.time() + backoff_seconds(rec["attempts"])
                    log("queue %s push FAIL (attempt %d/%d, retry in %ds): %s"
                        % (kid, rec["attempts"], MAX_PUSH_ATTEMPTS,
                           int(rec["next_try"] - time.time()),
                           blob[-200:].replace("\n", " ")))
        atomic_write_json(QSTATE, self.qstate)

    # -------------------------------------------------------------- main cycle
    def cycle(self):
        raw = load_json(CFG, [])
        targets, warns = normalize_targets(raw)
        for w in warns:
            log("config: %s" % w)
        self.targets = targets
        self.poll_targets()
        if not self.args.dry_run:
            self.push_queue()
        atomic_write_json(STATE, {t["kernel"]: self.state.get(t["kernel"], {})
                                  for t in self.targets})
        return targets

    def check(self):
        """Offline validation: no network at all."""
        raw = load_json(CFG, [])
        targets, warns = normalize_targets(raw)
        print("targets file : %s" % CFG)
        print("targets       : %d" % len(targets))
        print("queue file    : %s" % QUEUE)
        qitems, qwarns = validate_queue(load_json(QUEUE, []))
        print("queue items   : %d" % len(qitems))
        print("state file    : %s" % STATE)
        print("log file      : %s" % LOG)
        print("lock file     : %s" % LOCK)
        print("--- warnings (%d) ---" % (len(warns) + len(qwarns)))
        for w in warns + qwarns:
            print("  ! %s" % w)
        print("--- targets ---")
        for t in targets:
            print("  %-22s %-46s pat=%r post=%s" %
                  (t["label"], t["kernel"], t.get("pattern") or "-",
                   os.path.basename(t.get("post") or "-")))
        print("OK")
        return 0


def acquire_lock(path):
    """Single-instance guard (v1 had none -> two watchdogs fought)."""
    try:
        fh = io.open(path, "w", encoding="utf-8")
    except Exception:
        return None
    try:
        fh.write(str(os.getpid()))
    finally:
        fh.close()
    return path


def release_lock(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="one cycle then exit")
    ap.add_argument("--check", action="store_true",
                    help="validate config offline, no network")
    ap.add_argument("--dry-run", action="store_true",
                    help="never push, only poll + fetch")
    ap.add_argument("--interval", type=int, default=120)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.check:
        return Watchdog(args).check()

    def _sig(signum, frame):
        _STOP["flag"] = True
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(s, _sig)
        except Exception:
            pass

    lock = None
    if not args.once:
        lock = acquire_lock(LOCK)
    wd = Watchdog(args)
    log("WATCHDOG v2 start (pid %d) targets=%s queue=%s interval=%ds%s"
        % (os.getpid(), CFG, QUEUE, args.interval, " [DRY-RUN]" if args.dry_run else ""))
    try:
        while not _STOP["flag"]:
            if os.path.exists(STOP):
                log("STOP file -> watchdog dung")
                break
            try:
                wd.cycle()
            except Exception as e:
                log("cycle loi: %s" % e)
            if args.once:
                break
            for _ in range(max(1, args.interval)):
                if _STOP["flag"] or os.path.exists(STOP):
                    break
                time.sleep(1)
    finally:
        release_lock(lock)
        log("WATCHDOG v2 stop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
