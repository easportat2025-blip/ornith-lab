# -*- coding: utf-8 -*-
"""TASK-13 local dry-check — khong can Blender, khong can mang.

5 nhom kiem tra:
  1. 90 row / 30 task / 3 variant, deterministic, script compile.
  2. id clash vs 87 old (blender_gen.TASKS) + 45 mui2 (NEW_TASKS_MUI2); seed unique.
  3. constraint schema self-test: check_one tung kieu (pass + fail mau).
  4. mock-scene: exec PREFIX+code bang FAKE bpy, xay scene dump dung dang TAIL,
     chay check_one tren TAT CA constraint (pixel_region kiem tra param) ->
     emitter phai thoa constraint cua chinh no.
  5. instruction grammar spot-check.
Chay:  python dry_check.py   -> exit 0 = PASS
"""
import json
import math
import os
import re
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_hard as vh  # noqa: E402

FAILED = []


def chk(name, cond, extra=""):
    if not cond:
        FAILED.append(name)
    print("[%s] %s %s" % ("PASS" if cond else "FAIL", name, extra))


# ---------------------------------------------------------------- 1. rows
print("=== 1. rows & scripts ===")
rows = vh.gen_rows_hard()
rows2 = vh.gen_rows_hard()
tasks = sorted({r["task"] for r in rows})
chk("90 rows", len(rows) == 90, "got %d" % len(rows))
chk("30 tasks", len(tasks) == 30, "got %d" % len(tasks))
chk("3 rows/task",
    all(sum(1 for r in rows if r["task"] == t) == 3 for t in tasks))
chk("variant 0..2",
    all(sorted(r["variant"] for r in rows if r["task"] == t) == [0, 1, 2]
        for t in tasks))
chk("deterministic (2x gen identical)",
    json.dumps(rows, sort_keys=True) == json.dumps(rows2, sort_keys=True))
bad_compile = []
for r in rows:
    try:
        compile(r["script"], r["id"] + ".py", "exec")
    except SyntaxError as e:
        bad_compile.append("%s: %s" % (r["id"], e))
chk("all 90 scripts compile", not bad_compile, "; ".join(bad_compile[:3]))
chk("jsonl-serializable", bool(json.dumps(rows, ensure_ascii=False)))

instrs = " || ".join(r["instruction"] for r in rows)
gram = re.findall(r"\b(a a|an a|the the|a [aeiou]\w+|an [bcdfghjklmnpqrstvwxyz]\w+)",
                  instrs)
chk("instruction grammar spot-check", not gram, str(gram[:6]))
chk("no empty instruction", all(len(r["instruction"]) > 30 for r in rows))
chk("constraints non-empty",
    all(isinstance(r["constraints"], list) and r["constraints"] for r in rows))

# ---------------------------------------------------------------- 2. id/seed
print("=== 2. id & seed clash ===")


def parse_tnames(path, start_marker, end_marker):
    txt = open(path, encoding="utf-8", errors="replace").read()
    i = txt.find(start_marker)
    assert i >= 0, "marker not found: " + start_marker
    j = txt.find(end_marker, i + len(start_marker))
    if j < 0:
        j = i + 400000
    block = txt[i:j]
    return re.findall(r'\(\s*"([a-z0-9_]+)"\s*,\s*t_[a-z0-9_]+', block)


repo = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
old_names = parse_tnames(
    os.path.join(repo, "phase14-blender", "gen_kernel", "blender_gen.py"),
    "TASKS = [", "os.environ.get")
mui2_names = parse_tnames(
    os.path.join(repo, "phase14-blender", "verify_kernel", "verify_mui2.py"),
    "NEW_TASKS_MUI2 = [", "# Goi vao file v2")
hard_ids = {r["id"] for r in rows}
old_ids = {"%s_v%d" % (n, v) for n in old_names for v in range(3)}
mui2_ids = {"%s_v%d" % (n, v) for n in mui2_names for v in range(3)}
chk("old ids = 87 (29 task x3)", len(old_ids) == 87,
    "names=%d ids=%d" % (len(old_names), len(old_ids)))
chk("mui2 ids = 45 (15 task x3)", len(mui2_ids) == 45,
    "names=%d ids=%d" % (len(mui2_names), len(mui2_ids)))
chk("no id clash hard vs old", not (hard_ids & old_ids),
    str(sorted(hard_ids & old_ids)[:5]))
chk("no id clash hard vs mui2", not (hard_ids & mui2_ids),
    str(sorted(hard_ids & mui2_ids)[:5]))
