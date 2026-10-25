"""local_selftest_deepseek.py — E2E local cho bench_v15 (DeepSeek doc lap, 19/10).

Muc dich: xac minh CO HOC (runner bench_v15 + 12 trang + exec action) tren may
local (playwright 1.58) khong can GPU/Kaggle:
  - scan   : mo trang that, do toa do nut, mo phong tung buoc de tinh action
             sequence CHINH XAC (click, type, clipboard, scroll, slider, canvas,
             delayed tile co sleep trong policy).
  - pass-run: 12 task x v0 voi sequence dung  -> ky vong 12/12 success.
  - fail-run: 6 task co tinh lam sai          -> ky vong bat dung 6/6 fail.
Checker duoc STUB in-memory theo semantics `document.body.dataset` (khi
`checker.py` cua MiMo co that, chay `--real` de doi chieu DOC LAP).

Chay: python phase13-gui/bench_v15/local_selftest_deepseek.py [--real]
"""
import json
import os
import re
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
VW, VH = 1280, 720


def _i(s, d=-1):
    try:
        return int(s)
    except Exception:
        return d


def _expected_coupon(d):
    try:
        return f"{float(d['price']) * (1 - float(d['disc'])):.2f}"
    except Exception:
        return None


# stub semantics — theo field map da verify bang lint_pages.py + local_probe
SUCC = {
    "T01_signup": lambda d: d.get("created") == "1",
    "T02_login": lambda d: d.get("loggedin") == "1",
    "T03_delayed": lambda d: d.get("correct") == "1",
    "T04_slider": lambda d: d.get("value") == d.get("target"),
    "T05_shortcut": lambda d: d.get("match") == "1",
    "T06_tabcode": lambda d: d.get("correct") == "1",
    "T07_scroll": lambda d: (_i(d.get("clicked")) == _i(d.get("total")) - 1
                             and _i(d.get("clickedcount")) == _i(d.get("total"))),
    "T08_errorfix": lambda d: (d.get("errorsshown") == "1"
                               and d.get("submittedok") == "1"),
    "T09_coupon": lambda d: (d.get("selected") == d.get("targetplan")
                             and d.get("applied") == "1"
                             and d.get("confirmed") == "1"
                             and d.get("total") == _expected_coupon(d)),
    "T10_canvas": lambda d: d.get("correct") == "1",
    "T11_counter": lambda d: (d.get("submitted") == "1"
                              and d.get("count") == d.get("targetcount")),
    "T12_pagecode": lambda d: d.get("correct") == "1",
}

ALL12 = ["T01_signup", "T02_login", "T03_delayed", "T04_slider",
         "T05_shortcut", "T06_tabcode", "T07_scroll", "T08_errorfix",
         "T09_coupon", "T10_canvas", "T11_counter", "T12_pagecode"]


def norm(rect):
    return (int(round((rect["x"] + rect["width"] / 2) / VW * 1000)),
            int(round((rect["y"] + rect["height"] / 2) / VH * 1000)))


