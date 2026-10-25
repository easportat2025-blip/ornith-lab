# -*- coding: utf-8 -*-
"""
check_replay_quality.py - kiem tra data desktop-replay: sau khi chay dummy
policy, app co THUC SU duoc giai khong? (neu khong => data day model mot
duong di khong hoan thanh => vo dung)

Dung (local):
    REPLAY_WORK=... REPLAY_OUT=... REPLAY_ZIP=... REPLAY_EPISODES=1 \
    REPLAY_ONLY_APPS=t21_form_desktop.html python scripts/check_replay_quality.py
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
WORK = os.environ.get("REPLAY_WORK",
                       os.path.join(ROOT, "phase13-gui", "colab_staging",
                                    "desktop_replay_in"))
sys.path.insert(0, WORK)
import dummy_mimo  # noqa: E402
import dummy_2048  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

W, H = 1280, 720
# (task_id, app, kiem tra thanh cong)
CHECKS = {
    "T20_2048": "window.__score",
    "T21_form_desktop": "window.__form_state && window.__form_state.ok",
    "T22_calc": "window.__state && window.__state.ok",
    "T23_table_sort": "window.__state && window.__state.ok",
    "T24_text_edit": "window.__state && window.__state.ok",
}
POL = {"DummyFormDesktop": dummy_mimo.DummyFormDesktop,
       "DummyCalc": dummy_mimo.DummyCalc,
       "DummyTableSort": dummy_mimo.DummyTableSort,
       "DummyTextEdit": dummy_mimo.DummyTextEdit,
       "Dummy2048": dummy_2048.Dummy2048}


# FIX 22/10 (MiMo): ten phim cho PLAYWRIGHT (khop e.key cua app) - phan GHI
# action van dung ten xdotool ("KEY left") de khop format data train.
KEY_MAP = {
    "left": "ArrowLeft", "down": "ArrowDown",
    "right": "ArrowRight", "up": "ArrowUp",
    "esc": "Escape", "escape": "Escape", "enter": "Enter", "tab": "Tab",
    "space": "Space", "backspace": "Backspace", "delete": "Delete",
    "home": "Home", "end": "End", "pageup": "PageUp", "pagedown": "PageDown",
    "ctrl+a": "Control+a", "ctrl+c": "Control+c", "ctrl+v": "Control+v",
    "ctrl+x": "Control+x", "ctrl+z": "Control+z", "shift+tab": "Shift+Tab",
}


def press_key(pg, name):
    """Bam phim theo ten xdotool -> ten phim cua Playwright."""
    k = (name or "").strip().lower()
    pg.keyboard.press(KEY_MAP.get(k, name))


def act_to_str(act):
    if not act:
        return None
    v, a = act
    if v == "click":
        return "CLICK %d %d" % (a[0], a[1])
    if v == "type":
        return "TYPE %s" % a
    if v == "key":
        return "KEY %s" % str(a).lower()
    return None


def main():
    tasks = json.load(io.open(os.path.join(WORK, "tasks.json"),
                              encoding="utf-8"))["tasks"]
    eps = int(os.environ.get("REPLAY_EPISODES", "2"))
    only = [a for a in (os.environ.get("REPLAY_ONLY_APPS", "") or "").split(",")
            if a.strip()]
    st = {"page": None}

    def _page_state(expr):
        pg = st.get("page")
        if pg is None:
            return None
        try:
            return pg.evaluate("() => %s" % expr)
        except Exception:
            return None

    dummy_mimo._page_state = _page_state
    dummy_2048._page_state = _page_state
    n_ok = n_bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for t in tasks:
            tid = t["task_id"]
            if only and t["app"] not in only and tid not in only:
                continue
            for ep in range(eps):
                ctx = b.new_context(viewport={"width": W, "height": H})
                pg = ctx.new_page()
                st["page"] = pg
                pg.goto("file://" + os.path.join(WORK, t["app"]))
                pg.wait_for_timeout(350)
                pol = POL[t["dummy"]]()
                for step in range(16):
                    _d, act = pol.act("", t, step)
                    astr = act_to_str(act)
                    if astr is None:
                        break
                    if astr.startswith("CLICK"):
                        x, y = astr.split()[1:3]
                        pg.mouse.click(int(x) * W // 1000, int(y) * H // 1000)
                    elif astr.startswith("TYPE"):
                        pg.keyboard.type(astr[5:])
                    elif astr.startswith("KEY"):
                        press_key(pg, astr[4:].strip())
                    pg.wait_for_timeout(90)
                expr = CHECKS.get(tid, "1")
                try:
                    val = pg.evaluate("() => (%s)" % expr)
                except Exception as e:
                    val = "LOI %s" % e
                good = bool(val) if not isinstance(val, str) else val not in ("", "0", "None")
                print("   %-18s ep%d: %s = %r => %s"
                      % (tid, ep, expr, val, "GIAI OK" if good else "CHUA GIAI"))
                n_ok += 1 if good else 0
                n_bad += 0 if good else 1
                ctx.close()
        b.close()
    print("=> giai duoc %d / %d episode" % (n_ok, n_ok + n_bad))
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
