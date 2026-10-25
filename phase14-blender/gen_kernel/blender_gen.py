"""Demo A data-gen: instruction -> bpy script, verify bang Blender headless.

- Tai Blender 4.2.23 portable (mirror NLUUG + UA) — y het probe v3 da xanh.
- Sinh cap (instruction, script bpy hoan chinh) tu bo task tham so hoa:
  primitive / transform / material / compound / modifier.
- Chay TUNG script bang 1 tien trinh Blender rieng (isolate + timeout 240s).
- Verify doc lap: rc=0 + VERIFY_OK + parse GLB (meshes>0, tris>0) + render png.
- Xuat /kaggle/working/blend_gen: rows.jsonl (task PASS), failures.jsonl,
  renders/, glb/, summary.json.

Y tuong xuong duoi: harness nay CHINH LA verifier cho vong tu-luyen
(model de xuat script -> chay -> verify -> giu ban PASS lam data).
"""
import json
import math
import os
import random
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
WORK = "/kaggle/working/blend_gen"
TASKS_DIR = "/tmp/gen_tasks"
OUT_DIR = "/tmp/gen_out"
VARIANTS = 3
TIMEOUT = 240


def log(m):
    print(f"[gen] {m}", flush=True)


# ---------------------------------------------------------------- Blender
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


# ---------------------------------------------------------------- template
PREFIX = '''import bpy, math, os

out = os.environ["BLEND_OUT"]
os.makedirs(out, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def mat(name, color, metallic=0.0, rough=0.5, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    if emit > 0.0:
        b.inputs["Emission Color"].default_value = (color[0], color[1],
                                                    color[2], 1.0)
        b.inputs["Emission Strength"].default_value = emit
    return m

'''

TAIL = '''
world = bpy.data.worlds.new("World")
world.use_nodes = True
bgn = world.node_tree.nodes["Background"]
bgn.inputs[0].default_value = (0.85, 0.87, 0.92, 1.0)
scene.world = world

cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam.location = (9.5, -9.5, 6.5)
tgt = bpy.data.objects.new("Target", None)
scene.collection.objects.link(tgt)
tgt.location = (0.0, 0.0, 1.6)
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

glb = os.path.join(out, "scene.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")

scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.resolution_x = 320
scene.render.resolution_y = 320
png = os.path.join(out, "render.png")
scene.render.filepath = png
bpy.ops.render.render(write_still=True)

meshes = [o for o in bpy.data.objects if o.type == "MESH"]
tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
print("VERIFY_N_MESH", len(meshes), flush=True)
print("VERIFY_TRIS", tris, flush=True)
print("VERIFY_GLB", os.path.exists(glb),
      os.path.getsize(glb) if os.path.exists(glb) else -1, flush=True)
print("VERIFY_PNG", os.path.exists(png),
      os.path.getsize(png) if os.path.exists(png) else -1, flush=True)
print("VERIFY_OK", flush=True)
'''


# ---------------------------------------------------------------- emitters
PALETTE = [
    ("red", (0.80, 0.10, 0.10)),
    ("blue", (0.15, 0.35, 0.85)),
    ("green", (0.15, 0.70, 0.25)),
    ("yellow", (0.90, 0.75, 0.10)),
    ("purple", (0.50, 0.20, 0.75)),
    ("orange", (0.90, 0.50, 0.10)),
    ("cyan", (0.10, 0.70, 0.80)),
    ("white", (0.90, 0.90, 0.90)),
    ("brown", (0.45, 0.30, 0.15)),
    ("pink", (0.90, 0.50, 0.65)),
]


def fmt(v):
    if isinstance(v, (tuple, list)):
        return "(" + ", ".join(fmt(x) for x in v) + ")"
    return f"{float(v):.4g}"


def mdef(var, color, metallic=0.0, rough=0.5, emit=0.0):
    c = fmt(color)
    return (f'{var} = mat("{var}", {c}, metallic={metallic:.3g}, '
            f"rough={rough:.3g}, emit={emit:.3g})")


