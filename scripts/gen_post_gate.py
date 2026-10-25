"""gen_post_gate.py - tao script post-action cho tung muc trong gpu_queue (A/B).

Watchdog goi: powershell -File <script>  (khong truyen args) -> can 1 file .ps1
rieng cho moi muc. File nay goi chung scripts/post_gate.ps1 voi tham so dung.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, "scripts", "post_gates")
os.makedirs(GEN, exist_ok=True)

# muc -> (label, thu muc output)
PLAN = {
    "khoadangnguye/ornith-gui-bench-v21": ("v21", "phase13-gui/out_bench_v21"),
    "khoadangnguye/ornith-gui-bench-v155-v21": ("v21", "phase13-gui/out_bench_v155_v21"),
    "khoadangnguye/ornith-gui-bench-v14-v21": ("v21", "phase13-gui/out_bench_v14_v21"),
    "khoadangnguye/ornith-gui-bench-v16-v21": ("v21", "phase13-gui/out_bench_v16_v21"),
    "khoadangnguye/ornith-gui-bench-v15-think0": ("v18-think0", "phase13-gui/out_bench_v18_think0"),
    "dieniw/ornith-bench-v155-b1": ("v18-base", "phase13-gui/out_bench_v155_B"),
    "dieniw/ornith-bench-v16-b1": ("v18-base", "phase13-gui/out_bench_v16_B"),
    # --- bench 3D (metric bbox-hit, khong qua gate_report) ---
    "khoadangnguye/ornith-gui-bench-3d": ("v18-3D", "phase13-gui/out_bench_3d"),
    "khoadangnguye/ornith-gui-bench-3d-hard": ("v18-3D-hard",
                                               "phase13-gui/out_bench_3d_hard"),
    "khoadangnguye/ornith-gui-bench-3d-v21": ("v21-3D",
                                               "phase13-gui/out_bench_3d_v21"),
    "khoadangnguye/ornith-gui-bench-3d-hard-v21": (
        "v21-3D-hard", "phase13-gui/out_bench_3d_hard_v21"),
    "dieniw/ornith-bench-3d-b1": ("v18-3D", "phase13-gui/out_bench_3d_B"),
    "dieniw/ornith-bench-3d-hard-b1": ("v18-3D-hard",
                                       "phase13-gui/out_bench_3d_hard_B"),
}

TPL = """# auto-gen by gen_post_gate.py - post-action cho {kid}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\\Users\\Admin\\Desktop\\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\\post_gate.ps1' `
    -Kernel '{kid}' -Out '{out}' -Label '{label}'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
"""


def main():
    made = []
    for qf in ("scripts/gpu_queue.json", "scripts/gpu_queue_B.json"):
        q = json.load(io.open(os.path.join(ROOT, qf), encoding="utf-8"))
        for item in q:
            kid = item.get("id")
            if kid not in PLAN:
                continue
            label, out = PLAN[kid]
            name = "post_" + kid.replace("/", "_") + ".ps1"
            path = os.path.join(GEN, name)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(TPL.format(kid=kid, out=out, label=label))
            item["post"] = "scripts\\post_gates\\" + name
            made.append((kid, name))
        json.dump(q, io.open(os.path.join(ROOT, qf), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    for k, n in made:
        print("  ", k, "->", n)
    print("tong", len(made))


if __name__ == "__main__":
    main()
