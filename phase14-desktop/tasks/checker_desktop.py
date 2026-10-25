# -*- coding: utf-8 -*-
"""
checker_desktop.py - TASK-26: checker + success-policy + fail-policy cho 5
app desktop (T20_2048, T21_form_desktop, T22_calc, T23_table_sort, T24_text_edit).

Nguyen tac (giong B15/B15.5):
  * Checker DOC DOM (text/element/value), KHONG tin co-flag cua app.
  * Bien NGAY NHIEN: moi app sinh gia tri moi moi lan load; checker TIN LAI
    trong Python tu DOM (vd parse "137 + 58 = ?" roi cong lai).
  * Success-policy DOC bien tu DOM (peek) roi moi lam dung buoc.
  * Fail-policy phai bi reject.
  * Self-test: moi task chay N lan (moi lan la 1 bien moi) x success + fail.

Chay:
    python phase14-desktop/tasks/checker_desktop.py --self-test
"""
import json
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VIEW_W, VIEW_H = 1280, 720
SCORE_MIN = 40          # nguong diem cua T20_2048


# ---------------------------------------------------------------- helpers
APP_FILES = {
    "T20_2048": "game_2048.html",
    "T21_form_desktop": "t21_form_desktop.html",
    "T22_calc": "t22_calc.html",
    "T23_table_sort": "t23_table_sort.html",
    "T24_text_edit": "t24_text_edit.html",
}


def app_file(task_id):
    return os.path.join(HERE, APP_FILES.get(task_id, task_id.lower() + ".html"))


def _r2n(x, y):
    return [max(0, min(1000, int(round(x / VIEW_W * 1000)))),
            max(0, min(1000, int(round(y / VIEW_H * 1000))))]


def click_norm(x, y):
    return "CLICK %d %d" % _r2n(x, y)


KEY_ALIAS = {"ctrl": "Control", "shift": "Shift", "alt": "Alt", "meta": "Meta",
             "esc": "Escape", "return": "Enter", "space": "Space",
             # FIX 22/10 (MiMo): phim mui ten - ten xdotool (left) khac ten
             # Playwright/e.key (ArrowLeft) => run_task() (duong Playwright)
             # bi "Unknown key" => 2048 khong chay. (bench that dung xdotool
             # nen loi nay khong lo; KEY_ALIAS chi dung cho run_task.)
             "left": "ArrowLeft", "right": "ArrowRight",
             "up": "ArrowUp", "down": "ArrowDown",
             "pgup": "PageUp", "pgdn": "PageDown",
             "pageup": "PageUp", "pagedown": "PageDown",
             "del": "Delete", "bs": "Backspace"}


def _norm_key(name):
    parts = str(name).split("+")
    return "+".join(KEY_ALIAS.get(p.strip().lower(), p.strip()) for p in parts)


def fmt(v):
    return "CLICK %d %d" % (int(v[0]), int(v[1]))


# ---------------------------------------------------------------- checkers
def check_t20(page):
    st = page.evaluate("""() => ({
        score_txt: (document.getElementById('s')||{}).textContent || '0',
        score_win: (window.__score)||0,
        cells: document.querySelectorAll('#board .t').length,
        max_tile: Math.max.apply(null, Array.from(
            document.querySelectorAll('#board .t')).map(
                e => parseInt(e.textContent||'0',10)||0)),
    })""")
    m = re.search(r"-?\d+", st["score_txt"] or "")
    shown = int(m.group(0)) if m else 0
    tests = {
        "score text is a number": shown >= 0,
        "board rendered": st["cells"] == 16,
        "score >= %d" % SCORE_MIN: shown >= SCORE_MIN,
    }
    st["score"] = shown
    return tests, st


def check_t21(page):
    st = page.evaluate("""() => {
      const v=id=>(document.getElementById(id)||{}).value||'';
      return {want_user:(document.getElementById('nu')||{}).textContent||'',
              want_email:(document.getElementById('ne')||{}).textContent||'',
              want_pw:(document.getElementById('np')||{}).textContent||'',
              u:v('u'), e:v('e'), p:v('p'), p2:v('p2'),
              terms:!!(document.getElementById('terms')||{}).checked,
              status:(document.getElementById('status')||{}).textContent||''};
    }""")
    tests = {
        "username matches note": st["u"].strip() == st["want_user"].strip()
                                  and st["want_user"].strip() != "",
        "email matches note": st["e"].strip() == st["want_email"].strip()
                               and st["want_email"].strip() != "",
        "password matches note": st["p"].strip() == st["want_pw"].strip()
                                  and st["want_pw"].strip() != "",
        "confirm password matches": st["p2"].strip() == st["want_pw"].strip(),
        "terms ticked": st["terms"],
        "submitted": "Account created" in st["status"],
    }
    return tests, st


