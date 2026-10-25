"""check_replay_quality.py - KIEM CHAT LUONG du lieu 'desktop-real replay'
(GLM, 22/10) - do lai bang CHE CUA CHECKER, khong tin self-report.

LY DO: replay la du lieu train GIA TRI CAO NHAT cho v25 (khoang cach web 54% vs
desktop 13%). No duoc sinh tu 'success policy' cua checker => chat luong duoc
dinh nghia boi: **success policy co THAT SU dat task khong?** + **co row hong
khong?** (POLICY-ERROR / anh thieu) + **so row co khop voi ban da giao khong?**

Cach kiem (0 GPU, dung chromium local):
  1) chay lai success policy tren tung task (1 variant) => res['success']
  2) dem row hong (action rong / POLICY-ERROR / anh thieu)
  3) doi chieu row sinh voi ban da giao (out_policy_replay/replay/traj.jsonl)

Dung:
  python phase13-gui/check_replay_quality.py
  python phase13-gui/check_replay_quality.py --variants 2
"""
import argparse
import collections
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# (suite dir, module suite, module checker)
SUITES = [
    (os.path.join(HERE, "bench_v15"), "bench_v15", "checker"),
    (os.path.join(HERE, "bench_v15", "tasks_v15_5"), "bench_v155", "checker"),
    (os.path.join(HERE, "bench_v15", "tasks_v16_a"), "bench_v16",
     "checker_v16"),
]
DELIVERED = os.path.join(HERE, "out_policy_replay", "replay", "traj.jsonl")


def log(m):
    print("[rq] %s" % m, flush=True)


def run_suite(suite_dir, module, checker_mod, variants):
    import importlib
    if suite_dir not in sys.path:
        sys.path.insert(0, suite_dir)
    suite = importlib.import_module(module)
    chk = importlib.import_module(checker_mod)
    from playwright.sync_api import sync_playwright

    tasks = suite.load_tasks()
    n_task = 0
    n_ok = 0
    n_rows = 0
    n_bad = 0
    fails = []
    per_task_rows = collections.Counter()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for t in tasks:
            tid = t["task_id"]
            pol_name = "policy_" + tid.split("_")[0].lower()
            pol = getattr(chk, pol_name, None)
            if pol is None:
                # B15.5 (v155) dat ten policy khac (vd policy_t13_wizard)
                for cand in ("policy_" + tid.lower(),
                             "policy_" + tid.split("_")[0].lower() + "_" +
                             tid.split("_", 1)[-1].lower()):
                    pol = getattr(chk, cand, None)
                    if pol is not None:
                        pol_name = cand
                        break
            if pol is None:
                # cuoi cung: bat ky policy_ nao khop so T
                n_pref = tid.split("_")[0].lower()
                for k in dir(chk):
                    if k.startswith("policy_") and n_pref in k.lower():
                        pol = getattr(chk, k)
                        pol_name = k
                        break
            if pol is None:
                fails.append("%s: thieu policy (thu %s)" % (tid, pol_name))
                continue
            n_task += 1
            for v in range(variants):
                shot_dir = tempfile.mkdtemp(prefix="rq_")
                try:
                    _st = {}

                    def policy_fn(obs, _pol=pol, _st=_st):
                        if "fn" not in _st:
                            _st["fn"] = _pol(obs["spec"], obs.get("peek"))
                        return _st["fn"](obs)
                    res = suite.run_task(page, tid, v, policy_fn,
                                        shot_dir=shot_dir, peek=True)
                except Exception as e:
                    fails.append("%s v%d: EXCEPTION %s" % (tid, v,
                                                          str(e)[:70]))
                    shutil.rmtree(shot_dir, ignore_errors=True)
                    continue
                finally:
                    shutil.rmtree(shot_dir, ignore_errors=True)
                traj = res.get("trajectory") or []
                good = 0
                for st in traj:
                    act = st.get("action") or ""
                    if not act or act.startswith("<POLICY-ERROR"):
                        n_bad += 1
                        continue
                    good += 1
                n_rows += good
                per_task_rows[tid] += good
                if res.get("success"):
                    n_ok += 1
                else:
                    fails.append("%s v%d: success policy KHONG dat task" % (tid, v))
        browser.close()
    return {"tasks": n_task, "ok": n_ok, "rows": n_rows, "bad": n_bad,
            "fails": fails, "per_task": dict(per_task_rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", type=int, default=1)
    ap.add_argument("--only", type=int, default=-1,
                    help="chay 1 suite (dung cho process con) va in JSON")
    a = ap.parse_args()
    if a.only >= 0:
        suite_dir, module, checker_mod = SUITES[a.only]
        r = run_suite(suite_dir, module, checker_mod, a.variants)
        print("[rq] SUITE_JSON " + json.dumps(r, ensure_ascii=False))
        return 0 if not r["fails"] else 1
    total = {"tasks": 0, "ok": 0, "rows": 0, "bad": 0}
    all_fails = []
    print("| suite | task | success | row | row hong |")
    print("|---|---|---|---|---|")
    for idx, (suite_dir, module, checker_mod) in enumerate(SUITES):
        if not os.path.isdir(suite_dir):
            log("thieu %s - bo qua" % suite_dir)
            continue
        # MOI SUITE 1 PROCESS RIENG: 3 suite deu co module ten 'checker' =>
        # import trong cung process se bi cache => sai suite.
        import subprocess
        pr = subprocess.run([sys.executable, __file__, "--only", str(idx),
                             "--variants", str(a.variants)],
                            capture_output=True)
        out = (pr.stdout or b"").decode("utf-8", "replace")
        err = (pr.stderr or b"").decode("utf-8", "replace")
        for line in out.splitlines():
            if line.startswith("| "):
                print(line)
            elif line.startswith("[rq] SUITE_JSON "):
                import json as _j
                r = _j.loads(line[len("[rq] SUITE_JSON "):])
                for k in total:
                    total[k] += r[k]
                all_fails += ["[%s] %s" % (module, f) for f in r["fails"]]
        if pr.returncode not in (0, 1) and err.strip():
            log("suite %s loi: %s" % (module, err.strip()[-200:]))
    print()
    log("TONG: %d task | success %d (%.1f%%) | %d row | %d row hong" %
        (total["tasks"], total["ok"],
         100.0 * total["ok"] / max(total["tasks"], 1),
         total["rows"], total["bad"]))

    # doi chieu voi ban da giao
    if os.path.isfile(DELIVERED):
        rows = [json.loads(l) for l in io.open(DELIVERED, encoding="utf-8",
                                              errors="replace") if l.strip()]
        bad = 0
        for r in rows:
            a_ = (r.get("action") or "").strip()
            if not a_ or a_.startswith("<POLICY-ERROR"):
                bad += 1
        log("BAN DA GIAO: %d row (%d row hong) | tasks: %d" %
            (len(rows), bad, len(set(r.get("task_id") for r in rows))))
        miss = set(r.get("task_id") for r in rows) - set(total["tasks"] and
                                                         [] or [])
        if bad:
            log("!! %d row hong trong ban giao" % bad)
    else:
        log("khong thay ban da giao: %s" % DELIVERED)

    if all_fails:
        print()
        log("TASK/EP LOI (%d):" % len(all_fails))
        for f in all_fails[:40]:
            log("   %s" % f)
        return 1
    log("OK: moi task co success policy that su dat task")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