chk("no id clash old vs mui2", not (old_ids & mui2_ids),
    str(sorted(old_ids & mui2_ids)[:5]))
chk("hard id prefix h", all(re.match(r"^h\d\d_", i) for i in hard_ids))
n_k = len(old_names) + len(mui2_names)
old_seeds = {1000 + k * 97 + v for k in range(n_k) for v in range(3)}
hard_seeds = {r["seed"] for r in rows}
chk("90 unique hard seeds", len(hard_seeds) == 90, str(sorted(hard_seeds)[:3]))
chk("seed disjoint old/mui2", not (hard_seeds & old_seeds),
    str(sorted(hard_seeds & old_seeds)[:5]))

# ---------------------------------------------------------------- 3. schema
print("=== 3. constraint schema self-test ===")
PAL, PMAP = vh.PALETTE, vh.PAL_MAP


def M(name, loc, dims, color="red", metallic=0.0, rough=0.5, emit=0.0,
      rot=(0, 0, 0), kind="MESH"):
    return {"name": name, "type": kind, "loc": list(loc), "rot": list(rot),
            "scale": [1, 1, 1], "dims": list(dims),
            "mats": [{"base": list(PMAP[color]), "metallic": metallic,
                      "rough": rough, "emit": emit}]}


class _Crop(object):
    def __init__(self, px):
        self._px = px

    def getdata(self):
        return self._px


class _IM(object):
    def __init__(self, px):
        self.size = (10, 10)
        self._px = px

    def crop(self, box):
        return _Crop(self._px)


RED = [(204, 26, 26)] * 100
BLUE = [(38, 89, 217)] * 100