def scan(v=0):
    from playwright.sync_api import sync_playwright
    acts = {}
    notes = []

    def url(tid):
        p = os.path.join(HERE, "tasks", tid.lower() + ".html")
        return "file:///" + p.replace("\\", "/") + f"?v={v}"

    def cen(page, sel):
        return norm(page.locator(sel).bounding_box())

    def px(page, x, y):
        page.mouse.click(x / 1000 * VW, y / 1000 * VH)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": VW, "height": VH})
        page.set_default_timeout(5000)

        def goto(tid):
            page.goto(url(tid))
            page.wait_for_timeout(320)

        # ---- T01 signup ----
        goto("t01_signup")
        em, p1, p2 = cen(page, "#email"), cen(page, "#pass"), cen(page, "#confirm")
        ck, bt = cen(page, "#terms"), cen(page, "#submit")
        pw = "abcd1234xyzw"          # 12 chars — du moi variant
        head = [f"CLICK {em[0]} {em[1]}", "TYPE user@example.com",
                f"CLICK {p1[0]} {p1[1]}", "TYPE " + pw,
                f"CLICK {p2[0]} {p2[1]}"]
        tail = [f"CLICK {ck[0]} {ck[1]}", f"CLICK {bt[0]} {bt[1]}"]
        acts["T01_signup"] = head + ["TYPE " + pw] + tail
        acts["T01_signup_fail"] = head + ["TYPE wrong-pass"] + tail

        # ---- T02 login ----
        goto("t02_login")
        user = page.locator("#note_user").text_content().strip()
        pwd = page.locator("#note_pass").text_content().strip()
        u, q, si = cen(page, "#user"), cen(page, "#pass"), cen(page, "#signin")
        acts["T02_login"] = [f"CLICK {u[0]} {u[1]}", "TYPE " + user,
                             f"CLICK {q[0]} {q[1]}", "TYPE " + pwd,
                             f"CLICK {si[0]} {si[1]}"]
        acts["T02_login_fail"] = [f"CLICK {u[0]} {u[1]}", "TYPE " + user,
                                  f"CLICK {q[0]} {q[1]}", "TYPE wrongpw",
                                  f"CLICK {si[0]} {si[1]}"]

        # ---- T03 delayed ----
        goto("t03_delayed")
        tgt = int(page.evaluate("() => document.body.dataset.target"))
        delay = int(page.evaluate("() => document.body.dataset.delay"))
        txy = cen(page, f"#tile{tgt}")
        wxy = cen(page, f"#tile{(tgt + 1) % 12}")
        sl = delay / 1000.0 + 0.6
        acts["T03_delayed"] = [f"SLEEP:{sl:.1f}|CLICK {txy[0]} {txy[1]}"]
        acts["T03_delayed_fail"] = [f"SLEEP:{sl:.1f}|CLICK {wxy[0]} {wxy[1]}"]
        page.wait_for_timeout(delay + 350)
        px(page, *txy)
        page.wait_for_timeout(150)
        notes.append("sim T03 correct="
                     + str(page.evaluate("() => document.body.dataset.correct")))

        # ---- T04 slider ----
        goto("t04_slider")
        tgt4 = int(page.evaluate("() => document.body.dataset.target"))
        box = page.locator("#slider").bounding_box()
        x = box["x"] + box["width"] * (tgt4 / 100.0)
        y = box["y"] + box["height"] / 2
        page.mouse.click(x, y)
        page.wait_for_timeout(100)
        val = int(page.evaluate("() => document.body.dataset.value"))
        delta = tgt4 - val
        seq = [f"CLICK {int(round(x / VW * 1000))} {int(round(y / VH * 1000))}"]
        if delta > 0:
            seq += ["KEY ArrowRight"] * delta
        elif delta < 0:
            seq += ["KEY ArrowLeft"] * (-delta)
        acts["T04_slider"] = seq
        notes.append(f"sim T04 target={tgt4} click->{val} delta={delta}")

        # ---- T05 clipboard ----
        goto("t05_shortcut")
        a, c = cen(page, "#src"), cen(page, "#dst")
        acts["T05_shortcut"] = [f"CLICK {a[0]} {a[1]}", "KEY Control+a",
                                "KEY Control+c", f"CLICK {c[0]} {c[1]}",
                                "KEY Control+v"]

        # ---- T06 tab code ----
        goto("t06_tabcode")
        tcb = cen(page, "#tab_code")
        px(page, *tcb)
        page.wait_for_timeout(200)
        raw = page.locator("#code_text").text_content().strip()
        m = re.search(r"[A-Za-z0-9]{4,8}", raw)
        code6 = m.group(0) if m else raw
        thb = cen(page, "#tab_home")
        px(page, *thb)
        page.wait_for_timeout(150)
        ci, sc = cen(page, "#code_in"), cen(page, "#submit_code")
        acts["T06_tabcode"] = [f"CLICK {tcb[0]} {tcb[1]}",
                               f"CLICK {thb[0]} {thb[1]}",
                               f"CLICK {ci[0]} {ci[1]}", "TYPE " + code6,
                               f"CLICK {sc[0]} {sc[1]}"]
        acts["T06_tabcode_fail"] = [f"CLICK {tcb[0]} {tcb[1]}",
                                    f"CLICK {thb[0]} {thb[1]}",
                                    f"CLICK {ci[0]} {ci[1]}", "TYPE WRONG",
                                    f"CLICK {sc[0]} {sc[1]}"]
        notes.append("sim T06 code=" + code6)

        # ---- T07 scroll ----
        goto("t07_scroll")
        lb = cen(page, "#list")
        px(page, *lb)
        page.wait_for_timeout(120)
        for _ in range(8):
            page.keyboard.press("End")
            page.wait_for_timeout(200)
            if (page.evaluate("() => document.body.dataset.loaded")
                    == page.evaluate("() => document.body.dataset.total")):
                break
        page.keyboard.press("End")   # reveal item cuoi
        page.wait_for_timeout(220)
        last = page.evaluate(
            "() => { const it = document.querySelectorAll('#list .item');"
            " const el = it[it.length-1]; const r = el.getBoundingClientRect();"
            " return {x:r.x+r.width/2, y:r.y+r.height/2}; }")
        lx = int(round(last["x"] / VW * 1000))
        ly = int(round(last["y"] / VH * 1000))
        acts["T07_scroll"] = ([f"CLICK {lb[0]} {lb[1]}"]
                              + ["KEY End"] * 6 + [f"CLICK {lx} {ly}"])
        notes.append(f"sim T07 last=({lx},{ly})")

        # ---- T08 errorfix (layout SHIFT khi hien error — do lai toa do!) ----
        goto("t08_errorfix")
        sb0 = cen(page, "#sub")            # truoc khi hien error
        px(page, *sb0)                     # reveal errors
        page.wait_for_timeout(180)
        nm, em2, qt = cen(page, "#name"), cen(page, "#email"), cen(page, "#qty")
        sb1 = cen(page, "#sub")            # SAU khi hien error (vi tri moi)
        acts["T08_errorfix"] = [f"CLICK {sb0[0]} {sb0[1]}",
                                f"CLICK {nm[0]} {nm[1]}", "TYPE Alice Nguyen",
                                f"CLICK {em2[0]} {em2[1]}",
                                "TYPE alice@example.com",
                                f"CLICK {qt[0]} {qt[1]}", "TYPE 5",
                                f"CLICK {sb1[0]} {sb1[1]}"]

        # ---- T09 coupon ----
        goto("t09_coupon")
        tp = int(page.evaluate("() => document.body.dataset.targetplan"))
        code9 = page.evaluate("() => document.body.dataset.code")
        pl, cpin = cen(page, f"#plan{tp}"), cen(page, "#coupon_in")
        ap, cf = cen(page, "#apply"), cen(page, "#confirm")
        acts["T09_coupon"] = [f"CLICK {pl[0]} {pl[1]}",
                              f"CLICK {cpin[0]} {cpin[1]}", "TYPE " + code9,
                              f"CLICK {ap[0]} {ap[1]}",
                              f"CLICK {cf[0]} {cf[1]}"]
        # sim full (kiem co che)
        px(page, *pl)
        px(page, *cpin)
        page.keyboard.type(code9)
        px(page, *ap)
        page.wait_for_timeout(120)
        px(page, *cf)
        page.wait_for_timeout(150)
        d9 = page.evaluate("() => Object.assign({}, document.body.dataset)")
        notes.append("sim T09 " + json.dumps(
            {k: d9.get(k) for k in ("selected", "applied", "confirmed",
                                    "total", "targetplan", "code")}))

        # ---- T10 canvas ----
        goto("t10_canvas")
        tc = page.evaluate("() => document.body.dataset.targetcolor")
        tt = page.evaluate("() => document.body.dataset.targettype")
        geo = json.loads(page.evaluate(
            "() => document.getElementById('geo').textContent"))
        shp = next(s for s in geo
                   if s["color"]["name"] == tc and s["type"] == tt)
        cbox = page.locator("canvas").bounding_box()
        cpx = cbox["x"] + shp["x"]
        cpy = cbox["y"] + shp["y"]
        acts["T10_canvas"] = [f"CLICK {int(round(cpx/VW*1000))} "
                              f"{int(round(cpy/VH*1000))}"]
        other = next(s for s in geo
                     if not (s["color"]["name"] == tc and s["type"] == tt))
        acts["T10_canvas_fail"] = [f"CLICK {int(round((cbox['x']+other['x'])/VW*1000))} "
                                   f"{int(round((cbox['y']+other['y'])/VH*1000))}"]
        page.mouse.click(cpx, cpy)
        page.wait_for_timeout(150)
        notes.append("sim T10 correct="
                     + str(page.evaluate("() => document.body.dataset.correct")))

        # ---- T11 counter ----
        goto("t11_counter")
        ix, iy = cen(page, "#inc")
        sx, sy = cen(page, "#sub")
        acts["T11_counter"] = [f"CLICK {ix} {iy}"] * 5 + [f"CLICK {sx} {sy}"]
        acts["T11_counter_fail"] = [f"CLICK {sx} {sy}"]

        # ---- T12 page code ----
        goto("t12_pagecode")
        raw12 = page.locator("#code1").text_content().strip()
        m2 = re.search(r"\d{4,8}", raw12)
        code12 = m2.group(0) if m2 else raw12
        to2 = cen(page, "#to2")
        px(page, *to2)
        page.wait_for_timeout(200)
        ci2, s2 = cen(page, "#code_in"), cen(page, "#sub2")
        acts["T12_pagecode"] = [f"CLICK {to2[0]} {to2[1]}",
                                f"CLICK {ci2[0]} {ci2[1]}", "TYPE " + code12,
                                f"CLICK {s2[0]} {s2[1]}"]
        notes.append("sim T12 code=" + code12)

        b.close()
    print("\n".join("  " + n for n in notes))
    return acts


