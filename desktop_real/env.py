"""env.py - wrapper for a REAL X11 desktop (Xvfb + openbox + native apps).

This module is deliberately small and dependency-free (Python standard
library only). It drives a real X server with xdotool / wmctrl / xclip and
captures the screen with ImageMagick (or xwd/scrot as fallbacks).

Linux/X11 only. Importing this file on Windows or macOS is safe: no X11
command is executed at import time. Functions that need X11 raise
DesktopUnavailable or return a failure value.

Coordinates are absolute screen pixels by default (the screen is 1280x800).
Helpers with a "norm" suffix accept normalized 0..1000 coordinates, which is
the action format used by the older phase14 desktop benchmark.

Typical use:

    import env
    info = env.start_display(wm=True)
    app = env.launch_xterm(cwd="/tmp")
    env.focus_window(app.window)
    env.type_text("echo hello > /tmp/hello.txt")
    env.key("Return")
    env.screenshot("/tmp/shot.png")
    app.close()
    env.stop_display()

ASCII-only source on purpose (Windows cp1252 lesson).
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

IS_LINUX = platform.system() == "Linux"
W = int(os.environ.get("DESKTOP_W", "1280"))
H = int(os.environ.get("DESKTOP_H", "800"))
DEPTH = int(os.environ.get("DESKTOP_DEPTH", "24"))
DISPLAY = os.environ.get("DISPLAY", ":99")
LOG_PATH = os.environ.get("DESKTOP_LOG", "/tmp/ornith_desktop.log")

if IS_LINUX:
    os.environ.setdefault("DISPLAY", DISPLAY)


class DesktopUnavailable(RuntimeError):
    """Raised when a real X11 desktop cannot be used."""


class Run:
    """Small result object returned by sh()."""

    __slots__ = ("rc", "out", "err")

    def __init__(self, rc, out="", err=""):
        self.rc = int(rc)
        self.out = out or ""
        self.err = err or ""

    @property
    def ok(self):
        return self.rc == 0

    def __repr__(self):
        return "Run(rc=%d, out=%r, err=%r)" % (
            self.rc, self.out[-120:], self.err[-120:])


def log(msg):
    """Print a timestamped line and append it to LOG_PATH when possible."""
    line = "[desktop] %s" % msg
    print(line, flush=True)
    if IS_LINUX and LOG_PATH:
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
        except Exception:
            pass


_RUNTIME = None


def _runtime_dir():
    """Return a private XDG_RUNTIME_DIR (GTK and dbus like having one)."""
    global _RUNTIME
    if _RUNTIME:
        return _RUNTIME
    uid = os.getuid() if hasattr(os, "getuid") else 0
    path = os.path.join("/tmp", "ornith-runtime-%d" % uid)
    try:
        os.makedirs(path, mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    except Exception:
        path = "/tmp"
    _RUNTIME = path
    return path


def _env(extra=None):
    """Environment for every child process; DISPLAY is always set."""
    env = dict(os.environ)
    env["DISPLAY"] = DISPLAY
    env.setdefault("NO_AT_BRIDGE", "1")
    env.setdefault("GDK_BACKEND", "x11")
    if IS_LINUX:
        env.setdefault("XDG_RUNTIME_DIR", _runtime_dir())
    if extra:
        for key, value in extra.items():
            if value is not None:
                env[str(key)] = str(value)
    return env


def _decode(data):
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", "replace")
    return str(data)


def sh(args, timeout=30, input=None, cwd=None, env=None, shell=False):
    """Run a command and return Run(rc, stdout, stderr).

    This helper never raises for a missing binary or a timeout. Callers can
    inspect rc: 127 means "command not found", 124 means "timeout".
    """
    if isinstance(input, str):
        input = input.encode("utf-8")
    try:
        proc = subprocess.run(
            args, shell=shell, cwd=cwd, env=_env(env), input=input,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return Run(proc.returncode, _decode(proc.stdout), _decode(proc.stderr))
    except FileNotFoundError as exc:
        return Run(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return Run(124, _decode(exc.stdout),
                   "timeout after %ss" % timeout)
    except Exception as exc:
        return Run(1, "", "%s: %s" % (type(exc).__name__, exc))


def which(name):
    return shutil.which(name)


def require_linux():
    if not IS_LINUX:
        raise DesktopUnavailable(
            "a real X11 desktop requires Linux (current: %s)"
            % platform.system())


def _display_num(display):
    return str(display or DISPLAY).lstrip(":").split(".")[0]


def display_ready(display=None):
    """True when an X server answers on this display."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    if which("xdotool"):
        res = sh(["xdotool", "getdisplaygeometry"], timeout=5,
                 env={"DISPLAY": disp})
        if res.ok and res.out.strip():
            return True
    if which("xdpyinfo"):
        return sh(["xdpyinfo", "-display", disp], timeout=5).ok
    return False


def display_size(display=None):
    """Return (width, height) of the X screen, or the configured default."""
    disp = display or DISPLAY
    if which("xdotool"):
        res = sh(["xdotool", "getdisplaygeometry"], timeout=5,
                 env={"DISPLAY": disp})
        match = re.search(r"(\d+)\s+(\d+)", res.out)
        if match:
            return int(match.group(1)), int(match.group(2))
    if which("xdpyinfo"):
        res = sh(["xdpyinfo", "-display", disp], timeout=5)
        match = re.search(r"dimensions:\s+(\d+)x(\d+)", res.out)
        if match:
            return int(match.group(1)), int(match.group(2))
    return W, H