def add(shape, s, loc, mvar, name, rot=None, scale=None, depth=None):
    kw = {"cube": "(size={s}, location={loc})",
          "sphere": ("(segments=32, ring_count=16, radius={s}, "
                     "location={loc})"),
          "cylinder": "(vertices=32, radius={s}, depth={d}, location={loc})",
          "cone": "(vertices=32, radius1={s}, depth={d}, location={loc})",
          "torus": ("(major_segments=48, minor_segments=12, major_radius={s}, "
                    "minor_radius={d}, location={loc})"),
          "plane": "(size={s}, location={loc})"}[shape]
    d = depth if depth is not None else (0.48 if shape == "torus" else s)
    ops = {"cube": "primitive_cube_add", "sphere": "primitive_uv_sphere_add",
           "cylinder": "primitive_cylinder_add", "cone": "primitive_cone_add",
           "torus": "primitive_torus_add", "plane": "primitive_plane_add"}[shape]
    code = (f"bpy.ops.mesh.{ops}" + kw.format(s=fmt(s), d=fmt(d),
                                              loc=fmt(loc)) + "\n")
    code += "o = bpy.context.active_object\n"
    code += f'o.name = "{name}"\n'
    code += f"o.data.materials.append({mvar})\n"
    if rot:
        code += f"o.rotation_euler = {rot}\n"
    if scale:
        code += f"o.scale = {fmt(scale)}\n"
    return code


def rotz(deg):
    return f"(0.0, 0.0, math.radians({fmt(deg)}))"


# ---------------------------------------------------------------- tasks
def t_cube(pal, rng):
    c = pal[0]
    s = rng.choice([1.5, 2.0, 2.6])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", s, (0.0, 0.0, round(s / 2 + 0.01, 3)), "m0", "Cube")
    return f"Create a {c[0]} cube with size {s} at the origin.", code


def t_sphere(pal, rng):
    c = pal[0]
    r = rng.choice([0.8, 1.2, 1.6])
    code = mdef("m0", c[1]) + "\n"
    code += add("sphere", r, (0.0, 0.0, r), "m0", "Sphere")
    return f"Create a {c[0]} sphere with radius {r}.", code


def t_cylinder(pal, rng):
    c = pal[0]
    r = rng.choice([0.5, 0.8])
    code = mdef("m0", c[1]) + "\n"
    code += add("cylinder", r, (0.0, 0.0, 1.0), "m0", "Cylinder", depth=2.0)
    return f"Create a {c[0]} cylinder with radius {r} and height 2.", code


def t_cone(pal, rng):
    c = pal[0]
    r = rng.choice([1.0, 1.4])
    code = mdef("m0", c[1]) + "\n"
    code += add("cone", r, (0.0, 0.0, 1.0), "m0", "Cone", depth=2.0)
    return f"Create a {c[0]} cone with base radius {r} and height 2.", code


def t_torus(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("torus", 1.2, (0.0, 0.0, 0.5), "m0", "Torus")
    return f"Create a {c[0]} torus with major radius 1.2 and minor 0.48.", code


def t_plane(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1], rough=0.9) + "\n"
    code += add("plane", 4.0, (0.0, 0.0, 0.0), "m0", "Plane")
    return f"Create a {c[0]} plane with size 4 lying flat at the origin.", code


def t_moved(pal, rng):
    c = pal[0]
    x = rng.choice([1.5, 2.2])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 1.6, (x, 0.0, 0.81), "m0", "Cube")
    return f"Create a {c[0]} cube with size 1.6 moved {x} units along X.", code


def t_rotated(pal, rng):
    c = pal[0]
    deg = rng.choice([45, 30, 60])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.01), "m0", "Cube", rot=rotz(deg))
    return f"Create a {c[0]} cube with size 2 rotated {deg} degrees around Z.", code


def t_scaled(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 0.51), "m0", "Cube",
                scale=(2.0, 1.0, 0.5))
    return f"Create a {c[0]} cube scaled to (2, 1, 0.5).", code


