"""lint_pages.py — kiem tra nhanh 12 trang B15 x 3 variant (DeepSeek, 19/10).

Chay LOCAL (khong GPU, playwright 1.58 co san):
  - mo tung trang file://.../tXX.html?v=N
  - bat JS pageerror + console.error
  - doc `document.body.dataset` (nguon state cho checker) + `window.__task_ok`
  - chup man hinh vao lint_shots/ de doi chieu

Chay:  python phase13-gui/bench_v15/lint_pages.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TDIR = os.path.join(HERE, "tasks")
SHOTS = os.path.join(HERE, "lint_shots")


def main():
    from playwright.sync_api import sync_playwright

    meta = json.load(open(os.path.join(TDIR, "tasks.json"), encoding="utf-8"))
    os.makedirs(SHOTS, exist_ok=True)
    nbad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for task in meta["tasks"]:
            tid = task["task_id"]
            f = os.path.join(TDIR, tid.lower() + ".html")
            if not os.path.exists(f):
                print(f"THIEU-FILE {tid}: {f}")
                nbad += 1
                continue
            for v in task.get("variants", [0, 1, 2]):
                page = b.new_page(viewport={"width": 1280, "height": 720})
                errs = []

                def _on_err(e, errs=errs):
                    errs.append("pageerror: " + str(e)[:150])

                def _on_con(m, errs=errs):
                    if m.type == "error":
                        errs.append("console.error: " + m.text[:120])

                page.on("pageerror", _on_err)
                page.on("console", _on_con)
                url = "file:///" + f.replace("\\", "/") + f"?v={v}"
                try:
                    page.goto(url)
                    page.wait_for_timeout(400)
                    ds = page.evaluate(
                        "() => Object.assign({}, document.body.dataset)")
                    ok_flag = page.evaluate("() => window.__task_ok")
                    page.screenshot(
                        path=os.path.join(SHOTS, f"{tid}_v{v}.png"))
                except Exception as e:
                    errs.append("EXC: " + type(e).__name__ + ": " + str(e)[:150])
                    ds = {}
                    ok_flag = None
                page.close()
                tag = "ERR" if errs else "OK "
                if errs:
                    nbad += 1
                print(f"{tag} {tid} v{v}  __task_ok={ok_flag}  "
                      f"ds[{','.join(sorted(ds.keys()))}]")
                if ds:
                    print("      ds=" + json.dumps(ds, ensure_ascii=False)[:230])
                for e in errs[:4]:
                    print("      ! " + e)
    print(f"\nDONE lint. so ban ghi loi: {nbad}")
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main())
