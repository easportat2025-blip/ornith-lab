# -*- coding: utf-8 -*-
"""Test duong LOCAL cua harness: mo app, dung chinh chuoi action cua dummy
(click #ta -> ctrl+a -> type WANT -> click #save) qua harness.cdp_action,
roi doc gia tri textarea + reward."""
import io
import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HP = r"C:\Users\Admin\Desktop\New folder\phase14-desktop"
sys.path.insert(0, HP)
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
    # --- chuoi action DUNG nhu dummy
    for act in ("KEY ctrl+a",):
        print("  cdp_action(%r) ->" % act, H.cdp_action(act))
    # click textarea + type + save (theo toa do normalized cua app)
    r = page.query_selector("#ta")
    bb = r.bounding_box()
    page.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
    page.keyboard.type(want)
    val = page.eval_on_selector("#ta", "e => e.value")
    print("value sau type (co ctrl+a truoc do):", repr(val[:90]))
    print("=> khop want?", val.strip() == want.strip())
    b.close()
