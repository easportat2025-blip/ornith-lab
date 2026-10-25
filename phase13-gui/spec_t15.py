"""spec_t15.py - lay vi tri phan tu cua page T15 (local chromium) de sua policy."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bench_v15", "tasks_v15_5"))
from playwright.sync_api import sync_playwright  # noqa: E402

PAGE = os.path.join(HERE, "bench_v15", "tasks_v15_5", "tasks",
                    "t15_dialog.html")
SPEC_JS = {
    "T15_dialog": """() => {
      const g=id=>document.getElementById(id);
      const r=id=>{const e=g(id); if(!e) return null; const b=e.getBoundingClientRect();
        return {x:(b.x+b.width/2)/innerWidth*1000, y:(b.y+b.height/2)/innerHeight*1000,
                w:b.width, h:b.height, top:b.y, left:b.x};};
      return {openbtn:r('openbtn'), ack:r('ack'), contbtn:r('contbtn'),
              terms:r('terms'), ref:r('ref'), subbtn:r('subbtn'),
              yesbtn:r('yesbtn'), nobbtn:r('nobbtn'),
              scrollH: g('terms')? g('terms').scrollHeight:0,
              clientH: g('terms')? g('terms').clientHeight:0};
    }"""
}

for v in (0,):
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = b.new_page(viewport={"width": 1280, "height": 720})
        page.goto("file:///" + os.path.abspath(PAGE).replace("\\", "/")
                  + "?v=%d" % v)
        page.wait_for_timeout(300)
        # MO DIALOG truoc khi do (phan tu khac display:none -> size 0)
        page.click("#openbtn")
        page.wait_for_timeout(300)
        spec = page.evaluate(SPEC_JS["T15_dialog"])
        print("=== T15 v%d spec (sau khi mo modal) ===" % v)
        for k, val in spec.items():
            if isinstance(val, dict):
                print("   %-8s x=%.1f y=%.1f (%dx%d)" %
                      (k, val["x"], val["y"], val["w"], val["h"]))
            else:
                print("   %-8s %s" % (k, val))
        # thu: click open -> scroll bang KEY End -> xem co scroll khong
        page.wait_for_timeout(200)
        before = page.evaluate("document.getElementById('terms').scrollTop")
        page.keyboard.press("End")
        page.wait_for_timeout(300)
        after = page.evaluate(
            "() => ({top: document.getElementById('terms').scrollTop,"
            " scrolled: document.body.dataset.scrolled,"
            " scrolledat: document.body.dataset.scrolledat||''})")
        print("KEY End: scrollTop %s -> %s | %s" % (before, after["top"], after))
        # thu: click vao terms (focus) roi KEY End
        page.click("#terms")
        page.keyboard.press("End")
        page.wait_for_timeout(300)
        after2 = page.evaluate(
            "() => ({top: document.getElementById('terms').scrollTop,"
            " scrolled: document.body.dataset.scrolled,"
            " scrolledat: document.body.dataset.scrolledat||''})")
        print("click+KEY End: %s" % after2)
        # thu: mouse wheel
        page.mouse.move(640, 400)
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(300)
        after3 = page.evaluate(
            "() => ({top: document.getElementById('terms').scrollTop,"
            " scrolled: document.body.dataset.scrolled,"
            " scrolledat: document.body.dataset.scrolledat||''})")
        print("mouse wheel: %s" % after3)
        b.close()
