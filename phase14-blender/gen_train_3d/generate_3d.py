"""generate_3d.py - sinh DU LIEU TRAIN 3D (grounding) tren Kaggle CPU.

Muc dich: day model "nhin anh 3D -> click doi tuong" bang CHUNG action space
voi GUI (CLICK x y, toa do 0..1000) => ky nang grounding chung 2D/3D.

Output (kaggle/working/blend3d/):
  train3d.jsonl  : {"image", "instruction", "action", "family", "color", "shape"}
  shots/*.png    : anh render
Chay: python generate_3d.py [--n 300] [--seed 7]
"""
import argparse
import json
import os
import random
import subprocess
import sys
import tarfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# --- BEGIN BLENDER_SCRIPT (embed) ---
BLENDER_SCRIPT = r'''import json
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view

OUT = os.environ["BLEND_OUT"]
SPEC = os.environ["BLEND_SPEC"]
W = H = 320

with open(SPEC, "r", encoding="utf-8") as fh:
    scenes = json.load(fh)

os.makedirs(OUT, exist_ok=True)
results = []

for sc in scenes:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # --- vat lieu
    for ob in sc["objects"]:
        shape = ob["shape"]
        if shape == "cube":
            bpy.ops.mesh.primitive_cube_add(size=2.0, location=ob["loc"])
        elif shape == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0,
                                                 location=ob["loc"])
        else:
            bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0,
                                                location=ob["loc"])
        o = bpy.context.object
        o.name = ob["name"]
        o.scale = (ob["size"], ob["size"], ob["size"])
        o.rotation_euler = (0.0, 0.0, ob.get("rot", 0.0))
        mat = bpy.data.materials.new("M_" + ob["name"])
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (ob["color"][0],
                                                   ob["color"][1],
                                                   ob["color"][2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.55
        o.data.materials.append(mat)

    # --- san
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0, 0, 0))
    g = bpy.context.object
    gm = bpy.data.materials.new("M_ground")
    gm.use_nodes = True
    gbsdf = gm.node_tree.nodes["Principled BSDF"]
    gbsdf.inputs["Base Color"].default_value = (0.55, 0.57, 0.60, 1.0)
    gbsdf.inputs["Roughness"].default_value = 0.8
    g.data.materials.append(gm)

    # --- world / camera / sun
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bgn = world.node_tree.nodes["Background"]
    bgn.inputs[0].default_value = (0.85, 0.87, 0.92, 1.0)
    scene.world = world

    cd = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cd)
    scene.collection.objects.link(cam)
    cam.location = sc["cam"]
    tgt = bpy.data.objects.new("Target", None)
    scene.collection.objects.link(tgt)
    tgt.location = sc["cam_tgt"]
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    scene.camera = cam

    sd = bpy.data.lights.new("Sun", "SUN")
    sd.energy = 3.0
    sun = bpy.data.objects.new("Sun", sd)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.6, 0.0, 0.5)

    # --- render settings (giong verify_hard: CYCLES 16 samples, Standard)
    scene.render.engine = "CYCLES"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    png = os.path.join(OUT, sc["id"] + ".png")
    scene.render.filepath = png
    bpy.ops.render.render(write_still=True)

    # --- toa do chieu cua target (normalized 0..1000, y xuong duoi nhu GUI)
    tob = bpy.data.objects[sc["objects"][sc["target"]]["name"]]
    co = world_to_camera_view(scene, cam, tob.matrix_world.translation)
    results.append({
        "id": sc["id"],
        "x": round(co.x * 1000.0, 1),
        "y": round((1.0 - co.y) * 1000.0, 1),
        "on_screen": bool(0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0),
    })

with open(os.path.join(OUT, "proj.json"), "w", encoding="utf-8") as fh:
    json.dump(results, fh)
print("[blend3d] xong %d scene" % len(results))
'''
# --- END BLENDER_SCRIPT (embed) ---