def _lock_pid(display):
    path = "/tmp/.X%s-lock" % _display_num(display)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return int(fh.read().strip())
    except Exception:
        return None


def _cmdline(pid):
    try:
        with open("/proc/%d/cmdline" % int(pid), "rb") as fh:
            data = fh.read()
        return data.replace(b"\0", b" ").decode("utf-8", "replace")
    except Exception:
        return ""


def _pids_for_display(comm, display=None):
    """PIDs whose comm is `comm` and whose environment has our DISPLAY."""
    if not IS_LINUX:
        return []
    disp = display or DISPLAY
    res = sh(["pgrep", "-x", comm], timeout=5)
    pids = []
    needle = ("DISPLAY=%s" % disp).encode("utf-8")
    for token in res.out.split():
        try:
            pid = int(token)
        except ValueError:
            continue
        try:
            with open("/proc/%d/environ" % pid, "rb") as fh:
                env_parts = fh.read().split(b"\0")
        except Exception:
            continue
        if needle in env_parts:
            pids.append(pid)
    return pids


def _terminate(pid, timeout=3.0):
    """SIGTERM a PID, then SIGKILL if it does not exit."""
    if not IS_LINUX or int(pid) <= 1:
        return False
    try:
        os.kill(int(pid), signal.SIGTERM)
    except ProcessLookupError:
        return True
    except Exception:
        return False
    end = time.time() + timeout
    while time.time() < end:
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return True
        except Exception:
            return False
        time.sleep(0.1)
    try:
        os.kill(int(pid), signal.SIGKILL)
    except Exception:
        pass
    return True


def _tail(path, lines=25):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return "".join(fh.readlines()[-lines:]).strip()
    except Exception:
        return ""


def start_display(width=None, height=None, depth=None, display=None,
                  wm=True, vnc=False, timeout=15):
    """Start Xvfb (if needed), openbox and an optional x11vnc.

    Returns a dict with ok/display/width/height/reused/wm. Never raises on
    Windows; the caller gets {"ok": False, "error": ...}.
    """
    global W, H, DEPTH, DISPLAY
    if not IS_LINUX:
        return {"ok": False, "platform": platform.system(),
                "error": "Linux/X11 only"}
    disp = display or DISPLAY
    width = int(width or W)
    height = int(height or H)
    depth = int(depth or DEPTH)
    DISPLAY = disp
    os.environ["DISPLAY"] = disp
    reused = display_ready(disp)
    xvfb_pid = None
    if not reused:
        xvfb = which("Xvfb")
        if not xvfb:
            return {"ok": False, "display": disp,
                    "error": "Xvfb not installed (run setup_linux.sh)"}
        lock = "/tmp/.X%s-lock" % _display_num(disp)
        old_pid = _lock_pid(disp)
        if old_pid and "Xvfb" in _cmdline(old_pid):
            log("Xvfb lock exists for pid %s; waiting for it" % old_pid)
        else:
            try:
                os.remove(lock)
            except FileNotFoundError:
                pass
            except Exception:
                pass
        log_path = "/tmp/ornith_xvfb%s.log" % _display_num(disp)
        cmd = [xvfb, disp, "-screen", "0",
               "%dx%dx%d" % (width, height, depth), "-ac",
               "-nolisten", "tcp", "-dpi", "96", "-noreset"]
        try:
            with open(log_path, "ab") as fh:
                proc = subprocess.Popen(
                    cmd, stdout=fh, stderr=subprocess.STDOUT, env=_env(),
                    start_new_session=True)
            xvfb_pid = proc.pid
        except Exception as exc:
            return {"ok": False, "display": disp,
                    "error": "cannot start Xvfb: %s" % exc}
        end = time.time() + max(3, int(timeout))
        while time.time() < end:
            if display_ready(disp):
                break
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        if not display_ready(disp):
            return {"ok": False, "display": disp,
                    "error": "X display did not start",
                    "log": _tail(log_path)}
        log("Xvfb %s started (pid %s)" % (disp, xvfb_pid))
    else:
        log("X display %s already running" % disp)

    W, H = display_size(disp)
    DEPTH = depth
    os.environ["DISPLAY"] = disp

    wm_info = {"ok": True, "name": "", "reused": True}
    if wm:
        wm_info = start_openbox(disp)
        if not wm_info.get("ok"):
            return {"ok": False, "display": disp, "reused": reused,
                    "xvfb_pid": xvfb_pid,
                    "error": "openbox failed: %s" % wm_info.get("error"),
                    "log": wm_info.get("log", "")}

    ensure_dbus()
    vnc_info = start_vnc(disp) if vnc else None
    return {"ok": True, "display": disp, "width": W, "height": H,
            "depth": DEPTH, "reused": reused, "xvfb_pid": xvfb_pid,
            "wm": wm_info.get("name", ""), "wm_reused": wm_info.get("reused"),
            "vnc": vnc_info}


def wm_name(display=None):
    """Name of the running window manager, or an empty string."""
    if not IS_LINUX:
        return ""
    res = sh(["wmctrl", "-m"], timeout=5,
             env={"DISPLAY": display or DISPLAY})
    if not res.ok:
        return ""
    for line in res.out.splitlines():
        if line.lower().startswith("name:"):
            return line.split(":", 1)[1].strip()
    return res.out.strip()


