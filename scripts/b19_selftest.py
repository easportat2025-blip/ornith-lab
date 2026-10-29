# -*- coding: utf-8 -*-
"""b19_selftest.py - GT policies cho B19 (DOM/mouse/keyboard, khong phai model).

Muc dich: chay checker self-test 8/8 truoc khi upload dataset/kernel.
Moi policy chi dung hanh vi ma app cho phep; checker doc DOM + __state.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def p_t41(page):
    page.evaluate("""() => {
      const o = document.getElementById('outer');
      o.scrollTop = o.scrollHeight;
      o.dispatchEvent(new Event('scroll'));
      const i = document.getElementById('inner');
      i.scrollTop = i.scrollHeight;
      i.dispatchEvent(new Event('scroll'));
    }""")
    code = page.evaluate("() => window.__spec.vars.CODE")
    page.evaluate("""(code) => {
      const rows = [...document.querySelectorAll('#tb tr')];
      const r = rows.find(x => x.cells[1].textContent.trim() === code);
      if (!r) throw new Error('target row not found');
      r.click();
    }""", code)
    page.click("#sub")
    page.wait_for_timeout(200)


def p_t42(page):
    target = int(page.evaluate("() => window.__spec.vars.VALUE"))
    box = page.locator("#wrap").bounding_box()
    if not box:
        raise RuntimeError("slider box missing")
    y = box["y"] + box["height"] / 2
    x0 = box["x"] + 1
    x1 = box["x"] + box["width"] * target / 100.0
    page.mouse.move(x0, y)
    page.mouse.down()
    page.mouse.move(x1, y, steps=12)
    page.mouse.up()
    page.click("#sub")
    page.wait_for_timeout(200)


def p_t43(page):
    sp = page.evaluate("() => window.__spec.vars")
    page.fill("#project", sp["PROJECT"])
    page.click("#b1")
    page.select_option("#region", sp["REGION"])
    page.select_option("#tier", sp["TIER"])
    page.click("#b2")
    page.check("#confirm")
    page.click("#b3")
    page.wait_for_timeout(200)


def p_t44(page):
    sp = page.evaluate("() => window.__spec.vars")
    page.evaluate("() => document.getElementById('name').focus()")
    page.keyboard.type(sp["NAME"])
    page.keyboard.press("Tab")
    page.keyboard.type(sp["EMAIL"])
    page.keyboard.press("Tab")
    plan_idx = {"Basic": 1, "Pro": 2, "Ultra": 3}[sp["PLAN"]]
    for _ in range(plan_idx):
        page.keyboard.press("ArrowDown")
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")
    page.wait_for_timeout(250)


def p_t45(page):
    page.click("#src")
    page.keyboard.press("Control+A")
    page.keyboard.press("Control+C")
    page.click("#dst")
    page.keyboard.press("Control+V")
    page.click("#verify")
    page.wait_for_timeout(200)


def p_t46(page):
    name = page.evaluate("() => window.__spec.vars.NAME")
    page.fill("#q", name)
    page.wait_for_timeout(150)
    page.click('#list .row[data-name="%s"]' % name)
    page.click("#sub")
    page.wait_for_timeout(200)


def p_t47(page):
    item = page.evaluate("() => window.__spec.vars.ITEM")
    src = page.locator('#list .item[data-name="%s"]' % item)
    first = page.locator("#list .item").first
    a = src.bounding_box()
    b = first.bounding_box()
    if not a or not b:
        raise RuntimeError("reorder boxes missing")
    page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
    page.mouse.down()
    page.mouse.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, steps=12)
    page.mouse.up()
    page.click("#sub")
    page.wait_for_timeout(200)


def p_t48(page):
    sp = page.evaluate("() => window.__spec.vars")
    page.hover('.menu[data-menu="%s"]' % sp["MENU"])
    page.wait_for_timeout(120)
    page.click('.menu[data-menu="%s"] .sub div[data-item="%s"]'
               % (sp["MENU"], sp["ITEM"]))
    page.wait_for_timeout(200)


POLICIES = {
    "t41_nested_scroll.html": p_t41,
    "t42_precision_drag.html": p_t42,
    "t43_wizard_validation.html": p_t43,
    "t44_keyboard_only.html": p_t44,
    "t45_clipboard_verify.html": p_t45,
    "t46_dynamic_filter.html": p_t46,
    "t47_drag_reorder.html": p_t47,
    "t48_hover_submenu.html": p_t48,
}


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.join(here, "..", "phase13-gui", "bench_b19"))
    import checker
    raise SystemExit(checker.selftest())
