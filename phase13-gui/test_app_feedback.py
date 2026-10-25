# -*- coding: utf-8 -*-
"""
test_app_feedback.py - TEST CHONG TAI PHAT: moi app phai TRA LAI PHAI HOI tren
man hinh (dong #status) sau khi model lam viec.

Ly do (22/10): bug JS `var status = ...` o top-level bi DE len `window.status`
=> gán `status.textContent` khong bao loi nhung cung KHONG hien gi => dong
phan hoi CHET trong 8 app (4 task web + 4 app desktop) => model lap Ctrl+C 12
lan vi khong co tin hieu nao. Self-test checker chi kiem KET QUA, khong kiem
PHAN HOI => loi do lot qua.

Kiem tra 2 tang:
  (A) STATIC: moi thuoc tinh `var <ten>` o top-level phai KHONG trung ten voi
      mot thuoc tinh co san cua window (status/name/length/top/...) - vi
      `var` se ghi de window.<ten> thay vi tao binding moi.
  (B) DYNAMIC: chay success policy cua tung task roi doc #status => phai
      KHONG RONG (neu app co #status).

Chay offline (playwright + CPU):
    python phase13-gui/test_app_feedback.py
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FAILS = []

# thuoc tinh co san cua window (global) - gan `var <ten>` se DE len chung
WINDOW_PROPS = {
    "status", "name", "length", "top", "self", "parent", "closed", "origin",
    "opener", "frames", "history", "location", "document", "window", "screen",
    "clientInformation", "event", "external", "crypto", "indexedDB",
}

SUITES = [
    ("bench_v155", "checker", "tasks_v15_5"),
    ("bench_v16", "checker_v16", "tasks_v16_a"),
]


def ok(cond, msg):
    print("  %s %s" % ("ok  " if cond else "FAIL", msg))
    if not cond:
        FAILS.append(msg)


def static_check():
    print("(A) STATIC: bien top-level var <ten> co trung ten voi window.<ten>")
    base = os.path.dirname(os.path.abspath(__file__))
    dirs = [os.path.join(base, "bench_v15", "tasks_v15_5", "tasks"),
            os.path.join(base, "bench_v15", "tasks_v16_a", "tasks"),
            os.path.join(os.path.dirname(base), "phase14-desktop", "tasks")]
    n = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".html"):
                continue
            p = os.path.join(d, fn)
            s = io.open(p, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"(?m)^\s*var\s+([A-Za-z_$][\w$]*)\s*=",
                                 s):
                name = m.group(1)
                if name in WINDOW_PROPS:
                    ok(False, "%s: `var %s` o top-level se DE len window.%s "
                              "=> assign vo bi bo qua (im lang)" % (fn, name, name))
                    n += 1
    ok(n == 0, "khong con bien top-level trung ten voi window.* (%d loi)" % n)


def dynamic_check():
    print("(B) DYNAMIC: trong khi model lam viec, #status phai CO noi dung")
    from playwright.sync_api import sync_playwright
    base = os.path.dirname(os.path.abspath(__file__))
    for runner_name, checker_name, folder in SUITES:
        d = os.path.join(base, "bench_v15", folder)
        if not os.path.isdir(d):
            continue
        if d not in sys.path:
            sys.path.insert(0, d)
        runner = __import__(runner_name)
        checker = __import__(checker_name)
        tids = [t["task_id"] for t in runner.load_tasks()]
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = b.new_page(viewport={"width": 1280, "height": 720})
            for tid in tids:
                seen = []

                def make(inner, seen=seen):
                    def pol_fn(obs):
                        a = inner(obs)
                        try:
                            if obs.get("peek"):
                                t = obs["peek"]("() => { const e="
                                                 "document.getElementById('status');"
                                                 " return e ? (e.textContent||'') : ''; }")
                                if t and t.strip():
                                    seen.append(t.strip())
                        except Exception:
                            pass
                        return a
                    return pol_fn

                base_pol = checker._Dispatcher(
                    lambda tid, spec, peek: checker.POLICIES[tid](spec, peek))
                runner.run_task(page, tid, 0, make(base_pol), peek=True)
                has = page.evaluate("() => !!document.getElementById('status')")
                if not has:
                    continue
                ok(bool(seen),
                   "%s: app PHAI tra phan hoi tren man hinh trong khi model "
                   "lam viec (thay vi chi xem ket qua cuoi)" % tid)
            b.close()


def main():
    print("[test] test_app_feedback - chong loi 'dong phan hoi chet'")
    static_check()
    try:
        dynamic_check()
    except Exception as e:
        ok(False, "dynamic check loi: %s" % str(e)[:120])
    print("[test] %s" % ("PASS" if not FAILS else "FAIL (%d)" % len(FAILS)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
