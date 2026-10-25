# -*- coding: utf-8 -*-
"""Test truc tiep app T24: click textarea -> ctrl+a -> type WANT -> doc value
=> xac nhan co select-all hoac khong (vuot 50% ky tu) va cho biet app co
chuan hoa (trim) hay khong."""
import io
import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APP = r"C:\Users\Admin\Desktop\New folder\phase13-gui\kernel_desktop_bench\apps\t24_text_edit.html"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1264, "height": 625})
    page.goto("file:///" + APP.replace("\\", "/"))
    page.wait_for_timeout(300)
    want = page.inner_text("#want")
    old = page.eval_on_selector("#ta", "e => e.value")
    print("WANT  :", repr(want))
    print("OLD   :", repr(old[:60]))
    page.click("#ta")
    page.keyboard.press("Control+a")
    page.keyboard.type(want)
    now = page.eval_on_selector("#ta", "e => e.value")
    print("SAU   :", repr(now[:120]))
    print("Khop want (trim)?", now.strip() == want.strip())
    # save + reward
    page.click("#save")
    page.wait_for_timeout(200)
    st = page.evaluate("() => window.__state || null")
    print("STATE :", st)
    b.close()
