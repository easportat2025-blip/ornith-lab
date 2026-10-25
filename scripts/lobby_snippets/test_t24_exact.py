# -*- coding: utf-8 -*-
"""Dung DUNG thu tu cua dummy: click #ta (qua _mimo_click) -> ctrl+a -> type."""
import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Admin\Desktop\New folder\phase14-desktop")
os.environ["DB_HEADLESS"] = "1"
import harness as H  # noqa

APP = r"C:\Users\Admin\Desktop\New folder\phase13-gui\kernel_desktop_bench\apps\t24_text_edit.html"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1264, "height": 625})
    H._PW_PAGE = page
    page.goto("file:///" + APP.replace("\\", "/"))
    page.wait_for_timeout(300)
    want = page.inner_text("#want")
    print("WANT:", repr(want))
    # 1) click #ta y nhu dummy
    rect = H._mimo_rect("#ta")
    print("  _mimo_rect('#ta') =", rect)
    if rect:
        print("  cdp click ->", H.cdp_action("CLICK %d %d" % (rect[0], rect[1])))
    print("  focus sau click:", page.evaluate(
        "() => document.activeElement && document.activeElement.id"))
    # 2) ctrl+a
    print("  cdp key ->", H.cdp_action("KEY ctrl+a"))
    sel = page.evaluate("() => { const e=document.getElementById('ta');"
                        " return [e.selectionStart, e.selectionEnd, e.value.length]; }")
    print("  selection sau ctrl+a:", sel)
    # 3) type
    print("  cdp type ->", H.cdp_action("TYPE %s" % want))
    val = page.eval_on_selector("#ta", "e => e.value")
    print("  value:", repr(val[:100]))
    print("  => khop want?", val.strip() == want.strip())
    b.close()