BVER = "4.2.23"
SERIES = BVER.rsplit(".", 1)[0]
NAME = "blender-%s-linux-x64" % BVER
URLS = [
    "https://ftp.nluug.nl/pub/graphics/blender/release/Blender%s/%s.tar.xz"
    % (SERIES, NAME),
    "https://ftp.halifax.rwth-aachen.de/blender/release/Blender%s/%s.tar.xz"
    % (SERIES, NAME),
    "https://download.blender.org/release/Blender%s/%s.tar.xz" % (SERIES, NAME),
]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TMP = "/tmp/blender"
BLENDER = os.path.join(TMP, NAME, "blender")
WORK = "/kaggle/working/blend3d"
BATCH = 10

PALETTE = {
    "red": (0.80, 0.10, 0.10), "green": (0.10, 0.65, 0.20),
    "blue": (0.10, 0.25, 0.80), "yellow": (0.90, 0.75, 0.10),
    "purple": (0.45, 0.15, 0.70), "orange": (0.90, 0.45, 0.10),
    "teal": (0.10, 0.60, 0.60), "white": (0.92, 0.92, 0.90),
}
SHAPES = ["cube", "sphere", "cylinder"]
TEMPLATES = [
    "Click the {color} {shape}.",
    "Select the {color} {shape} in the scene.",
    "Click on the {color} {shape}.",
    "Choose the {color} {shape}.",
]


def log(m):
    print("[gen3d] %s" % m, flush=True)


def download():
    if os.path.exists(BLENDER):
        return
    tar = os.path.join(TMP, NAME + ".tar.xz")
    os.makedirs(TMP, exist_ok=True)
    for url in URLS:
        try:
            log("tai %s" % url)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=600) as r, \
                    open(tar, "wb") as fh:
                shutil_copy(r, fh)
            with tarfile.open(tar) as tf:
                tf.extractall(TMP)
            if os.path.exists(BLENDER):
                return
        except Exception as e:
            log("fail %s: %s" % (url, e))
    raise RuntimeError("khong tai duoc Blender")


def shutil_copy(src, dst, chunk=1 << 20):
    import shutil as _sh
    _sh.copyfileobj(src, dst, chunk)


def make_specs(n, seed, hard=False):
    """Sinh n scene: 3-6 object phan biet (mau+shape), target ngau nhien.

    hard=True: nhieu object hon (5-8), nho hon, sat nhau -> kho hon (B16-3D).
    """
    rng = random.Random(seed)
    specs = []
    for i in range(n):
        n_obj = rng.randint(5, 8) if hard else rng.randint(3, 6)
        colors = rng.sample(list(PALETTE), n_obj)
        shapes = [rng.choice(SHAPES) for _ in range(n_obj)]
        # tranh trung (mau, shape) de instruction khong mo
        seen = set()
        for j in range(n_obj):
            while (colors[j], shapes[j]) in seen:
                shapes[j] = rng.choice(SHAPES)
            seen.add((colors[j], shapes[j]))
        objs = []
        span = 1.0 if hard else 1.2
        slots = [(x, y) for x in (-span, 0.0, span) for y in (-span, 0.0, span)]
        rng.shuffle(slots)
        for j in range(n_obj):
            sx, sy = slots[j % len(slots)]
            objs.append({
                "name": "O%d" % j,
                "shape": shapes[j],
                "color": list(PALETTE[colors[j]]),
                "loc": [round(sx + rng.uniform(-0.15, 0.15), 3),
                        round(sy + rng.uniform(-0.15, 0.15), 3),
                        round(rng.uniform(0.45, 0.95), 3)],
                "size": round(rng.uniform(0.28, 0.45) if hard
                              else rng.uniform(0.50, 0.72), 3),
                "rot": round(rng.uniform(0, 1.57), 3),
            })
        tgt = rng.randrange(n_obj)
        cname = [c for c in PALETTE
                 if list(PALETTE[c]) == objs[tgt]["color"]][0]
        specs.append({
            "id": "e%05d" % i,
            "objects": objs,
            "target": tgt,
            "cam": [round(rng.uniform(5.2, 7.2), 2),
                    round(rng.uniform(-7.2, -5.2), 2),
                    round(rng.uniform(3.2, 4.6), 2)],
            "cam_tgt": [0.0, 0.0, round(rng.uniform(0.5, 0.8), 2)],
            "instr": rng.choice(TEMPLATES).format(color=cname,
                                                  shape=objs[tgt]["shape"]),
            "color_name": cname,
        })
    return specs


