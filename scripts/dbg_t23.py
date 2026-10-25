# -*- coding: utf-8 -*-
"""
dbg_t23.py - debug task T23_table_sort: chay tung buoc, in state sau moi buoc.
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
WORK = os.path.join(ROOT, "phase13-gui", "colab_staging", "desktop_replay_in")
sys.path.insert(0, WORK)
import checker_desktop as chk
from playwright.sync_api import sync_playwright

W, H = 1280, 720
app = os.path.join(WORK, "t23_table_sort.html")
url = "file:///" + app.replace("\\", "/")


def st(pg):
    try:
        return pg.evaluate("""() => {
            const data=JSON.parse((document.getElementById('data')||{}).textContent||'[]');
            const rows=Array.from(document.querySelectorAll('#tb tr')).map(tr=>
              Array.from(tr.children).map(td=>td.textContent.trim()));
            const sel=document.querySelector('#tb tr.sel');
            return {rows:rows, selected: sel?Array.from(sel.children).map(td=>td.textContent.trim()):null,
                    status:(document.getElementById('status')||{}).textContent||'',
                    n_data:data.length};
        }""")
    except Exception as e:
        return {"err": str(e)}


with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.goto(url)
    pg.wait_for_timeout(300)
    print("init:", st(pg))
    # scroll
    pg.evaluate("() => {const p=document.getElementById('panel'); p.scrollTop=p.scrollHeight;}")
    pg.wait_for_timeout(200)
    print("after scroll:", st(pg))
    # click header
    pg.click("#hscore")
    pg.wait_for_timeout(150)
    print("after click1 (asc):", st(pg))
    pg.click("#hscore")
    pg.wait_for_timeout(150)
    print("after click2 (desc):", st(pg))
    # click first row
    pg.evaluate("() => {const tr=document.querySelector('#tb tr'); if(tr) tr.click();}")
    pg.wait_for_timeout(120)
    print("after click top row:", st(pg))
    pg.click("#confirm")
    pg.wait_for_timeout(120)
    print("after confirm:", st(pg))
    tests, _ = chk.check_task(pg, "T23_table_sort")
    print("tests:", tests, "=> success:", tests.get("order is score descending"),
          tests.get("top row selected"), tests.get("confirmed"))
    b.close()
