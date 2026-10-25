"""proof_real.py - end-to-end proof of the REAL X11 desktop.

Steps:
  1. start Xvfb :99 (1280x800x24) and openbox
  2. launch xterm
  3. type: echo REAL_DESKTOP > /tmp/ornith_real.txt
  4. wait, take a screenshot, verify the file content
  5. print PASS or FAIL

No GPU, model, browser or network is needed at run time. On Windows the
script exits with SKIP (exit code 2) instead of crashing.

Usage on Colab/Kaggle:
    python desktop_real/proof_real.py --setup
    python desktop_real/proof_real.py            # setup already done
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import env  # noqa: E402  (local file, same directory)

TARGET = "/tmp/ornith_real.txt"
COMMAND = "echo REAL_DESKTOP > %s" % TARGET


def log(msg):
    print("[proof] %s" % msg, flush=True)


def _tail(path, lines=20):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return "".join(fh.readlines()[-lines:]).strip()
    except Exception:
        return ""


def run_setup():
    script = os.path.join(HERE, "setup_linux.sh")
    if not os.path.isfile(script):
        return False, "setup_linux.sh not found next to proof_real.py"
    log("running setup_linux.sh --minimal (apt + Xvfb + openbox)")
    try:
        proc = subprocess.run(
            ["bash", script, "--minimal"], capture_output=True, text=True,
            timeout=1800)
    except Exception as exc:
        return False, "setup failed to start: %s" % exc
    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if output:
        print(output[-3000:], flush=True)
    if proc.returncode != 0:
        return False, "setup_linux.sh exited with %d" % proc.returncode
    return True, "setup OK"


def collect_logs(app):
    logs = {}
    for name, path in (
            ("xvfb", "/tmp/ornith_xvfb99.log"),
            ("openbox", "/tmp/ornith_openbox.log"),
            ("app", app.log_path if app else "")):
        if path:
            text = _tail(path)
            if text:
                logs[name] = text
    return logs


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prove a real X11 desktop with xterm and a file write.")
    parser.add_argument("--setup", action="store_true",
                        help="run setup_linux.sh --minimal first")
    parser.add_argument("--out", default="/tmp/ornith_proof")
    parser.add_argument("--display", default=None)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--keep", action="store_true",
                        help="keep xterm/display for manual inspection")
    args = parser.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    report_path = os.path.join(args.out, "proof.json")
    report = {
        "ok": False,
        "platform": platform.system(),
        "display": args.display or env.DISPLAY,
        "command": COMMAND,
        "target": TARGET,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if not env.IS_LINUX:
        report["error"] = "Linux/X11 only"
        log("SKIP: real X11 desktop requires Linux (current: %s)"
            % platform.system())
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
        return 2

    if args.setup:
        ok, detail = run_setup()
        if not ok:
            report["error"] = detail
            log("FAIL: %s" % detail)
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=1, sort_keys=True)
            return 1

    missing = [name for name in ("Xvfb", "openbox", "xdotool", "wmctrl")
               if not env.which(name)]
    if missing:
        report["error"] = "missing tools: %s" % ", ".join(missing)
        log("FAIL: missing %s" % ", ".join(missing))
        log("hint: bash %s/setup_linux.sh" % HERE.replace("\\", "/"))
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
        return 2

    app = None
    info = {}
    started_here = False
    try:
        info = env.start_display(
            width=args.width, height=args.height,
            display=args.display, wm=True)
        report["display_info"] = info
        if not info.get("ok"):
            report["error"] = info.get("error", "display start failed")
            log("FAIL: %s" % report["error"])
            if info.get("log"):
                log(info["log"][-1500:])
            return 1
        started_here = not info.get("reused", False)
        log("display %s %dx%d wm=%s (%s)" % (
            info.get("display"), info.get("width"), info.get("height"),
            info.get("wm"), "reused" if info.get("reused") else "started"))

        if os.path.exists(TARGET):
            os.remove(TARGET)
        if os.path.exists(TARGET):
            report["error"] = "cannot remove old %s" % TARGET
            log("FAIL: %s" % report["error"])
            return 1

        app = env.launch_xterm(
            cwd="/tmp", title="OrnithProof", geometry="100x30+40+40",
            timeout=20)
        report["xterm_window"] = "0x%08x" % app.window if app.window else None
        log("xterm window %s (pid %s)" % (report["xterm_window"], app.pid))

        env.focus_window(app.window)
        env.click(400, 300)
        time.sleep(1.0)

        before = os.path.join(args.out, "before.png")
        before_ok = env.screenshot(before)
        report["screenshot_before"] = before if before_ok else None

        log("typing: %s" % COMMAND)
        if not env.type_text(COMMAND):
            report["error"] = "xdotool type failed"
            log("FAIL: %s" % report["error"])
            return 1
        env.key("Return")

        found = env.wait_for_file(TARGET, timeout=args.timeout,
                                  contains="REAL_DESKTOP")
        content = env.read_text(TARGET).strip()
        report["file_found"] = bool(found)
        report["file_content"] = content

        after = os.path.join(args.out, "after.png")
        after_ok = env.screenshot(after)
        size = env.screenshot_size(after) if after_ok else None
        report["screenshot_after"] = after if after_ok else None
        report["screenshot_size"] = list(size) if size else None

        windows = env.window_list()
        xterm_windows = [win for win in windows
                         if win.get("id") == app.window]
        report["xterm_windows"] = len(xterm_windows)
        report["active_window"] = env.active_window()

        checks = {
            "file_exists": os.path.isfile(TARGET),
            "file_content_ok": content == "REAL_DESKTOP",
            "screenshot_ok": bool(after_ok and size),
            "xterm_window_ok": bool(xterm_windows),
        }
        report["checks"] = checks
        report["ok"] = all(checks.values())
        report["logs"] = collect_logs(app)

        log("file content: %r" % content)
        log("screenshot: %s size=%s" % (
            after if after_ok else "FAILED", size))
        log("checks: %s" % json.dumps(checks, sort_keys=True))
        if report["ok"]:
            log("PASS")
            return 0
        report["error"] = "one or more checks failed"
        log("FAIL: %s" % report["error"])
        return 1
    except Exception as exc:
        report["error"] = "%s: %s" % (type(exc).__name__, exc)
        report["logs"] = collect_logs(app)
        log("FAIL: %s" % report["error"])
        return 1
    finally:
        report["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(report_path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=1, sort_keys=True)
        except Exception:
            pass
        if app is not None and not args.keep:
            try:
                app.close(force=True)
            except Exception:
                pass
        if started_here and not args.keep:
            try:
                env.stop_display()
            except Exception:
                pass
        log("report: %s" % report_path)


if __name__ == "__main__":
    raise SystemExit(main())
