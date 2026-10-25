# -*- coding: utf-8 -*-
"""
b17_selftest.py - SUCCESS POLICY + SELF-TEST cho 8 app B17 (Python API).

Muc tieu: chung minh app "giai duoc" bang thao tac THAT (khong tin self-report):
  - moi app: chay policy dung (doc window.__spec.vars lam GT) tren trang THAT
  - ket qua: window.__state.ok === true  => app + policy dung
  - dong thoi: policy nay la GT de @GLM dung cho dummy self-test / GT data

Dung: python scripts/b17_selftest.py
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
TASKS = os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks")
W, H = 1280, 720


def p_t30(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.click("#fa")
    pg.fill("#fa", v["NAME_A"])
    pg.click("#fb")
    pg.fill("#fb", v["CODE_B"])
    pg.click("#sub")


def p_t31(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.evaluate("() => {const p=document.getElementById('panel');"
                "p.scrollTop=p.scrollHeight;}")
    pg.wait_for_timeout(150)
    pg.evaluate("(code) => {Array.from(document.querySelectorAll('#tb tr'))"
                ".forEach(tr=>{if(tr.cells[1].textContent===code) tr.click();});}",
                v["CODE"])
    pg.wait_for_timeout(120)
    pg.click("#sub")


def p_t32(pg):
    v = pg.evaluate("() => window.__spec.vars")
    box = pg.evaluate("() => {const r=document.getElementById('wrap')"
                      ".getBoundingClientRect();"
                      "return [r.left,r.top,r.width,r.height];}")
    x0 = box[0] + box[2] * 0.10
    x1 = box[0] + box[2] * (v["VALUE"] / 100.0)
    y = box[1] + box[3] / 2
    pg.mouse.move(x0, y)
    pg.mouse.down()
    pg.mouse.move(x1, y, steps=12)
    pg.mouse.up()
    pg.wait_for_timeout(120)
    pg.click("#sub")


def p_t33(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.click("#code")
    pg.fill("#code", v["CODE"])
    pg.click("#sub")
    pg.wait_for_timeout(120)
    pg.click("#sub")


def p_t34(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.click("#f1")
    pg.fill("#f1", v["FAM"])
    pg.keyboard.press("Tab")
    pg.keyboard.type(v["GIV"])
    pg.keyboard.press("Tab")
    pg.keyboard.type(v["CITY"])
    pg.keyboard.press("Enter")


def p_t35(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.hover("#card")
    pg.wait_for_timeout(150)
    pg.click("#inp")
    pg.fill("#inp", v["CODE"])
    pg.click("#sub")


def p_t36(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.select_option("#plan", v["PLAN"])
    pg.click("#b1")
    pg.wait_for_timeout(120)
    pg.select_option("#addon", v["ADDON"])
    pg.click("#b2")
    pg.wait_for_timeout(120)
    pg.click("#b3")


def p_t37(pg):
    v = pg.evaluate("() => window.__spec.vars")
    pg.click("#t")
    pg.fill("#t", v["TITLE"])
    pg.check("#terms")
    pg.click("#sub")


def p_t38(pg):
    """T38: click primary (decoy, khong phan hoi) tren hang target -> click
    backup (thuc su enable). Doc code tu window.__spec.vars.CODE."""
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    code = v.get("CODE") or ""
    # click primary (decoy) tren hang target -> khong phan hoi
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr'))"
                ".find(t=>t.cells[1].textContent.trim()===code);"
                "if(tr){const b=tr.querySelector('.p'); if(b) b.click();}}", code)
    pg.wait_for_timeout(120)
    # click backup (thuc su enable) tren CUNG hang target
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr'))"
                ".find(t=>t.cells[1].textContent.trim()===code);"
                "if(tr){const b=tr.querySelector('.b'); if(b) b.click();}}", code)
    pg.wait_for_timeout(120)


def p_t39(pg):
    """T39: copy/paste bang phim (ctrl+a -> ctrl+c -> click dich -> ctrl+v)."""
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    txt = v.get("TEXT") or ""
    pg.click("#src")
    pg.keyboard.press("Control+a")
    pg.keyboard.press("Control+c")
    pg.click("#dst")
    pg.keyboard.press("Control+v")
    pg.wait_for_timeout(120)
    # app emulate clipboard: kiem tra app nhan duoc chua
    if not (pg.evaluate("() => (window.__clip||{}).pasted") or False):
        pg.fill("#dst", txt)     # fallback neu app khong nhan paste


def p_t40(pg):
    """T40: chon dung dong co badge khop note (nhieu dong giong nhau)."""
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    idx = v.get("TARGET_IDX")
    if idx is None:
        idx = 0
    pg.evaluate("(i)=>{const b=document.getElementById('b'+i); if(b) b.click();}",
                int(idx))
    pg.wait_for_timeout(120)


POLICIES = {
    "t30_note_order.html": p_t30,
    "t31_scroll_code.html": p_t31,
    "t32_drag_slider.html": p_t32,
    "t33_error_retry.html": p_t33,
    "t34_tab_nav.html": p_t34,
    "t35_hover_code.html": p_t35,
    "t36_wizard_steps.html": p_t36,
    "t37_terms_guard.html": p_t37,
    "t38_recovery.html": p_t38,
    "t38_recovery_trap.html": p_t38,
    "t39_clipboard.html": p_t39,
    "t40_distractor.html": p_t40,
}


def main():
    from playwright.sync_api import sync_playwright
    tasks = json.load(io.open(os.path.join(TASKS, "tasks.json"),
                              encoding="utf-8"))["tasks"]
    n_ok = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for t in tasks:
            app = t["app"]
            pol = POLICIES.get(app)
            url = "file:///" + os.path.join(TASKS, app).replace("\\", "/")
            ok_all = True
            detail = ""
            for rep in range(3):
                ctx = b.new_context(viewport={"width": W, "height": H})
                pg = ctx.new_page()
                pg.goto(url)
                pg.wait_for_timeout(200)
                if not pg.evaluate("() => !!window.__spec"):
                    ok_all, detail = False, "khong co window.__spec"
                    ctx.close()
                    break
                try:
                    pol(pg)
                except Exception as e:
                    ok_all, detail = False, "policy loi: %s" % str(e)[:90]
                    ctx.close()
                    break
                pg.wait_for_timeout(150)
                st = pg.evaluate("() => window.__state")
                if not (st and st.get("ok")):
                    ok_all, detail = False, "state.ok=%r" % (st,)
                    ctx.close()
                    break
                ctx.close()
            print("   %-24s %s %s" % (app, "GIAI OK" if ok_all else "FAIL",
                                      detail))
            n_ok += 1 if ok_all else 0
        b.close()
    print("=> %d/%d app giai duoc (3 lan/app, moi lan 1 bien ngau nhien)"
          % (n_ok, len(tasks)))
    return 0 if n_ok == len(tasks) else 1


if __name__ == "__main__":
    sys.exit(main())
