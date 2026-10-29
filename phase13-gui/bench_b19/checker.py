# -*- coding: utf-8 -*-
"""checker.py - CHECKER cho bo bench B19 (8 task hard holdout).

Nguyen tac: khong tin self-report cua app. Moi check doc DOM + `window.__spec.vars`
(GT) + `window.__state` (trang thai that do app cap nhat) va doi chieu doc lap.

Interface:
    check_tNN(page) -> (tests: dict, state: dict)
    CHECKS: {task_id: fn}
Dung:
    python phase13-gui/bench_b19/checker.py     # self-test GT policy (8/8)
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks")


def _v(page, js, default=None):
    try:
        return page.evaluate(js)
    except Exception:
        return default


def _spec(page):
    return _v(page, "() => (window.__spec && window.__spec.vars) || {}", {}) or {}


def _state(page):
    return _v(page, "() => window.__state || {}", {}) or {}


def _msg(page):
    return (_v(page, "() => (document.getElementById('msg')||{}).textContent || ''", "")
            or "").strip()


def _text(page, sel):
    return (_v(page, "() => (document.querySelector(%r)||{}).textContent || ''"
               % sel, "") or "").strip()


def _val(page, sel):
    return _v(page, "() => (document.querySelector(%r)||{}).value || ''"
              % sel, "") or ""


def check_t41(page):
    sp = _spec(page)
    st = _state(page)
    code = str(sp.get("CODE") or "")
    clicked = str(st.get("clicked") or "")
    tests = {
        "click dung row theo note": clicked != "" and clicked == code,
        "da scroll outer panel": int(st.get("outer_scroll") or 0) > 0,
        "da scroll inner panel": int(st.get("inner_scroll") or 0) > 0,
        "da bam Confirm": bool(st.get("submitted")),
        "thong bao Confirmed": _msg(page) == "Confirmed",
    }
    return tests, {"spec": sp, "state": st, "msg": _msg(page)}


def check_t42(page):
    sp = _spec(page)
    st = _state(page)
    target = int(sp.get("VALUE") or -1)
    value = int(st.get("value") or -1)
    tests = {
        "value dung note (±1)": target >= 0 and abs(value - target) <= 1,
        "da bam Apply": bool(st.get("submitted")),
        "thong bao Applied": _msg(page) == "Applied",
    }
    return tests, {"spec": sp, "state": st, "msg": _msg(page)}


def check_t43(page):
    sp = _spec(page)
    st = _state(page)
    tests = {
        "project dung note": str(st.get("project") or "") == str(sp.get("PROJECT") or ""),
        "region dung note": str(st.get("region") or "") == str(sp.get("REGION") or ""),
        "tier dung note": str(st.get("tier") or "") == str(sp.get("TIER") or ""),
        "da tick confirm": bool(st.get("confirm")),
        "da hoan tat wizard": int(st.get("step") or 0) >= 3,
        "da bam Finish": bool(st.get("submitted")),
        "thong bao Provisioned": _msg(page) == "Provisioned",
    }
    return tests, {"spec": sp, "state": st, "msg": _msg(page)}


def check_t44(page):
    sp = _spec(page)
    st = _state(page)
    tests = {
        "name dung note": str(st.get("name") or "") == str(sp.get("NAME") or ""),
        "email dung note": str(st.get("email") or "") == str(sp.get("EMAIL") or ""),
        "plan dung note": str(st.get("plan") or "") == str(sp.get("PLAN") or ""),
        "khong click chuot": int(st.get("mouse_clicks") or 0) == 0,
        "da submit": bool(st.get("submitted")),
        "thong bao Registered": _msg(page) == "Registered",
    }
    return tests, {"spec": sp, "state": st, "msg": _msg(page)}


def check_t45(page):
    sp = _spec(page)
    st = _state(page)
    text = str(sp.get("TEXT") or "")
    src = _val(page, "#src")
    dst = _val(page, "#dst")
    tests = {
        "source dung spec": src != "" and src == text,
        "target copy dung source": dst != "" and dst == src,
        "da bam Verify": bool(st.get("verify_clicked")),
        "da submit": bool(st.get("submitted")),
        "thong bao Copied": _msg(page) == "Copied",
    }
    return tests, {"spec": sp, "state": st, "src": src, "dst": dst,
                   "msg": _msg(page)}


def check_t46(page):
    sp = _spec(page)
    st = _state(page)
    tests = {
        "click dung nguoi": str(st.get("picked") or "") == str(sp.get("NAME") or ""),
        "da bam Select": bool(st.get("submitted")),
        "thong bao Selected": _msg(page) == "Selected",
    }
    return tests, {"spec": sp, "state": st, "msg": _msg(page)}


def check_t47(page):
    sp = _spec(page)
    st = _state(page)
    first = _v(page, "() => { const e=document.querySelector('#list .item'); "
                     "return e ? e.textContent.trim() : ''; }", "")
    tests = {
        "item dung note o dau list": str(first) == str(sp.get("ITEM") or ""),
        "da bam Save": bool(st.get("saved")),
        "thong bao Saved": _msg(page) == "Saved",
    }
    return tests, {"spec": sp, "state": st, "first": first, "msg": _msg(page)}


def check_t48(page):
    sp = _spec(page)
    st = _state(page)
    tests = {
        "da hover dung menu": str(st.get("hovered") or "") == str(sp.get("MENU") or ""),
        "click dung submenu": str(st.get("clicked") or "") == str(sp.get("ITEM") or ""),
        "da submit": bool(st.get("submitted")),
        "thong bao Applied": _msg(page) == "Applied",
    }
    return tests, {"spec": sp, "state": st, "msg": _msg(page)}


CHECKS = {
    "T41_nested_scroll": check_t41,
    "T42_precision_drag": check_t42,
    "T43_wizard_validation": check_t43,
    "T44_keyboard_only": check_t44,
    "T45_clipboard_verify": check_t45,
    "T46_dynamic_filter": check_t46,
    "T47_drag_reorder": check_t47,
    "T48_hover_submenu": check_t48,
}


# ------------------------------------------------------------------ self-test
def selftest():
    """Chay GT policy (scripts/b19_selftest.py) roi kiem bang checker CUA TOI."""
    sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
    import importlib
    b19 = importlib.import_module("b19_selftest")
    from playwright.sync_api import sync_playwright
    tasks = json.load(io.open(os.path.join(TASKS, "tasks.json"),
                              encoding="utf-8"))["tasks"]
    n_ok = 0
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = br.new_page(viewport={"width": 1280, "height": 720})
        for t in tasks:
            app = t.get("app") or t.get("file")
            tid = t.get("task_id")
            pol = b19.POLICIES.get(app)
            if pol is None:
                print("  %-24s THIEU policy" % tid)
                continue
            url = "file:///" + os.path.join(TASKS, app).replace("\\", "/")
            page.goto(url)
            page.wait_for_timeout(200)
            try:
                pol(page)
                page.wait_for_timeout(200)
            except Exception as e:
                print("  %-24s policy loi: %s" % (tid, str(e)[:80]))
                continue
            chk = CHECKS.get(tid)
            if chk is None:
                print("  %-24s THIEU checker" % tid)
                continue
            tests, st = chk(page)
            bad = [k for k, v in tests.items() if not v]
            if bad:
                print("  %-24s FAIL: %s | state=%s" %
                      (tid, bad, json.dumps(st, ensure_ascii=False)[:220]))
            else:
                n_ok += 1
                print("  %-24s PASS (%d/%d check)" %
                      (tid, len(tests), len(tests)))
        br.close()
    print()
    print("B19 SELF-TEST (GT policy + checker): %d/%d task PASS" %
          (n_ok, len(tasks)))
    return 0 if n_ok == len(tasks) else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
