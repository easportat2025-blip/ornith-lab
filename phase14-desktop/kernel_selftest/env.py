"""env.py - DESKTOP-ENV: moi truong computer-use THAT cho Ornith.

Y tuong: thay vi "click vao DOM HTML" (B15), day duoc dung chuot/ban phim THAT
tren mot desktop ao (X11/Xvfb):
  - quan sat  = anh chup toan man hinh (1280x720)
  - hanh dong = move/click/drag/scroll + go phim (xdotool -> su kien OS that)
  - phan thuong = trang thai app (DOM qua CDP, diem game, ...) -> checker
Giao dien policy **giong het** bench_v15: policy_fn(obs) -> "CLICK x y" / "TYPE .."
/ "KEY ..." (x,y normalized 0..1000) => model + code cu chay lai duoc ngay.

Chay CPU (khong ton GPU-quota): Xvfb + chromium + xdotool + imagemagick.
"""
import json
import os
import re
import shutil
import subprocess
import time

W, H = 1280, 720
DISPLAY = os.environ.get("DISPLAY", ":99")
WORK = os.environ.get("ENV_WORK", "/kaggle/working/desktop")
SHOTS = os.path.join(WORK, "shots")
XDO = "xdotool"


def sh(cmd, timeout=300, env=None):
    e = dict(os.environ)
    e["DISPLAY"] = DISPLAY
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, env=e,
                           timeout=timeout)
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
            (p.stderr or b"").decode("utf-8", "replace")
    except Exception as ex:
        return -1, "", str(ex)


def log(m):
    print("[env] %s" % m, flush=True)


# ------------------------------------------------------------------ display
def start_display():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(SHOTS, exist_ok=True)
    if not shutil.which("Xvfb"):
        log("thieu Xvfb -> cai dat")
        sh("apt-get update -qq && apt-get install -y -qq xvfb x11-utils "
           "xdotool imagemagick fluxbox >/dev/null 2>&1", timeout=1200)
    rc, out, err = sh("pgrep -f 'Xvfb %s' >/dev/null && echo ok || "
                       "(Xvfb %s -screen 0 %dx%dx24 -ac >/dev/null 2>&1 & sleep 2; "
                       "echo started)" % (DISPLAY, DISPLAY, W, H))
    log("display %s: %s" % (DISPLAY, out.strip() or err.strip()[:120]))
    sh("xdpyinfo -display %s >/dev/null 2>&1 && echo 'X OK' || echo 'X FAIL'"
       % DISPLAY)
    return True


def screenshot(path):
    """Chup man hinh X11 -> PNG."""
    rc, out, err = sh("import -window root %s" % path, timeout=120)
    if rc != 0 or not os.path.exists(path):
        rc2, o2, e2 = sh("xwd -root -silent | convert xwd:- %s" % path, timeout=120)
        if rc2 != 0:
            log("screenshot fail: %s | %s" % (err.strip()[:80], e2.strip()[:80]))
            return False
    return os.path.exists(path)


# ------------------------------------------------------------------ actions
def _px(norm, total):
    return max(1, min(total - 1, int(round(float(norm) / 1000.0 * total))))


def act_click(x, y, button=1):
    px, py = _px(x, W), _px(y, H)
    sh("%s mousemove %d %d sleep 0.15 click %d" % (XDO, px, py, button))
    return "click(%d,%d)" % (px, py)


def act_move(x, y):
    px, py = _px(x, W), _px(y, H)
    sh("%s mousemove %d %d" % (XDO, px, py))
    return "move(%d,%d)" % (px, py)


def act_drag(x1, y1, x2, y2):
    ax, ay = _px(x1, W), _px(y1, H)
    bx, by = _px(x2, W), _px(y2, H)
    sh("%s mousemove %d %d mousedown 1 sleep 0.2 mousemove %d %d sleep 0.2 mouseup 1"
       % (XDO, ax, ay, bx, by))
    return "drag(%d,%d->%d,%d)" % (ax, ay, bx, by)


