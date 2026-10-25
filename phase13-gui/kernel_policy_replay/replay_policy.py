"""replay_policy.py - sinh DU LIEU TRAIN kieu THAT tu chinh cac task B15/B15.5/B16.

Y tuong: bench co script "success policy" (ground truth) cho tung task. Chay
policy tren trang THAT, chup anh TRUOC moi buoc -> row (image, instruction, action)
voi action dang "CLICK x y" (normalized 0..1000) — dung format data train GUI.
=> model hoc "nhin trang THAT -> bam dung cho", ke ca o nhung task no dang 0/3.

CHI variant 0 va 1 (variant 2 GIU LAI lam held-out de gate van sach).
Chay tren Kaggle CPU (khong ton GPU-quota).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

SUITES = [
    ("bench_v15", "checker", "ornith-gui-bench-v15"),
    ("bench_v155", "checker", "ornith-gui-bench-v155"),
    ("bench_v16", "checker_v16", "ornith-gui-bench-v16"),
]
VARIANTS = (0, 1)
OUT_ROOT = "/kaggle/working/replay"


def log(m):
    print("[replay] %s" % m, flush=True)


def find_suite_dir(module):
    for root, _dirs, files in os.walk("/kaggle/input"):
        if module + ".py" in files:
            return root
    return None


def child(suite_dir, module, checker_mod, out_dir):
    """Chay 1 suite trong process rieng (tranh xung module 'checker' giua 3 suite)."""
    sys.path.insert(0, suite_dir)
    import importlib
    suite = importlib.import_module(module)
    chk = importlib.import_module(checker_mod)
    from playwright.sync_api import sync_playwright

    tasks = suite.load_tasks()
    rows = []
    os.makedirs(out_dir, exist_ok=True)
    shots = os.path.join(out_dir, "shots")
    os.makedirs(shots, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        for t in tasks:
            tid = t["task_id"]
            pol_name = "policy_" + tid.split("_")[0].lower()
            pol = getattr(chk, pol_name, None)
            if pol is None:
                log("thieu policy %s -> bo qua" % pol_name)
                continue
            for v in VARIANTS:
                shot_dir = tempfile.mkdtemp(prefix="replay_")
                try:
                    # policy_tNN(spec, peek) la FACTORY -> tra policy_fn(obs)
                    _st = {}

                    def policy_fn(obs, _pol=pol, _st=_st):
                        if "fn" not in _st:
                            _st["fn"] = _pol(obs["spec"], obs.get("peek"))
                        return _st["fn"](obs)
                    res = suite.run_task(page, tid, v, policy_fn,
                                        shot_dir=shot_dir, peek=True)
                except Exception as e:
                    log("task %s v%d loi: %s" % (tid, v, e))
                    continue
                traj = res.get("trajectory") or []
                instr = res.get("instruction") or ""
                for i, st in enumerate(traj):
                    act = st.get("action") or ""
                    if not act or act.startswith("<POLICY-ERROR"):
                        continue
                    src = os.path.join(shot_dir, "%s_v%d_s%d.png" % (tid, v, i))
                    if not os.path.exists(src):
                        continue
                    name = "%s_v%d_s%d.png" % (tid, v, i)
                    shutil.copy2(src, os.path.join(shots, name))
                    rows.append({
                        "image": "shots/" + name,
                        "instruction": instr,
                        "action": _norm_action(act),
                        "task_id": tid, "variant": v, "step": i,
                        "suite": module, "src": "policy-replay",
                    })
                shutil.rmtree(shot_dir, ignore_errors=True)
        browser.close()
    with open(os.path.join(out_dir, "traj.jsonl"), "w", encoding="utf-8",
              newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log("suite %s: %d row" % (module, len(rows)))
    return rows


def _norm_action(act):
    """'CLICK 322.2 440.3' -> 'CLICK 322 440' (int, nhu format data train)."""
    p = act.strip().split()
    if not p:
        return act
    v = p[0].upper()
    if v == "CLICK" and len(p) >= 3:
        try:
            return "CLICK %d %d" % (round(float(p[1])), round(float(p[2])))
        except ValueError:
            return act
    if v == "TYPE" and len(p) >= 2:
        return "TYPE " + " ".join(p[1:])
    return act


def main():
    if "--child" in sys.argv:
        i = sys.argv.index("--child")
        return child(sys.argv[i + 1], sys.argv[i + 2], sys.argv[i + 3],
                     sys.argv[i + 4])
    # --- setup browser THAT (offline-browsers: copy /tmp + replay deps + ldconfig)
    # (image Kaggle thieu libatk... va chua co playwright -> phai dung setup)
    import subprocess as _sp
    import zipfile as _zf
    import tempfile as _tf
    helper = None
    for root, _dirs, files in os.walk("/kaggle/input"):
        if "setup_playwright_offline.py" in files:
            helper = root
            break
    if not helper:
        print("[replay] khong thay setup_playwright_offline.py", flush=True)
        return 1
    sys.path.insert(0, helper)
    from setup_playwright_offline import setup_playwright_offline
    info = setup_playwright_offline()
    print("[replay] offline browsers OK: %s" % str(info)[:200], flush=True)
    all_rows = []
    for module, chk, ds in SUITES:
        d = find_suite_dir(module)
        if not d:
            log("khong tim thay suite %s (dataset %s?)" % (module, ds))
            continue
        out_dir = os.path.join(OUT_ROOT, module)
        cmd = [sys.executable, os.path.abspath(__file__), "--child", d, module,
               chk, out_dir]
        p = subprocess.run(cmd, capture_output=True, timeout=5400)
        out = (p.stdout or b"").decode("utf-8", "replace")
        err = (p.stderr or b"").decode("utf-8", "replace")
        for ln in out.splitlines():
            if ln.startswith("[replay]"):
                log(ln)
        if p.returncode != 0:
            log("child %s rc=%s: %s" % (module, p.returncode, err[-800:]))
        f = os.path.join(out_dir, "traj.jsonl")
        if os.path.exists(f):
            with open(f, encoding="utf-8") as fh:
                for ln in fh:
                    if ln.strip():
                        all_rows.append(json.loads(ln))
    os.makedirs(OUT_ROOT, exist_ok=True)
    with open(os.path.join(OUT_ROOT, "traj.jsonl"), "w", encoding="utf-8",
              newline="\n") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_shot = 0
    with zipfile.ZipFile(os.path.join(OUT_ROOT, "shots.zip"), "w",
                         zipfile.ZIP_DEFLATED) as z:
        seen = set()
        for r in all_rows:
            name = os.path.basename(r["image"])
            if name in seen:
                continue
            seen.add(name)
            for module, _c, _d in SUITES:
                p = os.path.join(OUT_ROOT, module, "shots", name)
                if os.path.exists(p):
                    z.write(p, name)
                    n_shot += 1
                    break
    from collections import Counter
    cnt = Counter(r["task_id"] for r in all_rows)
    with open(os.path.join(OUT_ROOT, "replay_summary.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"n_rows": len(all_rows), "n_shots": n_shot,
                   "by_task": dict(cnt)}, fh, ensure_ascii=False, indent=1)
    log("TONG: %d row, %d anh" % (len(all_rows), n_shot))
    log("theo task: %s" % json.dumps(dict(cnt)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
