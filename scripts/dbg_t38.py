# -*- coding: utf-8 -*-
"""
dbg_t38.py - debug app t38_recovery: chay policy + in state.
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
    print("spec vars:", v)
    code = v.get("CODE") or ""
    print("CODE:", code)
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr'))"
                ".find(t=>t.cells[1].textContent.trim()===code);"
                "if(tr) tr.querySelector('.p').click();}", code)
    pg.wait_for_timeout(120)
    print("after primary:", pg.evaluate("() => window.__state"))
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr'))"
                ".find(t=>t.cells[1].textContent.trim()===code);"
                "if(tr) tr.querySelector('.b').click();}", code)
    pg.wait_for_timeout(120)
    print("after backup:", pg.evaluate("() => window.__state"))
    b.close()