def t_stack3(pal, rng):
    c0 = pal[0]
    code = mdef("m0", c0[1]) + "\n"
    code += add("cube", 1.2, (0.0, 0.0, 0.61), "m0", "Cube1")
    code += add("cube", 1.2, (0.0, 0.0, 1.81), "m0", "Cube2")
    code += add("cube", 1.2, (0.0, 0.0, 3.01), "m0", "Cube3")
    return f"Stack three {c0[0]} cubes of size 1.2 on top of each other.", code


def t_row5(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    for i in range(-2, 3):
        code += add("sphere", 0.6, (1.5 * i, 0.0, 0.6), "m0", f"S{i + 2}")
    return f"Create a row of five {c[0]} spheres (radius 0.6) 1.5 apart.", code


def t_pyramid(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    for z, xs in [(0.6, [-1.2, 0.0, 1.2]), (1.8, [-0.6, 0.6]), (3.0, [0.0])]:
        for x in xs:
            code += add("cube", 1.2, (x, 0.0, z), "m0",
                        f"C{int(z * 10)}_{int(x * 10)}")
    return f"Build a pyramid out of six {c[0]} cubes of size 1.2.", code


def t_ring8(pal, rng):
    c = pal[0]
    lines = [mdef("m0", c[1])]
    for i in range(8):
        ang = math.radians(i * 45)
        x = round(3.0 * math.cos(ang), 3)
        y = round(3.0 * math.sin(ang), 3)
        lines.append(add("cube", 1.0, (x, y, 0.5), "m0", f"R{i}",
                         rot=rotz(i * 45)))
    return (f"Place eight {c[0]} cubes of size 1 evenly in a circle of "
            f"radius 3, each rotated 45 degrees from the previous."), \
        "\n".join(lines)


def t_gold(pal, rng):
    code = mdef("m0", PALETTE[3][1], metallic=1.0, rough=0.3) + "\n"
    code += add("sphere", 1.2, (0.0, 0.0, 1.2), "m0", "Sphere")
    return "Create a golden sphere (fully metallic, glossy) of radius 1.2.", code


def t_emissive(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1], emit=5.0) + "\n"
    code += add("sphere", 1.0, (0.0, 0.0, 1.0), "m0", "Bulb")
    return f"Create a glowing {c[0]} sphere (emission strength 5).", code


def t_matte(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1], rough=0.95) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.01), "m0", "Cube")
    return f"Create a matte (very rough) {c[0]} cube of size 2.", code


def t_two_color(pal, rng):
    a, b = pal[0], pal[1]
    code = mdef("m0", a[1]) + "\n" + mdef("m1", b[1]) + "\n"
    code += add("sphere", 1.0, (-1.6, 0.0, 1.0), "m0", "Left")
    code += add("sphere", 1.0, (1.6, 0.0, 1.0), "m1", "Right")
    return (f"Create two spheres side by side: {a[0]} on the left, "
            f"{b[0]} on the right."), code


def t_house(pal, rng):
    wall, roof = pal[0], pal[1]
    code = mdef("m0", wall[1]) + "\n" + mdef("m1", roof[1]) + "\n"
    code += add("cube", 4.0, (0.0, 0.0, 2.01), "m0", "Walls")
    code += add("cone", 3.0, (0.0, 0.0, 5.01), "m1", "Roof", depth=2.0)
    return (f"Build a house: a {wall[0]} cube of size 4 for the walls and a "
            f"{roof[0]} cone for the roof on top."), code


def t_snowman(pal, rng):
    col = pal[0]
    code = mdef("m0", col[1]) + "\n"
    code += add("sphere", 1.2, (0.0, 0.0, 1.2), "m0", "Bottom")
    code += add("sphere", 0.85, (0.0, 0.0, 3.25), "m0", "Middle")
    code += add("sphere", 0.6, (0.0, 0.0, 4.7), "m0", "Head")
    return (f"Build a snowman from three stacked {col[0]} spheres, biggest at "
            f"the bottom."), code


def t_table(pal, rng):
    wood = PALETTE[8]
    c = pal[0]
    code = mdef("m0", wood[1], rough=0.7) + "\n" + mdef("m1", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.5), "m1", "Top",
                scale=(1.3, 0.9, 0.06))
    for i, (x, y) in enumerate([(-0.95, 0.6), (0.95, 0.6),
                                (-0.95, -0.6), (0.95, -0.6)]):
        code += add("cylinder", 0.07, (x, y, 0.75), "m0", f"Leg{i}",
                    depth=1.5)
    return (f"Build a table: a {c[0]} top with four low wooden legs."), code


