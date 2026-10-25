# -*- coding: utf-8 -*-
"""
dbg_t38c.py - debug t38_recovery.
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
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto("file:///" + app.replace("\\", "/"))
    pg.wait_for_timeout(250)
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    print("spec:", v)
    print("CODE:", v.get("CODE"))
    # check buttons
    n = pg.evaluate("() => document.querySelectorAll('.p').length")
    print("n .p buttons:", n)
    print("data-i of .p:", pg.evaluate("() => Array.from(document.querySelectorAll('.p')).map(b=>b.dataset.i)"))
    # click the .p of the target row
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); console.log('tr found:', !!tr); if(tr){const btn=tr.querySelector('.p'); console.log('btn found:', !!btn); if(btn) btn.click();}}", v.get("CODE"))
    pg.wait_for_timeout(120)
    print("after primary:", pg.evaluate("() => window.__state"))
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); if(tr){const btn=tr.querySelector('.b'); if(btn) btn.click();}}", v.get("CODE"))
    pg.wait_for_timeout(120)
    print("after backup:", pg.evaluate("() => window.__state"))
    b.close()
