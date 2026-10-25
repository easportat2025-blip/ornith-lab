# -*- coding: utf-8 -*-
"""
colab_desktop_replay.py - TASK COLAB (MiMo): sinh GT trajectory cho 5 app
desktop theo DUNG format policy-replay (traj.jsonl + anh) - "thuoc" cho khoang
cach web 54% vs desktop 13%.

Ban 3 (22/10): dung CHINH run_task() cua checker_desktop (cung duong voi
bench) => trajectory khop 100% voi bench + co co 'success' cho tung episode.
Chi giu episode THUC SU GIAI DUOC (episode khong giai duoc = day sai).

Chay tren Colab CPU:
    python scripts/colab_exec_bg.py mimo-cpu2 scripts/colab_desktop_replay.py --acc 5 --wait 7200

ASCII-only source.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

IN_ZIP_URL = ("https://huggingface.co/datasets/kkouadn/ornith-colab-data/"
              "resolve/main/desktop_replay_in.zip")
WORK = os.environ.get("REPLAY_WORK", "/content/desktop_replay")
OUT = os.environ.get("REPLAY_OUT", "/content/desktop_replay_out")
ZIP_OUT = os.environ.get("REPLAY_ZIP", "/content/desktop_replay.zip")
W, H = 1280, 720
EPISODES = int(os.environ.get("REPLAY_EPISODES", "6"))
MAX_STEPS = int(os.environ.get("REPLAY_MAX_STEPS", "18"))
ONLY = [a for a in (os.environ.get("REPLAY_ONLY_APPS", "") or "").split(",")
        if a.strip()]
T0 = time.time()


def log(m):
    print("[replay] %s (t=%.0fs)" % (m, time.time() - T0), flush=True)


def sh(cmd, timeout=1800):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    tail = ((p.stdout or "") + (p.stderr or ""))[-300:].replace("\n", " ")
    log("rc=%s | %s" % (p.returncode, tail[:150]))
    return p.returncode == 0


def fetch_input():
    os.makedirs(WORK, exist_ok=True)
    zp = os.path.join(WORK, "in.zip")
    log("tai input: %s" % IN_ZIP_URL)
    with urllib.request.urlopen(IN_ZIP_URL, timeout=300) as r:
        data = r.read()
    with open(zp, "wb") as fh:
        fh.write(data)
    log("input: %d byte" % len(data))
    with zipfile.ZipFile(zp) as z:
        z.extractall(WORK)
    log("files: %s" % sorted(os.listdir(WORK))[:12])


def setup_browser():
    sh("pip install -q playwright 2>&1 | tail -2")
    sh("python -m playwright install chromium 2>&1 | tail -3", timeout=2400)
    sh("python -m playwright install-deps chromium 2>&1 | tail -3", timeout=2400)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.set_content("<h1>ok</h1>")
        pg.screenshot(path="/content/_probe.png")
        b.close()
    log("browser OK")


KEY_MAP = {
    "left": "ArrowLeft", "down": "ArrowDown",
    "right": "ArrowRight", "up": "ArrowUp",
    "esc": "Escape", "escape": "Escape", "enter": "Enter", "tab": "Tab",
    "space": "Space", "backspace": "Backspace", "delete": "Delete",
    "home": "Home", "end": "End", "pageup": "PageUp", "pagedown": "PageDown",
    "ctrl+a": "Control+a", "ctrl+c": "Control+c", "ctrl+v": "Control+v",
    "ctrl+x": "Control+x", "ctrl+z": "Control+z", "shift+tab": "Shift+Tab",
}


def press_key(pg, name):
    k = (name or "").strip().lower()
    pg.keyboard.press(KEY_MAP.get(k, name))


def act_to_str(act):
    if not act:
        return None
    v, a = act
    if v == "click":
        return "CLICK %d %d" % (a[0], a[1])
    if v == "type":
        return "TYPE %s" % a
    if v == "key":
        return "KEY %s" % str(a).lower()
    if v == "scroll":
        return "SCROLL %s" % (a if a else "3")
    return None


def main():
    fetch_input()
    setup_browser()
    sys.path.insert(0, WORK)
    import dummy_mimo
    import dummy_2048
    import checker_desktop as chk
    from playwright.sync_api import sync_playwright

    tasks = json.load(io.open(os.path.join(WORK, "tasks.json"),
                              encoding="utf-8"))["tasks"]
    os.makedirs(OUT, exist_ok=True)
    rows = []
    meta = {"apps": {}, "n_rows": 0}
    n_solved = n_ep = n_skip = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for t in tasks:
            tid = t["task_id"]
            if ONLY and t["app"] not in ONLY and tid not in ONLY:
                continue
            pol_cls = None
            if t["dummy"] == "DummyTableSort":
                # T23: policy theo Playwright, toa do tinh bang peek() (run_task
                # goi policy_fn({}, peek) -> fn(obs)).
                def _t23_policy(spec, peek):
                    def _rect(sel):
                        r = peek("(function(){const e=document.querySelector('%s');"
                                 "if(!e) return null;const r=e.getBoundingClientRect();"
                                 "return [Math.round((r.left+r.width/2)/innerWidth*1000),"
                                 "Math.round((r.top+r.height/2)/innerHeight*1000)];})()"
                                 % sel)
                        return r

                    def fn(obs):
                        s = obs["step"]
                        if s == 0:
                            r = _rect("#hscore")
                            return "CLICK %d %d" % (r[0], r[1])
                        if s == 1:
                            r = _rect("#hscore")
                            return "CLICK %d %d" % (r[0], r[1])
                        if s == 2:
                            r = _rect("#tb tr")
                            if r is None:
                                return "DONE"
                            return "CLICK %d %d" % (r[0], r[1])
                        if s == 3:
                            r = _rect("#confirm")
                            return "CLICK %d %d" % (r[0], r[1])
                        return "DONE"

                    return fn

                policy_fn = _t23_policy
            else:
                pol_cls = None
                try:
                    pol_cls = {"DummyFormDesktop": dummy_mimo.DummyFormDesktop,
                               "DummyCalc": dummy_mimo.DummyCalc,
                               "DummyTextEdit": dummy_mimo.DummyTextEdit,
                               "Dummy2048": dummy_2048.Dummy2048}[t["dummy"]]
                except Exception:
                    pol_cls = None
                if pol_cls is None:
                    log("!! thieu policy %s" % t["dummy"])
                    continue

                def _make(spec, peek, _cls=pol_cls, _t=t):
                    pol = _cls()

                    def fn(obs):
                        _d, act = pol.act("", _t, obs["step"])
                        return act_to_str(act) or "DONE"

                    return fn

                policy_fn = _make
            task = t
            ep_ok = 0
            for ep in range(EPISODES):
                ctx = browser.new_context(viewport={"width": W, "height": H})
                pg = ctx.new_page()
                dummy_mimo._page_state = (lambda js, _p=pg: _p.evaluate(js))
                dummy_2048.cdp_eval = (lambda js, _p=pg: _p.evaluate(js))
                shot_dir = os.path.join(OUT, "_tmp_%s_e%02d" % (tid, ep))
                try:
                    res = chk.run_task(pg, tid, policy_fn,
                                       max_steps=MAX_STEPS, shot_dir=shot_dir)
                except Exception as e:
                    log("%s ep%d run_task loi: %s" % (tid, ep, e))
                    ctx.close()
                    continue
                n_ep += 1
                if res.get("success"):
                    n_solved += 1
                    ep_ok += 1
                else:
                    n_skip += 1
                    shutil.rmtree(shot_dir, ignore_errors=True)
                    ctx.close()
                    continue
                for st in (res.get("trajectory") or []):
                    act = (st.get("action") or "").strip()
                    if not act or act.startswith("<ERR"):
                        continue
                    src = os.path.join(shot_dir, "%s_s%02d.png"
                                       % (tid, st.get("step") or 0))
                    if not os.path.exists(src):
                        continue
                    name = "%s_e%02d_s%02d.png" % (tid, ep,
                                                    st.get("step") or 0)
                    shutil.copy2(src, os.path.join(OUT, name))
                    rows.append({"image": name, "instruction": t["instruction"],
                                 "action": act, "task_id": tid,
                                 "variant": 0, "step": st.get("step") or 0,
                                 "suite": "desktop", "src": "policy-replay"})
                shutil.rmtree(shot_dir, ignore_errors=True)
                ctx.close()
            meta["apps"][tid] = {"app": t["app"], "episodes": EPISODES,
                                 "solved": ep_ok}
            log("%s: %d/%d episode giai duoc" % (tid, ep_ok, EPISODES))
        browser.close()
    tj = os.path.join(OUT, "traj.jsonl")
    with open(tj, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta["n_rows"] = len(rows)
    meta["n_episodes"] = n_ep
    meta["n_solved"] = n_solved
    meta["n_skipped_unsolved"] = n_skip
    meta["solve_rate"] = round(n_solved / max(n_ep, 1), 3)
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    if os.path.exists(ZIP_OUT):
        os.remove(ZIP_OUT)
    with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(OUT)):
            z.write(os.path.join(OUT, f), f)
    log("KET QUA: %d row | %d/%d episode giai duoc (%.0f%%) -> %s (%.1f MB)"
        % (len(rows), n_solved, n_ep, 100.0 * n_solved / max(n_ep, 1),
           ZIP_OUT, os.path.getsize(ZIP_OUT) / 1048576.0))
    if not rows:
        log("!! 0 row - FAIL")
        return 1
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:
        import traceback
        log("EXCEPTION: %s" % e)
        traceback.print_exc()
        rc = 1
    sys.exit(rc)
