# -*- coding: utf-8 -*-
"""
gen_dummy_actions.py - SINH LAI dummy_actions*.json tu TASK HIEN TAI.

Vay: dummy_actions_v16.json (19/10) viet tay cho DOM CU. Sau khi sua task
(15 fix), toa do/phan tu bi doi => dummy cu khong con dung. File
dummy_run_result*.json cua 21/10 11:13 CUNG CU (truoc cac fix 12:05-12:09)
=> bang chung "dummy 24/24" cu bi CU.

Cach sinh: CHAY SUCCESS POLICY cua checker tren task hien tai, gom action
tra ve trong trajectory -> day chinh la chuoi action dung cho task moi.
Sau do chay lai dummy de kiem: <suite>/bench_v*.py --dummy <file> --out <out>

Dung:
    python scripts/gen_dummy_actions.py phase13-gui/bench_v15/tasks_v16_a
    python scripts/gen_dummy_actions.py phase13-gui/bench_v15/tasks_v15_5
    python scripts/gen_dummy_actions.py <dir> --dry-run
"""
import argparse
import importlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_suite(sdir):
    """-> (runner_mod, checker_mod, ten_file_actions)"""
    name = os.path.basename(sdir.rstrip("/\\"))
    if name == "tasks_v16_a":
        runner_name, actions_name = "bench_v16", "dummy_actions_v16.json"
    elif name == "tasks_v15_5":
        runner_name, actions_name = "bench_v155", "dummy_actions_v155.json"
    else:
        raise SystemExit("khong doan duoc suite tu '%s'" % name)
    p = os.path.join(ROOT, sdir.replace("/", os.sep))
    if p not in sys.path:
        sys.path.insert(0, p)
    runner = importlib.import_module(runner_name)
    checker = importlib.import_module("checker_v16" if runner_name == "bench_v16"
                                      else "checker")
    return p, runner, checker, actions_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    p, runner, checker, actions_name = load_suite(a.suite)

    tids = [t["task_id"] for t in runner.load_tasks()]
    print("suite: %s | %d task x 3 variant" % (a.suite, len(tids)))

    pol = checker._Dispatcher(lambda tid, spec, peek: checker.POLICIES[tid](spec, peek))
    res = runner.run_suite(pol, tasks=tids, variants=(0, 1, 2), peek=True)

    out = {}
    nerr = 0
    for r in res:
        key = "%s@%d" % (r["task_id"], r["variant"])
        acts = []
        for st in r.get("trajectory", []):
            act = st.get("action", "")
            if act.startswith("<POLICY-ERROR"):
                nerr += 1
                print("  !! %s policy error: %s" % (key, act[:80]))
                continue
            acts.append(act)
        out[key] = acts
    npass = sum(1 for r in res if r.get("success"))
    print("success policy: %d/%d PASS | policy error: %d" % (npass, len(res), nerr))
    if a.dry_run:
        for k in list(out)[:3]:
            print("   %-20s %s" % (k, out[k][:6]))
        return 0
    if npass != len(res):
        print("FAIL: success policy khong pass het => khong ghi file (de khong "
              "ghi action sai vao suite)")
        return 1
    dst = os.path.join(p, actions_name)
    with io.open(dst, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("wrote %s (%d task-variant)" % (os.path.relpath(dst, ROOT), len(out)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