def act_scroll(x, y, amount):
    px, py = _px(x, W), _px(y, H)
    sh("%s mousemove %d %d click %d" % (XDO, px, py, 4 if amount < 0 else 5),
       timeout=60)
    return "scroll(%d)" % amount


def act_type(text):
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    sh("%s type --delay 12 \"%s\"" % (XDO, safe))
    return "type(%s)" % text[:30]


def act_key(name):
    keymap = {"enter": "Return", "tab": "Tab", "esc": "Escape", "space": "space",
              "up": "Up", "down": "Down", "left": "Left", "right": "Right",
              "backspace": "BackSpace", "ctrl+a": "ctrl+a", "ctrl+c": "ctrl+c",
              "ctrl+v": "ctrl+v", "delete": "Delete"}
    k = keymap.get(str(name).lower(), str(name))
    sh("%s key %s" % (XDO, k))
    return "key(%s)" % k


ACT_RX = re.compile(r"^\s*(CLICK|TYPE|KEY|MOVE|DRAG|SCROLL)\b(.*)$", re.I)


def do_action(a):
    """'CLICK 322 440' -> thuc hien tren X11. Tra ve (ok, mo ta)."""
    if not a:
        return False, "empty"
    m = ACT_RX.match(a)
    if not m:
        return False, "unparsed:%s" % a[:40]
    verb = m.group(1).upper()
    rest = m.group(2).strip()
    if verb == "CLICK":
        p = rest.split()
        if len(p) < 2:
            return False, "click need 2 nums"
        return True, act_click(p[0], p[1])
    if verb == "MOVE":
        p = rest.split()
        if len(p) < 2:
            return False, "move need 2 nums"
        return True, act_move(p[0], p[1])
    if verb == "DRAG":
        p = rest.split()
        if len(p) < 4:
            return False, "drag need 4 nums"
        return True, act_drag(p[0], p[1], p[2], p[3])
    if verb == "SCROLL":
        p = rest.split()
        amt = int(p[0]) if p and p[0].lstrip("-").isdigit() else 3
        return True, act_scroll(500, 500, amt)
    if verb == "TYPE":
        return True, act_type(rest)
    if verb == "KEY":
        return True, act_key(rest)
    return False, "unknown verb %s" % verb


# ------------------------------------------------------------------ app
def open_app(url, title=None, extra_env=None):
    """Mo mot app tren display (chromium neu co, fallback xterm/ffplay)."""
    env = {"DISPLAY": DISPLAY}
    if extra_env:
        env.update(extra_env)
    cmd = ("chromium --no-sandbox --disable-gpu --window-size=%d,%d "
           "--window-position=0,0 --kiosk --disable-dev-shm-usage '%s' "
           ">/dev/null 2>&1 &" % (W, H, url))
    sh(cmd, timeout=60, env=env)
    time.sleep(3)
    log("app: %s" % url)


def dom_state(port=9222):
    """Doc trang thai DOM qua Chrome DevTools Protocol (JSON list)."""
    try:
        import urllib.request
        url = "http://127.0.0.1:%d/json" % port
        with urllib.request.urlopen(url, timeout=5) as r:
            tabs = json.loads(r.read().decode("utf-8", "replace"))
        out = []
        for t in tabs:
            ws = t.get("webSocketDebuggerUrl")
            if not ws:
                continue
            out.append({"title": t.get("title"), "url": t.get("url"),
                        "ws": ws})
        return out
    except Exception as e:
        log("dom_state loi: %s" % e)
        return []


if __name__ == "__main__":
    start_display()
    ok = screenshot(os.path.join(WORK, "probe.png"))
    log("screenshot: %s" % ok)
    log("do_action CLICK 500 500 -> %s" % (do_action("CLICK 500 500"),))
    log("DONE")
