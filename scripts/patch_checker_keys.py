# -*- coding: utf-8 -*-
"""
patch_checker_keys.py - checker_desktop.KEY_ALIAS: them ten phim MUI TEN
(xdotool: left/right/up/down) -> ten cua Playwright (e.key: ArrowLeft/...).

LY DO (22/10, @MiMo): khi sinh data desktop-replay bang run_task() cua
checker (duong Playwright) => `keyboard.press("down")` => LOI "Unknown key"
=> 2048 khong chay duoc. Trong bench that (xdotool) nen loi nay khong lo.
=> KEY_ALIAS chi dung cho run_task => them an toan cho moi noi goi.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "phase14-desktop", "tasks", "checker_desktop.py")

OLD = '''KEY_ALIAS = {"ctrl": "Control", "shift": "Shift", "alt": "Alt", "meta": "Meta",
             "esc": "Escape", "return": "Enter", "space": "Space"}'''

NEW = '''KEY_ALIAS = {"ctrl": "Control", "shift": "Shift", "alt": "Alt", "meta": "Meta",
             "esc": "Escape", "return": "Enter", "space": "Space",
             # FIX 22/10 (MiMo): phim mui ten - ten xdotool (left) khac ten
             # Playwright/e.key (ArrowLeft) => run_task() (duong Playwright)
             # bi "Unknown key" => 2048 khong chay. (bench that dung xdotool
             # nen loi nay khong lo; KEY_ALIAS chi dung cho run_task.)
             "left": "ArrowLeft", "right": "ArrowRight",
             "up": "ArrowUp", "down": "ArrowDown",
             "pgup": "PageUp", "pgdn": "PageDown",
             "pageup": "PageUp", "pagedown": "PageDown",
             "del": "Delete", "bs": "Backspace"}'''

s = io.open(P, encoding="utf-8", newline="").read()
if '"left": "ArrowLeft"' in s:
    print("da co arrow alias")
    sys.exit(0)
if OLD not in s:
    print("FAIL: khong tim thay KEY_ALIAS")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da them phim mui ten vao KEY_ALIAS")