def check_t22(page):
    st = page.evaluate("""() => ({
        e1:(document.getElementById('e1')||{}).textContent||'',
        e2:(document.getElementById('e2')||{}).textContent||'',
        a1:(document.getElementById('a1')||{}).value||'',
        a2:(document.getElementById('a2')||{}).value||'',
        status:(document.getElementById('status')||{}).textContent||'',
    })""")
    def solve(expr):
        m = re.search(r"(\d+)\s*([+-])\s*(\d+)", expr or "")
        if not m:
            return None
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return a + b if op == "+" else a - b
    s1, s2 = solve(st["e1"]), solve(st["e2"])
    tests = {
        "question 1 expression parsed": s1 is not None,
        "question 2 expression parsed": s2 is not None,
        "answer 1 correct": s1 is not None and st["a1"].strip() == str(s1),
        "answer 2 correct": s2 is not None and st["a2"].strip() == str(s2),
        "submitted": "accepted" in st["status"],
    }
    return tests, st


def check_t23(page):
    st = page.evaluate("""() => {
      const data=(document.getElementById('data')||{}).textContent||'[]';
      const rows=Array.from(document.querySelectorAll('#tb tr')).map(tr=>
        Array.from(tr.children).map(td=>td.textContent.trim()));
      const sel=document.querySelector('#tb tr.sel');
      return {data:data, rows:rows,
              selected: sel ? Array.from(sel.children).map(td=>td.textContent.trim()) : null,
              status:(document.getElementById('status')||{}).textContent||''};
    }""")
    try:
        data = json.loads(st["data"])
    except Exception:
        data = []
    by_region = {d["region"]: d for d in data}
    # thu tu mong doi: score giam dan (desc) - neu 2 bang bang, theo thu tu goc
    expect = sorted(data, key=lambda d: -d["score"])
    exp_rows = [[d["region"], d["owner"], str(d["score"])] for d in expect]
    got_rows = st["rows"]
    top = expect[0]["region"] if expect else None
    sel_ok = bool(st["selected"]) and st["selected"][0] == top
    tests = {
        "source data present": len(data) == 12,
        "all rows rendered": len(got_rows) == len(data),
        "order is score descending": got_rows == exp_rows,
        "top row selected": sel_ok,
        "confirmed": "Confirmed" in st["status"],
    }
    st["n_data"] = len(data)
    return tests, st


def check_t24(page):
    st = page.evaluate("""() => ({
        want:(document.getElementById('want')||{}).textContent||'',
        text:(document.getElementById('ta')||{}).value||'',
        status:(document.getElementById('status')||{}).textContent||'',
    })""")
    tests = {
        "target text present": st["want"].strip() != "",
        "text matches target": st["text"].strip() == st["want"].strip(),
        "saved": "Saved" in st["status"],
    }
    return tests, st


CHECKS = {
    "T20_2048": check_t20,
    "T21_form_desktop": check_t21,
    "T22_calc": check_t22,
    "T23_table_sort": check_t23,
    "T24_text_edit": check_t24,
}


def check_task(page, task_id):
    fn = CHECKS[task_id]
    tests, state = fn(page)
    failed = [k for k, v in tests.items() if not v]
    ok = not failed
    return {"success": ok, "score": 1.0 if ok else 0.0,
            "reason": "all %d checks pass" % len(tests) if ok
                      else "failed: " + ", ".join(failed),
            "state": {"tests": tests, **state}}


# ------------------------------------------------------------- 2048 helper
def _slide(row):
    a = [x for x in row if x]
    res = []
    i = 0
    while i < len(a):
        if i + 1 < len(a) and a[i] == a[i + 1]:
            res.append(a[i] * 2)
            i += 2
        else:
            res.append(a[i])
            i += 1
    res += [0] * (4 - len(res))
    return res