def start_openbox(display=None):
    """Start openbox on this display if no WM is registered."""
    if not IS_LINUX:
        return {"ok": False, "error": "Linux/X11 only"}
    disp = display or DISPLAY
    name = wm_name(disp)
    if name:
        return {"ok": True, "name": name, "reused": True}
    openbox = which("openbox")
    if not openbox:
        return {"ok": False, "error": "openbox not installed"}
    log_path = "/tmp/ornith_openbox.log"
    try:
        with open(log_path, "ab") as fh:
            proc = subprocess.Popen(
                [openbox, "--sm-disable"], stdout=fh,
                stderr=subprocess.STDOUT, env=_env({"DISPLAY": disp}),
                start_new_session=True)
    except Exception as exc:
        return {"ok": False, "error": "cannot start openbox: %s" % exc}
    end = time.time() + 10
    while time.time() < end:
        name = wm_name(disp)
        if name:
            log("openbox started on %s (pid %s)" % (disp, proc.pid))
            return {"ok": True, "name": name, "pid": proc.pid,
                    "reused": False}
        if proc.poll() is not None:
            break
        time.sleep(0.2)
    return {"ok": False, "error": "openbox did not register a WM",
            "log": _tail(log_path), "pid": proc.pid}


_DBUS_TRIED = False


def ensure_dbus():
    """Start a session bus if the environment does not already have one."""
    global _DBUS_TRIED
    if not IS_LINUX:
        return False
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        return True
    if _DBUS_TRIED:
        return False
    _DBUS_TRIED = True
    launcher = which("dbus-launch")
    if launcher:
        res = sh([launcher, "--sh-syntax"], timeout=10,
                 env={"DISPLAY": DISPLAY})
        if res.ok:
            match = re.search(r"DBUS_SESSION_BUS_ADDRESS='([^']+)'", res.out)
            if match:
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = match.group(1)
                pid_match = re.search(r"DBUS_SESSION_BUS_PID=(\d+)", res.out)
                if pid_match:
                    os.environ["DBUS_SESSION_BUS_PID"] = pid_match.group(1)
                log("dbus session bus started")
                return True
    daemon = which("dbus-daemon")
    if daemon:
        res = sh([daemon, "--session", "--fork", "--print-address=1",
                  "--print-pid=1"], timeout=10)
        lines = [line.strip() for line in res.out.splitlines() if line.strip()]
        if res.ok and lines:
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = lines[0]
            if len(lines) > 1:
                os.environ["DBUS_SESSION_BUS_PID"] = lines[1]
            log("dbus-daemon session bus started")
            return True
    log("warning: no dbus session bus (GTK apps may print warnings)")
    return False


def start_vnc(display=None, port=5900, local=True):
    """Best-effort x11vnc; localhost-only by default (use an SSH tunnel)."""
    if not IS_LINUX:
        return {"ok": False, "error": "Linux/X11 only"}
    disp = display or DISPLAY
    vnc = which("x11vnc")
    if not vnc:
        return {"ok": False, "error": "x11vnc not installed"}
    if _pids_for_display("x11vnc", disp):
        return {"ok": True, "reused": True, "port": port, "local": local}
    cmd = [vnc, "-display", disp, "-forever", "-shared", "-nopw",
           "-rfbport", str(port), "-bg", "-o", "/tmp/ornith_x11vnc.log"]
    if local:
        cmd.append("-localhost")
    res = sh(cmd, timeout=10)
    return {"ok": res.ok, "port": port, "local": local,
            "error": "" if res.ok else res.err.strip()[:200]}


APP_COMMS = ["xterm", "gedit", "pcmanfm", "thunar", "galculator",
             "soffice.bin", "soffice", "libreoffice", "oosplash", "xclip"]


def stop_apps(names=None, display=None):
    """Kill known benchmark apps on this display (not the WM or Xvfb)."""
    if not IS_LINUX:
        return {"ok": False, "error": "Linux/X11 only", "killed": []}
    disp = display or DISPLAY
    killed = []
    for name in (names or APP_COMMS):
        for pid in _pids_for_display(name, disp):
            if _terminate(pid):
                killed.append((name, pid))
    return {"ok": True, "killed": killed}


def stop_display(display=None, stop_wm=True, stop_vnc=True, apps=True):
    """Stop apps, openbox, x11vnc and the Xvfb server for this display."""
    if not IS_LINUX:
        return {"ok": False, "error": "Linux/X11 only", "killed": []}
    disp = display or DISPLAY
    killed = []
    if apps:
        killed.extend(stop_apps(display=disp).get("killed", []))
    if stop_vnc:
        for pid in _pids_for_display("x11vnc", disp):
            if _terminate(pid):
                killed.append(("x11vnc", pid))
    if stop_wm:
        for pid in _pids_for_display("openbox", disp):
            if _terminate(pid):
                killed.append(("openbox", pid))
    lock_pid = _lock_pid(disp)
    if lock_pid and "Xvfb" in _cmdline(lock_pid):
        if _terminate(lock_pid):
            killed.append(("Xvfb", lock_pid))
    else:
        for pid in _pids_for_display("Xvfb", disp):
            if _terminate(pid):
                killed.append(("Xvfb", pid))
    time.sleep(0.3)
    for path in ("/tmp/.X%s-lock" % _display_num(disp),
                 "/tmp/.X11-unix/X%s" % _display_num(disp)):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    return {"ok": True, "killed": killed}


