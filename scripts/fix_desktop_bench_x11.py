# -*- coding: utf-8 -*-
"""fix_desktop_bench_x11.py - apt install trong env.py inline qua nang (fluxbox)
-> timeout -> X khong bat duoc -> kernel ERROR.

Sua: bo fluxbox (khong can), them --no-install-recommends, timeout 1200 -> 2700.
Ap dung: 2 kernel desktop-bench (A/B) + env.py local.
"""
import io

OLD = 'apt-get update -qq && apt-get install -y -qq xvfb x11-utils "'
NEW = ('apt-get update -qq && apt-get install -y -qq --no-install-recommends '
       'xvfb x11-utils "')
# (trong file inline, chuoi duoc escape)
OLD_ESC = OLD.replace('"', '\\"')
NEW_ESC = NEW.replace('"', '\\"')

for p in ["phase13-gui/kernel_desktop_bench_a/desktop_bench_kernel.py",
          "phase13-gui/kernel_desktop_bench_b/desktop_bench_kernel.py",
          "phase14-desktop/env.py"]:
    try:
        s = io.open(p, encoding="utf-8").read()
    except Exception as e:
        print("skip", p, e)
        continue
    o = s
    s = s.replace(OLD_ESC, NEW_ESC).replace(OLD, NEW)
    s = s.replace("imagemagick fluxbox >/dev/null 2>&1\", timeout=1200)",
                  "imagemagick >/dev/null 2>&1\", timeout=2700)")
    s = s.replace("imagemagick fluxbox >/dev/null 2>&1\", timeout=1200)",
                  "imagemagick >/dev/null 2>&1\", timeout=2700)")
    s = s.replace("xdotool imagemagick fluxbox >/dev/null 2>&1\", timeout=1200)",
                  "xdotool imagemagick >/dev/null 2>&1\", timeout=2700)")
    if s != o:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("patched", p)
    else:
        print("khong doi", p)