def main():
    # "checker stub in-memory" (mac dinh) HOAC "--real" de import checker.py that
    use_real = "--real" in sys.argv
    if use_real:
        import checker as _c
        assert hasattr(_c, "check_task"), "checker.py thieu check_task"
        print("== dung checker.py THAT (--real) ==")
    else:
        ck = types.ModuleType("checker")

        def check_task(page, task_id, spec):
            d = page.evaluate("() => Object.assign({}, document.body.dataset)")
            f = SUCC.get(task_id)
            ok = bool(f(d)) if f else False
            return {"success": ok, "score": 1.0 if ok else 0.0,
                    "reason": json.dumps(d, ensure_ascii=False)[:160],
                    "state": d}

        ck.check_task = check_task
        sys.modules["checker"] = ck

    print("== scan (do toa do + mo phong) — cac variant duoi day ==")
    import bench_v15

    def policy_for(dic):
        def fn(obs):
            seq = dic.get(obs["task_id"], [])
            if obs["step"] >= len(seq):
                return "DONE"
            e = seq[obs["step"]]
            if e.startswith("SLEEP:"):
                head, act = e.split("|", 1)
                time.sleep(float(head[6:]))
                return act
            return e
        return fn

    fail_map = [
        ("T01_signup", "T01_signup_fail"),
        ("T02_login", "T02_login_fail"),
        ("T03_delayed", "T03_delayed_fail"),
        ("T06_tabcode", "T06_tabcode_fail"),
        ("T10_canvas", "T10_canvas_fail"),
        ("T11_counter", "T11_counter_fail"),
    ]

    ok_all = True
    for v in (0, 1, 2):
        print(f"\n== PASS-RUN {len(ALL12)} task v{v} ==")
        acts = scan(v)
        res = bench_v15.run_suite(policy_for(acts), tasks=ALL12, variants=(v,))
        npass = sum(1 for r in res if r["success"])
        for r in res:
            if not r["success"]:
                print(f"  {r['task_id']:12s} FAIL "
                      f"| {str(r.get('reason',''))[:130]}")
        print(f"  => PASS {npass}/{len(ALL12)}")
        ok_all = ok_all and (npass == len(ALL12))

        if v in (0, 2):
            fail_acts = {tid: acts[k] for tid, k in fail_map}
            res2 = bench_v15.run_suite(policy_for(fail_acts),
                                       tasks=list(fail_acts), variants=(v,))
            nfail = sum(1 for r in res2 if not r["success"])
            for r in res2:
                if r["success"]:
                    print(f"  FAIL-RUN {r['task_id']:12s} KHONG bi bat (LOI!)")
            print(f"  => FAIL-RUN v{v}: bat dung {nfail}/{len(fail_acts)}")
            ok_all = ok_all and (nfail == len(fail_acts))

    print(f"\nKET QUA TONG: {'OK' if ok_all else 'CO VAN DE'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
