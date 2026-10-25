"""blender_scenes.py - chay TRONG Blender: doc spec JSON, render tung scene,
ghi toa do chieu cua object target.

Input : env BLEND_SPEC (file JSON: list of scene spec)
Output: env BLEND_OUT (dir) -> <id>.png + proj.json
"""
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
    from mathutils import Vector
    tob = bpy.data.objects[sc["objects"][sc["target"]]["name"]]
    co = world_to_camera_view(scene, cam, tob.matrix_world.translation)
    # --- bbox CHIEU cua target (de checker "click co trong bbox khong?")
    xs, ys = [], []
    for corner in tob.bound_box:
        wc = tob.matrix_world @ Vector(corner)
        c2 = world_to_camera_view(scene, cam, wc)
        xs.append(c2.x * W)
        ys.append((1.0 - c2.y) * H)
    bx0, bx1 = round(min(xs) / W * 1000.0, 1), round(max(xs) / W * 1000.0, 1)
    by0, by1 = round(min(ys) / H * 1000.0, 1), round(max(ys) / H * 1000.0, 1)
    results.append({
        "id": sc["id"],
        "x": round(co.x * 1000.0, 1),
        "y": round((1.0 - co.y) * 1000.0, 1),
        "bbox": [bx0, by0, bx1, by1],
        "on_screen": bool(0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0),
    })

with open(os.path.join(OUT, "proj.json"), "w", encoding="utf-8") as fh:
    json.dump(results, fh)
print("[blend3d] xong %d scene" % len(results))
