"""Probe khoa hoc: Blender portable + headless tren Kaggle.

- Tai Blender 4.2.23 LTS linux-x64 (~350MB) tu download.blender.org
- Chay `blender --background --python make_cube.py`:
  tao cube + vat lieu vang kim + camera + sun, export GLB, render Cycles CPU 384px
- Verify: file ton tai + size + triangle count

Neu probe nay xanh -> t2 (script-as-action cho 3D) khoa thi.
"""
import os
import shutil
import subprocess
import tarfile
import time
import urllib.request

BVER = "4.2.23"
SERIES = BVER.rsplit(".", 1)[0]   # "4.2" — thu muc release theo series
NAME = f"blender-{BVER}-linux-x64"
URLS = [
    f"https://ftp.nluug.nl/pub/graphics/blender/release/"
    f"Blender{SERIES}/{NAME}.tar.xz",
    f"https://ftp.halifax.rwth-aachen.de/blender/release/"
    f"Blender{SERIES}/{NAME}.tar.xz",
    f"https://download.blender.org/release/Blender{SERIES}/{NAME}.tar.xz",
]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TMP = "/tmp/blender"
BLENDER = os.path.join(TMP, NAME, "blender")
OUT = "/kaggle/working/out_blender"


def log(m):
    print(f"[blend] {m}", flush=True)


def download(tarball):
    last = None
    for url in URLS:
        try:
            log(f"tai {url}")
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                with open(tarball, "wb") as f:
                    shutil.copyfileobj(r, f)
            sz = os.path.getsize(tarball)
            if sz > 100e6:
                log(f"  OK {sz / 1e6:.0f}MB")
                return
            last = f"file nho bat thuong ({sz}B)"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            log(f"  fail: {last}")
    raise RuntimeError(f"tai Blender that bai: {last}")


def get_blender():
    if os.path.exists(BLENDER):
        log("blender da co san")
        return
    os.makedirs(TMP, exist_ok=True)
    tarball = os.path.join(TMP, "blender.tar.xz")
    if not os.path.exists(tarball) or os.path.getsize(tarball) < 100e6:
        download(tarball)
    log(f"giai nen {os.path.getsize(tarball) / 1e6:.0f}MB")
    with tarfile.open(tarball) as tf:
        tf.extractall(TMP)


SCRIPT = r'''
import bpy, os, math

out = os.environ["BLEND_OUT"]
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
cube = bpy.context.active_object
cube.name = "MyCube"

mat = bpy.data.materials.new("Gold")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.9, 0.7, 0.2, 1.0)
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.35
cube.data.materials.append(mat)

world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.85, 0.9, 1.0)
scene.world = world

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
cam.location = (6.5, -6.5, 4.5)
tgt = bpy.data.objects.new("Target", None)
scene.collection.objects.link(tgt)
tgt.location = (0, 0, 1)
con = cam.constraints.new("TRACK_TO")
con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.camera = cam

sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 4.0
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))

glb = os.path.join(out, "cube.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")

scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.resolution_x = 384
scene.render.resolution_y = 384
png = os.path.join(out, "cube_render.png")
scene.render.filepath = png
bpy.ops.render.render(write_still=True)

tris = sum(len(p.vertices) - 2 for p in cube.data.polygons)
print("VERIFY_GLB", os.path.exists(glb),
      os.path.getsize(glb) if os.path.exists(glb) else -1, flush=True)
print("VERIFY_PNG", os.path.exists(png),
      os.path.getsize(png) if os.path.exists(png) else -1, flush=True)
print("VERIFY_TRIS", tris, flush=True)
print("VERIFY_OK", flush=True)
'''


def main():
    t0 = time.time()
    get_blender()
    os.makedirs(OUT, exist_ok=True)
    sp = os.path.join(TMP, "make_cube.py")
    with open(sp, "w") as f:
        f.write(SCRIPT)
    log("chay blender --background")
    env = dict(os.environ)
    env["BLEND_OUT"] = OUT
    r = subprocess.run([BLENDER, "--background", "--factory-startup",
                        "--python", sp],
                       capture_output=True, text=True, env=env)
    for line in (r.stdout or "").strip().splitlines()[-25:]:
        log(f"  {line}")
    if r.returncode != 0:
        log(f"stderr tail: {(r.stderr or '')[-800:]}")
    log(f"rc={r.returncode} t={time.time() - t0:.0f}s")
    log("files: " + ", ".join(sorted(os.listdir(OUT))))


if __name__ == "__main__":
    main()
