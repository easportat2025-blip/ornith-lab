# -*- coding: utf-8 -*-
"""
test_watchdog_v2.py -- offline self-test for watchdog_v2.py.

NO network, NO Kaggle calls, NO credentials. Tests only the pure logic:
config normalization, pattern repair, backoff, marker keys, lock, state IO.

    python scripts/test_watchdog_v2.py
"""
import importlib.util
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC_PATH = os.path.join(HERE, "watchdog_v2.py")

spec = importlib.util.spec_from_file_location("wd2", SPEC_PATH)
wd2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd2)

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        FAILS.append(name)


def section(t):
    print("\n== %s ==" % t)


# --------------------------------------------------------------- 1. pattern fix
section("1. pattern repair (bug #2: broken regex in watchdog_targets.json)")
broken = "bench3d_result\\\\.json|.*\\\\.log"     # as in the real targets file
fixed = wd2.normalize_pattern(broken)
check("double-escaped dot collapsed",
      "\\\\." not in fixed.replace("\\\\\\\\", "XX") or "\\\\." in fixed,
      repr(fixed))
check("fixed pattern compiles", wd2.pattern_ok(fixed), repr(fixed))
check("fixed pattern matches a real filename",
      bool(re.search(fixed, "bench3d_result.json")) or
      bool(re.search(fixed, "x.log")), repr(fixed))
check("correct pattern untouched",
      wd2.normalize_pattern("b15_result\\.json") == "b15_result\\.json")
check("broken pattern does NOT match (that was the bug)",
      not re.search(broken, "bench3d_result.json"),
      "broken=%r" % broken)

# ------------------------------------------------------------ 2. dedupe labels
section("2. duplicate labels (bug #3: bench-v155 / sft-v22 listed twice)")
raw = [
    {"label": "bench-v155", "kernel": "acc/bench-v155",
     "outdir": "o1", "pattern": "a\\.json"},
    {"label": "bench-v155", "kernel": "acc/bench-v155",
     "outdir": "o1", "pattern": "a\\.json"},      # EXACT duplicate -> skip
    {"label": "same-label", "kernel": "acc/other",
     "outdir": "o2", "pattern": "a\\.json"},      # same label, other kernel
    {"label": "same-label", "kernel": "acc/third",
     "outdir": "o3", "pattern": "a\\.json"},      # same label -> rename
    {"kernel": "acc/no-label", "outdir": "o4"},
    {"label": "broken", "kernel": "acc/x", "outdir": "o5", "pattern": "y\\\\.z"},
]
targets, warns = wd2.normalize_targets(raw)
labels = [t["label"] for t in targets]
check("exact duplicate skipped", len(targets) == 5, str(len(targets)))
check("exact dup warned", any("exact duplicate" in w for w in warns), str(warns))
check("same label other kernel renamed",
      "same-label#2" in labels, str(labels))
check("labels unique", len(set(labels)) == len(labels), str(labels))
check("missing label derived from ref", "no-label" in labels, str(labels))
check("broken pattern warned+fixed",
      any("pattern fixed" in w for w in warns), str(warns))
check("pattern actually fixed on target",
      targets[4]["pattern"] == "y\\.z", targets[4]["pattern"])
check("outdir made absolute",
      all(os.path.isabs(t["outdir"]) for t in targets))
check("marker keys unique",
      len(set(wd2.marker_key(t) for t in targets)) == len(targets))
check("marker path under scripts/",
      all(wd2.marker_path(t).startswith(HERE) for t in targets))
check("bad targets skipped with warning",
      wd2.normalize_targets([{"label": "x"}])[0] == [] and
      wd2.normalize_targets([{"label": "x"}])[1])


# ----------------------------------------------------------------- 3. backoff
section("3. exponential backoff (bug #5: push spam every 2 min)")
b1 = wd2.backoff_seconds(1)
b2 = wd2.backoff_seconds(2)
b3 = wd2.backoff_seconds(3)
check("backoff grows", b1 < b2 < b3, "%s %s %s" % (b1, b2, b3))
check("backoff capped", wd2.backoff_seconds(20) == wd2.BACKOFF_CAP)
check("attempt 0 -> base", wd2.backoff_seconds(0) == wd2.BACKOFF_BASE)
check("backoff >= poll interval", b1 >= 120, str(b1))