cases = [
    ("count eq ok", {"t": "count_mesh", "n": 2, "op": "eq"},
     [M("a", (0, 0, 0), (1, 1, 1)), M("b", (2, 0, 0), (1, 1, 1))], {}, None, True),
    ("count eq fail", {"t": "count_mesh", "n": 3, "op": "eq"},
     [M("a", (0, 0, 0), (1, 1, 1))], {}, None, False),
    ("rel_z above ok", {"t": "rel_z", "a": "a", "b": "b", "op": "above", "tol": 0.1},
     [M("a", (0, 0, 3), (1, 1, 1)), M("b", (0, 0, 1), (1, 1, 1))], {}, None, True),
    ("rel_z above fail", {"t": "rel_z", "a": "a", "b": "b", "op": "above", "tol": 0.1},
     [M("a", (0, 0, 0), (1, 1, 1)), M("b", (0, 0, 1), (1, 1, 1))], {}, None, False),
    ("rel_xy right ok", {"t": "rel_xy", "a": "a", "b": "b", "axis": "x", "op": "right", "tol": 0.2},
     [M("a", (3, 0, 0), (1, 1, 1)), M("b", (0, 0, 0), (1, 1, 1))], {}, None, True),
    ("rel_xy right fail", {"t": "rel_xy", "a": "a", "b": "b", "axis": "x", "op": "right", "tol": 0.2},
     [M("a", (-3, 0, 0), (1, 1, 1)), M("b", (0, 0, 0), (1, 1, 1))], {}, None, False),
    ("same_z ok", {"t": "same_z", "a": "a", "b": "b", "tol": 0.05},
     [M("a", (0, 0, 1), (1, 1, 1)), M("b", (2, 0, 1), (1, 1, 1))], {}, None, True),
    ("same_z fail", {"t": "same_z", "a": "a", "b": "b", "tol": 0.05},
     [M("a", (0, 0, 1), (1, 1, 1)), M("b", (2, 0, 2), (1, 1, 1))], {}, None, False),
    ("touching ok", {"t": "touching", "a": "a", "b": "b", "axis": "z", "tol": 0.06},
     [M("a", (0, 0, 1.5), (1, 1, 1)), M("b", (0, 0, 0.5), (1, 1, 1))], {}, None, True),
    ("touching fail", {"t": "touching", "a": "a", "b": "b", "axis": "z", "tol": 0.05},
     [M("a", (0, 0, 1.8), (1, 1, 1)), M("b", (0, 0, 0.5), (1, 1, 1))], {}, None, False),
    ("size_ratio ok", {"t": "size_ratio", "a": "a", "b": "b", "axis": "x", "ratio": 3.0, "tol": 0.3},
     [M("a", (0, 0, 0), (3, 1, 1)), M("b", (5, 0, 0), (1, 1, 1))], {}, None, True),
    ("size_ratio fail", {"t": "size_ratio", "a": "a", "b": "b", "axis": "x", "ratio": 3.0, "tol": 0.1},
     [M("a", (0, 0, 0), (1.5, 1, 1)), M("b", (5, 0, 0), (1, 1, 1))], {}, None, False),
    ("bbox_within ok", {"t": "bbox_within", "a": "a", "b": "b", "tol": 0.1},
     [M("a", (0, 0, 0), (1, 1, 1)), M("b", (0, 0, 0), (3, 3, 3))], {}, None, True),
    ("bbox_within fail", {"t": "bbox_within", "a": "a", "b": "b", "tol": 0.1},
     [M("a", (2, 0, 0), (1, 1, 1)), M("b", (0, 0, 0), (3, 3, 3))], {}, None, False),
    ("mat_color ok", {"t": "mat_color", "a": "a", "color": "red"},
     [M("a", (0, 0, 0), (1, 1, 1), color="red")], {}, None, True),
    ("mat_color fail", {"t": "mat_color", "a": "a", "color": "red"},
     [M("a", (0, 0, 0), (1, 1, 1), color="blue")], {}, None, False),
    ("mat_prop emit ok", {"t": "mat_prop", "a": "a", "prop": "emit", "op": "ge", "v": 4.0},
     [M("a", (0, 0, 0), (1, 1, 1), emit=6.0)], {}, None, True),
    ("mat_prop emit fail", {"t": "mat_prop", "a": "a", "prop": "emit", "op": "ge", "v": 4.0},
     [M("a", (0, 0, 0), (1, 1, 1), emit=0.0)], {}, None, False),
    ("cam ok", {"t": "cam", "azim": [255, 285], "elev": [5, 35]},
     [M("a", (0, -10, 3), (2, 2, 2), kind="CAMERA")],
     {"target": [0, 0, 1]}, None, True),
    ("cam fail", {"t": "cam", "azim": [165, 195], "elev": [5, 35]},
     [M("a", (0, -10, 3), (2, 2, 2), kind="CAMERA")],
     {"target": [0, 0, 1]}, None, False),
    ("light ok", {"t": "light", "kind": "SUN", "op": "eq", "n": 1, "energy": [1, 8]},
     [M("s", (0, 0, 8), (0, 0, 0), kind="LIGHT")],
     {}, {"light_type": "SUN", "energy": 4.0}, True),
    ("light fail kind", {"t": "light", "kind": "AREA", "op": "eq", "n": 1},
     [M("s", (0, 0, 8), (0, 0, 0), kind="LIGHT")],
     {}, {"light_type": "SUN", "energy": 4.0}, False),
    ("rot ok", {"t": "rot", "a": "a", "axis": "z", "deg": [25, 35]},
     [M("a", (0, 0, 0), (1, 1, 1), rot=(0, 0, math.radians(30)))], {}, None, True),
    ("rot fail", {"t": "rot", "a": "a", "axis": "z", "deg": [40, 60]},
     [M("a", (0, 0, 0), (1, 1, 1), rot=(0, 0, math.radians(30)))], {}, None, False),
    ("pixel ok", {"t": "pixel_region", "region": [0.2, 0.2, 0.8, 0.8],
                  "color": "red", "frac": 0.9},
     [], {}, None, True, RED),
    ("pixel fail", {"t": "pixel_region", "region": [0.2, 0.2, 0.8, 0.8],
                    "color": "red", "frac": 0.9},
     [], {}, None, False, BLUE),
]
npass = 0
for case in cases:
    name, c, objs, scene_extra, light_extra, want = case[:6]
    px = case[6] if len(case) > 6 else None
    scene = {"objects": objs, "target": scene_extra.get("target", [0, 0, 0])}
    o_by_name = {o["name"]: o for o in objs}
    if light_extra:
        for o in objs:
            if o["type"] == "LIGHT":
                o.update(light_extra)
    im = _IM(px) if px is not None else None
    try:
        ok, det = vh.check_one(c, o_by_name, scene, im)
    except Exception as e:
        ok, det = False, "%s: %s" % (type(e).__name__, e)
    if bool(ok) == want:
        npass += 1
    else:
        print("   case %r: got %s (%s) want %s" % (name, ok, det, want))
chk("schema self-test", npass == len(cases), "%d/%d" % (npass, len(cases)))

# ---------------------------------------------------------------- 4. mock
print("=== 4. mock-scene: emitter vs own constraints ===")


