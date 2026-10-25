# -*- coding: utf-8 -*-
"""Test 4 dummy cua MiMo: chay voi Playwright (gia lap _page_state cua harness)
va kiem tra app co dat trang thai THANH CONG."""
import importlib.util
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

T = r"C:\Users\Admin\Desktop\New folder\phase14-desktop\tasks"
spec = importlib.util.spec_from_file_location("dm", os.path.join(T, "dummy_mimo.py"))
dm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dm)

import checker_desktop as cd

PAIRS = [("T21_form_desktop", "t21_form_desktop.html", dm.DummyFormDesktop),
         ("T22_calc", "t22_calc.html", dm.DummyCalc),
         ("T23_table_sort", "t23_table_sort.html", dm.DummyTableSort),
         ("T24_text_edit", "t24_text_edit.html", dm.DummyTextEdit)]


def parse_action_v2(t):
    t = (t or "").strip()
    m = re.search(r"CLICK\s+(\d+)\s+(\d+)", t, re.I)
    if m:
        return ("click", [int(m.group(1)), int(m.group(2))])
    m = re.search(r"TYPE\s+(.+)", t, re.I)
    if m:
        return ("type", m.group(1))
    m = re.search(r"KEY\s+(\w+)", t, re.I)
    if m:
        return ("key", m.group(1).lower())
    m = re.search(r"SCROLL\s+(\d+)", t, re.I)
    if m:
        return ("scroll", m.group(1))
    if t.upper() == "DONE":
        return ("done", None)
    return None


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1280, "height": 720})

    def page_state(expr):
        # giong _page_state cua harness: tra ve CHUOI JSON (co quotes)
        m = re.match(r"JSON\.stringify\((.*)\)\s*$", expr, re.S)
        js = m.group(1) if m else expr
        v = page.evaluate(js)
        return json.dumps(v)

    dm._page_state = page_state
    dm.parse_action_v2 = parse_action_v2

    ok_all = True
    for tid, fn, cls in PAIRS:
        path = os.path.join(T, fn)
        page.goto("file:///" + path.replace("\\", "/"))
        page.wait_for_timeout(200)
        pol = cls()
        desc = ""
        for step in range(20):
            desc, act = pol.act(None, tid, step)
            verb, arg = act
            if verb == "click":
                page.mouse.click(arg[0] / 1000 * 1280, arg[1] / 1000 * 720)
            elif verb == "type":
                page.keyboard.type(arg, delay=5)
            elif verb == "key":
                kk = {"ctrl+a": "Control+a", "ctrl+c": "Control+c",
                      "ctrl+v": "Control+v"}.get(arg, arg)
                page.keyboard.press(kk)
            elif verb == "scroll":
                page.mouse.wheel(0, 400)
            page.wait_for_timeout(60)
            if verb == "done":
                break
        res = cd.check_task(page, tid)
        print("%-18s dummy -> %-5s  (%s)" % (tid, res["success"],
                                             res["reason"][:60]))
        if not res["success"]:
            ok_all = False
            print("      state:", page.evaluate("() => window.__state"))
    b.close()
print("OK" if ok_all else "CO VAI DUMMY CHUA DAT")
