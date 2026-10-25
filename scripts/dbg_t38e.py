# -*- coding: utf-8 -*-
"""
dbg_t38e.py - debug backup click.
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
    print("CODE:", code)
    # primary click
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); console.log('tr found:', !!tr); if(tr){const btn=tr.querySelector('.p'); console.log('primary btn:', !!btn); if(btn) btn.click();}}", code)
    pg.wait_for_timeout(120)
    print("after primary: tries=", pg.evaluate("() => window.__state.tries"))
    # check .b in the same tr
    has_b = pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); return tr ? (tr.querySelector('.b') !== null) : false;}", code)
    print("backup btn exists in tr:", has_b)
    # click backup
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr')).find(t=>t.cells[1].textContent.trim()===code); if(tr){const btn=tr.querySelector('.b'); console.log('backup btn:', !!btn); if(btn) btn.click();}}", code)
    pg.wait_for_timeout(120)
    print("after backup: tries=", pg.evaluate("() => window.__state.tries"))
    print("after backup: enabled=", pg.evaluate("() => window.__state.enabled"))
    b.close()
