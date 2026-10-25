# -*- coding: utf-8 -*-
"""
bench_v155.py — runner cho B15.5 (TASK-15), copy cua bench_v15.py (DONG BANG)
chi doi 2 cho: TASKS_DIR -> tasks_v15_5/tasks, import checker CUNG thu muc.

Khong doi action space so voi v14/v15 (TASK-10 parser khong can sua):
    CLICK <x> <y>    toa do 0..1000 normalized -> x/1000*1280, y/1000*720
    TYPE <text>      go text (co the chua space)
    KEY  <name>      Enter, Tab, ..., ctrl+a/c/v, End, PageDown, DoubleClick
    DONE             ket thuc task

3 variant/task qua query string: tasks/tXX.html?v=0|1|2 (file://).

API (giong bench_v15 — kernel DeepSeek chi doi doi ten import):
    from bench_v155 import run_suite
    results = run_suite(policy_fn)          # policy_fn(obs) -> action string
    # obs = {"task_id","variant","step","instruction","screenshot","spec",
    #        "peek"}  (peek chi co khi run_suite(..., peek=True))

Chay:
    python bench_v155.py --list
    python bench_v155.py --dummy dummy_actions_v155.json --out dummy_run_result.json
    python checker.py --self-test            # 18/18 success + 18/18 fail
"""
import argparse
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = os.path.join(HERE, "tasks")
VIEW_W, VIEW_H = 1280, 720

V14_KEYS = {"Enter", "Tab", "Escape", "Backspace",
            "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"}
EXTRA_KEYS = {"End", "PageDown", "PageUp", "Home", "Delete", "Space",
              "ctrl+a", "ctrl+c", "ctrl+v", "ctrl+x", "ctrl+shift+r",
              "ctrl+z", "shift+Tab", "DoubleClick"}
KEY_ALIAS = {"ctrl": "Control", "shift": "Shift", "alt": "Alt", "meta": "Meta",
             "cmd": "Meta", "command": "Meta", "esc": "Escape",
             "return": "Enter", "space": "Space"}


def norm_key(name):
    parts = str(name).split("+")
    return "+".join(KEY_ALIAS.get(p.strip().lower(), p.strip()) for p in parts)


def load_tasks():
    with open(os.path.join(TASKS_DIR, "tasks.json"), "r", encoding="utf-8") as f:
        return json.load(f)["tasks"]


def task_file(task_id):
    return os.path.join(TASKS_DIR, task_id.lower() + ".html")


def get_spec(task_id, variant=0):
    from checker import SPEC_JS
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = b.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        page.goto("file:///" + task_file(task_id).replace("\\", "/") + "?v=%d" % variant)
        page.wait_for_timeout(300)
        spec = page.evaluate(SPEC_JS[task_id])
        b.close()
    return spec


def render_instruction(meta, spec):
    instruction = meta["instruction"]
    for k in sorted(spec.get("vars", {}), key=len, reverse=True):
        instruction = instruction.replace(k, str(spec["vars"][k]))
    return instruction


def parse_action(action):
    action = (action or "").strip()
    parts = action.split(None, 2)
    if not parts:
        return ("IGNORE", "")
    cmd = parts[0].upper()
    if cmd == "CLICK" and len(parts) >= 3:
        return ("CLICK", (float(parts[1]), float(parts[2])))
    if cmd == "TYPE":
        return ("TYPE", action.split(None, 1)[1] if len(parts) > 1 else "")
    if cmd == "KEY" and len(parts) >= 2:
        return ("KEY", parts[1])
    if cmd == "DONE":
        return ("DONE", "")
    return ("IGNORE", action)


def exec_action(page, kind, payload):
    if kind == "CLICK":
        nx, ny = payload
        page.mouse.click(nx / 1000.0 * VIEW_W, ny / 1000.0 * VIEW_H)
    elif kind == "TYPE":
        page.keyboard.type(payload, delay=5)
    elif kind == "KEY":
        if payload == "DoubleClick":
            page.mouse.dblclick()
        else:
            page.keyboard.press(norm_key(payload))
    return True