def t_traffic_light(pal, rng):
    code = mdef("m0", (0.2, 0.2, 0.22), rough=0.8) + "\n"
    code += mdef("m1", PALETTE[0][1], rough=0.4) + "\n"
    code += mdef("m2", PALETTE[3][1], rough=0.4) + "\n"
    code += mdef("m3", PALETTE[2][1], rough=0.4) + "\n"
    code += add("cylinder", 0.1, (0.0, 0.0, 1.5), "m0", "Pole", depth=3.0)
    code += add("cube", 1.0, (0.0, 0.0, 3.6), "m0", "Box",
                scale=(0.65, 0.5, 1.5))
    code += add("sphere", 0.26, (0.0, -0.52, 4.25), "m1", "Red")
    code += add("sphere", 0.26, (0.0, -0.52, 3.6), "m2", "Yellow")
    code += add("sphere", 0.26, (0.0, -0.52, 2.95), "m3", "Green")
    return ("Build a traffic light: dark pole, box and red/yellow/green "
            "lights."), code


def t_rocket(pal, rng):
    body = pal[0]
    lines = [mdef("m0", body[1], metallic=0.5, rough=0.3),
             mdef("m1", PALETTE[0][1], rough=0.4),
             mdef("m2", PALETTE[5][1], emit=4.0)]
    lines.append(add("cylinder", 0.6, (0.0, 0.0, 1.5), "m0", "Body",
                     depth=2.4))
    lines.append(add("cone", 0.6, (0.0, 0.0, 3.3), "m1", "Nose", depth=1.2))
    lines.append(add("cone", 0.42, (0.0, 0.0, -0.5), "m2", "Flame",
                     rot="(math.radians(180), 0.0, 0.0)", depth=1.0))
    return (f"Build a {body[0]} rocket: cylinder body, red nose cone and a "
            f"glowing flame cone underneath."), "\n".join(lines)


def t_robot_head(pal, rng):
    skin = pal[0]
    code = mdef("m0", skin[1], metallic=0.7, rough=0.35) + "\n"
    code += mdef("m1", (0.95, 0.95, 0.95), rough=0.3) + "\n"
    code += mdef("m2", (0.05, 0.05, 0.08), rough=0.3) + "\n"
    code += mdef("m3", PALETTE[0][1], emit=3.0) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.01), "m0", "Head")
    code += add("sphere", 0.22, (-0.45, -0.98, 1.3), "m1", "EyeL")
    code += add("sphere", 0.22, (0.45, -0.98, 1.3), "m1", "EyeR")
    code += add("sphere", 0.09, (-0.45, -1.15, 1.31), "m2", "PupilL")
    code += add("sphere", 0.09, (0.45, -1.15, 1.31), "m2", "PupilR")
    code += add("cylinder", 0.05, (0.0, 0.0, 2.4), "m0", "Antenna", depth=0.8)
    code += add("sphere", 0.16, (0.0, 0.0, 2.9), "m3", "Light")
    return ("Build a robot head: metallic cube head, two white eyes with dark "
            "pupils, antenna with a glowing red tip."), code


def t_tree(pal, rng):
    crown = pal[0]
    code = mdef("m0", PALETTE[8][1], rough=0.8) + "\n"
    code += mdef("m1", crown[1], rough=0.6) + "\n"
    code += add("cylinder", 0.22, (0.0, 0.0, 1.0), "m0", "Trunk", depth=2.0)
    code += add("sphere", 1.3, (0.0, 0.0, 3.0), "m1", "Crown")
    return f"Build a tree: brown trunk and a big {crown[0]} crown.", code