def _sim(grid, d):
    g = [r[:] for r in grid]
    if d == "L":
        return [_slide(r) for r in g]
    if d == "R":
        return [list(reversed(_slide(list(reversed(r))))) for r in g]
    if d == "U":
        cols = [list(c) for c in zip(*g)]
        return [list(x) for x in zip(*[_slide(c) for c in cols])]
    if d == "D":
        cols = [list(reversed(c)) for c in zip(*g)]
        return [list(x) for x in zip(*[_slide(c) for c in cols])]
    return g


_DIRS = ["L", "U", "R", "D"]
_W = [[16, 8, 4, 2], [8, 4, 2, 1], [4, 2, 1, 0.5], [2, 1, 0.5, 0.25]]


def _h(g):
    """Heuristic 2048: o trong + bonus goc + snake weight (2-ply de khong ket)."""
    flat = [v for r in g for v in r]
    empt = flat.count(0)
    mx = max(flat)
    bonus = 100 if g[3][3] == mx else (60 if g[0][0] == mx else 0)
    snake = sum(v * _W[i][j] for i, row in enumerate(g) for j, v in enumerate(row))
    return empt * 10 + bonus + snake * 0.01


def _best_move(grid):
    """Chon nuoc di tot nhat (2-ply). Tra None neu khong con nuoc di."""
    best, besth = None, -1e18
    for d in _DIRS:
        g1 = _sim(grid, d)
        if g1 == grid:
            continue
        h1 = _h(g1)
        best2 = -1e18
        for d2 in _DIRS:
            g2 = _sim(g1, d2)
            if g2 == g1:
                continue
            best2 = max(best2, _h(g2))
        val = best2 if best2 > -1e17 else h1
        if val > besth:
            best, besth = d, val
    return best


# ------------------------------------------------------------- policies
def _queue(acts):
    st = {"i": 0}

    def fn(obs):
        i = st["i"]
        st["i"] += 1
        if i >= len(acts):
            return "DONE"
        a = acts[i]
        return a(obs) if callable(a) else a
    return fn


def _tg(peek, tid, key):
    """Toa do normalized cua 1 element (doc tu DOM moi)."""
    js = ("() => { const t=window.__targets||{}; const v=t['%s'];"
          " return v? v : null; }" % key)
    return peek(js)


def _live(peek, key):
    """Toa do normalized SONG (getBoundingClientRect luc chay) - dung khi
    trang bi cuon (nut Confirm cua T23 nam ngoai viewport o luc load)."""
    js = ("() => { const e=document.getElementById('%s'); if(!e) return null;"
          " const r=e.getBoundingClientRect();"
          " return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10,"
          "         Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }" % key)
    return peek(js)


def policy_t20(spec, peek):
    """Greedy bot 2048: moi buoc mo phong 4 nuoc di, chon nuoc tot nhat."""
    st = {"n": 0}

    def fn(obs):
        st["n"] += 1
        if st["n"] > 120:
            return "DONE"
        grid = peek("() => window.__grid")
        if not grid:
            return "DONE"
        d = _best_move(grid)
        if d is None:
            return "DONE"
        return "KEY " + {"L": "ArrowLeft", "U": "ArrowUp",
                         "R": "ArrowRight", "D": "ArrowDown"}[d]
    return fn


def policy_t21(spec, peek):
    def act(key):
        return lambda obs: fmt(_live(peek, key))
    nu = peek("() => (document.getElementById('nu')||{}).textContent||''")
    ne = peek("() => (document.getElementById('ne')||{}).textContent||''")
    npw = peek("() => (document.getElementById('np')||{}).textContent||''")
    return _queue([
        act("u"), "TYPE " + nu,
        act("e"), "TYPE " + ne,
        act("p"), "TYPE " + npw,
        act("p2"), "TYPE " + npw,
        act("terms"),
        act("submit"),
    ])


def policy_t22(spec, peek):
    def act(key):
        return lambda obs: fmt(_live(peek, key))
    e1 = peek("() => (document.getElementById('e1')||{}).textContent||''")
    e2 = peek("() => (document.getElementById('e2')||{}).textContent||''")

    def solve(e):
        m = re.search(r"(\d+)\s*([+-])\s*(\d+)", e or "")
        if not m:
            return "0"
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return str(a + b if op == "+" else a - b)
    return _queue([
        act("a1"), "TYPE " + solve(e1), act("c1"),
        act("a2"), "TYPE " + solve(e2), act("c2"),
        act("submit"),
    ])


