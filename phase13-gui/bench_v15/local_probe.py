"""local_probe.py — do co che T04/T05/T07 tren Playwright local (DeepSeek, tam thoi).

Chay: python phase13-gui/bench_v15/local_probe.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VW, VH = 1280, 720


def url(tid, v=0):
    p = os.path.join(HERE, "tasks", tid.lower() + ".html")
    return "file:///" + p.replace("\\", "/") + f"?v={v}"


def ds(page):
    return page.evaluate("() => Object.assign({}, document.body.dataset)")


def active(page):
    return page.evaluate(
        "() => document.activeElement && "
        "(document.activeElement.id || document.activeElement.tagName)")


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": VW, "height": VH})

        # ---- T07 ----
        page.goto(url("t07_scroll"))
        page.wait_for_timeout(300)
        print("T07 init        :", ds(page), "active=", active(page))
        print("T07 tabindex    :", page.evaluate(
            "() => document.getElementById('list').getAttribute('tabindex')"))
        lb = page.locator("#list").bounding_box()
        page.mouse.click(lb["x"] + lb["width"] / 2, lb["y"] + lb["height"] / 2)
        page.wait_for_timeout(120)
        print("T07 after click :", ds(page), "active=", active(page))
        for i in range(6):
            page.keyboard.press("End")
            page.wait_for_timeout(250)
            d = ds(page)
            print(f"T07 End#{i+1}      : loaded={d.get('loaded')} "
                  f"clicked={d.get('clicked')} premature={d.get('premature')}")
            if d.get("loaded") == d.get("total"):
                break
        # click last item
        last = page.evaluate(
            "() => { const items = document.querySelectorAll('#list .item');"
            " const el = items[items.length-1]; const r = el.getBoundingClientRect();"
            " return {x:r.x+r.width/2, y:r.y+r.height/2}; }")
        print("T07 last center :", last)
        page.mouse.click(last["x"], last["y"])
        page.wait_for_timeout(120)
        print("T07 after last  :", ds(page))

        # ---- T04 ----
        page.goto(url("t04_slider"))
        page.wait_for_timeout(300)
        tgt = int(ds(page)["target"])
        box = page.locator("#slider").bounding_box()
        x = box["x"] + box["width"] * (tgt / 100.0)
        y = box["y"] + box["height"] / 2
        page.mouse.click(x, y)
        page.wait_for_timeout(120)
        d = ds(page)
        print(f"T04 target={tgt} click@{tgt}% -> value={d['value']}")
        diff = tgt - int(d["value"])
        key = "ArrowRight" if diff > 0 else "ArrowLeft"
        for _ in range(abs(diff)):
            page.keyboard.press(key)
        page.wait_for_timeout(120)
        print("T04 after arrows:", ds(page))

        # ---- T05 ----
        page.goto(url("t05_shortcut"))
        page.wait_for_timeout(300)
        src = page.locator("#src").bounding_box()
        dst = page.locator("#dst").bounding_box()
        page.mouse.click(src["x"] + src["width"] / 2, src["y"] + src["height"] / 2)
        page.keyboard.press("Control+a")
        page.keyboard.press("Control+c")
        page.wait_for_timeout(80)
        d = ds(page)
        print("T05 after copy  :", d, "active=", active(page))
        page.mouse.click(dst["x"] + dst["width"] / 2, dst["y"] + dst["height"] / 2)
        page.keyboard.press("Control+v")
        page.wait_for_timeout(120)
        print("T05 after paste :", ds(page))
        print("T05 dst.value   :", page.evaluate(
            "() => document.getElementById('dst').value"))

        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
