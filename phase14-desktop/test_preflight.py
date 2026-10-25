"""Unit test cho lop guard X11 moi trong harness.py (GLM, 22/10).

Vay: log that out_desktop_bench cho thay desktop-env chet 2 lan:
  - pgrep tu khop => Xvfb chua chay (chromium: 'Missing X server')
  - thieu imagemagick/x11-apps => 'import: not found | xwd: not found'
=> harness.py them ensure_x11() / ensure_display() / preflight().

Test nay khong can X11 that, khong can GPU, khong can key: gia lap
shutil.which + env.sh.

Dung: python phase14-desktop/test_preflight.py
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ENV_WORK", os.path.join(HERE, "_t_preflight"))

import harness  # noqa: E402
import env  # noqa: E402

FAILED = []


def check(name, cond, extra=""):
    print("  %s %s%s" % ("ok  " if cond else "FAIL", name,
                         ("" if cond else "  <- " + extra)))
    if not cond:
        FAILED.append(name)


# ---------------------------------------------------------------- helpers
class FakeWhich:
    def __init__(self, present):
        self.present = set(present)

    def __call__(self, b):
        return "/usr/bin/" + b if b in self.present else None


def with_fake(monkey, present_tools, x_ok):
    """Gia lap shutil.which + env.sh cho 1 trong hai trang thai."""
    real_which = harness.shutil.which
    real_sh = env.sh
    harness.shutil.which = FakeWhich(present_tools)
    calls = []

    def fake_sh(cmd, timeout=300, env=None):
        calls.append(cmd)
        if "xdpyinfo" in cmd:
            return (0, "OK\n" if x_ok else "NO\n", "")
        if "apt-get install" in cmd:
            return (0, "Setting up imagemagick...\n", "")
        if "apt-get update" in cmd:
            return (0, "Hit:1 http://deb.debian.org\n", "")
        if "Xvfb" in cmd:
            return (0, "", "")
        return (0, "", "")

    env.sh = fake_sh
    return calls, real_which, real_sh


def restore(real_which, real_sh):
    harness.shutil.which = real_which
    env.sh = real_sh


ALL_TOOLS = set(harness.X11_TOOLS) | {"Xvfb"}
NO_TOOLS = set()

print("== 1) moi truong DAY DU (tools co, X chay) ==")
calls, rw, rs = with_fake(None, ALL_TOOLS, True)
try:
    ok_tools = harness.ensure_x11(log=lambda m: None)
    ok_disp = harness.ensure_display(log=lambda m: None)
finally:
    restore(rw, rs)
check("ensure_x11 True khi tools co", ok_tools is True)
check("ensure_display True khi X chay", ok_disp is True)
check("khong goi apt khi tools du", not any("apt-get install" in c for c in calls))

print("== 2) thieu tools (phai cai, co log) ==")
calls, rw, rs = with_fake(None, NO_TOOLS, True)
try:
    ok_tools = harness.ensure_x11(log=lambda m: None)
finally:
    restore(rw, rs)
check("ensure_x11 False khi cai that bai", ok_tools is False)
check("co goi 'apt-get install'", any("apt-get install" in c for c in calls))
check("co goi 'apt-get update'",
      any("apt-get" in c and "update" in c for c in calls))
check("co goi 'x11-apps' (xwd)", any("x11-apps" in c for c in calls))
check("co goi 'imagemagick' (import)", any("imagemagick" in c for c in calls))

print("== 3) X chay duoc (tool co) ==")
# xdpyinfo tra "NO" truoc khi co lenh bat Xvfb, "OK" sau do (gia lap that)
started = {"v": False}
real_which, real_sh = harness.shutil.which, env.sh
calls = []


def fake_sh3(cmd, timeout=300, env=None):
    calls.append(cmd)
    if "xdpyinfo" in cmd:
        return (0, ("OK\n" if started["v"] else "NO\n"), "")
    if "Xvfb" in cmd:
        started["v"] = True
        return (0, "", "")
    return (0, "", "")


harness.shutil.which = FakeWhich(ALL_TOOLS)
env.sh = fake_sh3
try:
    ok_disp = harness.ensure_display(log=lambda m: None)
finally:
    harness.shutil.which = real_which
    env.sh = real_sh
check("ensure_display True (da bat Xvfb roi)", ok_disp is True)
check("co lenh bat Xvfb", any("Xvfb" in c for c in calls))
check("verify bang xdpyinfo (khong pgrep)",
      any("xdpyinfo" in c for c in calls) and
      not any("pgrep" in c for c in calls))

print("== 4) X bat khong duoc -> preflight phai fail RO RANG ==")
calls, rw, rs = with_fake(None, ALL_TOOLS, False)
try:
    # gia lap: env.sh luon tra NO cho xdpyinfo va "khong co Xvfb binary"
    def fake_sh(cmd, timeout=300, env=None):
        if "xdpyinfo" in cmd:
            return (0, "NO\n", "")
        if "Xvfb" in cmd:
            return (1, "", "not found")
        return (0, "", "")

    env.sh = fake_sh
    harness.shutil.which = FakeWhich(set())
    msg = ""
    try:
        harness.preflight(log=lambda m: None)
    except SystemExit as e:
        msg = str(e)
finally:
    restore(rw, rs)
check("preflight raise SystemExit", msg != "", msg[:80])
check("thong diep nhac X server", "X server" in msg, msg[:120])

print("== 5) anh chup that -> preflight fail ==")
calls, rw, rs = with_fake(None, ALL_TOOLS, True)
real_find = harness.find_browser
try:
    env.sh = lambda cmd, timeout=300, env=None: (0, "OK\n" if "xdpyinfo" in cmd else "", "")
    harness.shutil.which = FakeWhich(ALL_TOOLS)
    harness.find_browser = lambda: None      # vo du phong chup qua CDP
    real_shot = env.screenshot
    env.screenshot = lambda p: False
    msg = ""
    try:
        harness.preflight(log=lambda m: None)
    except SystemExit as e:
        msg = str(e)
    finally:
        env.screenshot = real_shot
finally:
    harness.find_browser = real_find
    restore(rw, rs)
check("preflight raise SystemExit khi khong chup duoc anh", msg != "", msg[:80])
check("thong diep nhac anh chup", "chup" in msg or "anh" in msg, msg[:120])

print()
if FAILED:
    print("FAILED: %d -> %s" % (len(FAILED), FAILED))
    sys.exit(1)
print("ALL PREFLIGHT TESTS PASSED")
