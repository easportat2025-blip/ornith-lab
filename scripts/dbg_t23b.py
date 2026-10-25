# -*- coding: utf-8 -*-
"""
dbg_t23b.py - debug T23_table_sort: chay policy (header x2 + click top row +
confirm) va in state.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
WORK = os.path.join(ROOT, "phase13-gui", "colab_staging", "desktop_replay_in")
sys.path.insert(0, WORK)
from playwright.sync_api import sync_playwright

W, H = 1280, 720


def state(pg):
    try:
        return pg.evaluate("""() => {
            const data=JSON.parse((document.getElementById('data')||{}).textContent||'[]');
            const rows=Array.from(document.querySelectorAll('#tb tr')).map(tr=>
                Array.from(tr.children).map(td=>td.textContent.trim()));
            const sel=document.querySelector('#tb tr.sel');
            const exp=JSON.parse(JSON.stringify(data)).sort((a,b)=>b.score-a.score);
            return {rows:rows, selected: sel?Array.from(sel.children).map(td=>td.textContent.trim()):null,
                    status:(document.getElementById('status')||{}).textContent||'',
                    expected_first: exp[0]?exp[0].region:null};
        }""")
    except Exception as e:
        return {"err": str(e)}


def main():
    app = os.path.join(WORK, "t23_table_sort.html")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto("file:///" + app.replace("\\", "/"))
        pg.wait_for_timeout(300)
        print("init:", state(pg))
        pg.click("#hscore"); pg.wait_for_timeout(120)
        print("after click1 (asc):", state(pg))
        pg.click("#hscore"); pg.wait_for_timeout(120)
        print("after click2 (desc):", state(pg))
        pg.evaluate("() => {const tr=document.querySelector('#tb tr'); if(tr) tr.click();}")
        pg.wait_for_timeout(120)
        print("after click top row:", state(pg))
        pg.click("#confirm"); pg.wait_for_timeout(120)
        print("after confirm:", state(pg))
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
