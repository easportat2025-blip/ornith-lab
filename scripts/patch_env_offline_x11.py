# -*- coding: utf-8 -*-
"""patch_env_offline_x11.py - env.py: khi co dataset 'ornith-gui-xdotool'
(kernel GPU internet OFF) thi cai X11 tools bang dpkg -i thay vi apt-get.

Ap dung: env.py local + ban INLINE trong 3 kernel desktop-bench.
"""
import io

# (cau cai, thay the) - khop ca ban inline (escape) va ban thuong
OLD_PLAIN = '''    if not shutil.which("Xvfb"):
        log("thieu Xvfb -> cai dat")
        sh("apt-get update -qq && apt-get install -y -qq --no-install-recommends xvfb x11-utils "
           "xdotool imagemagick >/dev/null 2>&1", timeout=2700)'''
NEW_PLAIN = '''    if not shutil.which("Xvfb"):
        log("thieu Xvfb -> cai dat")
        debs = None
        # FIX 22/10 (MiMo): Kaggle mount dataset theo HAI layout:
        #   cua CHINH acc dang chay voi: /kaggle/input/<owner>/<slug>  (1 cap)
        #   cua acc KHAC (public):       /kaggle/input/datasets/<owner>/<slug> (2 cap)
        # Bundle xdotool thuoc acc A nhung kernel split B thuoc acc B => noi
        # dung 2 cap => tim 1 cap se KHONG thay => apt lai chay (30') va fail.
        roots = []
        for base in ("/kaggle/input",):
            roots += [base + "/datasets/*/ornith-gui-xdotool",
                      base + "/*/ornith-gui-xdotool",
                      base + "/ornith-gui-xdotool",
                      base + "/*/*/ornith-gui-xdotool"]
        import glob as _g
        for pat in roots:
            for root in sorted(_g.glob(pat)):
                if os.path.isdir(root):
                    debs = sorted(_g.glob(root + "/*.deb"))
                    if debs:
                        log("cai offline tu %d file .deb (%s)" % (len(debs), root))
                        break
            if debs:
                break
        if debs:
            sh("dpkg -i %s >/dev/null 2>&1 || apt-get -f install -y "
               ">/dev/null 2>&1" % " ".join(debs), timeout=2700)
        else:
            sh("apt-get update -qq && apt-get install -y -qq --no-install-recommends xvfb x11-utils "
               "xdotool imagemagick >/dev/null 2>&1", timeout=2700)'''

OLD_ESC = OLD_PLAIN.replace('"', '\\"')
NEW_ESC = NEW_PLAIN.replace('"', '\\"')


def esc(t):
    return t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


TARGETS = [
    "phase14-desktop/env.py",
    "phase13-gui/kernel_desktop_bench_a/desktop_bench_kernel.py",
    "phase13-gui/kernel_desktop_bench_b/desktop_bench_kernel.py",
    "phase13-gui/kernel_desktop_bench_smoke/desktop_bench_kernel.py",
    "phase13-gui/kernel_desktop_bench/desktop_bench_kernel.py",
]
for p in TARGETS:
    try:
        s = io.open(p, encoding="utf-8").read()
    except Exception as e:
        print("skip", p, e)
        continue
    o = s
    if OLD_ESC in s:
        s = s.replace(OLD_ESC, NEW_ESC)
    elif OLD_PLAIN in s:
        s = s.replace(OLD_PLAIN, NEW_PLAIN)
    else:
        print("!! khong khop cau cai trong", p)
        continue
    if s != o:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("patched", p)
