"""gen_bench3d.py - sinh BENCH GROUNDING 3D (tap + metric) tren Kaggle CPU.

Muc dich: co METRIC cho track 3D (giong B15 cho GUI) de do model tren 3D.
Moi episode: render 1 scene (3-6 object, (mau,shape) duy nhat) + instruction
'Click the {mau} {shape}' + bbox CHIEU cua object target (normalized 0..1000).
Checker: click co nam trong bbox target khong? (giong 'hit(point,bbox)' cua GUI)

Output (kaggle/working/bench3d/):
  bench3d.jsonl : {"image","instruction","bbox":[x0,y0,x1,y1],"color","shape"}
  shots.zip     : anh (ten o top-level)
Chay: python gen_bench3d.py [--n 100] [--seed 999]
"""
import argparse
import json
import os
import random
import shutil
import sys
import subprocess
import tarfile
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from generate_3d import (BLENDER, PALETTE, SHAPES, TEMPLATES, TMP,  # noqa
                          download, log, make_specs)

WORK = "/kaggle/working/bench3d"
BATCH = 10

BLENDER_EVAL = r'''
import json
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

    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0, 0, 0))
    g = bpy.context.object
    gm = bpy.data.materials.new("M_ground")
    gm.use_nodes = True
    gb = gm.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = (0.55, 0.57, 0.60, 1.0)
    gb.inputs["Roughness"].default_value = 0.8
    g.data.materials.append(gm)

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

    from mathutils import Vector
    tob = bpy.data.objects[sc["objects"][sc["target"]]["name"]]
    co = world_to_camera_view(scene, cam, tob.matrix_world.translation)
    xs, ys = [], []
    for corner in tob.bound_box:
        wc = tob.matrix_world @ Vector(corner)
        c2 = world_to_camera_view(scene, cam, wc)
        xs.append(c2.x * W)
        ys.append((1.0 - c2.y) * H)
    results.append({
        "id": sc["id"],
        "x": round(co.x * 1000.0, 1),
        "y": round((1.0 - co.y) * 1000.0, 1),
        "bbox": [round(min(xs) / W * 1000.0, 1), round(min(ys) / H * 1000.0, 1),
                 round(max(xs) / W * 1000.0, 1),
                 round(max(ys) / H * 1000.0, 1)],
        "on_screen": bool(0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0),
    })

with open(os.path.join(OUT, "proj.json"), "w", encoding="utf-8") as fh:
    json.dump(results, fh)
print("[bench3d] xong %d scene" % len(results))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=999)
    ap.add_argument("--hard", action="store_true",
                    help="che do kho (B16-3D): nhieu object hon, nho hon")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(WORK, exist_ok=True)
    specs = make_specs(a.n, a.seed, hard=a.hard)
    log("specs: %d" % len(specs))
    download()
    bpath = os.path.join(TMP, "blender_bench3d.py")
    with open(bpath, "w", encoding="utf-8") as fh:
        fh.write(BLENDER_EVAL)
    rows = []
    for i in range(0, len(specs), BATCH):
        batch = specs[i:i + BATCH]
        outdir = os.path.join(WORK, "b%03d" % (i // BATCH))
        os.makedirs(outdir, exist_ok=True)
        sp = os.path.join(outdir, "spec.json")
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(batch, fh)
        env = dict(os.environ)
        env["BLEND_SPEC"] = sp
        env["BLEND_OUT"] = outdir
        p = subprocess.run([BLENDER, "-b", "-noaudio", "--python", bpath],
                           capture_output=True, env=env, timeout=3600)
        pj = os.path.join(outdir, "proj.json")
        if not os.path.exists(pj):
            log("batch %d fail: %s" % (i // BATCH,
                 (p.stderr or b"").decode("utf-8", "replace")[-300:]))
            continue
        proj = {x["id"]: x for x in json.load(open(pj, encoding="utf-8"))}
        for sc in batch:
            q = proj.get(sc["id"])
            if not q or not q.get("on_screen"):
                continue
            src = os.path.join(outdir, sc["id"] + ".png")
            if not os.path.exists(src):
                continue
            rows.append({
                "image": "shots/%s.png" % sc["id"],
                "instruction": sc["instr"],
                "bbox": q["bbox"],
                "center": [q["x"], q["y"]],
                "color": sc["color_name"],
                "shape": sc["objects"][sc["target"]]["shape"],
                "src": "bench3d-d1",
            })
        log("xong %d/%d -> %d row (%.0fs)" %
            (i + len(batch), len(specs), len(rows), time.time() - t0))
    shots = os.path.join(WORK, "shots")
    os.makedirs(shots, exist_ok=True)
    with zipfile.ZipFile(os.path.join(WORK, "shots.zip"), "w",
                         zipfile.ZIP_DEFLATED) as z:
        for r in rows:
            p = os.path.join(WORK, os.path.basename(
                os.path.dirname(r["image"])), os.path.basename(r["image"]))
            # file render nam trong outdir cua batch
            found = None
            for d in os.listdir(WORK):
                cand = os.path.join(WORK, d, os.path.basename(r["image"]))
                if os.path.exists(cand):
                    found = cand
                    break
            if found:
                z.write(found, os.path.basename(r["image"]))
    out = os.path.join(WORK, "bench3d.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log("ROWS: %d -> %s" % (len(rows), out))
    with open(os.path.join(WORK, "bench3d_summary.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"n": len(rows), "seed": a.seed,
                   "t_sec": round(time.time() - t0, 1)}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
