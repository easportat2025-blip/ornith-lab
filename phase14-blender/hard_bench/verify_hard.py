# -*- coding: utf-8 -*-
"""verify_hard.py — Blender HARD-30 verifier + 30 emitter (TASK-13, MiMo).

Mo rong verify_mui2 (TASK-7): 30 task multi-object x 3 variants = 90 cap.
Moi task ghi ro CONSTRAINT list ktra duoc tu scene dump JSON + pixel render:
  count_mesh / rel_z / rel_xy / same_z / touching / size_ratio / bbox_within /
  mat_color / mat_prop / cam / light / rot / pixel_region

Pipeline (giong verify_mui2): headless Blender 4.2 -> script PREFIX+code+TAIL
-> GLB (parse meshes/tris) + render PNG 320x320 > 2KB + scene dump JSON
(objects/ten/loai/loc/rot/scale/dims/mats, camera, light) -> constraint check
Python doc scene.json (KHONG tin flag cua script) + pixel doc PNG
-> hard_report.json (summary + 90 cap chi tiet) + rows_hard.jsonl (chi PASS).

Seed/palette rieng, khong trung 87 old + 45 mui2:
    seed = 6000 + ti*97 + v       (old den ~3718, mui2 den ~5173)
Id tien to "hNN_": h01_..._v0 ... h30_..._v2  (0 clash).
HARD-30 la eval held-out (khong train tren anh render cua no).

Chay:  python verify_hard.py        (can Blender — tren Kaggle CPU)
      python dry_check.py          (local, khong can Blender)
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
SERIES = BVER.rsplit(".", 1)[0]
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
WORK = "/kaggle/working/blend_hard"
TASKS_DIR = "/tmp/hard_tasks"
OUT_DIR = "/tmp/hard_out"
VARIANTS = 3
TIMEOUT = 300


def log(m):
    print(f"[hard] {m}", flush=True)


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


def find_offline_tarball():
    for root, _, files in os.walk("/kaggle/input"):
        for f in files:
            if f.startswith("blender-") and f.endswith(".tar.xz"):
                return os.path.join(root, f)
    return None


def get_blender():
    if os.path.exists(BLENDER):
        log("blender da co san")
        return
    os.makedirs(TMP, exist_ok=True)
    src = find_offline_tarball()
    if src:
        log(f"OFFLINE: giai nen tarball tu {src}")
        with tarfile.open(src) as tf:
            tf.extractall(TMP)
        if not os.path.exists(BLENDER):
            raise RuntimeError(f"tarball {src} khong chua {NAME}/blender")
        return
    log("khong thay tarball trong /kaggle/input -> download (can internet ON)")
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

# TAIL: camera/sun co the DUOC OVERWRITE truoc bang bien toan cuc
# CAM_LOC / CAM_TGT / SUN_ROT / SUN_ENERGY (emitter camera/light set truoc).
TAIL = '''
_cam_loc = globals().get("CAM_LOC", (9.5, -9.5, 6.5))
_cam_tgt = globals().get("CAM_TGT", (0.0, 0.0, 1.6))
_sun_rot = globals().get("SUN_ROT", (math.radians(50), 0.0, math.radians(30)))
_sun_energy = globals().get("SUN_ENERGY", 4.0)

world = bpy.data.worlds.new("World")
world.use_nodes = True
bgn = world.node_tree.nodes["Background"]
bgn.inputs[0].default_value = (0.85, 0.87, 0.92, 1.0)
scene.world = world

cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam.location = _cam_loc
tgt = bpy.data.objects.new("Target", None)
scene.collection.objects.link(tgt)
tgt.location = _cam_tgt
con = cam.constraints.new("TRACK_TO")
con.target = tgt
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.camera = cam

_extra_lights = globals().get("EXTRA_LIGHTS", [])   # [(kind, loc, energy, rot)]
for _kind, _loc, _en, _rot in _extra_lights:
    _ld = bpy.data.lights.new("L_" + _kind, _kind)
    _ld.energy = _en
    _lo = bpy.data.objects.new("L_" + _kind, _ld)
    scene.collection.objects.link(_lo)
    _lo.location = _loc
    if _rot:
        _lo.rotation_euler = _rot

sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = _sun_energy
sun = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler = _sun_rot

glb = os.path.join(out, "scene.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB")

scene.render.engine = "CYCLES"
# TASK-16 (DeepSeek 19/10): AgX view transform lam mau bi rua manh
# (red 0.8,0.1,0.1 -> ~0.86,0.55,0.54) => pixel_region fail gia tao.
# Standard cho mau render ~ mau vat lieu (van clip khi qua sang, da tinh).
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.render.resolution_x = 320
scene.render.resolution_y = 320
png = os.path.join(out, "render.png")
scene.render.filepath = png
bpy.ops.render.render(write_still=True)

# ---- scene dump JSON (verifier doc, khong tin flag cua script)
import json as _json
_dump = []
for o in bpy.data.objects:
    e = {"name": o.name, "type": o.type,
         "loc": [round(float(x), 4) for x in o.location],
         "rot": [round(float(x), 4) for x in o.rotation_euler],
         "scale": [round(float(x), 4) for x in o.scale]}
    if o.type == "MESH":
        e["dims"] = [round(float(x), 4) for x in o.dimensions]
        mats = []
        for m in o.data.materials:
            if m and m.use_nodes:
                b = m.node_tree.nodes.get("Principled BSDF")
                if b is not None:
                    mats.append({
                        "base": [round(float(c), 4) for c in
                                 b.inputs["Base Color"].default_value[:3]],
                        "metallic": round(float(
                            b.inputs["Metallic"].default_value), 4),
                        "rough": round(float(
                            b.inputs["Roughness"].default_value), 4),
                        "emit": round(float(
                            b.inputs["Emission Strength"].default_value), 4)})
        e["mats"] = mats
    if o.type == "LIGHT":
        e["light_type"] = o.data.type
        e["energy"] = round(float(o.data.energy), 3)
    if o.type == "CAMERA":
        e["lens"] = round(float(o.data.lens), 2)
    _dump.append(e)
_tgt = bpy.data.objects.get("Target")
_json.dump({"objects": _dump,
            "camera": scene.camera.name if scene.camera else None,
            "target": [round(float(x), 4) for x in _tgt.location] if _tgt
                      else [0.0, 0.0, 1.6]},
           open(os.path.join(out, "scene.json"), "w"))

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

# ---------------------------------------------------------------- palette/helpers

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


def rotate_palette(off):
    return PALETTE[off % len(PALETTE):] + PALETTE[:off % len(PALETTE)]


def art(w):
    return "an" if w[:1].lower() in "aeiou" else "a"


# ---------------------------------------------------------------- constraint
# Moi emitter TRA VE (instruction, code, constraints). Constraint la dict:
#   {"t": "...", ...params} — verifier doc scene.json + render.png, khong tin
#   bat ky flag nao script tu dat.

# Kieu constraint ho tro (xem check_constraints):
#   count_mesh     {n, op=eq|ge|le}
#   rel_z          {a, b, op=above|below, tol=0.1}
#   rel_xy         {a, b, axis=x|y, op=left|right|front|behind, tol=0.1}
#   same_z         {a, b, tol=0.05}
#   touching       {a, b, axis=z, tol=0.18}   (a dung len tren hoac duoi b)
#   size_ratio     {a, b, axis=x|y|z, ratio, tol=0.3}
#   bbox_within    {a, b, tol=0.1}             (a nam trong bbox cua b)
#   mat_color      {a, color, tol=0.45}
#   mat_prop       {a, prop=metallic|rough|emit, op=eq|ge|le, v, tol=0.12}
#   cam            {azim=[min,max], elev=[min,max]}   (do tu target -> camera)
#   light          {kind, op=eq|ge, n, energy=[min,max] opt}
#   rot            {a, axis=x|y|z, deg=[min,max]}
#   pixel_region   {region=[x0,y0,x1,y1] 0..1 tu tren-trai, color, frac}

# ---------------------------------------------------------------- 30 emitters
# Moi emitter: (instruction, code, constraints). Code chay trong PREFIX+TAIL.

def h01_row_of_balls(pal, rng):
    n = rng.choice([3, 4, 5])
    gap = rng.choice([1.2, 1.5])
    cb, cc = pal[0], pal[1]
    code = mdef("m0", cb[1]) + "\n" + mdef("m1", cc[1]) + "\n"
    for i in range(n):
        code += add("sphere", 0.4, (round(i * gap, 3), 0.0, 0.4), "m0",
                    f"Ball{i}")
    xe = round((n - 1) * gap + gap, 3)
    code += add("cube", 0.8, (xe, 0.0, 0.4), "m1", "End")
    cons = [{"t": "count_mesh", "n": n + 1, "op": "eq"},
            {"t": "same_z", "a": "Ball0", "b": "End", "tol": 0.05},
            {"t": "rel_xy", "a": "End", "b": f"Ball{n - 1}", "axis": "x",
             "op": "right", "tol": 0.3},
            {"t": "mat_color", "a": "Ball0", "color": cb[0]},
            {"t": "mat_color", "a": "End", "color": cc[0]}]
    for i in range(1, n):
        cons.append({"t": "rel_xy", "a": f"Ball{i}", "b": f"Ball{i - 1}",
                     "axis": "x", "op": "right", "tol": 0.2})
    return (f"Create {n} {cb[0]} spheres of radius 0.4 in a "
            f"straight row along +X, {gap} apart, all centered at the same "
            f"height, then put {art(cc[0])} {cc[0]} cube of size 0.8 at the "
            f"same height further along +X, beyond the last sphere."), code, cons


def h02_pyramid_blocks(pal, rng):
    rows = rng.choice([3, 4])
    s = rng.choice([0.8, 1.0])
    ca, cb = pal[0], pal[1]
    code = mdef("m0", ca[1]) + "\n" + mdef("m1", cb[1]) + "\n"
    for i in range(rows):
        cnt = rows - i
        mv = "m0" if i % 2 == 0 else "m1"
        for j in range(cnt):
            x = round((j - (cnt - 1) / 2) * s, 3)
            code += add("cube", s, (x, 0.0, round((i + 0.5) * s, 3)), mv,
                        f"R{i}_{j}")
    total = rows * (rows + 1) // 2
    cons = [{"t": "count_mesh", "n": total, "op": "eq"},
            {"t": "rel_z", "a": "R1_0", "b": "R0_0", "op": "above",
             "tol": 0.1},
            {"t": "mat_color", "a": "R0_0", "color": ca[0]},
            {"t": "mat_color", "a": "R1_0", "color": cb[0]}]
    return (f"Build a {rows}-row block pyramid of cubes (side {s}): the bottom "
            f"row has {rows} cubes side by side on the ground, each row above "
            f"has one cube less, rows alternate {ca[0]} and {cb[0]} starting "
            f"with {ca[0]} at the bottom."), code, cons


def h03_bookend_shelf(pal, rng):
    n = rng.choice([3, 4])
    w = rng.choice([3.0, 3.4])
    bh = rng.choice([0.7, 0.8])
    cf, cbk, cbe = pal[0], pal[1], pal[2]
    code = (mdef("m0", cf[1], rough=0.7) + "\n" + mdef("m1", cbk[1]) + "\n"
            + mdef("m2", cbe[1]) + "\n")
    code += add("cube", 1.0, (0.0, 0.0, 0.06), "m0", "Plank",
                scale=(w, 0.7, 0.12))
    for i in range(n):
        x = round(-(n - 1) * 0.17 + i * 0.34, 3)
        code += add("cube", 1.0, (x, 0.0, round(0.12 + bh / 2, 3)), "m1",
                    f"Book{i}", scale=(0.16, 0.5, bh))
    xe = round(w / 2 - 0.25, 3)
    code += add("cube", 1.0, (-xe, 0.0, 0.57), "m2", "EndL",
                scale=(0.12, 0.6, 0.9))
    code += add("cube", 1.0, (xe, 0.0, 0.57), "m2", "EndR",
                scale=(0.12, 0.6, 0.9))
    cons = [{"t": "count_mesh", "n": n + 3, "op": "eq"},
            {"t": "touching", "a": "Book0", "b": "Plank", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "EndL", "b": "Plank", "axis": "z",
             "tol": 0.05},
            {"t": "rel_xy", "a": "EndL", "b": "Book0", "axis": "x",
             "op": "left", "tol": 0.05},
            {"t": "rel_xy", "a": "EndR", "b": f"Book{n - 1}", "axis": "x",
             "op": "right", "tol": 0.05},
            {"t": "mat_color", "a": "Plank", "color": cf[0]},
            {"t": "mat_color", "a": "EndL", "color": cbe[0]}]
    return (f"Build {art(cf[0])} {cf[0]} shelf plank ({w} wide) with {n} upright "
            f"{cbk[0]} books standing on it in a row in the middle, and one "
            f"{cbe[0]} bookend block at each end of the row, outside the "
            f"books, also resting on the plank."), code, cons


def h04_fence(pal, rng):
    n = rng.choice([5, 6])
    gap = rng.choice([0.9, 1.1])
    cp, cr = pal[0], pal[1]
    code = mdef("m0", cp[1], rough=0.8) + "\n" + mdef("m1", cr[1], rough=0.8) + "\n"
    x0 = -((n - 1) * gap) / 2
    for i in range(n):
        code += add("cube", 1.0, (round(x0 + i * gap, 3), 0.0, 0.7), "m0",
                    f"Post{i}", scale=(0.12, 0.12, 1.4))
    span = round((n - 1) * gap + 0.6, 3)
    for k, z in enumerate((0.5, 1.1)):
        code += add("cube", 1.0, (0.0, 0.0, z), "m1", f"Rail{k}",
                    scale=(span, 0.08, 0.1))
    cons = [{"t": "count_mesh", "n": n + 2, "op": "eq"},
            {"t": "rel_z", "a": "Rail1", "b": "Rail0", "op": "above",
             "tol": 0.1},
            {"t": "rel_xy", "a": "Post1", "b": "Post0", "axis": "x",
             "op": "right", "tol": 0.1},
            {"t": "mat_color", "a": "Post0", "color": cp[0]},
            {"t": "mat_color", "a": "Rail0", "color": cr[0]}]
    return (f"Build a fence: {n} {cp[0]} posts (0.12 x 0.12 x 1.4) in a row "
            f"along X spaced {gap} apart, plus two long {cr[0]} horizontal "
            f"rails crossing all posts, one at height 0.5 and one at 1.1.",
            code, cons)


def h05_stairs_banister(pal, rng):
    n = rng.choice([4, 5])
    rise = rng.choice([0.5, 0.6])
    step = rng.choice([1.0, 1.2])
    cst, cbl = pal[0], pal[1]
    code = mdef("m0", cst[1]) + "\n" + mdef("m1", cbl[1]) + "\n"
    x0 = -((n - 1) * step) / 2
    for i in range(n):
        code += add("cube", 1.0, (round(x0 + i * step, 3), 0.0,
                                  round(rise / 2 + i * rise, 3)), "m0",
                    f"Step{i}", scale=(step * 0.9, 1.4, rise))
    topz = round(n * rise + 0.35, 3)
    code += add("sphere", 0.35, (round(x0 + (n - 1) * step, 3), 0.0, topz),
                "m1", "Ball")
    cons = [{"t": "count_mesh", "n": n + 1, "op": "eq"},
            {"t": "touching", "a": "Ball", "b": f"Step{n - 1}", "axis": "z",
             "tol": 0.06},
            {"t": "rel_z", "a": "Ball", "b": f"Step{n - 2}", "op": "above",
             "tol": 0.1},
            {"t": "mat_color", "a": "Step0", "color": cst[0]},
            {"t": "mat_color", "a": "Ball", "color": cbl[0]}]
    return (f"Build a {n}-step {cst[0]} staircase rising along +X (each step "
            f"{rise} taller, {step} deep) and place {art(cbl[0])} {cbl[0]} "
            f"sphere of radius 0.35 resting exactly on the top step.",
            code, cons)


def h06_sphere_on_cube(pal, rng):
    s = rng.choice([1.4, 1.8])
    cb, cs = pal[0], pal[1]
    code = mdef("m0", cb[1]) + "\n" + mdef("m1", cs[1]) + "\n"
    code += add("cube", s, (0.0, 0.0, round(s / 2, 3)), "m0", "Base")
    code += add("sphere", 0.45, (0.0, 0.0, round(s + 0.45, 3)), "m1", "Ball")
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "touching", "a": "Ball", "b": "Base", "axis": "z",
             "tol": 0.05},
            {"t": "rel_z", "a": "Ball", "b": "Base", "op": "above", "tol": 0.1},
            {"t": "rel_xy", "a": "Ball", "b": "Base", "axis": "x",
             "op": "aligned_x", "tol": 0.03},
            {"t": "rel_xy", "a": "Ball", "b": "Base", "axis": "y",
             "op": "aligned_y", "tol": 0.03},
            {"t": "mat_color", "a": "Base", "color": cb[0]},
            {"t": "mat_color", "a": "Ball", "color": cs[0]}]
    return (f"Place {art(cb[0])} {cb[0]} cube of size {s} on the ground and "
            f"rest {art(cs[0])} {cs[0]} sphere of radius 0.45 exactly on its "
            f"top face, perfectly centered on the cube."), code, cons


def h07_arch_gate(pal, rng):
    span = rng.choice([3.0, 3.6])
    ph = rng.choice([2.4, 2.8])
    cp, cb, cbl = pal[0], pal[1], pal[2]
    code = (mdef("m0", cp[1]) + "\n" + mdef("m1", cb[1]) + "\n"
            + mdef("m2", cbl[1]) + "\n")
    code += add("cube", 1.0, (-span / 2, 0.0, round(ph / 2, 3)), "m0",
                "PillarL", scale=(0.6, 0.6, ph))
    code += add("cube", 1.0, (span / 2, 0.0, round(ph / 2, 3)), "m0",
                "PillarR", scale=(0.6, 0.6, ph))
    code += add("cube", 1.0, (0.0, 0.0, round(ph + 0.3, 3)), "m1", "Beam",
                scale=(span + 0.6, 1.0, 0.6))
    code += add("sphere", 0.4, (0.0, 0.0, 0.4), "m2", "Ball")
    cons = [{"t": "count_mesh", "n": 4, "op": "eq"},
            {"t": "touching", "a": "Beam", "b": "PillarL", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Beam", "b": "PillarR", "axis": "z",
             "tol": 0.05},
            {"t": "rel_z", "a": "Beam", "b": "Ball", "op": "above", "tol": 0.5},
            {"t": "rel_xy", "a": "Ball", "b": "PillarL", "axis": "x",
             "op": "right", "tol": 0.2},
            {"t": "rel_xy", "a": "Ball", "b": "PillarR", "axis": "x",
             "op": "left", "tol": 0.2},
            {"t": "mat_color", "a": "PillarL", "color": cp[0]},
            {"t": "mat_color", "a": "Beam", "color": cb[0]}]
    return (f"Build a gate: two {cp[0]} pillars {span} apart, "
            f"{art(cb[0])} {cb[0]} beam "
            f"resting on top of both pillars, and {art(cbl[0])} {cbl[0]} "
            f"sphere of radius 0.4 standing on the ground exactly between "
            f"the pillars, under the beam."), code, cons


def h08_hanging_lamp(pal, rng):
    H = rng.choice([3.6, 4.0])
    cl = rng.choice([1.0, 1.3])
    clcc = pal[0]
    code = (mdef("m0", (0.25, 0.25, 0.28)) + "\n"
            + mdef("m1", clcc[1], emit=4.0) + "\n")
    code += add("plane", 6.0, (0.0, 0.0, H), "m0", "Ceiling")
    lz = round(H - cl - 0.4, 3)
    code += add("cylinder", 0.03, (0.0, 0.0, round(H - cl / 2, 3)), "m0",
                "Cord", depth=cl)
    code += add("sphere", 0.4, (0.0, 0.0, lz), "m1", "Lamp")
    cons = [{"t": "count_mesh", "n": 3, "op": "eq"},
            {"t": "touching", "a": "Cord", "b": "Ceiling", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Lamp", "b": "Cord", "axis": "z",
             "tol": 0.05},
            {"t": "rel_z", "a": "Lamp", "b": "Ceiling", "op": "below",
             "tol": 0.5},
            {"t": "mat_prop", "a": "Lamp", "prop": "emit", "op": "ge",
             "v": 2.0},
            {"t": "mat_color", "a": "Lamp", "color": clcc[0]}]
    return (f"Hang a glowing {clcc[0]} lamp bulb (emissive "
            f"sphere, radius 0.4) from a ceiling plane at height {H} by a "
            f"thin dark cord of length {cl}: the cord touches the ceiling "
            f"and the bulb touches the bottom of the cord."), code, cons


def h09_towers_bridge(pal, rng):
    d = rng.choice([1.6, 2.0])
    H = rng.choice([2.2, 2.6])
    ct, cbr, cw = pal[0], pal[1], pal[2]
    code = (mdef("m0", ct[1]) + "\n" + mdef("m1", cbr[1]) + "\n"
            + mdef("m2", cw[1]) + "\n")
    for nm, x in (("TowerL", -d), ("TowerR", d)):
        code += add("cylinder", 0.35, (x, 0.0, round(H / 2, 3)), "m0", nm,
                    depth=H)
    code += add("cube", 1.0, (0.0, 0.0, round(H + 0.175, 3)), "m1", "Bridge",
                scale=(round(2 * d + 0.8, 3), 0.7, 0.35))
    code += add("cube", 0.5, (0.0, 0.0, 0.25), "m2", "Crate")
    cons = [{"t": "count_mesh", "n": 4, "op": "eq"},
            {"t": "touching", "a": "Bridge", "b": "TowerL", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Bridge", "b": "TowerR", "axis": "z",
             "tol": 0.05},
            {"t": "rel_z", "a": "Bridge", "b": "Crate", "op": "above",
             "tol": 0.3},
            {"t": "rel_xy", "a": "Crate", "b": "TowerL", "axis": "x",
             "op": "right", "tol": 0.2},
            {"t": "rel_xy", "a": "Crate", "b": "TowerR", "axis": "x",
             "op": "left", "tol": 0.2},
            {"t": "mat_color", "a": "TowerL", "color": ct[0]},
            {"t": "mat_color", "a": "Bridge", "color": cbr[0]}]
    return (f"Build a bridge: two {ct[0]} cylindrical towers (radius 0.35, "
            f"height {H}) at x=-{d} and x={d}, a flat {cbr[0]} bridge deck "
            f"resting on top of both towers, and {art(cw[0])} {cw[0]} crate "
            f"(cube 0.5) standing on the ground midway between the towers, "
            f"below the bridge."), code, cons


def h10_stacked_shapes(pal, rng):
    cols = [pal[0], pal[1], pal[2], pal[3]]
    code = "".join(mdef(f"m{i}", cols[i][1]) + "\n" for i in range(4))
    z0 = 1.2
    code += add("cube", 1.2, (0.0, 0.0, round(z0 / 2, 3)), "m0", "Cube")
    z1 = round(z0 + 0.45, 3)
    code += add("cylinder", 0.5, (0.0, 0.0, z1), "m1", "Cyl", depth=0.9)
    z2 = round(z0 + 0.9 + 0.35, 3)
    code += add("cone", 0.35, (0.0, 0.0, z2), "m2", "Cone", depth=0.7)
    z3 = round(z0 + 0.9 + 0.7 + 0.3, 3)
    code += add("sphere", 0.3, (0.0, 0.0, z3), "m3", "Ball")
    cons = [{"t": "count_mesh", "n": 4, "op": "eq"},
            {"t": "touching", "a": "Cyl", "b": "Cube", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Cone", "b": "Cyl", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Ball", "b": "Cone", "axis": "z",
             "tol": 0.05},
            {"t": "rel_xy", "a": "Ball", "b": "Cube", "axis": "x",
             "op": "aligned_x", "tol": 0.03},
            {"t": "mat_color", "a": "Cube", "color": cols[0][0]},
            {"t": "mat_color", "a": "Ball", "color": cols[3][0]}]
    return (f"Stack four shapes exactly on top of each other, all sharing "
            f"the same center axis: {art(cols[0][0])} {cols[0][0]} cube "
            f"(size 1.2) on the "
            f"ground, {art(cols[1][0])} {cols[1][0]} cylinder (radius 0.5, "
            f"height 0.9) on "
            f"the cube, {art(cols[2][0])} {cols[2][0]} cone (radius 0.35, "
            f"height 0.7) on the "
            f"cylinder, and {art(cols[3][0])} {cols[3][0]} sphere "
            f"(radius 0.3) on the cone.",
            code, cons)


def h11_big_small_pair(pal, rng):
    sb = rng.choice([1.6, 2.0])
    ss = round(sb / 2, 3)
    cb, csm = pal[0], pal[1]
    code = mdef("m0", cb[1]) + "\n" + mdef("m1", csm[1]) + "\n"
    code += add("cube", sb, (-1.6, 0.0, round(sb / 2, 3)), "m0", "Big")
    code += add("cube", ss, (1.6, 0.0, round(ss / 2, 3)), "m1", "Small")
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "size_ratio", "a": "Big", "b": "Small", "axis": "x",
             "ratio": 2.0, "tol": 0.15},
            {"t": "rel_xy", "a": "Big", "b": "Small", "axis": "x",
             "op": "left", "tol": 0.3},
            {"t": "rel_xy", "a": "Big", "b": "Small", "axis": "y",
             "op": "aligned_y", "tol": 0.03},
            {"t": "mat_color", "a": "Big", "color": cb[0]},
            {"t": "mat_color", "a": "Small", "color": csm[0]}]
    return (f"Put {art(cb[0])} {cb[0]} cube of size {sb} on the left and "
            f"{art(csm[0])} {csm[0]} cube of size {ss} (exactly half as "
            f"wide) on the right, both on the ground and aligned in Y.",
            code, cons)


def h12_nested_cubes(pal, rng):
    k = rng.choice([1.0, 1.15])
    sizes = [round(2.4 * k, 3), round(1.6 * k, 3), round(0.9 * k, 3)]
    cols = [pal[0], pal[1], pal[2]]
    names = ["Outer", "Mid", "Inner"]
    code = "".join(mdef(f"m{i}", cols[i][1]) + "\n" for i in range(3))
    for i in range(3):
        code += add("cube", sizes[i], (0.0, 0.0, 1.6), f"m{i}", names[i])
    cons = [{"t": "count_mesh", "n": 3, "op": "eq"},
            {"t": "bbox_within", "a": "Mid", "b": "Outer", "tol": 0.05},
            {"t": "bbox_within", "a": "Inner", "b": "Mid", "tol": 0.05},
            {"t": "size_ratio", "a": "Outer", "b": "Mid", "axis": "x",
             "ratio": round(sizes[0] / sizes[1], 3), "tol": 0.1},
            {"t": "rel_xy", "a": "Outer", "b": "Mid", "axis": "x",
             "op": "aligned_x", "tol": 0.03},
            {"t": "mat_color", "a": "Outer", "color": cols[0][0]},
            {"t": "mat_color", "a": "Inner", "color": cols[2][0]}]
    return (f"Create three concentric {cols[0][0]}/{cols[1][0]}/"
            f"{cols[2][0]} cubes of sizes {sizes[0]}, {sizes[1]} and "
            f"{sizes[2]}, all with the same center point (each smaller cube "
            f"fully inside the next larger one)."), code, cons


def h13_shrinking_stack(pal, rng):
    r = rng.choice([0.7, 0.85])
    f = rng.choice([0.75, 0.8])
    h = rng.choice([0.8, 1.0])
    cs, cbl = pal[0], pal[1]
    code = mdef("m0", cs[1]) + "\n" + mdef("m1", cbl[1]) + "\n"
    z = 0.0
    rs = [round(r * (f ** i), 3) for i in range(3)]
    for i in range(3):
        z = round(z + h / 2, 3)
        code += add("cylinder", rs[i], (0.0, 0.0, z), "m0", f"Cyl{i}", depth=h)
        z = round(z + h / 2, 3)
    code += add("sphere", 0.3, (0.0, 0.0, round(z + 0.3, 3)), "m1", "Ball")
    cons = [{"t": "count_mesh", "n": 4, "op": "eq"},
            {"t": "touching", "a": "Cyl1", "b": "Cyl0", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Cyl2", "b": "Cyl1", "axis": "z",
             "tol": 0.05},
            {"t": "touching", "a": "Ball", "b": "Cyl2", "axis": "z",
             "tol": 0.05},
            {"t": "size_ratio", "a": "Cyl0", "b": "Cyl1", "axis": "x",
             "ratio": round(1 / f, 3), "tol": 0.12},
            {"t": "mat_color", "a": "Cyl0", "color": cs[0]},
            {"t": "mat_color", "a": "Ball", "color": cbl[0]}]
    return (f"Stack three {cs[0]} cylinders of height {h}, each one "
            f"{f}x the radius of the one below (bottom radius {r}), one on "
            f"top of another, and top the stack with {art(cbl[0])} "
            f"{cbl[0]} sphere of radius 0.3."), code, cons


def h14_sphere_pair_cube(pal, rng):
    r = rng.choice([0.5, 0.6])
    r2 = round(1.5 * r, 3)
    ca, cb, cc = pal[0], pal[1], pal[2]
    code = (mdef("m0", ca[1]) + "\n" + mdef("m1", cb[1]) + "\n"
            + mdef("m2", cc[1]) + "\n")
    code += add("sphere", r, (-2.2, 0.0, 1.2), "m0", "BallA")
    code += add("sphere", r2, (2.2, 0.0, 1.2), "m1", "BallB")
    code += add("cube", 0.6, (0.0, 0.0, 0.3), "m2", "Mid")
    cons = [{"t": "count_mesh", "n": 3, "op": "eq"},
            {"t": "size_ratio", "a": "BallB", "b": "BallA", "axis": "x",
             "ratio": 1.5, "tol": 0.12},
            {"t": "rel_xy", "a": "BallA", "b": "BallB", "axis": "x",
             "op": "left", "tol": 0.3},
            {"t": "rel_xy", "a": "Mid", "b": "BallA", "axis": "x",
             "op": "right", "tol": 0.3},
            {"t": "rel_xy", "a": "Mid", "b": "BallB", "axis": "x",
             "op": "left", "tol": 0.3},
            {"t": "same_z", "a": "BallA", "b": "BallB", "tol": 0.03},
            {"t": "mat_color", "a": "BallA", "color": ca[0]},
            {"t": "mat_color", "a": "BallB", "color": cb[0]}]
    return (f"Two spheres floating at the same height: {art(ca[0])} "
            f"{ca[0]} one of radius {r} on the left, {art(cb[0])} {cb[0]} "
            f"one of radius {r2} (1.5x bigger) on the right, and a small "
            f"{cc[0]} cube on the ground exactly between them."), code, cons


def h15_cone_on_cube(pal, rng):
    s = rng.choice([1.6, 2.0])
    d = rng.choice([0.6, 0.8])
    cc, cco = pal[0], pal[1]
    code = mdef("m0", cc[1]) + "\n" + mdef("m1", cco[1]) + "\n"
    code += add("cube", s, (0.0, 0.0, round(s / 2, 3)), "m0", "Base")
    code += add("cone", round(s / 2, 3), (0.0, 0.0, round(s + d / 2, 3)),
                "m1", "Top", depth=d)
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "touching", "a": "Top", "b": "Base", "axis": "z",
             "tol": 0.05},
            {"t": "size_ratio", "a": "Top", "b": "Base", "axis": "x",
             "ratio": 1.0, "tol": 0.1},
            {"t": "rel_xy", "a": "Top", "b": "Base", "axis": "x",
             "op": "aligned_x", "tol": 0.03},
            {"t": "mat_color", "a": "Base", "color": cc[0]},
            {"t": "mat_color", "a": "Top", "color": cco[0]}]
    return (f"Put {art(cc[0])} {cc[0]} cube of size {s} on the ground and a "
            f"{cco[0]} cone of depth {d} and base diameter equal to the cube "
            f"width on top of it, centered on the cube."), code, cons


def h16_metal_vs_rubber(pal, rng):
    r = rng.choice([0.9, 1.1])
    cm, crb = pal[0], pal[1]
    code = mdef("m0", cm[1], metallic=1.0, rough=0.15) + "\n"
    code += mdef("m1", crb[1], metallic=0.0, rough=0.9) + "\n"
    code += add("sphere", r, (-1.8, 0.0, 1.2), "m0", "Metal")
    code += add("sphere", r, (1.8, 0.0, 1.2), "m1", "Rubber")
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "mat_prop", "a": "Metal", "prop": "metallic", "op": "ge",
             "v": 0.85},
            {"t": "mat_prop", "a": "Metal", "prop": "rough", "op": "le",
             "v": 0.35},
            {"t": "mat_prop", "a": "Rubber", "prop": "metallic", "op": "le",
             "v": 0.15},
            {"t": "mat_prop", "a": "Rubber", "prop": "rough", "op": "ge",
             "v": 0.7},
            {"t": "same_z", "a": "Metal", "b": "Rubber", "tol": 0.03},
            {"t": "mat_color", "a": "Metal", "color": cm[0]},
            {"t": "mat_color", "a": "Rubber", "color": crb[0]}]
    return (f"Two {r}-radius spheres floating side by side at the same "
            f"height: the left {cm[0]} one must be fully metallic and glossy "
            f"(metallic ~1, roughness ~0.15), the right {crb[0]} one matte "
            f"rubber (metallic 0, roughness ~0.9)."), code, cons


def h17_color_positions(pal, rng):
    order = list(pal[:3])
    rng.shuffle(order)
    code = "".join(mdef(f"m{i}", order[i][1]) + "\n" for i in range(3))
    xs = (-2.2, 0.0, 2.2)
    names = ("Left", "Center", "Right")
    for i in range(3):
        code += add("cube", 1.0, (xs[i], 0.0, 0.6), f"m{i}", names[i],
                    scale=(1.2, 1.2, 1.2))
    cons = [{"t": "count_mesh", "n": 3, "op": "eq"}]
    for i in range(3):
        cons.append({"t": "mat_color", "a": names[i], "color": order[i][0]})
    cons += [
        {"t": "rel_xy", "a": "Left", "b": "Center", "axis": "x",
         "op": "left", "tol": 0.3},
        {"t": "rel_xy", "a": "Right", "b": "Center", "axis": "x",
         "op": "right", "tol": 0.3},
        {"t": "same_z", "a": "Left", "b": "Right", "tol": 0.03}]
    return (f"Place three cubes of size 1.2 in a row along X (left, center, "
            f"right), all on the ground: the left one {order[0][0]}, the "
            f"center one {order[1][0]}, the right one {order[2][0]}.",
            code, cons)


def h18_emissive_sign(pal, rng):
    cfr, cem = pal[0], pal[1]
    code = mdef("m0", cfr[1], rough=0.6) + "\n"
    code += mdef("m1", cem[1], emit=5.0) + "\n"
    code += add("cube", 1.0, (0.0, 0.3, 1.6), "m0", "Frame",
                scale=(2.6, 0.2, 1.4))
    code += add("cube", 1.0, (0.0, 0.0, 1.6), "m1", "Panel",
                scale=(2.0, 0.15, 0.9))
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "rel_xy", "a": "Panel", "b": "Frame", "axis": "y",
             "op": "front", "tol": 0.05},
            {"t": "mat_prop", "a": "Panel", "prop": "emit", "op": "ge",
             "v": 3.0},
            {"t": "mat_prop", "a": "Frame", "prop": "emit", "op": "le",
             "v": 0.01},
            {"t": "mat_color", "a": "Panel", "color": cem[0]},
            {"t": "mat_color", "a": "Frame", "color": cfr[0]}]
    return (f"Make a sign: a dark {cfr[0]} frame board standing upright, and "
            f"a glowing {cem[0]} emissive panel (emission >= 3) mounted in "
            f"front of the frame, facing the default camera side (-Y), "
            f"slightly smaller than the frame."), code, cons


def h19_glossy_floor(pal, rng):
    cf, co = pal[0], pal[1]
    code = mdef("m0", cf[1], rough=0.1) + "\n"
    code += mdef("m1", co[1], rough=0.9) + "\n"
    code += add("plane", 8.0, (0.0, 0.0, 0.0), "m0", "Floor")
    code += add("cube", 1.2, (0.0, 0.0, 0.6), "m1", "Crate")
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "touching", "a": "Crate", "b": "Floor", "axis": "z",
             "tol": 0.05},
            {"t": "mat_prop", "a": "Floor", "prop": "rough", "op": "le",
             "v": 0.25},
            {"t": "mat_prop", "a": "Crate", "prop": "rough", "op": "ge",
             "v": 0.7},
            {"t": "mat_color", "a": "Floor", "color": cf[0]},
            {"t": "mat_color", "a": "Crate", "color": co[0]}]
    return (f"A large glossy {cf[0]} floor plane (roughness ~0.1) with one "
            f"matte {co[0]} cube (roughness ~0.9, size 1.2) sitting on it.",
            code, cons)


def h20_traffic_light(pal, rng):
    cp = PALETTE
    cols = [cp[0], cp[3], cp[2]]   # red, yellow, green
    code = mdef("m0", (0.2, 0.2, 0.22)) + "\n"
    for i in range(3):
        code += mdef(f"m{i + 1}", cols[i][1], emit=1.5) + "\n"
    code += add("cylinder", 0.08, (0.0, 0.0, 1.4), "m0", "Pole", depth=2.8)
    zs = (3.0, 2.4, 1.8)
    names = ("Red", "Yellow", "Green")
    for i in range(3):
        code += add("sphere", 0.25, (0.35, 0.0, zs[i]), f"m{i + 1}", names[i])
    cons = [{"t": "count_mesh", "n": 4, "op": "eq"},
            {"t": "mat_color", "a": "Red", "color": "red", "tol": 0.45},
            {"t": "mat_color", "a": "Yellow", "color": "yellow", "tol": 0.45},
            {"t": "mat_color", "a": "Green", "color": "green", "tol": 0.45},
            {"t": "rel_z", "a": "Red", "b": "Yellow", "op": "above",
             "tol": 0.2},
            {"t": "rel_z", "a": "Yellow", "b": "Green", "op": "above",
             "tol": 0.2},
            {"t": "rel_xy", "a": "Red", "b": "Pole", "axis": "x",
             "op": "right", "tol": 0.1}]
    return ("A traffic light: a dark pole with three glowing lamp spheres "
            "beside it — red on top, yellow in the middle, green at the "
            "bottom, all slightly offset to the +X side of the pole.",
            code, cons)


def h21_cam_front(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += 'CAM_LOC = (0.0, -9.0, 3.0)\nCAM_TGT = (0.0, 0.0, 1.0)\n'
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "cam", "azim": [255, 285], "elev": [5, 35]},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.5}]
    return (f"A single {c[0]} cube (size 2) at the origin, viewed by a "
            f"camera positioned straight in front of it (-Y side, azimuth "
            f"270 +/- 15 degrees, elevation 5-35 degrees), looking at the "
            f"cube center."), code, cons


def h22_cam_side(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += 'CAM_LOC = (-9.0, 0.0, 3.0)\nCAM_TGT = (0.0, 0.0, 1.0)\n'
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "cam", "azim": [165, 195], "elev": [5, 35]},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.5}]
    return (f"A single {c[0]} cube (size 2) at the origin, viewed from "
            f"directly behind-left (camera azimuth 180 +/- 15 degrees, "
            f"elevation 5-35 degrees) looking at the cube center.",
            code, cons)


def h23_cam_topdown(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += 'CAM_LOC = (0.0, -0.3, 10.0)\nCAM_TGT = (0.0, 0.0, 1.0)\n'
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "cam", "azim": [240, 300], "elev": [70, 90]},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.5}]
    return (f"A single {c[0]} cube (size 2) at the origin, viewed almost "
            f"straight from above (camera elevation 70-90 degrees, azimuth "
            f"about 270), looking down at the cube."), code, cons


def h24_cam_orbit(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += 'CAM_LOC = (6.5, -6.5, 5.0)\nCAM_TGT = (0.0, 0.0, 1.0)\n'
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "cam", "azim": [300, 330], "elev": [20, 45]},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.5}]
    return (f"A single {c[0]} cube (size 2) at the origin, camera at a "
            f"front-right elevated 3/4 view (azimuth 315 +/- 15, elevation "
            f"20-45 degrees) looking at the cube center."), code, cons


def h25_cam_low(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += 'CAM_LOC = (0.0, -9.0, 1.4)\nCAM_TGT = (0.0, 0.0, 1.0)\n'
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "cam", "azim": [255, 285], "elev": [0, 10]},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.4}]
    return (f"A single {c[0]} cube (size 2) at the origin, camera almost at "
            f"ground level in front (azimuth 270 +/- 15, elevation 0-10 "
            f"degrees) looking straight at the cube."), code, cons


def h26_three_point_light(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += ('EXTRA_LIGHTS = [\n'
             '    ("AREA", (-4.0, -4.0, 6.0), 300.0, (math.radians(35), 0.0, math.radians(-45))),\n'
             '    ("AREA", (4.0, -4.0, 4.0), 120.0, (math.radians(45), 0.0, math.radians(45))),\n'
             '    ("SPOT", (0.0, 5.0, 5.0), 500.0, (math.radians(-40), 0.0, 0.0)),\n'
             ']\n')
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "light", "kind": "AREA", "op": "ge", "n": 2},
            {"t": "light", "kind": "SPOT", "op": "ge", "n": 1},
            {"t": "light", "kind": "AREA", "op": "ge", "n": 1,
             "energy": [80, 400]}]
    return (f"A {c[0]} cube (size 2) at the origin lit by a classic "
            f"three-point rig: two AREA lights on the front-left and "
            f"front-right (key brighter ~300W, fill dimmer ~120W) and one "
            f"SPOT from behind as rim light (~500W). The default sun stays.",
            code, cons)


def h27_spot_accent(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("sphere", 1.0, (0.0, 0.0, 1.0), "m0", "Statue")
    code += ('EXTRA_LIGHTS = [\n'
             '    ("SPOT", (0.0, 0.0, 7.0), 900.0, (0.0, 0.0, 0.0)),\n'
             ']\nSUN_ENERGY = 0.5\n')
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "light", "kind": "SPOT", "op": "ge", "n": 1,
             "energy": [500, 1200]},
            {"t": "light", "kind": "SUN", "op": "eq", "n": 1,
             "energy": [0.1, 1.0]},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.35}]
    return (f"A {c[0]} sphere statue (radius 1) at the origin under a "
            f"dramatic spotlight: one SPOT light directly above it (~900W, "
            f"pointing straight down) and the ambient sun dimmed to about "
            f"0.5 so the spot dominates."), code, cons


def h28_dim_scene(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1], emit=1.0) + "\n"
    code += add("sphere", 0.8, (0.0, 0.0, 1.6), "m0", "Orb")
    code += 'SUN_ENERGY = 0.3\n'
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "light", "kind": "SUN", "op": "eq", "n": 1,
             "energy": [0.1, 0.8]},
            {"t": "mat_prop", "a": "Orb", "prop": "emit", "op": "ge",
             "v": 0.8},
            {"t": "pixel_region", "region": [0.4, 0.4, 0.6, 0.6],
             "color": c[0], "frac": 0.3}]
    return (f"A dark night scene: sun dimmed to ~0.3, and one strongly "
            f"emissive {c[0]} orb (radius 0.8, emission >= 0.8) floating at "
            f"the center as the only real light source."), code, cons


def h29_two_suns(pal, rng):
    c = pal[0]
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", 2.0, (0.0, 0.0, 1.0), "m0", "Subject")
    code += ('EXTRA_LIGHTS = [\n'
             '    ("SUN", (0.0, 0.0, 8.0), 3.0,\n'
             '     (math.radians(-50), 0.0, math.radians(210))),\n'
             ']\nSUN_ENERGY = 3.0\n')
    cons = [{"t": "count_mesh", "n": 1, "op": "eq"},
            {"t": "light", "kind": "SUN", "op": "ge", "n": 2},
            {"t": "light", "kind": "SUN", "op": "ge", "n": 2,
             "energy": [1.5, 4.5]}]
    return (f"A {c[0]} cube (size 2) lit by TWO suns of similar intensity "
            f"(~3 each) coming from opposite azimuths (one from front-right, "
            f"one from back-left), so shadows partially cancel out.",
            code, cons)


def h30_composite_rig(pal, rng):
    ca, cb = pal[0], pal[1]
    code = mdef("m0", ca[1]) + "\n" + mdef("m1", cb[1]) + "\n"
    code += add("cube", 1.0, (0.0, 0.0, 0.5), "m0", "Stage",
                scale=(3.0, 3.0, 1.0))
    code += add("cylinder", 0.4, (0.0, 0.0, 2.1), "m1", "Column", depth=2.2)
    code += ('EXTRA_LIGHTS = [\n'
             '    ("AREA", (-3.0, -3.0, 5.5), 250.0,\n'
             '     (math.radians(35), 0.0, math.radians(-45))),\n'
             ']\nCAM_LOC = (7.0, -7.0, 4.5)\nCAM_TGT = (0.0, 0.0, 1.5)\n')
    cons = [{"t": "count_mesh", "n": 2, "op": "eq"},
            {"t": "touching", "a": "Column", "b": "Stage", "axis": "z",
             "tol": 0.05},
            {"t": "cam", "azim": [300, 330], "elev": [12, 35]},
            {"t": "light", "kind": "AREA", "op": "ge", "n": 1,
             "energy": [150, 400]},
            {"t": "mat_color", "a": "Stage", "color": ca[0]},
            {"t": "mat_color", "a": "Column", "color": cb[0]}]
    return (f"A small stage set: a wide {ca[0]} platform (3x3x1) with a "
            f"{cb[0]} cylinder column standing on its center, one AREA key "
            f"light from the front-left (~250W), and a 3/4 camera view "
            f"(azimuth 315 +/- 15, elevation 12-35) framing the whole set.",
            code, cons)


HARD_TASKS = [
    ("h01_row_balls", h01_row_of_balls), ("h02_pyramid", h02_pyramid_blocks),
    ("h03_bookshelf", h03_bookend_shelf), ("h04_fence", h04_fence),
    ("h05_stairs_ball", h05_stairs_banister),
    ("h06_sphere_cube", h06_sphere_on_cube), ("h07_arch_gate", h07_arch_gate),
    ("h08_hanging_lamp", h08_hanging_lamp),
    ("h09_towers_bridge", h09_towers_bridge),
    ("h10_stack4", h10_stacked_shapes), ("h11_big_small", h11_big_small_pair),
    ("h12_nested_cubes", h12_nested_cubes),
    ("h13_stack3", h13_shrinking_stack),
    ("h14_spheres_mid", h14_sphere_pair_cube),
    ("h15_cone_cube", h15_cone_on_cube),
    ("h16_metal_rubber", h16_metal_vs_rubber),
    ("h17_color_positions", h17_color_positions),
    ("h18_sign", h18_emissive_sign), ("h19_floor_crate", h19_glossy_floor),
    ("h20_traffic", h20_traffic_light), ("h21_cam_front", h21_cam_front),
    ("h22_cam_side", h22_cam_side), ("h23_cam_top", h23_cam_topdown),
    ("h24_cam_orbit", h24_cam_orbit), ("h25_cam_low", h25_cam_low),
    ("h26_3point", h26_three_point_light), ("h27_spot", h27_spot_accent),
    ("h28_night", h28_dim_scene), ("h29_two_suns", h29_two_suns),
    ("h30_stage", h30_composite_rig),
]


def gen_rows_hard():
    """90 cap: seed = 6000 + ti*97 + v (khong trung old/mui2)."""
    rows = []
    for ti, (tname, fn) in enumerate(HARD_TASKS):
        for v in range(VARIANTS):
            seed = 6000 + ti * 97 + v
            pal = rotate_palette((ti * 5 + v * 3) % len(PALETTE))
            rng = random.Random(seed)
            instr, code, cons = fn(pal, rng)
            rows.append({"id": f"{tname}_v{v}", "task": tname, "variant": v,
                         "seed": seed, "instruction": instr,
                         "constraints": cons,
                         "script": PREFIX + code + TAIL})
    return rows


# ---------------------------------------------------------------- verify

PAL_MAP = {name: rgb for name, rgb in PALETTE}
AX = {"x": 0, "y": 1, "z": 2}


def _dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _disp(c):
    """Linear -> display space (sRGB encode).

    Pixel PNG di qua view transform Standard = clamp + sRGB encode;
    palette la gia tri linear cua vat lieu -> phai encode moi so duoc.
    (TASK-16 v4: bug cu so linear vs display => pixel_region fail gia.)
    """
    out = []
    for v in c:
        v = max(0.0, min(1.0, v))
        out.append(12.92 * v if v <= 0.0031308
                   else 1.055 * (v ** (1.0 / 2.4)) - 0.055)
    return tuple(out)


def _deg(r):
    d = math.degrees(r) % 360.0
    return d - 360.0 if d > 180.0 else d


def load_png(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    return im


def check_one(c, objs, scene, im):
    """Kiem tra 1 constraint. Tra ve (ok, detail). objs = {ten: dict}."""
    t = c["t"]

    if t == "count_mesh":
        n = sum(1 for o in objs.values() if o.get("type") == "MESH")
        ok = {"eq": n == c["n"], "ge": n >= c["n"], "le": n <= c["n"]}[c["op"]]
        return ok, f"count_mesh={n} want {c['op']} {c['n']}"

    if t == "rel_z":
        a, b = objs[c["a"]], objs[c["b"]]
        d = a["loc"][2] - b["loc"][2]
        ok = d > c["tol"] if c["op"] == "above" else d < -c["tol"]
        return ok, f"z({c['a']})-z({c['b']})={d:.3f} want {c['op']}"

    if t == "rel_xy":
        a, b = objs[c["a"]], objs[c["b"]]
        i = AX[c["axis"]]
        d = a["loc"][i] - b["loc"][i]
        tol = c["tol"]
        ok = {"left": d < -tol, "right": d > tol,
              "front": d < -tol, "behind": d > tol,
              "aligned_x": abs(d) <= tol, "aligned_y": abs(d) <= tol}[c["op"]]
        return ok, f"{c['axis']}({c['a']})-{c['axis']}({c['b']})={d:.3f} " \
                   f"want {c['op']}"

    if t == "same_z":
        a, b = objs[c["a"]], objs[c["b"]]
        d = abs(a["loc"][2] - b["loc"][2])
        return d <= c["tol"], f"|z diff|={d:.3f} tol {c['tol']}"

    if t == "touching":
        a, b = objs[c["a"]], objs[c["b"]]
        i = AX[c["axis"]]
        half_a = a.get("dims", [0, 0, 0])[i] / 2
        half_b = b.get("dims", [0, 0, 0])[i] / 2
        gap = min(abs((a["loc"][i] - half_a) - (b["loc"][i] + half_b)),
                  abs((b["loc"][i] - half_b) - (a["loc"][i] + half_a)))
        return gap <= c["tol"], f"gap={gap:.3f} tol {c['tol']}"

    if t == "size_ratio":
        a, b = objs[c["a"]], objs[c["b"]]
        i = AX[c["axis"]]
        da = a.get("dims", [0, 0, 0])[i]
        db = b.get("dims", [0, 0, 0])[i]
        if db <= 1e-6:
            return False, "dim b = 0"
        r = da / db
        return abs(r - c["ratio"]) <= c["tol"], \
            f"ratio={r:.3f} want {c['ratio']}+/-{c['tol']}"

    if t == "bbox_within":
        a, b = objs[c["a"]], objs[c["b"]]
        for i in range(3):
            ha = a.get("dims", [0, 0, 0])[i] / 2
            hb = b.get("dims", [0, 0, 0])[i] / 2
            if abs(a["loc"][i] - b["loc"][i]) + ha > hb + c["tol"]:
                return False, f"axis {i}: off center/dist"
        return True, "inside bbox"

    if t == "mat_color":
        o = objs[c["a"]]
        mats = o.get("mats") or []
        if not mats:
            return False, "no material"
        want = PAL_MAP[c["color"]]
        d = _dist(mats[0]["base"], want)
        return d <= c.get("tol", 0.45), \
            f"color dist={d:.3f} tol {c.get('tol', 0.45)}"

    if t == "mat_prop":
        o = objs[c["a"]]
        mats = o.get("mats") or []
        if not mats:
            return False, "no material"
        v = mats[0][c["prop"]]
        tol = c.get("tol", 0.12)
        ok = {"ge": v >= c["v"] - tol, "le": v <= c["v"] + tol,
              "eq": abs(v - c["v"]) <= tol}[c["op"]]
        return ok, f"{c['prop']}={v} want {c['op']} {c['v']}"

    if t == "cam":
        cam = next((o for o in objs.values() if o.get("type") == "CAMERA"),
                   None)
        if cam is None:
            return False, "no camera"
        tgt = scene.get("target", [0.0, 0.0, 1.6])
        dx = cam["loc"][0] - tgt[0]
        dy = cam["loc"][1] - tgt[1]
        dz = cam["loc"][2] - tgt[2]
        azim = math.degrees(math.atan2(dy, dx)) % 360.0
        elev = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
        lo, hi = c["azim"]
        ok_a = lo <= azim <= hi
        lo, hi = c["elev"]
        ok_e = lo <= elev <= hi
        return ok_a and ok_e, f"azim={azim:.1f} elev={elev:.1f}"

    if t == "light":
        ls = [o for o in objs.values()
              if o.get("type") == "LIGHT"
              and (c["kind"] == "ANY" or o.get("light_type") == c["kind"])]
        if "energy" in c:
            ls = [o for o in ls
                  if c["energy"][0] <= o.get("energy", -1) <= c["energy"][1]]
        n = len(ls)
        ok = {"eq": n == c["n"], "ge": n >= c["n"], "le": n <= c["n"]}[c["op"]]
        return ok, f"lights {c['kind']}={n} want {c['op']} {c['n']}"

    if t == "rot":
        o = objs[c["a"]]
        d = _deg(o["rot"][AX[c["axis"]]])
        lo, hi = c["deg"]
        return lo <= d <= hi, f"rot {c['axis']}={d:.1f} want [{lo},{hi}]"

    if t == "pixel_region":
        x0, y0, x1, y1 = c["region"]
        W, H = im.size
        box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
        crop = im.crop(box)
        # TASK-16 v4: pixel PNG la display-space (sRGB encode), palette la
        # linear -> encode truoc khi so (bug cu: so linear vs display).
        want = _disp(PAL_MAP[c["color"]])
        px = list(crop.getdata())
        n_hit = sum(1 for p in px
                    if _dist([p[0] / 255.0, p[1] / 255.0, p[2] / 255.0],
                             want) <= 0.45)
        frac = n_hit / max(len(px), 1)
        return frac >= c["frac"], f"frac={frac:.2f} want >= {c['frac']}"

    return False, f"unknown constraint {t}"


def check_constraints(row, scene, png_path):
    objs = {o["name"]: o for o in scene.get("objects", [])}
    im = load_png(png_path) if any(
        c["t"] == "pixel_region" for c in row["constraints"]) else None
    out = []
    for c in row["constraints"]:
        try:
            ok, det = check_one(c, objs, scene, im)
        except KeyError as e:
            ok, det = False, f"missing object {e}"
        out.append({"t": c["t"], "ok": bool(ok), "detail": det})
    return out


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
    res = {"id": tid, "rc": rc, "t": round(dt, 1),
           "n_constraints": len(row["constraints"])}
    res["verify_ok"] = "VERIFY_OK" in out
    glb = os.path.join(od, "scene.glb")
    png = os.path.join(od, "render.png")
    sj = os.path.join(od, "scene.json")
    g = glb_stats(glb) if os.path.exists(glb) else None
    res["glb"] = g
    res["glb_bytes"] = os.path.getsize(glb) if os.path.exists(glb) else 0
    res["png_bytes"] = os.path.getsize(png) if os.path.exists(png) else 0
    base_ok = (rc == 0 and res["verify_ok"] and isinstance(g, dict)
               and g.get("meshes", 0) > 0 and g.get("glb_tris", 0) > 0
               and res["png_bytes"] > 2000 and os.path.exists(sj))
    res["checks"] = []
    if base_ok:
        scene = json.load(open(sj))
        res["checks"] = check_constraints(row, scene, png)
        res["n_pass"] = sum(1 for c in res["checks"] if c["ok"])
        res["ok"] = all(c["ok"] for c in res["checks"])
    else:
        res["n_pass"] = 0
        res["ok"] = False
        res["err_tail"] = (err or out)[-700:]
    # DEBUG (DeepSeek, TASK-16): giu render ca pair FAIL de soi pixel_region.
    # Khong doi logic check/ok — chi mo rong copy asset.
    try:
        if os.path.exists(glb):
            shutil.copyfile(glb, os.path.join(WORK, "glb", tid + ".glb"))
        if os.path.exists(png):
            shutil.copyfile(png, os.path.join(WORK, "renders", tid + ".png"))
    except OSError:
        pass
    return res


def main():
    t0 = time.time()
    get_blender()
    for d in ("glb", "renders"):
        os.makedirs(os.path.join(WORK, d), exist_ok=True)
    os.makedirs(TASKS_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = gen_rows_hard()
    log(f"verify {len(rows)} cap hard-30 ({len(HARD_TASKS)} task x "
        f"{VARIANTS} variants)")
    report = []
    for i, row in enumerate(rows, 1):
        res = run_one(row)
        res["task"] = row["task"]
        res["variant"] = row["variant"]
        res["seed"] = row["seed"]
        report.append(res)
        g = res.get("glb") or {}
        log(f"[{i}/{len(rows)}] {res['id']} rc={res['rc']} ok={res['ok']} "
            f"cons={res['n_pass']}/{res['n_constraints']} "
            f"mesh={g.get('meshes')} tris={g.get('glb_tris')} "
            f"png={res['png_bytes']}B t={res['t']}s")
    n_pass = sum(1 for r in report if r["ok"])
    cons_total = sum(r["n_constraints"] for r in report)
    cons_pass = sum(r.get("n_pass", 0) for r in report)
    idx = {name: i for i, (name, _) in enumerate(HARD_TASKS)}
    GROUPS = [("pos_count", range(0, 15)), ("material", range(15, 20)),
              ("camera", range(20, 25)), ("lighting", range(25, 29)),
              ("composite", range(29, 30))]
    by_group = {}
    for gname, rng_ in GROUPS:
        rs = [r for r in report if idx[r["task"]] in rng_]
        by_group[gname] = {"n": len(rs),
                           "n_pass": sum(1 for r in rs if r["ok"])}
    summary = {
        "n_pairs": len(report), "n_pass": n_pass,
        "n_fail": len(report) - n_pass,
        "pass_rate": round(n_pass / max(len(report), 1), 3),
        "constraints_total": cons_total, "constraints_pass": cons_pass,
        "constraint_pass_rate": round(cons_pass / max(cons_total, 1), 3),
        "by_group": by_group, "bver": BVER,
        "t_sec": round(time.time() - t0),
    }
    with open(os.path.join(WORK, "hard_report.json"), "w") as f:
        json.dump({"summary": summary, "pairs": report}, f, indent=2)
    by_id = {r["id"]: r for r in rows}
    with open(os.path.join(WORK, "rows_hard.jsonl"), "w") as f:
        for res in report:
            if res["ok"]:
                r = by_id[res["id"]]
                f.write(json.dumps({
                    "id": r["id"], "task": r["task"], "variant": r["variant"],
                    "instruction": r["instruction"],
                    "constraints": r["constraints"],
                    "script": r["script"],
                    "glb_tris": (res.get("glb") or {}).get("glb_tris")}
                    ) + "\n")
    log(f"SUMMARY {json.dumps(summary)}")
    if summary["n_fail"]:
        log(f"CANH BAO: {summary['n_fail']} cap FAIL — xem pairs[].err_tail/"
            f"checks trong hard_report.json")


if __name__ == "__main__":
    main()