def window_list(display=None):
    """Return visible windows as dicts (id, desktop, pid, geometry, class)."""
    if not IS_LINUX:
        return []
    disp = display or DISPLAY
    res = sh(["wmctrl", "-l", "-p", "-G", "-x"], timeout=8,
             env={"DISPLAY": disp})
    windows = []
    if res.ok:
        for line in res.out.splitlines():
            parts = line.split(None, 9)
            if len(parts) < 10:
                continue
            try:
                windows.append({
                    "id": int(parts[0], 16),
                    "hex": parts[0],
                    "desktop": int(parts[1]),
                    "pid": int(parts[2]),
                    "x": int(parts[3]),
                    "y": int(parts[4]),
                    "w": int(parts[5]),
                    "h": int(parts[6]),
                    "host": parts[7],
                    "wm_class": parts[8],
                    "title": parts[9],
                })
            except ValueError:
                continue
        return windows
    if which("xdotool"):
        res = sh(["xdotool", "search", "--onlyvisible", "--name", ".*"],
                 timeout=8, env={"DISPLAY": disp})
        for token in res.out.split():
            try:
                wid = int(token)
            except ValueError:
                continue
            geo = window_geometry(wid, disp) or {}
            name = sh(["xdotool", "getwindowname", str(wid)], timeout=5,
                      env={"DISPLAY": disp}).out.strip()
            windows.append({
                "id": wid, "hex": "0x%08x" % wid, "desktop": -1,
                "pid": None, "x": geo.get("x", 0), "y": geo.get("y", 0),
                "w": geo.get("w", 0), "h": geo.get("h", 0),
                "host": "", "wm_class": "", "title": name,
            })
    return windows


def find_windows(name=None, wm_class=None, title=None, display=None):
    """Filter window_list() by regex on name (title/class), class or title."""
    found = []
    for win in window_list(display):
        if wm_class and not re.search(wm_class, win.get("wm_class", ""),
                                      re.I):
            continue
        if title and not re.search(title, win.get("title", ""), re.I):
            continue
        if name:
            hay = "%s %s" % (win.get("title", ""), win.get("wm_class", ""))
            if not re.search(name, hay, re.I):
                continue
        found.append(win)
    return found


def wait_for_window(name=None, wm_class=None, title=None, timeout=20,
                    display=None, poll=0.25):
    """Poll until a matching window appears; return its dict or None."""
    end = time.time() + max(0.1, float(timeout))
    while time.time() < end:
        found = find_windows(name=name, wm_class=wm_class, title=title,
                             display=display)
        if found:
            return found[0]
        time.sleep(poll)
    return None


def _win_id(win):
    if isinstance(win, dict):
        win = win.get("id")
    if isinstance(win, int):
        return win
    text = str(win).strip()
    if text.lower().startswith("0x"):
        return int(text, 16)
    return int(text)


def active_window(display=None):
    """Return the active window dict, or None."""
    if not IS_LINUX:
        return None
    disp = display or DISPLAY
    res = sh(["xdotool", "getactivewindow"], timeout=5,
             env={"DISPLAY": disp})
    if not res.ok:
        return None
    try:
        wid = int(res.out.strip())
    except ValueError:
        return None
    title = sh(["xdotool", "getwindowname", str(wid)], timeout=5,
               env={"DISPLAY": disp}).out.strip()
    wm_class = ""
    for win in window_list(disp):
        if win.get("id") == wid:
            wm_class = win.get("wm_class", "")
            break
    return {"id": wid, "hex": "0x%08x" % wid, "title": title,
            "wm_class": wm_class}


def focus_window(win, display=None):
    """Activate a window by id; return True when it is active."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    wid = _win_id(win)
    hexid = "0x%08x" % wid
    res = sh(["wmctrl", "-i", "-a", hexid], timeout=8,
             env={"DISPLAY": disp})
    if not res.ok:
        sh(["xdotool", "windowactivate", "--sync", str(wid)], timeout=8,
           env={"DISPLAY": disp})
    time.sleep(0.25)
    active = active_window(disp)
    return bool(active and active.get("id") == wid)


def window_geometry(win, display=None):
    """Return {id,x,y,w,h} for a window, or None."""
    if not IS_LINUX:
        return None
    disp = display or DISPLAY
    wid = _win_id(win)
    res = sh(["xdotool", "getwindowgeometry", "--shell", str(wid)],
             timeout=8, env={"DISPLAY": disp})
    if res.ok:
        values = {}
        for line in res.out.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        try:
            return {"id": wid, "x": int(values["X"]),
                    "y": int(values["Y"]), "w": int(values["WIDTH"]),
                    "h": int(values["HEIGHT"])}
        except (KeyError, ValueError):
            pass
    for win_info in window_list(disp):
        if win_info.get("id") == wid:
            return {"id": wid, "x": win_info["x"], "y": win_info["y"],
                    "w": win_info["w"], "h": win_info["h"]}
    return None


def set_window_geometry(win, x, y, w, h, display=None):
    """Move and resize a window with wmctrl (xdotool fallback)."""
    if not IS_LINUX:
        return {"ok": False, "error": "Linux/X11 only"}
    disp = display or DISPLAY
    wid = _win_id(win)
    hexid = "0x%08x" % wid
    res = sh(["wmctrl", "-i", "-r", hexid, "-e",
              "0,%d,%d,%d,%d" % (int(x), int(y), int(w), int(h))],
             timeout=8, env={"DISPLAY": disp})
    if not res.ok:
        sh(["xdotool", "windowmove", str(wid), str(int(x)), str(int(y))],
           timeout=8, env={"DISPLAY": disp})
        sh(["xdotool", "windowsize", str(wid), str(int(w)), str(int(h))],
           timeout=8, env={"DISPLAY": disp})
    time.sleep(0.35)
    geo = window_geometry(wid, disp)
    return {"ok": bool(geo), "geometry": geo}


def move_window(win, x, y, display=None):
    geo = window_geometry(win, display)
    if not geo:
        return {"ok": False, "error": "window not found"}
    return set_window_geometry(win, x, y, geo["w"], geo["h"], display)


def resize_window(win, w, h, display=None):
    geo = window_geometry(win, display)
    if not geo:
        return {"ok": False, "error": "window not found"}
    return set_window_geometry(win, geo["x"], geo["y"], w, h, display)


def maximize_window(win, display=None):
    """Maximize a window; fallback to an explicit full-screen resize."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    wid = _win_id(win)
    hexid = "0x%08x" % wid
    res = sh(["wmctrl", "-i", "-r", hexid, "-b",
              "add,maximized_vert,maximized_horz"], timeout=8,
             env={"DISPLAY": disp})
    time.sleep(0.4)
    geo = window_geometry(wid, disp)
    width, height = display_size(disp)
    if geo and (geo["w"] < width * 0.8 or geo["h"] < height * 0.8):
        set_window_geometry(wid, 0, 0, width, height, disp)
    return res.ok


