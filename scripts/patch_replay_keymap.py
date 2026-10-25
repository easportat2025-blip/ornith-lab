# -*- coding: utf-8 -*-
"""
patch_replay_keymap.py - them KEY_MAP cho 2 script sinh desktop-replay
(colab_desktop_replay.py + check_replay_quality.py).

LY DO (22/10, @MiMo): Playwright `keyboard.press("down")` => LOI "Unknown key"
=> cac buoc KEY cua app 2048 KHONG chay => trajectory 2048 vo dung.
NHUNG app desktop nhan `e.key.toLowerCase()` (=> "arrowleft") va bench ghi
action theo ten xdotool ("KEY left") => phai:
   - GHI: "KEY left" (dung format data train, khop harness)
   - BAM: "ArrowLeft" (Playwright)
=> KEY_MAP chi dung cho PHAN THUC HIEN, KHONG doi phan ghi.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"

KEYMAP = '''
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
'''

TARGETS = [
    (os.path.join(ROOT, "scripts", "colab_desktop_replay.py"),
     '''                        elif astr.startswith("KEY"):
                            pg.keyboard.press(astr[4:].strip())''',
     '''                        elif astr.startswith("KEY"):
                            press_key(pg, astr[4:].strip())'''),
    (os.path.join(ROOT, "scripts", "check_replay_quality.py"),
     '''                    elif astr.startswith("KEY"):
                        pg.keyboard.press(astr[4:].strip())''',
     '''                    elif astr.startswith("KEY"):
                        press_key(pg, astr[4:].strip())'''),
]

n = 0
for path, old, new in TARGETS:
    s = io.open(path, encoding="utf-8", newline="").read()
    if "KEY_MAP" in s:
        print("   da co KEY_MAP: %s" % os.path.basename(path))
        continue
    if old not in s:
        print("   !! khong tim thay khoi trong %s" % os.path.basename(path))
        continue
    s = s.replace(old, new, 1)
    # them KEYMAP truoc def act_to_str
    anchor = "def act_to_str(act):"
    if anchor in s and "KEY_MAP = {" not in s:
        s = s.replace(anchor, KEYMAP.strip() + "\n\n\n" + anchor, 1)
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    n += 1
    print("   sua: %s" % os.path.basename(path))
print("=> %d file sua" % n)