def policy_t23(spec, peek):
    """Sort theo Score GIAM DAN, chon dong cao nhat, confirm.

    FIX 24/10 (GLM): policy cu (cuon xuong bang 'KEY End' roi moi chon dong
    cao nhat) lam dong TOP - sau khi sort desc la dong dau - bi DAY KHOI MAN
    HINH => click truot => 0/6 episode giai duoc (app bi loai khoi data).
    Nay: KHONG cuon (dong dau luon o tren man hinh) + normalize toa do theo
    VIEWPORT THAT (innerWidth/innerHeight, khong hard-code 1280x720).
    """
    st = {"phase": 0}

    def act(key):
        p = _live(peek, key)
        return "CLICK %d %d" % (int(p[0]), int(p[1])) if p else "DONE"

    def fn(obs):
        if st["phase"] == 0:
            st["phase"] = 1
            arrow = peek("() => (document.getElementById('arrow')||{}).textContent||''")
            if "desc" in (arrow or ""):
                return "DONE"                # da desc
            return act("hscore")            # chua desc -> click header 1 lan
        if st["phase"] == 1:
            # header vong 0->asc->desc: phai BAM LAI cho den khi arrow=desc
            arrow = peek("() => (document.getElementById('arrow')||{}).textContent||''")
            if "desc" not in (arrow or ""):
                return act("hscore")
            st["phase"] = 2
            return _click_row(peek)         # dong dau = dong score cao nhat
        if st["phase"] == 2:
            st["phase"] = 3
            # nut Confirm nam DUOI man hinh (y~1066/1000) => cuon xuong truoc
            p = _live(peek, "confirm")
            if p and int(p[1]) > 950:
                return "SCROLL 5"
            return act("confirm")
        if st["phase"] == 3:
            st["phase"] = 4
            p = _live(peek, "confirm")
            if p and int(p[1]) > 950:
                return "SCROLL 5"           # van chua cuon duoc -> cuon them
            return act("confirm")
        return "DONE"
    return fn


def _click_row(peek):
    """Click DONG DAU cua bang (sau khi sort desc = dong co score cao nhat).

    FIX 24/10 (GLM): (a) chon 'dong dau' thay vi 'score cao nhat' - sau khi
    sort desc thi dong dau DA la dong cao nhat va luon o tren man hinh;
    (b) normalize theo VIEWPORT THAT (innerWidth/innerHeight) thay vi
    hard-code 1280x720 (viewport that 1264x625 => click truot).
    """
    js = """() => {
      const rows=Array.from(document.querySelectorAll('#tb tr'));
      if(!rows.length) return null;
      const best=rows[0];
      const r=best.getBoundingClientRect();
      const W=window.innerWidth||1280,H=window.innerHeight||720;
      return [Math.round(((r.left+r.width/2)/W*1000)*10)/10,
              Math.round(((r.top+r.height/2)/H*1000)*10)/10];
    }"""
    p = peek(js)
    return "CLICK %d %d" % (int(p[0]), int(p[1])) if p else "DONE"


def policy_t24(spec, peek):
    def act(key):
        return lambda obs: fmt(_live(peek, key))
    want = peek("() => (document.getElementById('want')||{}).textContent||''")
    return _queue([
        act("ta"), "KEY ctrl+a", "TYPE " + want, act("save"),
    ])


POLICIES = {
    "T20_2048": policy_t20,
    "T21_form_desktop": policy_t21,
    "T22_calc": policy_t22,
    "T23_table_sort": policy_t23,
    "T24_text_edit": policy_t24,
}


def fail_policy(obs):
    """Policy that that: click goc man hinh roi DONE."""
    return "CLICK 10 10" if obs["step"] == 0 else "DONE"


def wrong_value_policy(obs):
    """Policy sai 'gia tri' (dung cho T21/T22/T24): go sai roi DONE."""
    if obs["step"] == 0:
        return "CLICK 10 10"
    if obs["step"] == 1:
        return "TYPE zzz-wrong-value"
    return "DONE"


