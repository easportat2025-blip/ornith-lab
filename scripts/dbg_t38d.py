# -*- coding: utf-8 -*-
"""
dbg_t38d.py - debug t38.
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
    print("spec:", v)
    # check if the buttons exist
    n = pg.evaluate("() => document.querySelectorAll('.p').length")
    print("n .p:", n)
    # try clicking by index
    pg.evaluate("(i) => {const b=document.querySelectorAll('.p')[i]; if(b){b.click(); console.log('clicked .p['+i+']');} }", v.get("target_row", 0))
    pg.wait_for_timeout(120)
    print("after primary:", pg.evaluate("() => window.__state"))
    b.close()