class _In(object):
    def __init__(self, v):
        self.default_value = v


class _BSDF(object):
    def __init__(self):
        self.inputs = {
            "Base Color": _In((0.8, 0.8, 0.8, 1.0)),
            "Metallic": _In(0.0),
            "Roughness": _In(0.5),
            "Emission Color": _In((0.0, 0.0, 0.0, 1.0)),
            "Emission Strength": _In(0.0),
        }


class _FakeMat(object):
    def __init__(self, name):
        self.name = name
        self.use_nodes = True
        self.node_tree = types.SimpleNamespace(
            nodes={"Principled BSDF": _BSDF()})


class _FakeObj(object):
    def __init__(self, base_dims):
        self.type = "MESH"
        self.name = ""
        self.location = [0.0, 0.0, 0.0]
        self.rotation_euler = [0.0, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]
        self.data = types.SimpleNamespace(materials=[])
        self._base = list(base_dims)


def _dims_for(kind, kw):
    if kind == "cube":
        s = kw["size"]
        return [s, s, s]
    if kind == "sphere":
        r = kw["radius"]
        return [2 * r, 2 * r, 2 * r]
    if kind == "cylinder":
        r, d = kw["radius"], kw["depth"]
        return [2 * r, 2 * r, d]
    if kind == "cone":
        r, d = kw["radius1"], kw["depth"]
        return [2 * r, 2 * r, d]
    if kind == "torus":
        M_, m = kw["major_radius"], kw["minor_radius"]
        return [2 * (M_ + m), 2 * (M_ + m), 2 * m]
    if kind == "plane":
        s = kw["size"]
        return [s, s, 0.0]
    raise ValueError(kind)


def mock_scene(code):
    """Exec PREFIX + emitter code under a fake bpy; build TAIL-shaped dump."""
    bpy = types.ModuleType("bpy")
    state = {"objs": []}
    bpy.ops = types.SimpleNamespace()
    bpy.ops.wm = types.SimpleNamespace(
        read_factory_settings=lambda **k: None)
    mesh_ns = types.SimpleNamespace()

    def mk(kind):
        def fn(**kw):
            o = _FakeObj(_dims_for(kind, kw))
            o.location = list(kw.get("location", (0.0, 0.0, 0.0)))
            state["objs"].append(o)
            bpy.context.active_object = o
        return fn

    for k, op in (("cube", "primitive_cube_add"),
                  ("sphere", "primitive_uv_sphere_add"),
                  ("cylinder", "primitive_cylinder_add"),
                  ("cone", "primitive_cone_add"),
                  ("torus", "primitive_torus_add"),
                  ("plane", "primitive_plane_add")):
        setattr(mesh_ns, op, mk(k))
    bpy.ops.mesh = mesh_ns
    bpy.context = types.SimpleNamespace(scene=types.SimpleNamespace(),
                                        active_object=None)
    bpy.data = types.SimpleNamespace(
        materials=types.SimpleNamespace(new=lambda n: _FakeMat(n)),
        worlds=types.SimpleNamespace(new=lambda n: None),
        cameras=types.SimpleNamespace(new=lambda n: None),
        lights=types.SimpleNamespace(new=lambda n: None),
        objects=types.SimpleNamespace(new=lambda n, d: None, get=lambda n: None))

    saved = sys.modules.get("bpy")
    sys.modules["bpy"] = bpy
    old_env = os.environ.get("BLEND_OUT")
    tmp = tempfile.mkdtemp(prefix="hard_dry_")
    os.environ["BLEND_OUT"] = tmp
    g = {}
    try:
        exec(compile(vh.PREFIX, "<prefix>", "exec"), g)
        exec(compile(code, "<emitter>", "exec"), g)
    finally:
        if saved is None:
            sys.modules.pop("bpy", None)
        else:
            sys.modules["bpy"] = saved
        if old_env is None:
            os.environ.pop("BLEND_OUT", None)
        else:
            os.environ["BLEND_OUT"] = old_env

    objs = []
    seen = {}

    def uniq(n):
        """Blender auto-suffixes duplicate names (.001, .002 ...)."""
        if n not in seen:
            seen[n] = 0
            return n
        seen[n] += 1
        return "%s.%03d" % (n, seen[n])

    for o in state["objs"]:
        mats = []
        for m in o.data.materials:
            b = m.node_tree.nodes["Principled BSDF"]
            mats.append({
                "base": [round(float(x), 4)
                         for x in b.inputs["Base Color"].default_value[:3]],
                "metallic": round(float(b.inputs["Metallic"].default_value), 4),
                "rough": round(float(b.inputs["Roughness"].default_value), 4),
                "emit": round(float(b.inputs["Emission Strength"].default_value), 4)})
        objs.append({
            "name": uniq(o.name), "type": "MESH",
            "loc": [round(float(x), 4) for x in o.location],
            "rot": [round(float(x), 4) for x in o.rotation_euler],
            "scale": [round(float(x), 4) for x in o.scale],
            "dims": [round(o._base[i] * o.scale[i], 4) for i in range(3)],
            "mats": mats})

    cam_loc = g.get("CAM_LOC", (9.5, -9.5, 6.5))
    cam_tgt = g.get("CAM_TGT", (0.0, 0.0, 1.6))
    sun_energy = g.get("SUN_ENERGY", 4.0)
    extras = g.get("EXTRA_LIGHTS", [])
    objs.append({"name": uniq("Camera"), "type": "CAMERA",
                 "loc": [float(x) for x in cam_loc], "rot": [0, 0, 0],
                 "scale": [1, 1, 1], "lens": 50.0})
    objs.append({"name": uniq("Sun"), "type": "LIGHT", "light_type": "SUN",
                 "energy": float(sun_energy),
                 "loc": [0.0, 0.0, 0.0], "rot": [0, 0, 0], "scale": [1, 1, 1]})
    for kind, loc, en, rot in extras:
        objs.append({"name": uniq("L_" + kind), "type": "LIGHT",
                     "light_type": kind,
                     "energy": float(en),
                     "loc": [float(x) for x in loc], "rot": [0, 0, 0],
                     "scale": [1, 1, 1]})
    return {"objects": objs, "camera": "Camera",
            "target": [float(x) for x in cam_tgt]}


