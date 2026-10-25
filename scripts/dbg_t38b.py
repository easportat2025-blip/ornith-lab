# -*- coding: utf-8 -*-
"""
dbg_t38b.py - debug app t38_recovery: chay tung buoc, in state.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
from playwright.sync_api import sync_playwright

W, H = 1280, 720
app = os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks", "t38_recovery.html")
url = "file:///" + app.replace("\\", "/")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto(url)
    pg.wait_for_timeout(250)
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    print("spec:", v)
    code = v.get("CODE")
    print("CODE:", code)
    # find the target row by code
    r = pg.evaluate("""(code) => {
        const trs = Array.from(document.querySelectorAll('#tb tr'));
        const tr = trs.find(t => t.cells[1].textContent.trim() === code);
        return tr ? {row: tr.cells[0].textContent, btns: tr.querySelectorAll('button').length} : null;
    }""", code)
    print("target row:", r)
    # click primary
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); if(tr){const b=tr.querySelector('.p'); if(b) b.click();}}", code)
    pg.wait_for_timeout(120)
    print("after primary:", pg.evaluate("() => window.__state"))
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); if(tr){const b=tr.querySelector('.b'); if(b) b.click();}}", code)
    pg.wait_for_timeout(120)
    print("after backup:", pg.evaluate("() => window.__state"))
    b.close()
