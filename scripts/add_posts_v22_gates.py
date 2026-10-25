# -*- coding: utf-8 -*-
"""add_posts_v22_gates.py - gan post-action cho 3 gate v22 (B15/B15.5/B16) de
watchdog tu tai output -> cham gate -> ghi LOBBY -> bus bao toi ngay.
"""
import io
import json
import os

GEN = "scripts/post_gates"
os.makedirs(GEN, exist_ok=True)
TPL = """# auto-gen cho gate v22
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\\Users\\Admin\\Desktop\\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\\post_gate.ps1' `
    -Kernel '{kid}' -Out '{out}' -Label '{label}'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
"""

JOBS = [
    ("khoadangnguye/ornith-gui-bench-v22", "phase13-gui/out_bench_v22", "v22"),
    ("khoadangnguye/ornith-gui-bench-v155-v22", "phase13-gui/out_bench_v155_v22", "v22"),
    ("khoadangnguye/ornith-gui-bench-v16-v22", "phase13-gui/out_bench_v16_v22", "v22"),
]

for kid, out, label in JOBS:
    name = "post_" + kid.replace("/", "_") + ".ps1"
    p = os.path.join(GEN, name)
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(TPL.format(kid=kid, out=out, label=label))
    print("tao", name)

# gan vao queue A
PQ = "scripts/gpu_queue.json"
q = json.load(io.open(PQ, encoding="utf-8"))
n = 0
for i in q:
    if i.get("id") in [j[0] for j in JOBS] and not i.get("post"):
        i["post"] = "scripts\\post_gates\\post_" + i["id"].replace("/", "_") + ".ps1"
        n += 1
json.dump(q, io.open(PQ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("gan post cho", n, "muc trong queue A")

# them vao watchdog targets (de fetch + chay post)
PT = "scripts/watchdog_targets.json"
t = json.load(io.open(PT, encoding="utf-8"))
have = {x.get("kernel") for x in t}
n = 0
for kid, out, label in JOBS:
    if kid not in have:
        t.append({"label": "gate-" + kid.split("-")[-1], "kernel": kid,
                  "outdir": out,
                  "pattern": "b15_result\\.json|.*\\.log",
                  "post": "scripts\\post_gates\\post_" + kid.replace("/", "_") + ".ps1"})
        n += 1
json.dump(t, io.open(PT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("them", n, "target vao watchdog")
