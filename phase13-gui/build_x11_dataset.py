"""build_x11_dataset.py - kernel CPU (internet ON) tai cac GOI .deb cua X11 tools
(xvfb, x11-utils, xdotool, imagemagick) + deps -> zip ra output.
Sau do toi upload zip do lam dataset 'khoadangnguye/ornith-gui-xdotool' de kernel
GPU (internet OFF) cai duoc offline.
"""
import json
import os
import subprocess

CODE = r'''"""build_x11_dataset.py - tai .deb cua X11 tools (offline cho kernel GPU)."""
import os
import shutil
import subprocess
import zipfile

WORK = "/kaggle/working/x11"
DL = os.path.join(WORK, "debs")
OUT = "/kaggle/working/x11_bundle.zip"
PKGS = ["xvfb", "x11-utils", "xdotool", "imagemagick", "x11-apps"]


def sh(c, timeout=1800):
    p = subprocess.run(c, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, (p.stdout or "")[-1500:], (p.stderr or "")[-1500:]


os.makedirs(DL, exist_ok=True)
rc, o, e = sh("apt-get update -qq")
print("apt update rc", rc, e[-200:], flush=True)
# tai .deb + deps
rc, o, e = sh("apt-get install --download-only -y --reinstall %s" %
              " ".join(PKGS))
print("download rc", rc, e[-300:], flush=True)
# doi cac .deb vao thu muc
n = 0
for root, _d, files in os.walk("/var/cache/apt/archives"):
    for f in files:
        if f.endswith(".deb"):
            shutil.copy2(os.path.join(root, f), os.path.join(DL, f))
            n += 1
print("so .deb:", n, flush=True)
if n == 0:
    # fallback: apt-get download truc tiep
    sh("cd %s && apt-get download %s" % (DL, " ".join(PKGS)))
    n = len([f for f in os.listdir(DL) if f.endswith(".deb")])
    print("fallback download ->", n, flush=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(DL)):
        if f.endswith(".deb"):
            z.write(os.path.join(DL, f), f)
print("X11 bundle:", OUT, os.path.getsize(OUT) / 1e6, "MB", flush=True)
print("DONE", flush=True)
'''

D = "phase13-gui/kernel_x11_bundle"
os.makedirs(D, exist_ok=True)
with open(os.path.join(D, "build_x11_dataset.py"), "w", encoding="utf-8",
          newline="\n") as fh:
    fh.write(CODE)
md = {
    "code_file": "build_x11_dataset.py",
    "competition_sources": [],
    "dataset_sources": [],
    "enable_gpu": False,
    "enable_internet": True,
    "enable_tpu": False,
    "id": "khoadangnguye/ornith-x11-bundle",
    "is_private": True,
    "kernel_sources": [],
    "kernel_type": "script",
    "language": "python",
    "model_sources": [],
    "title": "ornith-x11-bundle",
}
json.dump(md, open(os.path.join(D, "kernel-metadata.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=2)
print("da tao", D, "->", md["id"])