def close_window(win, display=None):
    """Ask the WM to close a window; return True when it disappears."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    wid = _win_id(win)
    hexid = "0x%08x" % wid
    sh(["wmctrl", "-i", "-c", hexid], timeout=8, env={"DISPLAY": disp})
    time.sleep(0.5)
    if any(item.get("id") == wid for item in window_list(disp)):
        sh(["xdotool", "windowclose", str(wid)], timeout=8,
           env={"DISPLAY": disp})
        time.sleep(0.5)
    return not any(item.get("id") == wid for item in window_list(disp))


def _is_png(path):
    try:
        if os.path.getsize(path) < 100:
            return False
        with open(path, "rb") as fh:
            return fh.read(8) == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False


def screenshot_size(path):
    """Return (width, height) from a PNG header, or None."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
            return None
        return (int.from_bytes(head[16:20], "big"),
                int.from_bytes(head[20:24], "big"))
    except Exception:
        return None


def screenshot(path, window=None, display=None, timeout=20):
    """Capture the root window (or one window) to a PNG file."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    if which("import"):
        target = "root" if window is None else str(_win_id(window))
        sh(["import", "-window", target, path], timeout=timeout,
           env={"DISPLAY": disp})
        if _is_png(path):
            return True
    if which("xwd"):
        converter = which("convert") or which("magick")
        if converter:
            try:
                producer = subprocess.Popen(
                    ["xwd", "-root", "-silent"], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, env=_env({"DISPLAY": disp}))
                consumer = subprocess.Popen(
                    [converter, "xwd:-", path], stdin=producer.stdout,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env=_env())
                producer.stdout.close()
                consumer.communicate(timeout=timeout)
                producer.wait(timeout=5)
                if _is_png(path):
                    return True
            except Exception:
                pass
    if which("scrot"):
        sh(["scrot", "-o", path], timeout=timeout,
           env={"DISPLAY": disp})
        if _is_png(path):
            return True
    return False


KEY_ALIASES = {
    "enter": "Return", "return": "Return", "esc": "Escape",
    "escape": "Escape", "tab": "Tab", "space": "space",
    "backspace": "BackSpace", "delete": "Delete", "del": "Delete",
    "insert": "Insert", "home": "Home", "end": "End",
    "pageup": "Page_Up", "page_up": "Page_Up", "prior": "Prior",
    "pagedown": "Page_Down", "page_down": "Page_Down", "next": "Next",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "menu": "Menu", "print": "Print", "pause": "Pause",
    "capslock": "Caps_Lock", "numlock": "Num_Lock",
}

MOD_ALIASES = {
    "ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift",
    "super": "super", "meta": "super", "win": "super", "cmd": "super",
}


def _normalize_key(name):
    text = str(name).strip()
    if not text:
        return ""
    parts = text.split("+")
    out = []
    for index, part in enumerate(parts):
        value = part.strip()
        if index < len(parts) - 1:
            out.append(MOD_ALIASES.get(value.lower(), value.lower()))
        else:
            out.append(KEY_ALIASES.get(value.lower(), value))
    return "+".join(out)


def key(name, display=None):
    """Press one key or a combination such as ctrl+a / alt+F4."""
    if not IS_LINUX:
        return False
    combo = _normalize_key(name)
    if not combo:
        return False
    res = sh(["xdotool", "key", "--clearmodifiers", combo], timeout=8,
             env={"DISPLAY": display or DISPLAY})
    return res.ok


def hotkey(*keys):
    return key("+".join(str(item) for item in keys))


def key_down(name, display=None):
    if not IS_LINUX:
        return False
    combo = _normalize_key(name)
    return sh(["xdotool", "keydown", "--clearmodifiers", combo], timeout=8,
              env={"DISPLAY": display or DISPLAY}).ok


def key_up(name, display=None):
    if not IS_LINUX:
        return False
    combo = _normalize_key(name)
    return sh(["xdotool", "keyup", "--clearmodifiers", combo], timeout=8,
              env={"DISPLAY": display or DISPLAY}).ok


def move(x, y, display=None):
    """Move the pointer to absolute screen coordinates."""
    if not IS_LINUX:
        return False
    return sh(["xdotool", "mousemove", str(int(round(float(x)))),
               str(int(round(float(y))))], timeout=5,
              env={"DISPLAY": display or DISPLAY}).ok


def click(x, y, button=1, clicks=1, display=None):
    """Click at absolute screen coordinates."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    if not move(x, y, disp):
        return False
    time.sleep(0.08)
    res = sh(["xdotool", "click", "--clearmodifiers",
              "--repeat", str(max(1, int(clicks))), "--delay", "80",
              str(int(button))], timeout=10, env={"DISPLAY": disp})
    return res.ok


