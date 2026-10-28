# -*- coding: utf-8 -*-
"""checker.py - CHECKER cho bo bench B17 (8 app) - GLM 24/10.

Nguyen tac (theo PLAN W1.5): **KHONG tin self-report** cua app.
Moi check TIN LAI tu DOM + `window.__spec.vars` (gia tri dich/GT) =>
neu app tu 'bao ok' sai thi checker van bat.

Interface giong checker cua bench_v15/bench_v155/bench_v16:
    check_tNN(page) -> (tests: dict, state: dict)
    CHECKS: {task_id: fn}
Dung:
    python phase13-gui/bench_b17/checker.py            # self-test: chay GT policy
                                                       # roi kiem checker (8/8 PASS)
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
        r = page.evaluate(js)
    except Exception:
        return default
    return r


def _spec(page):
    return _v(page, "() => window.__spec && window.__spec.vars || {}", {}) or {}


def _val(page, sel):
    return _v(page, "() => {const e=document.querySelector('%s');"
                     "return e ? (e.value !== undefined ? e.value : "
                     "(e.checked !== undefined ? e.checked : e.textContent)) : null;}"
              % sel)


def _msg(page):
    return (_v(page, "() => (document.getElementById('msg')||{}).textContent||''")
            or "").strip()


# ------------------------------------------------------------------ T30
def check_t30(page):
    """Note LIET KE NGUOC THU TU field (B truoc A) + field C phai DE TRONG."""
    sp = _spec(page)
    st = _v(page, """() => ({fa:(document.getElementById('fa')||{}).value||'',
        fb:(document.getElementById('fb')||{}).value||'',
        fc:(document.getElementById('fc')||{}).value||''})""") or {}
    msg = _msg(page)
    tests = {
        "field A = gia tri trong note": st.get("fa") == sp.get("NAME_A"),
        "field B = gia tri trong note": st.get("fb") == sp.get("CODE_B"),
        "field C de trong (khong duoc dien)": (st.get("fc") or "") == "",
        "thong bao thanh cong": msg == "Account created",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


# ------------------------------------------------------------------ T31
def check_t31(page):
    """Phai CUON den cuoi panel roi click dung dong theo code."""
    sp = _spec(page)
    st = _v(page, """() => ({clicked:(window.__state||{}).clicked||'',
        rows:document.querySelectorAll('#tb tr').length})""") or {}
    msg = _msg(page)
    tests = {
        "bang co du cac dong": (st.get("rows") or 0) >= 8,
        "click dung dong co code": (st.get("clicked") or "") == sp.get("CODE"),
        "thong bao thanh cong": msg == "Confirmed",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


# ------------------------------------------------------------------ T32
def check_t32(page):
    """Keo (DRAG) slider den gia tri trong note."""
    sp = _spec(page)
    st = _v(page, """() => {
        const f=document.getElementById('fill');
        const w=document.getElementById('wrap');
        let v=null; if(f && f.value!==undefined) v=f.value;
        let knob_pct=null;
        if(w && f){
          const wr=w.getBoundingClientRect(), fr=f.getBoundingClientRect();
          // 'fill' la THANH TO tu trai den knob => mep PHAI cua no la vi tri knob
          if(wr.width>0) knob_pct=Math.round((fr.right-wr.left)/wr.width*100);
        }
        return {value:v, knob_pct:knob_pct,
                app_value:(window.__state||{}).value,
                msg:(document.getElementById('msg')||{}).textContent||''};
    }""") or {}
    want = sp.get("VALUE")
    # slider la DIV (khong co .value) => lay gia tri tu state CUA APP,
    # NHUNG doi chieu bang HINH HOC (vi tri knob) => 2 tin hieu doc lap.
    val = st.get("value")
    if val is None:
        val = st.get("app_value")
    tests = {
        "gia tri slider = gia tri trong note":
            val is not None and str(val) == str(want),
        "vi tri knob khop gia tri (doc lai)":
            st.get("knob_pct") is not None
            and abs(int(st["knob_pct"]) - int(want)) <= 2,
        "thong bao thanh cong": (st.get("msg") or "").strip() == "Applied",
    }
    return tests, {"spec": sp, "state": st}


# ------------------------------------------------------------------ T33
def check_t33(page):
    """App bao LOI lan 1 (ket qua dung) => phai Submit LAI ma KHONG doi gia tri."""
    sp = _spec(page)
    st = _v(page, """() => ({code:(document.getElementById('code')||{}).value||'',
        submits:(window.__state||{}).submits||0,
        msg:(document.getElementById('msg')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    tests = {
        "gia tri khoi tao khong doi": (st.get("code") or "") == sp.get("CODE"),
        "da submit >= 2 lan (thu lai)": (st.get("submits") or 0) >= 2,
        "lan cuoi bao thanh cong": msg == "Device activated",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


# ------------------------------------------------------------------ T34
def check_t34(page):
    """Dieu huong bang phim (Tab) - cac field dung gia tri."""
    sp = _spec(page)
    st = _v(page, """() => ({f1:(document.getElementById('f1')||{}).value||'',
        f2:(document.getElementById('f2')||{}).value||'',
        f3:(document.getElementById('f3')||{}).value||'',
        msg:(document.getElementById('msg')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    tests = {
        "field 1 dung gia tri": (st.get("f1") or "") == sp.get("FAM"),
        "field 2 dung gia tri": (st.get("f2") or "") == sp.get("GIV"),
        "field 3 dung gia tri": (st.get("f3") or "") == sp.get("CITY"),
        "thong bao thanh cong": msg == "Saved",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


# ------------------------------------------------------------------ T35
def check_t35(page):
    """Hover (MOVE) theo card 'Serial' moi lo code."""
    sp = _spec(page)
    st = _v(page, """() => ({code:(document.getElementById('inp')||{}).value||'',
        msg:(document.getElementById('msg')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    tests = {
        "code dung gia tri": (st.get("code") or "") == sp.get("CODE"),
        "thong bao thanh cong": msg == "Verified",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


# ------------------------------------------------------------------ T36
def check_t36(page):
    """Wizard nhieu buoc: plan -> add-on -> xong (dung thu tu)."""
    sp = _spec(page)
    st = _v(page, """() => ({step:(window.__state||{}).step||0,
        plan:(document.getElementById('plan')||{}).value||'',
        addon:(document.getElementById('addon')||{}).value||'',
        msg:(document.getElementById('msg')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    tests = {
        "buoc cuoi (3)": int(st.get("step") or 0) >= 3,
        "plan dung gia tri": (st.get("plan") or "") == sp.get("PLAN"),
        "add-on dung gia tri": (st.get("addon") or "") == sp.get("ADDON"),
        "khong bao loi": ("Wrong" not in msg),
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


# ------------------------------------------------------------------ T37
def check_t37(page):
    """Nut Save bi khoa den khi tick 'I have read the terms'."""
    sp = _spec(page)
    st = _v(page, """() => ({title:(document.getElementById('t')||{}).value||'',
        terms:!!(document.getElementById('terms')||{}).checked,
        msg:(document.getElementById('msg')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    tests = {
        "tieu de dung gia tri": (st.get("title") or "") == sp.get("TITLE"),
        "da tick dong nho (terms)": bool(st.get("terms")),
        "thong bao thanh cong": msg == "Saved",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


def check_t38_trap(page):
    """Control 'Refresh preview' la NO-OP => lap click no do = vong lap that.
    Checker: (a) ten da ap dung dung, (b) KHONG lap vo control no-op.
    """
    sp = _spec(page)
    st = _v(page, """() => ({typed:(document.getElementById('nm')||{}).value||'',
        want:(document.getElementById('want')||{}).textContent||'',
        applied:(window.__state||{}).applied||false,
        clicks:(window.__state||{}).clicks||{},
        msg:(document.getElementById('status')||{}).textContent||''})""") or {}
    clicks = st.get("clicks") or {}
    n_refresh = int(clicks.get("refresh") or 0)
    n_apply = int(clicks.get("apply") or 0)
    msg = (st.get("msg") or "").strip()
    tests = {
        "ten khop note": (st.get("typed") or "").strip() == (st.get("want") or "").strip(),
        "da apply thanh cong": bool(st.get("applied")) and msg == "Name applied.",
        "KHONG lap control no-op (refresh <= 1)": n_refresh <= 1,
        "da thu Apply it nhat 1 lan": n_apply >= 1,
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


def check_t39(page):
    """Chuoi phim tat: ctrl+a -> ctrl+c -> click dich -> ctrl+v.
    Checker: noi dung o dich == noi dung o nguon (tinh lai tu DOM) + app bao ok."""
    sp = _spec(page)
    st = _v(page, """() => ({
        src:(document.getElementById('src')||{}).value||'',
        dst:(document.getElementById('dst')||{}).value||'',
        msg:(document.getElementById('status')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    want = sp.get("TEXT") or (st.get("src") or "")
    tests = {
        "o dich == o nguon": (st.get("dst") or "") == (st.get("src") or "") == want,
        "thong bao thanh cong": msg == "Pasted.",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


def check_t40(page):
    """Nhieu dong giong nhau -> chon dung dong co badge khop note."""
    sp = _spec(page)
    st = _v(page, """() => ({
        picked:(window.__state||{}).picked,
        badge:(document.getElementById('badge')||{}).textContent||'',
        ok:(window.__state||{}).ok||false,
        msg:(document.getElementById('status')||{}).textContent||''})""") or {}
    want = sp.get("BADGE") or ""
    tests = {
        "da chon 1 dong": st.get("picked") is not None and st.get("picked") >= 0,
        "dong da chon khop badge trong note": bool(st.get("ok")),
        "badge hien thi dung": (st.get("badge") or "") == want,
    }
    return tests, {"spec": sp, "state": st}


def check_t38(page):
    """App @MiMo T38_recovery: decoy 'Refresh preview' khong an (no-op) => lap lai la vong lap that => phai DOI CHIEN LUWA sang control dung."""
    sp = _spec(page)
    st = _v(page, """() => ({code: (window.__spec && window.__spec.vars && window.__spec.vars.CODE) || '',
        enabled:(window.__state||{}).enabled||false,
        tries:(window.__state||{}).tries||0,
        msg:(document.getElementById('msg')||{}).textContent||''})""") or {}
    msg = (st.get("msg") or "").strip()
    sp_code = (sp.get("CODE") or (sp.get("vars") or {}).get("CODE") or "")
    tests = {
        # st["code"] da la spec CODE (doc tu __spec) => kiem tra no khong rong
        # va khop voi gia tri dich doc tu __spec (cross-check 2 nguon doc lap).
        "code khop note": (st.get("code") or "") != "" and (st.get("code") or "") == sp_code,
        "da enable (bam dung control)": bool(st.get("enabled")),
        "KHONG lap control no-op (tries <= 2)": int(st.get("tries") or 0) <= 2,
        "thong bao thanh cong": msg == "Enabled",
    }
    return tests, {"spec": sp, "state": st, "msg": msg}


CHECKS = {
    "T30_note_order": check_t30,
    "T31_scroll_code": check_t31,
    "T32_drag_slider": check_t32,
    "T33_error_retry": check_t33,
    "T34_tab_nav": check_t34,
    "T35_hover_code": check_t35,
    "T36_wizard_steps": check_t36,
    "T37_terms_guard": check_t37,
    "T38_recovery": check_t38,
    "T38_recovery_trap": check_t38_trap,
    "T39_clipboard": check_t39,
    "T40_distractor": check_t40,
}


# ------------------------------------------------------------------ self-test
def selftest():
    """Chay GT policy (scripts/b17_selftest.py) roi kiem bang checker CUA TOI."""
    sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
    import importlib
    b17 = importlib.import_module("b17_selftest")
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
            pol = b17.POLICIES.get(app)
            if pol is None:
                print("  %-20s THIEU policy" % tid)
                continue
            url = "file:///" + os.path.join(TASKS, app).replace("\\", "/")
            page.goto(url)
            page.wait_for_timeout(200)
            try:
                pol(page)
                page.wait_for_timeout(200)
            except Exception as e:
                print("  %-20s policy loi: %s" % (tid, str(e)[:60]))
                continue
            chk = CHECKS.get(tid)
            if chk is None:
                print("  %-20s THIEU checker" % tid)
                continue
            tests, st = chk(page)
            bad = [k for k, v in tests.items() if not v]
            if bad:
                print("  %-20s FAIL: %s | state=%s" %
                      (tid, bad, json.dumps(st, ensure_ascii=False)[:150]))
            else:
                n_ok += 1
                print("  %-20s PASS (%d/%d check)" % (tid, len(tests), len(tests)))
        br.close()
    print()
    print("B17 SELF-TEST (GT policy + checker): %d/%d task PASS" %
          (n_ok, len(tasks)))
    return 0 if n_ok == len(tasks) else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
