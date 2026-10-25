"""selftest_desktop.py - kiem tra DESKTOP-ENV tren Kaggle CPU (0 GPU-quota).

v3: them app THAT + chung minh chuot that (xeyes: con nhin theo tro chuot ->
pixel diff giu 2 vi tri tro chuot = bang chung su kien chuot da toi X server).

Self-contained (Kaggle CHI upload code_file -> phai inline moi thu vien).
"""
import json
import os
import shutil
import subprocess
import time

WORK = "/kaggle/working/desktop"
SHOTS = os.path.join(WORK, "shots")
W, H = 1280, 720
DISPLAY = ":99"


def log(m):
    print("[env] %s" % m, flush=True)


def sh(cmd, timeout=900):
    e = dict(os.environ)
    e["DISPLAY"] = DISPLAY
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, env=e,
                           timeout=timeout)
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
            (p.stderr or b"").decode("utf-8", "replace")
    except Exception as ex:
        return -1, "", str(ex)


def install():
    log("cai dat xvfb/xdotool/imagemagick/x11-apps")
    sh("apt-get update -qq && apt-get install -y -qq xvfb x11-utils "
       "xdotool imagemagick x11-apps xterm >/dev/null 2>&1", timeout=1800)
    for b in ("Xvfb", "xdotool", "import", "xeyes", "xterm"):
        log("  %-9s %s" % (b, "OK" if shutil.which(b) else "THIEU"))


def start_display():
    os.makedirs(SHOTS, exist_ok=True)
    logfile = "/kaggle/working/xvfb.log"
    sh("pkill -f 'Xvfb %s' 2>/dev/null" % DISPLAY)
    sh("nohup Xvfb %s -screen 0 %dx%dx24 -ac +extension GLX +render -noreset "
       "> %s 2>&1 &" % (DISPLAY, W, H, logfile), timeout=60)
    time.sleep(4)
    for i in range(8):
        rc, o, e = sh("xdpyinfo -display %s >/dev/null 2>&1 && echo OK || echo FAIL"
                      % DISPLAY)
        if "OK" in o:
            log("display %s OK" % DISPLAY)
            return True
        time.sleep(2)
    log("display FAIL")
    return False


def shot(path):
    rc, o, e = sh("import -window root %s" % path, timeout=120)
    if rc != 0 or not os.path.exists(path):
        rc, o, e = sh("xwd -root -silent | convert xwd:- %s" % path, timeout=120)
    return os.path.exists(path)


def px(n, total):
    return max(1, min(total - 1, int(round(float(n) / 1000.0 * total))))


def do_action(a):
    """CLICK x y | MOVE x y | DRAG x1 y1 x2 y2 | SCROLL n | TYPE text | KEY name"""
    parts = a.split(" ", 1)
    verb = parts[0].upper()
    rest = parts[1] if len(parts) > 1 else ""
    if verb == "CLICK":
        p = rest.split()
        sh("xdotool mousemove %d %d sleep 0.2 click 1" % (px(p[0], W), px(p[1], H)))
        return "click"
    if verb == "MOVE":
        p = rest.split()
        sh("xdotool mousemove %d %d" % (px(p[0], W), px(p[1], H)))
        return "move"
    if verb == "DRAG":
        p = rest.split()
        sh("xdotool mousemove %d %d mousedown 1 sleep 0.2 mousemove %d %d "
           "sleep 0.2 mouseup 1" % (px(p[0], W), px(p[1], H), px(p[2], W),
                                     px(p[3], H)))
        return "drag"
    if verb == "SCROLL":
        n = int(rest.split()[0]) if rest.split() and \
            rest.split()[0].lstrip("-").isdigit() else 3
        sh("xdotool mousemove 640 360 click %d" % (4 if n < 0 else 5))
        return "scroll"
    if verb == "TYPE":
        sh("xdotool type --delay 15 \"%s\"" % rest.replace('"', '\\"'))
        return "type"
    if verb == "KEY":
        km = {"enter": "Return", "tab": "Tab", "esc": "Escape", "space": "space",
              "up": "Up", "down": "Down", "left": "Left", "right": "Right",
              "backspace": "BackSpace", "delete": "Delete"}
        sh("xdotool key %s" % km.get(rest.lower(), rest))
        return "key"
    return "?"


def pixel_diff(a, b):
    try:
        from PIL import Image, ImageChops
        ia = Image.open(a).convert("RGB")
        ib = Image.open(b).convert("RGB")
        d = ImageChops.difference(ia, ib)
        bbox = d.getbbox()
        n = sum(1 for px_ in d.getdata() if px_ != (0, 0, 0))
        return {"bbox": str(bbox), "n_changed_px": n}
    except Exception as e:
        return {"error": str(e)}


def main():
    os.makedirs(WORK, exist_ok=True)
    install()
    start_display()
    # --- app THAT: xeyes (con nhin theo tro chuot) + xterm nen
    sh("xeyes -geometry %dx%d+0+0 >/dev/null 2>&1 &" % (W, H), timeout=30)
    time.sleep(3)
    rc, o, e = sh("xdotool search --name xeyes | head -3")
    log("xeyes windows: %s" % o.strip()[:80])

    rows = []
    script = ["MOVE 200 200", "MOVE 900 500", "CLICK 900 500", "TYPE hello world",
              "KEY Tab", "KEY Return", "SCROLL 3", "DRAG 300 300 700 500",
              "MOVE 100 600"]
    for i, a in enumerate(script):
        desc = do_action(a)
        time.sleep(0.45)
        p = os.path.join(SHOTS, "step%02d.png" % i)
        ok = shot(p)
        rows.append({"step": i, "action": a, "desc": desc, "shot_ok": ok,
                     "size": os.path.getsize(p) if ok else 0})
        log("step %d %-22s -> %-6s shot=%s %sB" %
            (i, a, desc, ok, rows[-1]["size"]))

    # bang chung chuot THAT: so anh sau MOVE 200,200 voi anh sau MOVE 900,500
    d = pixel_diff(os.path.join(SHOTS, "step00.png"),
                   os.path.join(SHOTS, "step01.png"))
    log("pixel diff (chuot di giua 2 vi tri) = %s" % json.dumps(d))
    d2 = pixel_diff(os.path.join(SHOTS, "step00.png"),
                    os.path.join(SHOTS, "step%02d.png" % (len(script) - 1)))
    log("pixel diff (buoc dau vs cuoi) = %s" % json.dumps(d2))

    summary = {"n_steps": len(rows), "rows": rows, "screen": [W, H],
               "mouse_moved_diff": d, "first_vs_last_diff": d2,
               "mouse_really_works": bool(d.get("n_changed_px", 0) > 50)}
    with open(os.path.join(WORK, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    log("DONE %d steps | mouse_really_works=%s" %
        (len(rows), summary["mouse_really_works"]))


if __name__ == "__main__":
    main()
