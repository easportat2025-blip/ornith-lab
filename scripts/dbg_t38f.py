# -*- coding: utf-8 -*-
"""
dbg_t38f.py - debug t38.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users/Admin/Desktop\New folder"
from playwright.sync_api import sync_playwright

W, H = 1280, 720
app = os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks", "t38_recovery.html")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto("file:///" + app.replace("\\", "/"))
    pg.wait_for_timeout(250)
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    code = v.get("CODE")
    print("CODE:", repr(code))
    # inspect each row's cells
    rows = pg.evaluate("() => Array.from(document.querySelectorAll('#tb tr')).map(tr => Array.from(tr.children).map(td => JSON.stringify(td.textContent)))")
    for r in rows:
        print("   row cells:", r)
    # try clicking the primary button at index 0 (the row that has the target code)
    # find the index
    idx = pg.evaluate("(code) => Array.from(document.querySelectorAll('#tb tr')).findIndex(t => t.cells[1].textContent.trim() === code)", code)
    print("target row index:", idx)
    # click that row's primary button via index
    pg.evaluate("(i) => {const btns=document.querySelectorAll('.p'); console.log('btns len', btns.length); if(btns[i]) btns[i].click();}", idx)
    pg.wait_for_timeout(120)
    print("after primary:", pg.evaluate("() => window.__state"))
    b.close()