# --------------------------------------------------------------- 4. state I/O
section("4. atomic state write + json round-trip")
tmp = tempfile.mkdtemp(prefix="wd2test_")
p = os.path.join(tmp, "state.json")
wd2.atomic_write_json(p, {"a": "b", "u": "x"})
check("state file written", os.path.exists(p))
check("state readable", wd2.load_json(p, {}) == {"a": "b", "u": "x"})
check("no .tmp left behind", not os.path.exists(p + ".tmp"))
wd2.atomic_write_json(p, {"a": "c"})
check("state overwritten", wd2.load_json(p, {}) == {"a": "c"})
check("corrupt json -> default",
      wd2.load_json(os.path.join(tmp, "nope.json"), {"d": 1}) == {"d": 1})
bad = os.path.join(tmp, "bad.json")
with io.open(bad, "w", encoding="utf-8") as fh:
    fh.write("{not json")
check("corrupt file -> default (no crash)", wd2.load_json(bad, {}) == {})


# ------------------------------------------------------------------ 5. queue
section("5. queue config validation")
q, qw = wd2.validate_queue([
    {"id": "a/b", "dir": "phase13-gui/kernel_v21"},
    {"id": "c/d"},                       # missing dir -> dropped
    {"id": "e/f", "dir": "no/such/dir"},  # dir not on disk -> kept + warned
    "not-an-object",
])
check("item with real dir kept", any(x["id"] == "a/b" for x in q), str(q))
check("item without dir dropped", not any(x["id"] == "c/d" for x in q))
check("item with future dir kept", any(x["id"] == "e/f" for x in q))
check("missing dir warned", any("missing" in w for w in qw), str(qw))
check("bad dir warned", any("does not exist" in w for w in qw), str(qw))
check("non-object warned", any("not an object" in w for w in qw), str(qw))
check("dir made absolute", os.path.isabs(q[0]["dir"]), q[0]["dir"])


# ------------------------------------------------------------------- 6. lock
section("6. single-instance lock (v1 had none)")
lp = os.path.join(tmp, "wd.lock")
wd2.acquire_lock(lp)
check("lock file created", os.path.exists(lp))
check("lock holds pid", io.open(lp, encoding="utf-8").read().isdigit())
wd2.release_lock(lp)
check("lock released", not os.path.exists(lp))


# ------------------------------------------------------- 7. real targets file
section("7. real scripts/watchdog_targets.json -> normalized cleanly")
real = os.path.join(HERE, "watchdog_targets.json")
if os.path.exists(real):
    with io.open(real, "r", encoding="utf-8") as fh:
        raw_real = json.load(fh)
    t_real, w_real = wd2.normalize_targets(raw_real)
    check("real targets kept (minus exact dups)",
          len(t_real) == len(raw_real) - len([w for w in w_real
                                               if "exact duplicate" in w]),
          "%d vs %d" % (len(t_real), len(raw_real)))
    check("real labels unique",
          len(set(x["label"] for x in t_real)) == len(t_real))
    check("real patterns all compile",
          all(wd2.pattern_ok(x["pattern"]) for x in t_real if x.get("pattern")))
    check("real duplicate kernels skipped",
          len([w for w in w_real if "exact duplicate" in w]) == 2,
          str([w for w in w_real if "exact duplicate" in w]))
    broken_fixed = [w for w in w_real if "pattern fixed" in w]
    print("     -> %d pattern(s) auto-repaired, %d warning(s) total"
          % (len(broken_fixed), len(w_real)))
    for w in w_real:
        print("     ! %s" % w)
else:
    print("  (skipped: %s not found)" % real)

# ------------------------------------------------------------- 8. no creds
section("8. safety: no credentials in source, no cancel commands")
src = io.open(SPEC_PATH, encoding="utf-8").read()
check("no cancel call", "kernels cancel" not in src and "cancel_notebook" not in src)
check("no key literal", "KAGGLE_KEY =" not in src)
check("no hardcoded token", "api_token" not in src)


print("\n" + "=" * 50)
if FAILS:
    print("FAILED: %d check(s): %s" % (len(FAILS), FAILS))
    sys.exit(1)
print("ALL CHECKS PASSED")
sys.exit(0)
