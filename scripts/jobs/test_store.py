# -*- coding: utf-8 -*-
"""test_store.py - stdlib unittest for scripts/jobs/store.py.

Run:
    python -m unittest -v scripts/jobs/test_store.py
    python scripts/jobs/test_store.py -v

Every test uses a temporary state file.  No Colab command is executed.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from .store import (
        ACTIVE_STATUSES,
        STATUSES,
        TERMINAL_STATUSES,
        FileLock,
        JobStore,
        StoreError,
        now_iso,
        parse_ts,
    )
except ImportError:
    from store import (
        ACTIVE_STATUSES,
        STATUSES,
        TERMINAL_STATUSES,
        FileLock,
        JobStore,
        StoreError,
        now_iso,
        parse_ts,
    )


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jobs-store-test-")
        self.path = os.path.join(self.tmp, "state.json")
        self.store = JobStore(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_create_defaults_and_all_fields(self):
        job = self.store.create(script="task.py", account=2,
                                session="sess-a", backend="colab")
        expected = {
            "id", "backend", "account", "session", "script", "args",
            "status", "created", "started", "finished", "pid", "log_path",
            "artifacts", "keepalive_until", "attempts", "error", "meta",
        }
        self.assertEqual(expected, set(job))
        self.assertEqual("pending", job["status"])
        self.assertEqual([], job["args"])
        self.assertEqual([], job["artifacts"])
        self.assertEqual({}, job["meta"])
        self.assertEqual(0, job["attempts"])
        self.assertIsNone(job["started"])
        self.assertIsNone(job["finished"])
        self.assertIsNone(job["pid"])
        self.assertIsNone(job["log_path"])
        self.assertIsNone(job["keepalive_until"])
        self.assertIsNone(job["error"])
        self.assertIsNotNone(parse_ts(job["created"]))
        self.assertEqual(job, self.store.get(job["id"]))

    def test_update_meta_merge_and_replace(self):
        job = self.store.create(meta={"a": 1})
        updated = self.store.update(job["id"], meta={"b": 2})
        self.assertEqual({"a": 1, "b": 2}, updated["meta"])
        replaced = self.store.update(job["id"], meta={"c": 3},
                                     replace_meta=True)
        self.assertEqual({"c": 3}, replaced["meta"])

    def test_status_timestamps_and_terminal_finished(self):
        job = self.store.create()
        running = self.store.update(job["id"], status="running")
        self.assertIsNotNone(running["started"])
        self.assertIsNone(running["finished"])
        done = self.store.update(job["id"], status="done")
        self.assertIsNotNone(done["finished"])
        self.assertIn(done["status"], TERMINAL_STATUSES)

    def test_invalid_status_raises(self):
        with self.assertRaises(StoreError):
            self.store.create(status="bogus")
        job = self.store.create()
        with self.assertRaises(StoreError):
            self.store.update(job["id"], status="bogus")

    def test_status_aliases_are_normalized(self):
        job = self.store.create(status="success")
        self.assertEqual("done", job["status"])
        job2 = self.store.create(status="canceled")
        self.assertEqual("cancelled", job2["status"])
        job3 = self.store.create(status="queued")
        self.assertEqual("pending", job3["status"])

    def test_unknown_field_rejected(self):
        job = self.store.create()
        with self.assertRaises(StoreError):
            self.store.update(job["id"], typo_field=1)

    def test_artifacts_normalized(self):
        job = self.store.create(artifacts=[
            "/content/out.zip",
            {"remote": "/content/work", "kind": "dir"},
        ])
        self.assertEqual(2, len(job["artifacts"]))
        self.assertEqual("/content/out.zip", job["artifacts"][0]["remote"])
        self.assertEqual("file", job["artifacts"][0]["kind"])
        self.assertEqual("dir", job["artifacts"][1]["kind"])
        self.assertIsNone(job["artifacts"][0]["ok"])

    def test_claim_is_compare_and_set(self):
        job = self.store.create()
        claimed = self.store.claim(
            job["id"], from_statuses=("pending",), status="starting",
            increment={"attempts": 1}, meta={"keeper_pid": 123})
        self.assertIsNotNone(claimed)
        self.assertEqual("starting", claimed["status"])
        self.assertEqual(1, claimed["attempts"])
        self.assertEqual(123, claimed["meta"]["keeper_pid"])
        self.assertIsNotNone(claimed["started"])
        again = self.store.claim(job["id"], from_statuses=("pending",))
        self.assertIsNone(again)
        self.assertEqual(1, self.store.get(job["id"])["attempts"])

    def test_increment(self):
        job = self.store.create()
        self.assertEqual(1, self.store.increment(job["id"])["attempts"])
        self.assertEqual(3, self.store.increment(job["id"], delta=2)["attempts"])

    def test_list_filter_sort_and_limit(self):
        a = self.store.create(script="a.py", account=1)
        b = self.store.create(script="b.py", account=2)
        c = self.store.create(script="c.py", account=1)
        self.store.update(a["id"], created="2026-01-01T00:00:00Z",
                          status="running")
        self.store.update(b["id"], created="2026-01-02T00:00:00Z",
                          status="done")
        self.store.update(c["id"], created="2026-01-03T00:00:00Z",
                          status="running")
        newest = self.store.list()
        self.assertEqual([c["id"], b["id"], a["id"]],
                         [item["id"] for item in newest])
        oldest = self.store.list(oldest_first=True)
        self.assertEqual([a["id"], b["id"], c["id"]],
                         [item["id"] for item in oldest])
        self.assertEqual([a["id"], c["id"]],
                         [item["id"] for item in
                          self.store.list(status="running", oldest_first=True)])
        self.assertEqual([b["id"]],
                         [item["id"] for item in self.store.list(status="done")])
        self.assertEqual(1, len(self.store.list(limit=1)))
        self.assertEqual([], self.store.list(limit=0))
        self.assertEqual(2, len(self.store.list(account=1)))
        self.assertEqual(3, len(self.store.list(status="all")))

    def test_prune_terminal_only_and_dry_run(self):
        old = self.store.create()
        self.store.update(old["id"], status="done",
                          finished="2020-01-01T00:00:00Z")
        active = self.store.create()
        self.store.update(active["id"], status="running")
        dry = self.store.prune(older_than=86400, dry_run=True)
        self.assertEqual([old["id"]], dry)
        self.assertIsNotNone(self.store.get(old["id"]))
        removed = self.store.prune(older_than=86400)
        self.assertEqual([old["id"]], removed)
        self.assertIsNone(self.store.get(old["id"]))
        self.assertIsNotNone(self.store.get(active["id"]))

    def test_prune_explicit_statuses(self):
        job = self.store.create()
        self.store.update(job["id"], status="cancelled",
                          finished="2020-01-01T00:00:00Z")
        self.assertEqual([], self.store.prune(older_than=86400,
                                              statuses=("done",)))
        self.assertEqual([job["id"]], self.store.prune(older_than=86400,
                                                       statuses=("cancelled",)))

    def test_counts_and_delete(self):
        self.store.create()
        done = self.store.create()
        self.store.update(done["id"], status="done")
        counts = self.store.counts()
        self.assertEqual(1, counts["pending"])
        self.assertEqual(1, counts["done"])
        self.assertEqual(0, counts["running"])
        self.assertTrue(self.store.delete(done["id"]))
        self.assertFalse(self.store.delete(done["id"]))
        self.assertIsNone(self.store.get(done["id"]))

    def test_legacy_list_state_is_normalized(self):
        legacy = {
            "jobs": [
                {
                    "id": "legacy-1",
                    "status": "success",
                    "script": "old.py",
                    "artifacts": ["/content/old.zip"],
                    "created": 1234567890,
                }
            ]
        }
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(legacy, handle)
        job = self.store.get("legacy-1")
        self.assertIsNotNone(job)
        self.assertEqual("done", job["status"])
        self.assertEqual([], job["args"])
        self.assertEqual({}, job["meta"])
        self.assertEqual("/content/old.zip", job["artifacts"][0]["remote"])
        self.assertEqual("2009-02-13T23:31:30Z", job["created"])
        self.assertIsNotNone(parse_ts(job["created"]))

    def test_legacy_single_job_state_is_normalized(self):
        legacy = {"id": "solo", "status": "running", "script": "solo.py"}
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(legacy, handle)
        job = self.store.get("solo")
        self.assertIsNotNone(job)
        self.assertEqual("running", job["status"])
        self.assertEqual("solo.py", job["script"])

    def test_corrupt_state_raises(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{not valid json")
        with self.assertRaises(StoreError):
            self.store.get("anything")

    def test_atomic_writes_leave_valid_json_and_no_temp_files(self):
        job = self.store.create()
        for index in range(25):
            self.store.update(job["id"], meta={"index": index})
            with open(self.path, "r", encoding="utf-8") as handle:
                parsed = json.load(handle)
            self.assertIn(job["id"], parsed["jobs"])
        leftovers = [name for name in os.listdir(self.tmp)
                     if name.startswith(".state-") and name.endswith(".tmp")]
        self.assertEqual([], leftovers)
        self.assertEqual(24, self.store.get(job["id"])["meta"]["index"])

    def test_lock_creates_lock_file(self):
        job = self.store.create()
        self.assertTrue(os.path.exists(self.path + ".lock"))
        with FileLock(self.path + ".lock", timeout=2):
            self.assertIsNotNone(job)

    def test_concurrent_process_creates(self):
        script = (
            "import sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from store import JobStore\n"
            "s = JobStore(sys.argv[2])\n"
            "for i in range(int(sys.argv[3])):\n"
            "    s.create(script='worker.py', meta={'worker': sys.argv[4],"
            " 'i': i})\n"
        )
        flags = 0x08000000 if os.name == "nt" else 0
        processes = []
        for worker in range(3):
            processes.append(subprocess.Popen(
                [sys.executable, "-c", script, HERE, self.path, "5",
                 str(worker)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, creationflags=flags))
        for proc in processes:
            out, err = proc.communicate(timeout=90)
            self.assertEqual(0, proc.returncode,
                             "worker failed: %s\n%s" % (out, err))
        jobs = self.store.list(limit=None)
        self.assertEqual(15, len(jobs))
        workers = {}
        for job in jobs:
            worker = job["meta"]["worker"]
            workers[worker] = workers.get(worker, 0) + 1
        self.assertEqual({"0": 5, "1": 5, "2": 5}, workers)

    def test_status_constants(self):
        self.assertEqual(8, len(STATUSES))
        self.assertEqual({"starting", "running", "fetching"},
                         set(ACTIVE_STATUSES))
        self.assertEqual({"done", "failed", "cancelled", "lost"},
                         set(TERMINAL_STATUSES))
        self.assertEqual(STATUSES, tuple(STATUSES))

    def test_iso_helpers(self):
        stamp = now_iso()
        self.assertTrue(stamp.endswith("Z"))
        self.assertIsNotNone(parse_ts(stamp))
        self.assertIsNone(parse_ts(""))
        self.assertIsNone(parse_ts("not-a-date"))
        self.assertEqual(1234567890.0, parse_ts(1234567890))


if __name__ == "__main__":
    unittest.main(verbosity=2)