def run_blender(specs, outdir):
    os.makedirs(outdir, exist_ok=True)
    sp = os.path.join(outdir, "spec.json")
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(specs, fh)
    env = dict(os.environ)
    env["BLEND_SPEC"] = sp
    env["BLEND_OUT"] = outdir
    cmd = [BLENDER, "-b", "-noaudio", "--python",
           os.path.join(TMP, "blender_scenes.py")]
    p = subprocess.run(cmd, capture_output=True, env=env, timeout=3600)
    if p.returncode != 0:
        log("blender rc=%s" % p.returncode)
        log((p.stdout or b"").decode("utf-8", "replace")[-1500:])
        log((p.stderr or b"").decode("utf-8", "replace")[-1500:])
        return []
    pj = os.path.join(outdir, "proj.json")
    if not os.path.exists(pj):
        return []
    with open(pj, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--hard", action="store_true",
                    help="che do kho: nhieu object hon, nho hon, sat nhau")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True)
    shots = os.path.join(WORK, "shots")
    os.makedirs(shots, exist_ok=True)
    specs = make_specs(a.n, a.seed, hard=a.hard)
    log("specs: %d" % len(specs))
    download()
    log("blender: %s" % BLENDER)
    # ghi script Blender ra /tmp (Kaggle chi upload code_file)
    bpath = os.path.join(TMP, "blender_scenes.py")
    with open(bpath, "w", encoding="utf-8") as fh:
        fh.write(BLENDER_SCRIPT)
    log("blender script: %s (%d B)" % (bpath, len(BLENDER_SCRIPT)))
    rows = []
    n_ok = 0
    for i in range(0, len(specs), BATCH):
        batch = specs[i:i + BATCH]
        outdir = os.path.join(WORK, "batch_%03d" % (i // BATCH))
        proj = run_blender(batch, outdir)
        by_id = {p["id"]: p for p in proj}
        for sc in batch:
            p = by_id.get(sc["id"])
            if not p or not p.get("on_screen"):
                continue
            src = os.path.join(outdir, sc["id"] + ".png")
            if not os.path.exists(src):
                continue
            dst = os.path.join(shots, sc["id"] + ".png")
            with open(src, "rb") as f1, open(dst, "wb") as f2:
                f2.write(f1.read())
            rows.append({
                "image": "shots/%s.png" % sc["id"],
                "instruction": sc["instr"],
                "action": "CLICK %d %d" % (int(round(p["x"])),
                                           int(round(p["y"]))),
                "family": "select_%s" % sc["color_name"],
                "color": sc["color_name"],
                "shape": sc["objects"][sc["target"]]["shape"],
                "src": "blend3d-d1",
            })
        n_ok = len(rows)
        log("xong %d/%d spec -> %d row (%.0fs)" %
            (i + len(batch), len(specs), n_ok, time.time() - t0))
    out = os.path.join(WORK, "train3d.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    # gom anh vao 1 file zip (Kaggle CLI download tung file rat cham)
    import zipfile
    with zipfile.ZipFile(os.path.join(WORK, "shots.zip"), "w",
                         zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            p = os.path.join(shots, os.path.basename(r["image"]))
            if os.path.exists(p):
                z.write(p, os.path.basename(r["image"]))
    log("shots.zip: %d anh" % len(rows))
    # thong ke theo family
    from collections import Counter
    cnt = Counter(r["family"] for r in rows)
    log("rows: %d | theo family: %s" % (len(rows), dict(cnt)))
    with open(os.path.join(WORK, "gen3d_summary.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"n_spec": len(specs), "n_rows": len(rows),
                   "by_family": dict(cnt), "t_sec": round(time.time() - t0, 1)},
                  fh, ensure_ascii=False, indent=1)
    log("xong: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
