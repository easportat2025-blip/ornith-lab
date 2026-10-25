# -*- coding: utf-8 -*-
"""
dbg_t23e.py - debug T23: goi policy_fn({}, peek) truc tiep de xem kieu tra ve.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users/Admin/Desktop\New folder"
WORK = os.path.join(ROOT, "phase14-desktop", "tasks")
sys.path.insert(0, WORK)
from playwright.sync_api import sync_playwright

W, H = 1280, 720
app = os.path.join(WORK, "t23_table_sort.html")


def _t23_policy(spec, peek):
    def _rect(sel):
        r = peek("JSON.stringify((function(){const e=document.querySelector('%s');"
                 "if(!e) return null;const r=e.getBoundingClientRect();"
                 "return [Math.round((r.left+r.width/2)/innerWidth*1000),"
                 "Math.round((r.top+r.height/2)/innerHeight*1000)];})())" % sel)
        if isinstance(r, str):
            import json as _j
            try:
                r = _j.loads(r)
            except Exception:
                return None
        return r

    def fn(obs):
        s = obs["step"]
        if s == 0:
            r = _rect("#hscore")
            return "CLICK %d %d" % (r[0], r[1])
        if s == 1:
            r = _rect("#hscore")
            return "CLICK %d %d" % (r[0], r[1])
        if s == 2:
            r = _rect("#tb tr")
            if r is None:
                return "DONE"
            return "CLICK %d %d" % (r[0], r[1])
        if s == 3:
            r = _rect("#confirm")
            return "CLICK %d %d" % (r[0], r[1])
        return "DONE"

    return fn


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto("file:///" + app.replace("\\", "/"))
        pg.wait_for_timeout(250)
        peek = lambda js: pg.evaluate(js)
        pol = _t23_policy({}, peek)
        print("type(pol):", type(pol))
        obs = {"task_id": "T23_table_sort", "step": 0, "peek": peek}
        act = pol(obs)
        print("type(act):", type(act), "| act:", act)
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
