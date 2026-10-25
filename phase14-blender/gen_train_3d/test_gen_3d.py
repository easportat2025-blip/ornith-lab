"""test_gen_3d.py - test offline (khong can Blender): spec hop le + deterministic."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_3d as G  # noqa: E402

specs = G.make_specs(40, 7)
assert len(specs) == 40
seen_keys = set()
for s in specs:
    objs = s["objects"]
    assert 3 <= len(objs) <= 6, s["id"]
    keys = [(tuple(o["color"]), o["shape"]) for o in objs]
    assert len(set(keys)) == len(keys), ("trung mau/shape", s["id"], keys)
    assert 0 <= s["target"] < len(objs)
    for o in objs:
        assert 0.0 <= o["color"][0] <= 1.0 and 0.0 <= o["color"][1] <= 1.0
        assert 0.05 <= o["size"] <= 1.0, o
        assert len(o["loc"]) == 3
    cname = s["color_name"]
    assert cname in G.PALETTE
    assert cname in s["instr"], (cname, s["instr"])
    assert s["objects"][s["target"]]["shape"] in s["instr"], s["instr"]
    seen_keys.add(tuple(sorted((c, sh) for c, sh in keys)))
# deterministic
specs2 = G.make_specs(40, 7)
assert json.dumps(specs) == json.dumps(specs2), "khong deterministic"
specs3 = G.make_specs(40, 8)
assert json.dumps(specs) != json.dumps(specs3), "seed khong doi output"
# phu bi nhieu khac nhau (khong phai 40 task giong nhau)
assert len(seen_keys) >= 20, len(seen_keys)
print("mau 2 spec:")
for s in specs[:2]:
    print("  ", s["id"], "|", s["instr"], "| target", s["target"],
          "| cam", s["cam"], "| objs", [(o["shape"], o["color"]) for o in s["objects"]])
print("TEST PASS: %d spec, deterministic, (mau,shape) duy nhat" % len(specs))