def run_task(page, task_id, variant, policy_fn, max_steps=None, shot_dir=None,
             peek=False, action_wait=60):
    from checker import SPEC_JS, check_task
    meta = next(t for t in load_tasks() if t["task_id"] == task_id)
    if max_steps is None:
        max_steps = meta["max_steps"]
    shot_dir = shot_dir or tempfile.mkdtemp(prefix="b155_")
    url = "file:///" + task_file(task_id).replace("\\", "/") + "?v=%d" % variant
    page.goto(url)
    page.wait_for_timeout(350)
    spec = page.evaluate(SPEC_JS[task_id])
    instruction = render_instruction(meta, spec)

    trajectory = []
    t0 = time.time()
    for step in range(max_steps):
        shot = os.path.join(shot_dir, "%s_v%d_s%d.png" % (task_id, variant, step))
        page.screenshot(path=shot)
        obs = {"task_id": task_id, "variant": variant, "step": step,
               "instruction": instruction, "screenshot": shot, "spec": spec,
               "peek": (lambda js: page.evaluate(js)) if peek else None}
        try:
            action = policy_fn(obs)
        except Exception as e:
            trajectory.append({"step": step, "action": "<POLICY-ERROR:%s>" % e})
            break
        trajectory.append({"step": step, "action": action})
        kind, payload = parse_action(action)
        if kind == "DONE":
            break
        if kind == "IGNORE":
            continue
        try:
            exec_action(page, kind, payload)
        except Exception:
            continue
        page.wait_for_timeout(action_wait)
    elapsed = time.time() - t0
    res = check_task(page, task_id)
    page.screenshot(path=os.path.join(shot_dir, "%s_v%d_final.png" % (task_id, variant)))
    return {"task_id": task_id, "variant": variant,
            "steps": len(trajectory), "success": bool(res["success"]),
            "score": float(res["score"]), "reason": res.get("reason", ""),
            "state": res.get("state", {}), "elapsed": round(elapsed, 2),
            "instruction": instruction, "trajectory": trajectory}


def run_suite(policy_fn, tasks=None, variants=(0, 1, 2), max_steps=None,
              peek=False, action_wait=60):
    from playwright.sync_api import sync_playwright
    tasks = tasks or [t["task_id"] for t in load_tasks()]
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = b.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        for tid in tasks:
            for v in variants:
                try:
                    r = run_task(page, tid, v, policy_fn, max_steps=max_steps,
                                 peek=peek, action_wait=action_wait)
                except Exception as e:
                    r = {"task_id": tid, "variant": v, "success": False,
                         "score": 0.0, "reason": "runner-error: %s" % e,
                         "steps": 0, "elapsed": 0.0, "trajectory": []}
                results.append(r)
                print("[b155] %s v%d  %s  score=%.2f  steps=%s  %s" % (
                    tid, v, "PASS" if r["success"] else "FAIL",
                    r["score"], r.get("steps"), r.get("reason", "")[:60]))
        b.close()
    return results


def make_dummy_policy(actions_by_task):
    """Key: "T13_wizard@1" (cu the variant) hoac "T13_wizard" (fallback)."""
    def policy_fn(obs):
        key = "%s@%d" % (obs["task_id"], obs["variant"])
        seq = actions_by_task.get(key)
        if seq is None:
            seq = actions_by_task.get(obs["task_id"], [])
        i = obs["step"]
        return seq[i] if i < len(seq) else "DONE"
    return policy_fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dummy", help="file actions JSON {task_id@variant: [...]}")
    ap.add_argument("--run", nargs=2, metavar=("TASK", "V"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.list:
        for t in load_tasks():
            print("%-18s diff=%s max_steps=%2d  %s" % (
                t["task_id"], t["difficulty"], t["max_steps"], t["target"]))
        return 0

    if args.dummy:
        with open(args.dummy, "r", encoding="utf-8") as f:
            actions = json.load(f)
        if args.run:
            res = run_suite(make_dummy_policy(actions),
                            tasks=[args.run[0]], variants=(int(args.run[1]),),
                            action_wait=800)
        else:
            res = run_suite(make_dummy_policy(actions), action_wait=800)
        out = args.out or os.path.join(HERE, "dummy_run_result.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        npass = sum(1 for r in res if r["success"])
        print("[b155] dummy run: %d/%d PASS -> %s" % (npass, len(res), out))
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
