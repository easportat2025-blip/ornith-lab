# -*- coding: utf-8 -*-
"""build_xdotool_bundle.py - KERNEL CPU tren Kaggle: build bundle xdotool
offline (plan B cho desktop-bench).

Ly do: desktop-bench can xdotool de dieu kenh chuot/ban phim THAT vao app
X11. Image Kaggle CO Xvfb nhung THIEU xdotool; apt-get tren Kaggle treo do
DNS (security.ubuntu.com fail) => 38' GPU slot/run. Kernel nay (CPU, co
internet) tao bundle xdotool + libXdo OFFLINE, de desktop-bench khong can
apt lai.

Output: /kaggle/working/xdotool_bundle.zip (binary + lib + manifest)
Chay:  python scripts/build_xdotool_bundle.py --push
ASCII-only source.
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile

OUT = "/kaggle/working/xdotool_bundle"
APT_OPTS = ("-o Acquire::Retries=0 -o Acquire::http::Timeout=20 "
            "-o Acquire::https::Timeout=20")


def sh(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 1, "EXC %s" % e


def log(*a):
    print("[xdo]", *a, flush=True)


def apt_repair():
    """security.ubuntu.com -> archive.ubuntu.com (DNS fail tren Kaggle)."""
    for f in ("/etc/apt/sources.list",):
        if os.path.exists(f):
            sh("sed -i 's/security.ubuntu.com/archive.ubuntu.com/g' %s" % f)
    for d in ("/etc/apt/sources.list.d",):
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.endswith(".list") or fn.endswith(".sources"):
                    sh("sed -i 's/security.ubuntu.com/archive.ubuntu.com/g' "
                       "%s/%s" % (d, fn))
    sh("sed -i 's|security.ubuntu.com|archive.ubuntu.com|g' "
       "/etc/apt/sources.list.d/*.sources 2>/dev/null")
    log("sources patched")
    rc, out = sh("grep -rh '^deb ' /etc/apt/sources.list /etc/apt/sources.list.d/ "
                 "2>/dev/null | head -5")
    log("sources now:", out.strip()[:300])


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "bin"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "lib"), exist_ok=True)
    apt_repair()

    log("apt-get update ...")
    rc, out = sh("apt-get update %s" % APT_OPTS, timeout=300)
    log("update rc=%s | %s" % (rc, out.strip()[-200:].replace("\n", " ")))

    log("apt-get install xdotool ...")
    rc, out = sh("DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "
                 "%s xdotool" % APT_OPTS, timeout=600)
    log("install rc=%s | %s" % (rc, out.strip()[-300:].replace("\n", " ")))
    xd = shutil.which("xdotool")
    if not xd:
        # fallback: tai .deb roi giai nen
        log("fallback: apt-get download ...")
        sh("mkdir -p /tmp/debs && cd /tmp/debs && "
           "apt-get download %s xdotool libxdo3" % APT_OPTS, timeout=300)
        for d in sorted(os.listdir("/tmp/debs")):
            if d.endswith(".deb"):
                sh("dpkg-deb -x /tmp/debs/%s /tmp/xdo" % d)
        xd = "/tmp/xdo/usr/bin/xdotool"
        if not os.path.exists(xd):
            log("FAIL: khong lay duoc xdotool")
            sh("echo BUILD_FAIL > /kaggle/working/xdotool_status.txt")
            return 1
    log("xdotool:", xd)

    # copy binary + thu vien rieng (libXdo)
    shutil.copy2(xd, os.path.join(OUT, "bin", "xdotool"))
    os.chmod(os.path.join(OUT, "bin", "xdotool"), 0o755)
    libs = []
    for d in ("/usr/lib", "/lib", "/tmp/xdo/usr/lib", "/tmp/xdo/lib"):
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in files:
                if f.startswith("libXdo.so"):
                    src = os.path.join(root, f)
                    dst = os.path.join(OUT, "lib", f)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        libs.append(f)
    log("libs:", libs)

    # kiem thu vien can them (ldd) - phai co san trong image
    rc, ldd = sh("ldd %s" % os.path.join(OUT, "bin", "xdotool"), timeout=60)
    missing = [l for l in ldd.splitlines() if "not found" in l]
    log("ldd missing:", missing[:10] if missing else "none")

    # smoke: chay xdotool --version
    rc, ver = sh("%s --version" % os.path.join(OUT, "bin", "xdotool"), timeout=60)
    log("xdotool --version rc=%s | %s" % (rc, ver.strip()[:120]))

    man = {"xdotool": os.path.basename(xd),
           "libs": libs,
           "ldd_missing": missing,
           "version": ver.strip()[:200],
           "install_rc": rc}
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1)
    zp = "/kaggle/working/xdotool_bundle.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.join("xdotool_bundle",
                                        os.path.relpath(p, OUT)))
    log("wrote", zp, os.path.getsize(zp), "bytes")
    with open("/kaggle/working/xdotool_status.txt", "w") as fh:
        fh.write("OK\n" if (not missing and rc == 0) else "PARTIAL\n")
    print("BUILD_DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