def double_click(x, y, display=None):
    return click(x, y, clicks=2, display=display)


def right_click(x, y, display=None):
    return click(x, y, button=3, display=display)


def drag(x1, y1, x2, y2, duration=0.5, button=1, display=None):
    """Press, move in small steps and release (real drag-and-drop)."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    x1, y1, x2, y2 = [int(round(float(v))) for v in (x1, y1, x2, y2)]
    if not move(x1, y1, disp):
        return False
    time.sleep(0.1)
    if not sh(["xdotool", "mousedown", str(int(button))], timeout=5,
              env={"DISPLAY": disp}).ok:
        return False
    try:
        steps = max(4, int(float(duration) / 0.05))
        for index in range(1, steps + 1):
            x = x1 + (x2 - x1) * index // steps
            y = y1 + (y2 - y1) * index // steps
            sh(["xdotool", "mousemove", str(x), str(y)], timeout=5,
               env={"DISPLAY": disp})
            time.sleep(float(duration) / steps)
    finally:
        released = sh(["xdotool", "mouseup", str(int(button))], timeout=5,
                      env={"DISPLAY": disp}).ok
    return released


def scroll(x, y, amount, horizontal=False, display=None):
    """Scroll at a point. Positive amount = down/right."""
    if not IS_LINUX:
        return False
    disp = display or DISPLAY
    amount = int(amount)
    if amount == 0:
        return True
    if horizontal:
        button = 7 if amount > 0 else 6
    else:
        button = 5 if amount > 0 else 4
    if not move(x, y, disp):
        return False
    return sh(["xdotool", "click", "--clearmodifiers",
               "--repeat", str(abs(amount)), "--delay", "40",
               str(button)], timeout=10, env={"DISPLAY": disp}).ok


def _type_one_line(text, delay=12, display=None):
    disp = display or DISPLAY
    args = ["xdotool", "type", "--delay", str(max(1, int(delay))),
            "--clearmodifiers", "--", text]
    res = sh(args, timeout=max(10, len(text) // 8 + 5),
             env={"DISPLAY": disp})
    if res.ok:
        return True
    if not text.startswith("-"):
        res = sh(["xdotool", "type", "--delay", str(max(1, int(delay))),
                  "--clearmodifiers", text],
                 timeout=max(10, len(text) // 8 + 5),
                 env={"DISPLAY": disp})
    return res.ok


def type_text(text, delay=12, display=None):
    """Type text with xdotool. Newlines become Return; tabs become Tab."""
    if not IS_LINUX:
        return False
    text = str(text)
    if not text:
        return True
    disp = display or DISPLAY
    lines = text.split("\n")
    for line_index, line in enumerate(lines):
        chunks = line.split("\t")
        for chunk_index, chunk in enumerate(chunks):
            if chunk and not _type_one_line(chunk, delay, disp):
                log("type_text failed at line %d" % line_index)
                return False
            if chunk_index < len(chunks) - 1 and not key("Tab", disp):
                return False
        if line_index < len(lines) - 1 and not key("Return", disp):
            return False
    return True


def paste_text(text, display=None):
    """Put text on the clipboard and press ctrl+v."""
    return clipboard_set(text, display) and key("ctrl+v", display)


def clipboard_set(text, display=None):
    if not IS_LINUX:
        return False
    xclip = which("xclip")
    if not xclip:
        return False
    return sh([xclip, "-selection", "clipboard", "-i"], timeout=5,
              input=str(text).encode("utf-8"),
              env={"DISPLAY": display or DISPLAY}).ok


def clipboard_get(display=None, timeout=5):
    if not IS_LINUX:
        return ""
    xclip = which("xclip")
    if not xclip:
        return ""
    res = sh([xclip, "-selection", "clipboard", "-o"], timeout=timeout,
             env={"DISPLAY": display or DISPLAY})
    return res.out if res.ok else ""


def clipboard_wait(contains=None, timeout=5, display=None):
    end = time.time() + max(0.1, float(timeout))
    while time.time() < end:
        text = clipboard_get(display)
        if text and (contains is None or contains in text):
            return text
        time.sleep(0.2)
    return ""


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def write_text(path, text):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(str(text))


def wait_for_file(path, timeout=10, contains=None, poll=0.2):
    end = time.time() + max(0.1, float(timeout))
    while time.time() < end:
        if os.path.isfile(path):
            if contains is None:
                return True
            if contains in read_text(path):
                return True
        time.sleep(poll)
    return False


def norm_to_px(x, y):
    """Convert normalized 0..1000 coordinates to screen pixels."""
    return (max(1, min(W - 1, int(round(float(x) / 1000.0 * W)))),
            max(1, min(H - 1, int(round(float(y) / 1000.0 * H)))))


_ACTION_RE = re.compile(
    r"^\s*(CLICKN|CLICK|MOVE|DRAG|SCROLL|TYPE|KEY|WAIT|PASTE|DONE)\b(.*)$",
    re.I)


def do_action(action):
    """Execute a compact action string; return (ok, description).

    Supported:
      CLICK x y [button]       absolute pixels
      CLICKN x y [button]      normalized 0..1000
      MOVE x y
      DRAG x1 y1 x2 y2
      SCROLL n                 at screen centre
      SCROLL x y n
      TYPE text
      KEY ctrl+a
      WAIT seconds
      PASTE text
      DONE
    """
    if not action:
        return False, "empty action"
    match = _ACTION_RE.match(str(action))
    if not match:
        return False, "unparsed: %s" % str(action)[:60]
    verb = match.group(1).upper()
    rest = match.group(2)
    if rest.startswith(" "):
        rest = rest[1:]
    try:
        if verb in ("CLICK", "CLICKN"):
            parts = rest.split()
            if len(parts) < 2:
                return False, "click needs x y"
            x, y = float(parts[0]), float(parts[1])
            if verb == "CLICKN":
                x, y = norm_to_px(x, y)
            button = int(parts[2]) if len(parts) > 2 else 1
            return click(x, y, button), "click(%d,%d,b%d)" % (x, y, button)
        if verb == "MOVE":
            parts = rest.split()
            if len(parts) < 2:
                return False, "move needs x y"
            return move(parts[0], parts[1]), "move(%s,%s)" % (
                parts[0], parts[1])
        if verb == "DRAG":
            parts = rest.split()
            if len(parts) < 4:
                return False, "drag needs x1 y1 x2 y2"
            ok = drag(*parts[:4])
            return ok, "drag(%s)" % ",".join(parts[:4])
        if verb == "SCROLL":
            parts = rest.split()
            if len(parts) >= 3:
                x, y, amount = float(parts[0]), float(parts[1]), int(parts[2])
            else:
                amount = int(parts[0]) if parts else 3
                x, y = W // 2, H // 2
            return scroll(x, y, amount), "scroll(%d)" % amount
        if verb == "TYPE":
            return type_text(rest), "type(%s)" % rest[:40]
        if verb == "KEY":
            return key(rest.strip()), "key(%s)" % rest.strip()
        if verb == "WAIT":
            time.sleep(max(0.0, float(rest.strip() or "0.5")))
            return True, "wait(%s)" % rest.strip()
        if verb == "PASTE":
            return paste_text(rest), "paste(%s)" % rest[:40]
        if verb == "DONE":
            return True, "done"
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, exc)
    return False, "unknown action"


class App:
    """A launched native application and its main window."""

    def __init__(self, name, pid, window, cmd, log_path, proc=None):
        self.name = name
        self.pid = pid
        self.window = window
        self.cmd = cmd
        self.log_path = log_path
        self.proc = proc

    def close(self, force=True):
        """Close the window, then terminate the process tree if needed."""
        if self.window:
            close_window(self.window)
        time.sleep(0.4)
        alive = bool(self.proc and self.proc.poll() is None)
        if alive or force:
            if self.proc and self.proc.poll() is None:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
            elif self.pid:
                _terminate(self.pid, timeout=2)
        return True

    def __repr__(self):
        return "App(%s, pid=%s, window=%s)" % (
            self.name, self.pid,
            ("0x%08x" % self.window) if self.window else None)


def launch_app(cmd, name=None, cwd=None, env_extra=None, wait=True,
               wait_name=None, wait_class=None, wait_title=None,
               timeout=20, require_window=True):
    """Launch a native app and wait for its first window.

    Raises DesktopUnavailable when the binary cannot start or when a
    required window does not appear. The app log is /tmp/ornith_app_<name>.log.
    """
    require_linux()
    if not display_ready():
        raise DesktopUnavailable("X display %s is not ready" % DISPLAY)
    name = name or os.path.basename(str(cmd[0]))
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name))
    log_path = "/tmp/ornith_app_%s.log" % safe_name
    try:
        with open(log_path, "wb") as fh:
            proc = subprocess.Popen(
                [str(item) for item in cmd], cwd=cwd,
                env=_env(env_extra), stdout=fh, stderr=subprocess.STDOUT,
                start_new_session=True)
    except Exception as exc:
        raise DesktopUnavailable("cannot launch %s: %s" % (name, exc))
    window = None
    if wait:
        found = wait_for_window(name=wait_name, wm_class=wait_class,
                                title=wait_title, timeout=timeout)
        if found:
            window = found["id"]
        elif require_window:
            tail = _tail(log_path)
            try:
                proc.terminate()
            except Exception:
                pass
            raise DesktopUnavailable(
                "window for %s not found in %ss (log: %s)"
                % (name, timeout, tail[-400:]))
    return App(name, proc.pid, window, cmd, log_path, proc)


def launch_xterm(cwd=None, title="OrnithTerm", geometry="100x30+40+40",
                 timeout=20):
    """Launch xterm with a plain bash (no user rc files)."""
    xterm = which("xterm")
    if not xterm:
        raise DesktopUnavailable("xterm not installed")
    base = [xterm, "-title", title, "-geometry", geometry,
            "-bg", "black", "-fg", "white", "-e",
            "bash", "--noprofile", "--norc"]
    try:
        return launch_app(
            [xterm, "-title", title, "-geometry", geometry,
             "-fa", "DejaVu Sans Mono", "-fs", "12",
             "-bg", "black", "-fg", "white", "-e",
             "bash", "--noprofile", "--norc"],
            name="xterm", cwd=cwd, wait_class="xterm", timeout=timeout)
    except DesktopUnavailable:
        return launch_app(base, name="xterm", cwd=cwd,
                          wait_class="xterm", timeout=timeout)


def launch_gedit(path=None, timeout=25):
    """Launch gedit in a new window, optionally with a file."""
    gedit = which("gedit")
    if not gedit:
        raise DesktopUnavailable("gedit not installed")
    cmd = [gedit, "--new-window"]
    if path:
        cmd.append(str(path))
    return launch_app(cmd, name="gedit", wait_class="gedit",
                      env_extra={"GSETTINGS_BACKEND": "memory"},
                      timeout=timeout)


def file_manager_binary():
    """Return (path, name) for pcmanfm or thunar, or (None, None)."""
    pcmanfm = which("pcmanfm")
    if pcmanfm:
        return pcmanfm, "pcmanfm"
    thunar = which("thunar")
    if thunar:
        return thunar, "thunar"
    return None, None


def launch_file_manager(path=None, timeout=25):
    """Launch pcmanfm (preferred) or thunar at a directory."""
    binary, name = file_manager_binary()
    if not binary:
        raise DesktopUnavailable("pcmanfm/thunar not installed")
    if name == "pcmanfm":
        cmd = [binary, "--no-desktop"]
        if path:
            cmd.append(str(path))
    else:
        cmd = [binary]
        if path:
            cmd.append(str(path))
    return launch_app(cmd, name=name, wait_class="pcmanfm|thunar",
                      timeout=timeout)


def launch_calculator(timeout=20):
    """Launch galculator."""
    calc = which("galculator")
    if not calc:
        raise DesktopUnavailable("galculator not installed")
    return launch_app([calc], name="galculator",
                      wait_class="galculator|calculator", timeout=timeout)


def launch_writer(path=None, timeout=90):
    """Launch LibreOffice Writer with an isolated user profile."""
    binary = which("libreoffice") or which("soffice")
    if not binary:
        raise DesktopUnavailable("LibreOffice not installed")
    profile = os.environ.get("LO_PROFILE", "/tmp/ornith_lo_profile")
    cmd = [binary, "--writer", "--norestore", "--nologo",
           "-env:UserInstallation=file://%s" % profile]
    if path:
        cmd.append(str(path))
    return launch_app(cmd, name="writer", wait_class="libreoffice|soffice",
                      wait_title="LibreOffice Writer|Writer",
                      timeout=timeout)


def preflight():
    """Check binaries, display and WM; return a JSON-friendly dict."""
    tools = {}
    for name in ("Xvfb", "openbox", "xdotool", "wmctrl", "xclip",
                 "import", "convert", "xwd", "xdpyinfo", "scrot",
                 "xterm", "gedit", "pcmanfm", "thunar", "galculator",
                 "libreoffice", "soffice", "pdftotext", "x11vnc"):
        tools[name] = which(name)
    required = ["Xvfb", "openbox", "xdotool", "wmctrl", "xclip"]
    missing = [name for name in required if not tools.get(name)]
    if not tools.get("import") and not tools.get("xwd"):
        missing.append("import|xwd")
    ready = display_ready()
    wm = wm_name() if ready else ""
    width, height = display_size() if ready else (W, H)
    return {
        "platform": platform.system(),
        "linux": IS_LINUX,
        "display": DISPLAY,
        "display_ready": ready,
        "width": width,
        "height": height,
        "wm": wm,
        "tools": tools,
        "missing": missing,
        "ok": bool(IS_LINUX and ready and wm and not missing),
    }


def _json_print(obj):
    print(json.dumps(obj, indent=1, sort_keys=True))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Real X11 desktop helper (Xvfb + openbox + xdotool).")
    parser.add_argument("--check", action="store_true",
                        help="print tools/display/WM as JSON")
    parser.add_argument("--start", action="store_true",
                        help="start Xvfb and openbox")
    parser.add_argument("--stop", action="store_true",
                        help="stop apps, WM and Xvfb")
    parser.add_argument("--screenshot", default=None,
                        help="capture a PNG and exit")
    parser.add_argument("--windows", action="store_true",
                        help="list windows and exit")
    parser.add_argument("--launch", default=None,
                        choices=["xterm", "gedit", "filemanager",
                                 "calculator", "writer"])
    parser.add_argument("--display", default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--vnc", action="store_true")
    args = parser.parse_args(argv)

    if not IS_LINUX:
        _json_print({"ok": False, "platform": platform.system(),
                     "error": "Linux/X11 only"})
        return 2
    if args.display:
        globals()["DISPLAY"] = args.display
        os.environ["DISPLAY"] = args.display
    if args.check:
        _json_print(preflight())
        return 0 if preflight().get("ok") else 1
    if args.stop:
        _json_print(stop_display())
        return 0
    if args.start:
        _json_print(start_display(width=args.width, height=args.height,
                                  vnc=args.vnc))
        return 0
    if args.screenshot:
        ok = screenshot(args.screenshot)
        _json_print({"ok": ok, "path": args.screenshot,
                     "size": screenshot_size(args.screenshot)})
        return 0 if ok else 1
    if args.windows:
        _json_print(window_list())
        return 0
    if args.launch:
        if args.launch == "xterm":
            app = launch_xterm()
        elif args.launch == "gedit":
            app = launch_gedit()
        elif args.launch == "filemanager":
            app = launch_file_manager("/tmp")
        elif args.launch == "calculator":
            app = launch_calculator()
        else:
            app = launch_writer()
        _json_print({"ok": True, "app": repr(app),
                     "window": app.window, "pid": app.pid})
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