PIX_OK = ("region", "color", "frac")
task_pass = []
for ti, tname in enumerate(tasks):
    row = next(r for r in rows if r["task"] == tname and r["variant"] == 0)
    script = row["script"]
    assert script.startswith(vh.PREFIX) and script.endswith(vh.TAIL), tname
    code = script[len(vh.PREFIX):len(script) - len(vh.TAIL)]
    try:
        scene = mock_scene(code)
    except Exception as e:
        print("  %s EXEC-ERR %s: %s" % (tname, type(e).__name__, e))
        continue
    names = [o["name"] for o in scene["objects"]]
    dup = {n for n in names if names.count(n) > 1}
    problems = []
    if dup:
        problems.append("dup name %s" % dup)
    o_by_name = {}
    for o in scene["objects"]:
        o_by_name.setdefault(o["name"], o)
    pixel_ok = True
    for c in row["constraints"]:
        if c["t"] == "pixel_region":
            if not (0 <= c["region"][0] < c["region"][2] <= 1
                    and 0 <= c["region"][1] < c["region"][3] <= 1
                    and c["color"] in PMAP and 0 < c["frac"] <= 1):
                pixel_ok = False
                problems.append("bad pixel param %s" % c)
            continue
        try:
            ok, det = vh.check_one(c, o_by_name, scene, None)
        except Exception as e:
            ok, det = False, "%s: %s" % (type(e).__name__, e)
        if not ok:
            problems.append("%s -> %s" % (json.dumps(c, ensure_ascii=False), det))
    if not pixel_ok:
        problems.append("pixel param invalid")
    if problems:
        print("  %s FAIL" % tname)
        for p in problems:
            print("      %s" % p)
    else:
        task_pass.append(tname)
chk("emitters satisfy own constraints (30/30)",
    len(task_pass) == 30, "%d/30" % len(task_pass))

# ---------------------------------------------------------------- report
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "dry_check_report.json")
report = {"rows": len(rows), "tasks": len(tasks),
          "old_ids": len(old_ids), "mui2_ids": len(mui2_ids),
          "hard_ids": len(hard_ids),
          "schema_self_test": "%d/%d" % (npass, len(cases)),
          "mock_ok": len(task_pass), "failed": FAILED,
          "ok": not FAILED}
json.dump(report, open(out, "w", encoding="utf-8"), indent=1)
print("wrote", out)
print("=" * 54)
if FAILED:
    print("DRY-CHECK FAIL:", ", ".join(FAILED))
else:
    print("DRY-CHECK PASS 30/30  (90 rows, 0 id clash, schema %s)"
          % report["schema_self_test"])
print("=" * 54)
sys.exit(0 if not FAILED else 1)
