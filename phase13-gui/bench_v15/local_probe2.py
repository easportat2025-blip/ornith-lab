"""local_probe2.py — do layout T07 (DeepSeek). Chay: python phase13-gui/bench_v15/local_probe2.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1280, "height": 720})
        u = "file:///" + os.path.join(HERE, "tasks", "t07_scroll.html").replace("\\", "/") + "?v=0"
        page.goto(u)
        page.wait_for_timeout(300)
        info = page.evaluate("""() => {
          const l = document.getElementById('list');
          const r = l.getBoundingClientRect();
          return {list_top: r.y, list_bottom: r.y + r.height,
                  innerH: window.innerHeight, scrollY: window.scrollY,
                  bodyH: document.body.scrollHeight,
                  clientH: l.clientHeight, scrollH: l.scrollHeight};
        }""")
        print("initial:", info)
        lb = page.locator("#list").bounding_box()
        page.mouse.click(lb["x"] + lb["width"] / 2, lb["y"] + lb["height"] / 2)
        page.wait_for_timeout(100)
        for i in range(4):
            page.keyboard.press("End")
            page.wait_for_timeout(250)
        out = page.evaluate("""() => {
          const l = document.getElementById('list');
          const items = document.querySelectorAll('#list .item');
          const el = items[items.length - 1];
          const r = el.getBoundingClientRect();
          const lr = l.getBoundingClientRect();
          return {n: items.length, last_y: r.y, last_yb: r.y + r.height,
                  list_top: lr.y, list_bottom: lr.y + lr.height,
                  scrollTop: l.scrollTop, scrollY: window.scrollY,
                  innerH: window.innerHeight};
        }""")
        print("after End x4:", out)
        # thu scroll WINDOW bang cach click vao vung trung tinh roi End
        page.mouse.click(640, 60)  # h1/hint area
        page.wait_for_timeout(80)
        print("active after neutral click:", page.evaluate(
            "() => document.activeElement.id || document.activeElement.tagName"))
        page.keyboard.press("End")
        page.wait_for_timeout(200)
        out2 = page.evaluate("""() => {
          const items = document.querySelectorAll('#list .item');
          const el = items[items.length - 1];
          const r = el.getBoundingClientRect();
          return {last_y: r.y, last_yb: r.y + r.height, scrollY: window.scrollY};
        }""")
        print("after window End:", out2)
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
