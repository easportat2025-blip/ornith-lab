"""qa_synth.py - sinh mau data synth targeted va ghi ra thu muc de soi."""
import os
import sys

sys.path.insert(0, "phase13-gui")
import gen_synth_targeted as G

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "qa_synth_out")
os.makedirs(OUT, exist_ok=True)
rows = G.build_targeted(8, 4242, OUT)
print("rows:", len(rows))
seen = {}
for r in rows:
    fam = r["family"]
    if fam in seen:
        continue
    seen[fam] = r
    print("%-4s step%-2d | %-58s | %s" % (fam, r["step"],
                                          r["instruction"][:58], r["action"]))
print("images:", len([f for f in os.listdir(OUT) if f.endswith(".png")]))
print("OUT:", OUT)