def t_car(pal, rng):
    body = pal[0]
    code = mdef("m0", body[1], metallic=0.4, rough=0.35) + "\n"
    code += mdef("m1", pal[1][1], rough=0.4) + "\n"
    code += mdef("m2", (0.08, 0.08, 0.1), rough=0.6) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 0.75), "m0", "Body",
                scale=(1.4, 0.75, 0.45))
    code += add("cube", 1.0, (0.0, 0.0, 1.55), "m1", "Cabin",
                scale=(0.8, 0.7, 0.55))
    for i, (x, y) in enumerate([(-1.0, 0.72), (1.0, 0.72),
                                (-1.0, -0.72), (1.0, -0.72)]):
        code += add("cylinder", 0.34, (x, y, 0.35), "m2", f"W{i}",
                    rot="(math.radians(90), 0.0, 0.0)", depth=0.28)
    return (f"Build a simple car: {body[0]} body, blue cabin and four dark "
            f"wheels."), code


def t_bevel(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.01), "m0", "Cube")
    code += ('mod = o.modifiers.new("Bevel", "BEVEL")\n'
             "mod.width = 0.18\n"
             "mod.segments = 3\n"
             "o.select_set(True)\n"
             "bpy.context.view_layer.objects.active = o\n"
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create a {c[0]} cube with beveled edges (width 0.18, 3 "
            f"segments)."), code


def t_solidify(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("plane", 2.5, (0.0, 0.0, 1.0), "m0", "Plane")
    code += ('mod = o.modifiers.new("Solid", "SOLIDIFY")\n'
             "mod.thickness = 0.25\n"
             "o.select_set(True)\n"
             "bpy.context.view_layer.objects.active = o\n"
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return f"Create a thin {c[0]} slab from a plane (thickness 0.25).", code


def t_array(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 1.0, (-3.0, 0.0, 0.5), "m0", "Cube")
    code += ('mod = o.modifiers.new("Arr", "ARRAY")\n'
             "mod.count = 5\n"
             "mod.relative_offset_displace = (1.5, 0.0, 0.0)\n"
             "o.select_set(True)\n"
             "bpy.context.view_layer.objects.active = o\n"
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return f"Create five {c[0]} cubes of size 1 in a row (spacing 1.5).", code


def t_subsurf(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1], rough=0.3) + "\n"
    code += add("cube", 2.5, (0.0, 0.0, 1.26), "m0", "Blob")
    code += ('mod = o.modifiers.new("Sub", "SUBSURF")\n'
             "mod.levels = 3\n"
             "mod.render_levels = 3\n"
             "o.select_set(True)\n"
             "bpy.context.view_layer.objects.active = o\n"
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create a smooth rounded {c[0]} blob (a subdivided cube)."), code


TASKS = [
    ("cube", t_cube), ("sphere", t_sphere), ("cylinder", t_cylinder),
    ("cone", t_cone), ("torus", t_torus), ("plane", t_plane),
    ("moved", t_moved), ("rotated", t_rotated), ("scaled", t_scaled),
    ("stack3", t_stack3), ("row5", t_row5), ("pyramid", t_pyramid),
    ("ring8", t_ring8), ("gold", t_gold), ("emissive", t_emissive),
    ("matte", t_matte), ("two_color", t_two_color), ("house", t_house),
    ("snowman", t_snowman), ("table", t_table),
    ("traffic_light", t_traffic_light), ("rocket", t_rocket),
    ("robot_head", t_robot_head), ("tree", t_tree), ("car", t_car),
    ("bevel", t_bevel), ("solidify", t_solidify), ("array", t_array),
    ("subsurf", t_subsurf),
]


def rotate_palette(off):
    return PALETTE[off:] + PALETTE[:off]


def gen_rows():
    rows = []
    for ti, (tname, fn) in enumerate(TASKS):
        for v in range(VARIANTS):
            pal = rotate_palette((ti * 5 + v * 3) % len(PALETTE))
            rng = random.Random(1000 + ti * 97 + v)
            instr, code = fn(pal, rng)
            script = PREFIX + code + TAIL
            rows.append({"id": f"{tname}_v{v}", "task": tname, "variant": v,
                         "instruction": instr, "script": script})
    return rows


# ---------------------------------------------------------------- verify
def glb_stats(path):
    try:
        with open(path, "rb") as f:
            head = f.read(12)
            if len(head) < 12 or head[:4] != b"glTF":
                return None
            ln = int.from_bytes(f.read(4), "little")
            f.read(4)
            js = json.loads(f.read(ln).decode("utf-8", "replace"))
        tris = 0
        for m in js.get("meshes", []):
            for p in m.get("primitives", []):
                if "indices" in p:
                    tris += js["accessors"][p["indices"]]["count"] // 3
        return {"meshes": len(js.get("meshes", [])),
                "nodes": len(js.get("nodes", [])), "glb_tris": tris}
    except Exception as e:
        return {"loi": f"{type(e).__name__}: {e}"}


def run_one(row):
    tid = row["id"]
    sp = os.path.join(TASKS_DIR, tid + ".py")
    od = os.path.join(OUT_DIR, tid)
    os.makedirs(od, exist_ok=True)
    with open(sp, "w") as f:
        f.write(row["script"])
    env = dict(os.environ)
    env["BLEND_OUT"] = od
    t0 = time.time()
    try:
        r = subprocess.run([BLENDER, "--background", "--factory-startup",
                            "--python", sp],
                           capture_output=True, text=True, env=env,
                           timeout=TIMEOUT)
        rc, out, err = r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        rc, out, err = -9, "", f"TIMEOUT {TIMEOUT}s"
    dt = time.time() - t0
    res = {"id": tid, "rc": rc, "t": round(dt, 1)}
    res["verify_ok"] = "VERIFY_OK" in out
    glb = os.path.join(od, "scene.glb")
    png = os.path.join(od, "render.png")
    g = glb_stats(glb) if os.path.exists(glb) else None
    res["glb"] = g
    res["glb_bytes"] = os.path.getsize(glb) if os.path.exists(glb) else 0
    res["png_bytes"] = os.path.getsize(png) if os.path.exists(png) else 0
    ok = (rc == 0 and res["verify_ok"] and isinstance(g, dict)
          and g.get("meshes", 0) > 0 and g.get("glb_tris", 0) > 0
          and res["png_bytes"] > 2000)
    res["ok"] = bool(ok)
    if ok:
        shutil.copyfile(glb, os.path.join(WORK, "glb", tid + ".glb"))
        shutil.copyfile(png, os.path.join(WORK, "renders", tid + ".png"))
    else:
        res["err_tail"] = (err or out)[-700:]
    return res


def main():
    t0 = time.time()
    get_blender()
    for d in ("glb", "renders"):
        os.makedirs(os.path.join(WORK, d), exist_ok=True)
    os.makedirs(TASKS_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = gen_rows()
    log(f"tong {len(rows)} task ({len(TASKS)} base x {VARIANTS} variants)")
    oks, fails = [], []
    for i, row in enumerate(rows, 1):
        res = run_one(row)
        (oks if res["ok"] else fails).append(res)
        g = res.get("glb") or {}
        log(f"[{i}/{len(rows)}] {res['id']} rc={res['rc']} "
            f"ok={res['ok']} mesh={g.get('meshes')} tris={g.get('glb_tris')} "
            f"png={res['png_bytes']}B t={res['t']}s")
    out_rows = []
    by_id = {r["id"]: r for r in rows}
    for res in oks:
        r = by_id[res["id"]]
        out_rows.append({
            "id": r["id"], "task": r["task"], "variant": r["variant"],
            "instruction": r["instruction"], "script": r["script"],
            "glb_tris": (res.get("glb") or {}).get("glb_tris"),
            "render": f"renders/{r['id']}.png",
            "glb": f"glb/{r['id']}.glb",
        })
    with open(os.path.join(WORK, "rows.jsonl"), "w") as f:
        for r in out_rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(WORK, "failures.jsonl"), "w") as f:
        for r in fails:
            f.write(json.dumps(r) + "\n")
    summary = {"n_tasks": len(rows), "n_pass": len(out_rows),
               "n_fail": len(fails),
               "pass_rate": round(len(out_rows) / max(len(rows), 1), 3),
               "t_sec": round(time.time() - t0)}
    with open(os.path.join(WORK, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    log(f"SUMMARY {summary}")


if __name__ == "__main__":
    main()
