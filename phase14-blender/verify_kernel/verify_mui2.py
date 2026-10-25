"""Verify kernel CPU — 45 cap MUI2 (15 task moi x 3 variants) — TASK-7 (MiMo).

- Pipeline verify GIONG XI blender_gen.py: rc=0 + VERIFY_OK + parse GLB
  (meshes>0, glb_tris>0) + render png > 2KB; moi script chay trong 1 tien trinh
  Blender rieng (isolate + timeout 240s).
- 15 emitter: lay NGUYEN Appendix A cua mui2_tasklist_draft.md (da dry-run
  45/45 compile/bounds/dedupe). Helper PREFIX/TAIL/PALETTE/mdef/add/rotz/
  rotate_palette + glb_stats/run_one: lay NGUYEN gen_kernel/blender_gen.py
  (kernel da PASS 87/87). KHONG sua file cu — verify nay chi tao file moi.
- Seed/palette = dung NGUYEN cong thuc merge cua blender_gen.py (TASKS =
  TASKS + NEW_TASKS_MUI2, enumerate tren danh sach GOP, OLD_TASK_COUNT=29):
      pal   = rotate_palette(((29 + ti) * 5 + v * 3) % 10)
      seed  = 1000 + (29 + ti) * 97 + v
  -> 45 row o day = 45 row ma blender_gen_v2.py se sinh khi append block
     NEW_TASKS_MUI2 vao cuoi TASKS (da chung minh bang check equivalence chay
     local vs mui2_draft_check.py). Moi row ghi task/variant/seed/goi (A/B1/B2)
     vao report de trace tung cap.
- Internet: uu tien OFF. get_blender() tim tarball blender-*.tar.xz trong
  /kaggle/input TRUOC (attach dataset chua tarball la chay offline 100%);
  chi download (internet ON) khi khong tim thay.
- Output: /kaggle/working/blend_verify/verify_report.json (summary + 45 pairs
  chi tiet: rc/verify_ok/meshes/glb_tris/glb_bytes/png_bytes/err_tail) +
  rows_mui2.jsonl (chi row PASS — dung de so sanh vs v2 khi merge) +
  glb/ + renders/ (artifact de nhin tay).
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
WORK = "/kaggle/working/blend_verify"
TASKS_DIR = "/tmp/verify_tasks"
OUT_DIR = "/tmp/verify_out"
VARIANTS = 3
TIMEOUT = 240
# so task trong TASKS cua blender_gen.py hien tai (29 task / 87 id) — neu v2
# thay doi TASKS thi phai doi so nay va verify lai.
OLD_TASK_COUNT = 29


def log(m):
    print(f"[verify] {m}", flush=True)



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
    """Uu tien offline: tim blender-*.tar.xz trong cac dataset da attach."""
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
    return PALETTE[off:] + PALETTE[:off]


# ---------------------------------------------------------------- emitters (Appendix A — NGUYEN mau)

def art(w):
    """a/an dung truoc ten mau/color."""
    return "an" if w[:1].lower() in "aeiou" else "a"


# ---------------- GOI A (composition)
def t_staircase(pal, rng):
    c = pal[0]
    n = rng.choice([4, 5, 6])
    step = rng.choice([1.0, 1.2])
    rise = rng.choice([0.6, 0.8])
    code = mdef("m0", c[1]) + "\n"
    x0 = -((n - 1) * step) / 2
    for i in range(n):
        code += add("cube", 1.0, (x0 + i * step, 0.0, rise / 2 + i * rise), "m0",
                    f"S{i}", scale=(step * 0.9, 1.6, rise))
    return (f"Create a staircase with {n} {c[0]} steps rising along X (steps {step} "
            f"apart, each step {rise} taller)."), code


def t_arch(pal, rng):
    a, b = pal[0], pal[1]
    span = rng.choice([3.0, 3.6, 4.2])
    ph = rng.choice([2.6, 3.0])
    pw = rng.choice([0.6, 0.8])
    code = mdef("m0", a[1]) + "\n" + mdef("m1", b[1]) + "\n"
    code += add("cube", 1.0, (-span / 2, 0.0, ph / 2), "m0", "PillarL",
                scale=(pw, pw, ph))
    code += add("cube", 1.0, (span / 2, 0.0, ph / 2), "m0", "PillarR",
                scale=(pw, pw, ph))
    code += add("cube", 1.0, (0.0, 0.0, ph + 0.35), "m1", "Beam",
                scale=(span + pw, 1.0, 0.7))
    return (f"Build an arch gateway: two {a[0]} pillars {span} apart topped by "
            f"{art(b[0])} {b[0]} beam (pillar height {ph})."), code


def t_helix_tower(pal, rng):
    ball, po = pal[0], PALETTE[8]
    cnt = rng.choice([6, 8, 10])
    rad = rng.choice([1.2, 1.4, 1.6])
    rise = rng.choice([0.4, 0.45, 0.55])
    sdeg = rng.choice([45, 60])
    code = mdef("m0", po[1], rough=0.8) + "\n" + mdef("m1", ball[1]) + "\n"
    pole_h = 0.3 + cnt * rise
    code += add("cylinder", 0.12, (0.0, 0.0, pole_h / 2), "m0", "Pole", depth=pole_h)
    for i in range(cnt):
        ang = math.radians(i * sdeg)
        x = round(rad * math.cos(ang), 3)
        y = round(rad * math.sin(ang), 3)
        z = round(0.4 + i * rise, 3)
        code += add("sphere", 0.35, (x, y, z), "m1", f"B{i}")
    return (f"Create a helix of {cnt} {ball[0]} spheres (radius 0.35, orbit radius "
            f"{rad}, rising {rise} per {sdeg} degree step) winding around a brown "
            f"pole."), code


def t_bookshelf(pal, rng):
    frame, sh = pal[0], pal[1]
    w = rng.choice([2.4, 3.0])
    h = rng.choice([3.0, 3.6])
    shelves = rng.choice([2, 3])
    per = rng.choice([3, 4])
    code = mdef("m0", frame[1], rough=0.7) + "\n" + mdef("m1", sh[1], rough=0.7) + "\n"
    code += add("cube", 1.0, (-w / 2, 0.0, h / 2), "m0", "SideL", scale=(0.14, 0.5, h))
    code += add("cube", 1.0, (w / 2, 0.0, h / 2), "m0", "SideR", scale=(0.14, 0.5, h))
    for i in range(shelves + 1):
        code += add("cube", 1.0, (0.0, 0.0, i * (h / shelves)), "m1", f"Sh{i}",
                    scale=(w, 0.5, 0.1))
    bh = h / shelves - 0.3
    nb = 0
    for i in range(shelves):
        base_z = i * (h / shelves) + 0.05
        for j in range(per):
            x = round(-(per - 1) * 0.17 + j * 0.34, 3)
            col = pal[(i + j) % 4]
            code += mdef(f"mB{i}{j}", col[1], rough=0.6) + "\n"
            code += add("cube", 1.0, (x, 0.0, round(base_z + bh / 2, 3)),
                        f"mB{i}{j}", f"B{i}{j}", scale=(0.16, 0.4, round(bh, 3)))
            nb += 1
    return (f"Build a {w} wide {frame[0]} bookshelf {h} tall with {shelves} shelves "
            f"holding {nb} upright books."), code


def t_desk_lamp(pal, rng):
    shade, base_c = pal[0], (0.2, 0.2, 0.22)
    br = rng.choice([0.8, 1.0])
    arm = rng.choice([1.8, 2.1])
    tilt = rng.choice([30, 35, 40])
    s = math.sin(math.radians(tilt))
    ct = math.cos(math.radians(tilt))
    ay = round(arm / 2 * s, 3)
    az = round(0.26 + arm / 2 * ct, 3)
    ty = round(arm * s, 3)
    tz = round(0.26 + arm * ct, 3)
    code = mdef("m0", base_c, rough=0.6) + "\n"
    code += mdef("m1", shade[1], rough=0.45) + "\n"
    code += mdef("m2", (1.0, 0.95, 0.75), emit=5.0) + "\n"
    code += add("cylinder", br, (0.0, 0.0, 0.13), "m0", "Base", depth=0.26)
    code += add("cylinder", 0.09, (0.0, -ay, az), "m0", "Arm", depth=arm,
                rot=f"(math.radians({tilt}), 0.0, 0.0)")
    code += add("cone", 0.5, (0.0, -ty, round(tz + 0.15, 3)), "m1", "Shade", depth=0.8)
    code += add("sphere", 0.17, (0.0, -ty, round(tz - 0.05, 3)), "m2", "Bulb")
    return (f"Build a desk lamp: a dark base of radius {br}, an arm tilted {tilt} "
            f"degrees, {art(shade[0])} {shade[0]} cone shade and a glowing bulb."), code


def t_windmill(pal, rng):
    tw, bl_c = pal[0], pal[1]
    th = rng.choice([2.6, 3.0])
    bl = rng.choice([1.3, 1.6, 1.9])
    bw = rng.choice([0.3, 0.4])
    hz = round(th - 0.4, 3)
    code = mdef("m0", tw[1], rough=0.7) + "\n" + mdef("m1", bl_c[1], rough=0.5) + "\n"
    code += mdef("m2", (0.25, 0.25, 0.28), rough=0.6) + "\n"
    code += add("cone", 1.1, (0.0, 0.0, th / 2), "m0", "Tower", depth=th)
    code += add("cylinder", 0.1, (0.0, -0.38, hz), "m2", "Axle", depth=0.76,
                rot="(math.radians(90), 0.0, 0.0)")
    code += add("sphere", 0.3, (0.0, -0.75, hz), "m2", "Hub")
    reach = round(0.35 + bl / 2, 3)
    for i, beta in enumerate([0, 90, 180, 270]):
        r = math.radians(beta)
        x = round(math.cos(r) * reach, 3)
        z = round(hz - math.sin(r) * reach, 3)
        code += add("cube", 1.0, (x, -0.75, z), "m1", f"Blade{i}",
                    rot=f"(0.0, math.radians({beta}), 0.0)",
                    scale=(bl, 0.16, bw))
    return (f"Build a windmill: {art(tw[0])} {tw[0]} tapered tower {th} tall with a "
            f"front hub and four {bl_c[0]} blades in a cross (blade length {bl})."), code


def t_fountain(pal, rng):
    a, b = pal[0], pal[1]
    br = rng.choice([1.8, 2.2])
    ch = rng.choice([1.2, 1.6])
    code = mdef("m0", a[1], rough=0.6) + "\n" + mdef("m1", b[1], rough=0.5) + "\n"
    code += add("cylinder", br, (0.0, 0.0, 0.3), "m0", "Basin", depth=0.6)
    code += add("cylinder", 0.3, (0.0, 0.0, round(0.6 + ch / 2, 3)), "m1", "Column",
                depth=ch)
    code += add("cylinder", round(br * 0.45, 3), (0.0, 0.0, round(0.6 + ch + 0.15, 3)),
                "m0", "Top", depth=0.3)
    code += add("sphere", 0.35, (0.0, 0.0, round(0.6 + ch + 0.65, 3)), "m1", "Ball")
    return (f"Build a fountain: {art(a[0])} {a[0]} basin of radius {br} with "
            f"{art(b[0])} {b[0]} column ({ch} tall), a small upper basin and a ball "
            f"on top."), code


def t_dominoes(pal, rng):
    c0, c1 = pal[0], pal[1]
    n = rng.choice([4, 5, 6])
    gap = rng.choice([0.7, 0.85])
    dh = rng.choice([1.2, 1.5])
    tip = rng.choice([75, 90])
    t = 0.22
    code = mdef("m0", c0[1], rough=0.5) + "\n" + mdef("m1", c1[1], rough=0.5) + "\n"
    x_last = 0.0
    for i in range(n - 1):
        x = round((i - (n - 1) / 2) * gap, 3)
        code += add("cube", 1.0, (x, 0.0, dh / 2), "m0", f"D{i}", scale=(t, 0.6, dh))
        x_last = x
    r = math.radians(tip)
    half_x = (dh * math.cos(r) + t * math.sin(r)) / 2
    cz = (dh * abs(math.sin(r)) + t * abs(math.cos(r))) / 2
    fx = round(x_last + gap * 0.5 + half_x * 0.9, 3)
    code += add("cube", 1.0, (fx, 0.0, round(cz, 3)), "m1", "Fallen",
                rot=f"(0.0, math.radians({tip}), 0.0)", scale=(t, 0.6, dh))
    return (f"Create {n} {c0[0]} dominoes {dh} tall standing {gap} apart, the last "
            f"one {c1[0]} tipped over at {tip} degrees."), code


# ---------------- GOI B1 (modifier)
def t_boolean_hole(pal, rng):
    c = pal[0]
    size = rng.choice([2.4, 3.0])
    hole = rng.choice([0.7, 0.9])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", size, (0.0, 0.0, size / 2 + 0.01), "m0", "Block")
    code += add("cylinder", hole, (0.0, 0.0, size / 2 + 0.01), "m0", "Cutter",
                depth=size + 1.0, rot="(math.radians(90), 0.0, 0.0)")
    code += ('base = bpy.data.objects["Block"]\n'
             'cut = bpy.data.objects["Cutter"]\n'
             'mod = base.modifiers.new("Cut", "BOOLEAN")\n'
             'mod.operation = "DIFFERENCE"\n'
             'mod.object = cut\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'base.select_set(True)\n'
             'bpy.context.view_layer.objects.active = base\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n'
             'bpy.data.objects.remove(cut, do_unlink=True)\n')
    return (f"Create {art(c[0])} {c[0]} {size} cube with a round hole of radius "
            f"{hole} cut clean through its center (boolean difference with a "
            f"cylinder)."), code


def t_mirror_pair(pal, rng):
    c = pal[0]
    cs = rng.choice([1.6, 2.0])
    off = rng.choice([1.6, 2.0, 2.4])
    code = mdef("m0", c[1]) + "\n"
    code += add("cube", cs, (0.0, 0.0, cs / 2 + 0.01), "m0", "Twin")
    code += (f'for v in bpy.data.objects["Twin"].data.vertices:\n'
             f'    v.co.x += {fmt(off)}\n'
             'o = bpy.data.objects["Twin"]\n'
             'mod = o.modifiers.new("Mir", "MIRROR")\n'
             'mod.use_axis = (True, False, False)\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create {art(c[0])} {c[0]} cube of size {cs} shifted {off} units right "
            f"of center and mirror it across the middle plane to make a symmetric "
            f"pair."), code


def t_twist_column(pal, rng):
    c = pal[0]
    h = rng.choice([2.6, 3.0])
    rad = rng.choice([0.5, 0.65])
    ang = rng.choice([60, 90, 120])
    code = mdef("m0", c[1], rough=0.4) + "\n"
    code += add("cylinder", rad, (0.0, 0.0, h / 2), "m0", "Col", depth=h)
    code += ('mod = o.modifiers.new("Tw", "SIMPLE_DEFORM")\n'
             'mod.deform_method = "TWIST"\n'
             'mod.deform_axis = "Z"\n'
             f'mod.angle = math.radians({ang})\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create {art(c[0])} {c[0]} column of radius {rad} and height {h} "
            f"twisted {ang} degrees along its vertical axis."), code


def t_wireframe_globe(pal, rng):
    c = pal[0]
    rad = rng.choice([1.4, 1.6, 1.8])
    th = rng.choice([0.05, 0.07, 0.1])
    code = mdef("m0", c[1], metallic=0.6, rough=0.35) + "\n"
    code += add("sphere", rad, (0.0, 0.0, rad), "m0", "Globe")
    code += ('mod = o.modifiers.new("Wire", "WIREFRAME")\n'
             f'mod.thickness = {th}\n'
             'mod.use_replace = True\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Turn {art(c[0])} {c[0]} sphere of radius {rad} into a hollow wireframe "
            f"globe with wire thickness {th}."), code


def t_decimate_rock(pal, rng):
    c = pal[0]
    rad = rng.choice([1.1, 1.3])
    squash = rng.choice([(1.5, 1.0, 0.7), (1.3, 1.1, 0.8)])
    ratio = rng.choice([0.2, 0.3, 0.4])
    code = mdef("m0", c[1], rough=0.9) + "\n"
    code += (f'bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius={rad}, '
             'location=(0.0, 0.0, 1.0))\n'
             'o = bpy.context.active_object\n'
             'o.name = "Rock"\n'
             f'o.scale = {fmt(squash)}\n'
             'o.data.materials.append(m0)\n'
             'mod = o.modifiers.new("Dec", "DECIMATE")\n'
             f'mod.ratio = {ratio}\n'
             'bpy.ops.object.select_all(action="DESELECT")\n'
             'o.select_set(True)\n'
             'bpy.context.view_layer.objects.active = o\n'
             'bpy.ops.object.modifier_apply(modifier=mod.name)\n')
    return (f"Create a low-poly {c[0]} rock: a squashed icosphere (radius {rad}, "
            f"scaled {squash[0]} x {squash[1]} x {squash[2]}) decimated to {ratio} "
            f"of its triangles."), code


# ---------------- GOI B2 (FONT/CURVE -> MESH)
def t_text_3d(pal, rng):
    c = pal[0]
    word = rng.choice(["ORNITH", "BLENDER", "MESH", "GLTF"])
    size = rng.choice([0.9, 1.1])
    ext = rng.choice([0.05, 0.08])
    code = mdef("m0", c[1], metallic=0.2, rough=0.4) + "\n"
    code += ('bpy.ops.object.text_add(location=(0.0, 0.0, 1.5), '
             'rotation=(math.radians(90), 0.0, math.radians(45)))\n'
             'o = bpy.context.active_object\n'
             'o.name = "Label"\n'
             f'o.data.body = "{word}"\n'
             f'o.data.size = {size}\n'
             f'o.data.extrude = {ext}\n'
             'o.data.align_x = "CENTER"\n'
             'o.data.align_y = "CENTER"\n'
             'bpy.ops.object.convert(target="MESH")\n'
             'o = bpy.context.active_object\n'
             'o.data.materials.append(m0)\n')
    return (f"Create the {c[0]} 3D word \"{word}\" standing upright and centered, "
            f"text size {size} and extruded {ext}."), code


def t_curve_tube(pal, rng):
    c = pal[0]
    tr = rng.choice([0.12, 0.16])
    dz = rng.choice([0.5, 0.8])
    code = mdef("m0", c[1], metallic=0.7, rough=0.3) + "\n"
    code += ('bpy.ops.curve.primitive_bezier_curve_add(location=(0.0, 0.0, 1.5))\n'
             'o = bpy.context.active_object\n'
             'o.name = "Tube"\n'
             'sp = o.data.splines[0]\n'
             'bp = sp.bezier_points\n'
             f'bp[0].co = (-2.2, 0.0, -{dz})\n'
             f'bp[1].co = (2.2, 0.0, {dz})\n'
             'for p in bp:\n'
             '    p.handle_left_type = "AUTO"\n'
             '    p.handle_right_type = "AUTO"\n'
             f'o.data.bevel_depth = {tr}\n'
             'o.data.bevel_resolution = 4\n'
             'o.data.use_fill_caps = True\n'
             'bpy.ops.object.convert(target="MESH")\n'
             'o = bpy.context.active_object\n'
             'o.data.materials.append(m0)\n')
    return (f"Create a smooth {c[0]} arc tube from a beveled bezier curve, running "
            f"along X and rising from z=-{dz} to z={dz} at height 1.5 (wire radius "
            f"{tr})."), code


NEW_TASKS_MUI2 = [
    ("staircase", t_staircase), ("arch", t_arch), ("helix_tower", t_helix_tower),
    ("bookshelf", t_bookshelf), ("desk_lamp", t_desk_lamp),
    ("windmill", t_windmill), ("fountain", t_fountain), ("dominoes", t_dominoes),
    ("boolean_hole", t_boolean_hole), ("mirror_pair", t_mirror_pair),
    ("twist_column", t_twist_column), ("wireframe_globe", t_wireframe_globe),
    ("decimate_rock", t_decimate_rock), ("text_3d", t_text_3d),
    ("curve_tube", t_curve_tube),
]
# Goi vao file v2 (KHONG sua file cu):  TASKS = TASKS + NEW_TASKS_MUI2


# ---------------------------------------------------------------- 45 rows
GOI = (["A"] * 8) + (["B1"] * 5) + (["B2"] * 2)   # theo thu tu NEW_TASKS_MUI2


def gen_rows_mui2():
    """45 row — seed/palette theo NGUYEN cong thuc merge cua blender_gen.py."""
    rows = []
    for ti, (tname, fn) in enumerate(NEW_TASKS_MUI2):
        for v in range(VARIANTS):
            k = OLD_TASK_COUNT + ti
            pal = rotate_palette((k * 5 + v * 3) % len(PALETTE))
            seed = 1000 + k * 97 + v
            rng = random.Random(seed)
            instr, code = fn(pal, rng)
            script = PREFIX + code + TAIL
            rows.append({"id": f"{tname}_v{v}", "task": tname, "variant": v,
                         "seed": seed, "goi": GOI[ti], "instruction": instr,
                         "script": script})
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
    rows = gen_rows_mui2()
    log(f"verify {len(rows)} cap mui2 ({len(NEW_TASKS_MUI2)} task x "
        f"{VARIANTS} variants, OLD_TASK_COUNT={OLD_TASK_COUNT})")
    report = []
    for i, row in enumerate(rows, 1):
        res = run_one(row)
        res["task"] = row["task"]
        res["variant"] = row["variant"]
        res["seed"] = row["seed"]
        res["goi"] = row["goi"]
        report.append(res)
        g = res.get("glb") or {}
        log(f"[{i}/{len(rows)}] {res['id']} goi={res['goi']} rc={res['rc']} "
            f"ok={res['ok']} mesh={g.get('meshes')} tris={g.get('glb_tris')} "
            f"png={res['png_bytes']}B t={res['t']}s")
    n_pass = sum(1 for r in report if r["ok"])
    by_goi = {}
    for goi in ("A", "B1", "B2"):
        rs = [r for r in report if r["goi"] == goi]
        by_goi[goi] = {"n": len(rs), "n_pass": sum(1 for r in rs if r["ok"])}
    summary = {
        "n_pairs": len(report),
        "n_pass": n_pass,
        "n_fail": len(report) - n_pass,
        "pass_rate": round(n_pass / max(len(report), 1), 3),
        "by_goi": by_goi,
        "bver": BVER,
        "old_task_count": OLD_TASK_COUNT,
        "t_sec": round(time.time() - t0),
    }
    with open(os.path.join(WORK, "verify_report.json"), "w") as f:
        json.dump({"summary": summary, "pairs": report}, f, indent=2)
    by_id = {r["id"]: r for r in rows}
    with open(os.path.join(WORK, "rows_mui2.jsonl"), "w") as f:
        for res in report:
            if res["ok"]:
                r = by_id[res["id"]]
                f.write(json.dumps({
                    "id": r["id"], "task": r["task"], "variant": r["variant"],
                    "goi": r["goi"], "instruction": r["instruction"],
                    "script": r["script"],
                    "glb_tris": (res.get("glb") or {}).get("glb_tris")}) + "\n")
    log(f"SUMMARY {json.dumps(summary)}")
    if summary["n_fail"]:
        log(f"CANH BAO: {summary['n_fail']} cap FAIL — xem pairs[].err_tail "
            f"trong verify_report.json")


if __name__ == "__main__":
    main()
