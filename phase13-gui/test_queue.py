"""test_queue.py - dry-run logic hang doi GPU (khong push that)."""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location(
    "wd", os.path.join(ROOT, "scripts", "watchdog.py"))
wd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)

PUSHED = []


def fake_push(cmd, timeout=900):
    PUSHED.append(cmd[-1])
    return 0, "Kernel version 9 successfully pushed.\n", ""


wd.run = fake_push
wd.gpu_remaining_hours = lambda: 20.0
wd.dataset_ready = lambda slug: True
wd.log = lambda m: None

q = json.load(open(os.path.join(ROOT, "scripts", "gpu_queue.json"),
                   encoding="utf-8"))
state = {it["id"]: {"status": "UNKNOWN"} for it in q}

# vong 1: chua kernel nao xong -> chi push 2 muc dau (gioi han 2 session)
wd.process_queue(state, {})
print("vong 1 pushes:", PUSHED)
assert PUSHED == ["phase13-gui/kernel_v21", "phase13-gui/kernel_bench_v18_think0"], \
    PUSHED
for it in q:
    state[it["id"]]["status"] = "COMPLETE"
PUSHED[:] = []

# vong 2: moi kernel COMPLETE -> het phu thuoc -> push het (bo qua gioi han
# session vi cac muc da 'pushed' roi)
wd.process_queue(state, {})
print("vong 2 pushes:", len(PUSHED))
for p in PUSHED:
    print("   ", p)

# kiem tra: 2 muc 'after' co phu thuoc nao bi sai
ids = {it["id"] for it in q}
for it in q:
    if it.get("after"):
        assert it["after"] in ids, it
    assert it["dir"] and os.path.isdir(os.path.join(ROOT, it["dir"])), it
print("QUEUE TEST PASS")
