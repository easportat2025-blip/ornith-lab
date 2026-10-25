"""Bench end-to-end cho GUI agent: task thật trên fixtures, chấm pass/fail.

Chạy:  python bench_gui.py            (oracle + random)
       python bench_gui.py --only login
Policy ngoài (model thật): xem hook --policy module:factory bên dưới.
"""
import argparse
import importlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harness import run_episode, mock_policy  # noqa: E402

TASKS = [
    {"name": "click_green", "fixture": "click_button.html",
     "task": "Click the Green button.", "max_steps": 6},
    {"name": "login", "fixture": "login_form.html",
     "task": "Sign in: username admin, password 1234.",
     "max_steps": 10},
    {"name": "counter5", "fixture": "counter.html",
     "task": "Click + until the counter reaches 5+.", "max_steps": 10},
]


def _center(env, selector):
    box = env.page.eval_on_selector(
        selector, "el => { const r = el.getBoundingClientRect();"
                  " return [r.x, r.y, r.width, r.height]; }")
    x = box[0] + box[2] / 2.0
    y = box[1] + box[3] / 2.0
    return (int(round(x / env.width * 1000)),
            int(round(y / env.height * 1000)))


def oracle_policy(name):
    """Policy 'biết đáp án' — chứng minh task giải được bằng action schema."""
    def pol(obs, shot, t, hist, env=None):
        if name == "click_green":
            x, y = _center(env, "#btn-green")
            return ("CLICK", x, y)
        if name == "login":
            seq = [("#username", "CLICK"), ("#username", "admin"),
                   ("#password", "CLICK"), ("#password", "1234"),
                   ("#submit", "CLICK")]
            sel, kind = seq[min(t, len(seq) - 1)]
            x, y = _center(env, sel)
            if kind == "CLICK":
                return ("CLICK", x, y)
            return ("TYPE", kind)
        if name == "counter5":
            x, y = _center(env, "#plus")
            return ("CLICK", x, y)
        return ("WAIT",)
    return pol


def random_policy(obs, shot, t, hist, env=None):
    rng = random.Random(1000 + t)
    roll = rng.random()
    if roll < 0.5:
        return ("CLICK", rng.randint(20, 980), rng.randint(20, 680))
    if roll < 0.7:
        return ("TYPE", "test123")
    if roll < 0.9:
        return ("KEY", rng.choice(["tab", "enter", "space"]))
    return ("WAIT",)


def load_policy(spec):
    mod_name, _, fn_name = spec.partition(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


def run_bench(policy_factory, out_dir, only=None, verbose=False):
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for task in TASKS:
        if only and task["name"] != only:
            continue
        pol = policy_factory(task["name"])
        ok, hist, _ = run_episode(
            task["fixture"], pol, os.path.join(out_dir, task["name"]),
            max_steps=task["max_steps"], tag=task["name"],
            task=task["task"], verbose=verbose)
        results.append({"task": task["name"], "pass": bool(ok),
                        "steps": len(hist),
                        "actions": [list(a) for a, _ in hist]})
        print(f"{task['name']:12s} pass={ok} steps={len(hist)}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=None,
                    help="module:factory trả policy(obs,shot,t,hist,env)")
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "out_bench"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print("== oracle ==")
    r_or = run_bench(lambda n: oracle_policy(n), args.out, args.only,
                     args.verbose)
    print("== random (baseline) ==")
    r_rd = run_bench(lambda n: random_policy, os.path.join(args.out, "rand"),
                     args.only, args.verbose)
    all_r = {"oracle": r_or, "random": r_rd}
    if args.policy:
        print(f"== {args.policy} ==")
        fac = load_policy(args.policy)
        all_r["custom"] = run_bench(fac, os.path.join(args.out, "custom"),
                                    args.only, args.verbose)
    with open(os.path.join(args.out, "bench_results.json"), "w") as f:
        json.dump(all_r, f, indent=1)
    print("saved", os.path.join(args.out, "bench_results.json"))


if __name__ == "__main__":
    main()