# ---------------------------------------------------------------- runner
def run_task(page, task_id, policy_fn, max_steps=20, shot_dir=None):
    """policy_fn: (spec, peek) -> fn(obs) cho success-policy,
       hoac fn(obs) cho fail-policy (da dung ky hieu 1 tham so)."""
    url = "file:///" + app_file(task_id).replace("\\", "/")
    page.goto(url)
    page.wait_for_timeout(250)
    peek = lambda js: page.evaluate(js)
    try:
        pol = policy_fn({}, peek)
    except TypeError:
        pol = policy_fn
    trajectory = []
    for step in range(max_steps):
        obs = {"task_id": task_id, "step": step, "peek": peek}
        try:
            action = pol(obs)
        except Exception as e:
            trajectory.append({"step": step, "action": "<ERR:%s>" % e})
            break
        trajectory.append({"step": step, "action": action})
        if action == "DONE":
            break
        # FIX 22/10 (MiMo): chup anh TRUOC khi thuc hien action (quan sat cua
        # model) - dung de sinh data desktop-replay (policy-replay format).
        if shot_dir:
            import os as _os
            _os.makedirs(shot_dir, exist_ok=True)
            page.screenshot(path=_os.path.join(
                shot_dir, "%s_s%02d.png" % (task_id, step)))
        kind = action.split(None, 1)[0].upper()
        if kind == "CLICK":
            x, y = action.split()[1:3]
            page.mouse.click(int(x) / 1000.0 * VIEW_W,
                             int(y) / 1000.0 * VIEW_H)
        elif kind == "TYPE":
            page.keyboard.type(action.split(None, 1)[1], delay=5)
        elif kind == "KEY":
            page.keyboard.press(_norm_key(action.split(None, 1)[1]))
        elif kind == "SCROLL":
            # FIX 24/10 (GLM): runner bo qua SCROLL => policy "cuon xuong" vo
            # hieu luc => nut Confirm (y~1066) o ngoai man hinh => click truot
            # => T23_table_sort 0/6 episode giai duoc. Bay gio SCROLL = chuot xe.
            try:
                _n = int(action.split(None, 1)[1])
            except Exception:
                _n = 3
            page.mouse.move(VIEW_W / 2, VIEW_H / 2)
            page.mouse.wheel(0, _n * 100)
        page.wait_for_timeout(40)
    res = check_task(page, task_id)
    return {"task_id": task_id, "success": bool(res["success"]),
            "reason": res["reason"], "state": res["state"],
            "steps": len(trajectory), "trajectory": trajectory}


def self_test(reps=3):
    from playwright.sync_api import sync_playwright
    tasks = list(CHECKS.keys())
    rows = []
    n_ok = n_rej = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": VIEW_W, "height": VIEW_H})
        for tid in tasks:
            for r in range(reps):
                pol = POLICIES[tid]
                ok = run_task(page, tid, pol)
                # fail policies: (a) click goc (b) go sai gia tri
                f1 = run_task(page, tid, fail_policy)
                f2 = run_task(page, tid, wrong_value_policy)
                good = ok["success"] and not f1["success"] and not f2["success"]
                n_ok += 1 if ok["success"] else 0
                n_rej += 1 if (not f1["success"] and not f2["success"]) else 0
                rows.append({"task_id": tid, "rep": r,
                             "success_policy_pass": ok["success"],
                             "success_reason": ok["reason"],
                             "fail_click_rejected": not f1["success"],
                             "fail_wrongvalue_rejected": not f2["success"],
                             "ok": good})
                print("  %-18s rep%d  success:%s (%s)  fail-click:%s  fail-wrong:%s"
                      % (tid, r, "PASS" if ok["success"] else "FAIL",
                         ok["reason"][:44],
                         "rejected" if not f1["success"] else "ACCEPTED!",
                         "rejected" if not f2["success"] else "ACCEPTED!"))
        b.close()
    total = len(tasks) * reps
    passed = (n_ok == total and n_rej == total)
    out = os.path.join(HERE, "self_test_report.json")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"success_policies_pass": n_ok, "success_total": total,
                             "fail_policies_rejected": n_rej, "fail_total": total,
                             "reps_per_task": reps, "passed": passed,
                             "rows": rows}, ensure_ascii=False, indent=1))
    print("[self-test] success %d/%d, fail rejected %d/%d -> %s => %s"
          % (n_ok, total, n_rej, total, out, "PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        reps = 3
        for i, a in enumerate(sys.argv):
            if a == "--reps" and i + 1 < len(sys.argv):
                reps = int(sys.argv[i + 1])
        sys.exit(self_test(reps))
    print("usage: python checker_desktop.py --self-test [--reps N]")
    sys.exit(1)
