"""Tao ban SMOKE cho kernel desktop-bench: DB_EPISODES mac dinh 2 + chi 2 task
(kaggle script kernel khong set env duoc => phai bake vao code).
Dung: python phase13-gui/make_desktop_bench_smoke.py
"""
import io, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "kernel_desktop_bench")
DST = os.path.join(HERE, "kernel_desktop_bench_smoke")

shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST, exist_ok=True)
src = io.open(os.path.join(SRC, "desktop_bench_kernel.py"),
              encoding="utf-8").read()
# bake gia tri mac dinh: 2 episode + 2 task (nhanh ~10-15')
n1, n2 = 0, 0
if 'os.environ.get("DB_EPISODES", "20")' in src:
    src = src.replace('os.environ.get("DB_EPISODES", "20")',
                      'os.environ.get("DB_EPISODES", "2")')
    n1 = 1
m = re.search(r'os\.environ\.get\("DB_TASKS", "([^"]*)"\)', src)
if m:
    src = src[:m.start()] + 'os.environ.get("DB_TASKS", "T20_2048,T21_form_desktop")' \
        + src[m.end():]
    n2 = 1
print("bake DB_EPISODES: %d choi | DB_TASKS: %d choi" % (n1, n2))
assert n1 == 1 and n2 == 1, "khong tim thay placeholder de bake"
io.open(os.path.join(DST, "desktop_bench_kernel.py"), "w",
        encoding="utf-8", newline="\n").write(src)
meta = json.load(io.open(os.path.join(SRC, "kernel-metadata.json"),
                         encoding="utf-8"))
meta["id"] = "khoadangnguye/ornith-gui-desktop-bench-smoke"
meta["title"] = "ornith-gui-desktop-bench-smoke"
io.open(os.path.join(DST, "kernel-metadata.json"), "w", encoding="utf-8",
        newline="\n").write(json.dumps(meta, indent=1))
print("wrote", DST)
print("=> push: kaggle kernels push -p phase13-gui/kernel_desktop_bench_smoke")
