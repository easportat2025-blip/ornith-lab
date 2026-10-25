"""Rebuild kernel_v23a tu kernel_v22 + re-inline module gen_synth_targeted.py
HIEN TAI (repo) + truyen done_rate=0.75 + id moi.

Dung: python phase13-gui/make_kernel_v23a.py
"""
import io, json, os, re, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "kernel_v22")
DST = os.path.join(HERE, "kernel_v23a")
MOD = os.path.join(HERE, "gen_synth_targeted.py")
MARK = "# ==== gen_synth_targeted.py (INLINE: Kaggle chi upload code_file) ===="

shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST, exist_ok=True)
for f in ("gui_sft_v22.py", "kernel-metadata.json"):
    shutil.copy2(os.path.join(SRC, f), os.path.join(DST, f))

kp = os.path.join(DST, "gui_sft_v22.py")
lines = io.open(kp, encoding="utf-8", errors="replace").read().splitlines()
i = next(k for k, l in enumerate(lines) if l.strip() == MARK)
j = next(k for k in range(i + 1, len(lines))
         if lines[k].startswith('if __name__ == "__main__":'))
old_block = len(lines[i + 1:j])

# module repo: cat bo block __main__ (CLI) de khong chay trong kernel
mlines = io.open(MOD, encoding="utf-8", errors="replace").read().splitlines()
cut = len(mlines)
for k, l in enumerate(mlines):
    if l.startswith('if __name__ == "__main__":'):
        cut = k
        break
body = mlines[:cut]
while body and not body[-1].strip():
    body.pop()
print("inline moi: %d dong (cu %d) | module repo: %d dong (cat __main__ %d)" %
      (len(body), old_block, len(mlines), len(mlines) - cut))

new_lines = lines[:i + 1] + body + lines[j:]
src = "\n".join(new_lines) + "\n"

# call site: truyen done_rate=0.75 (giai ma seed theo convention cua kernel v22)
OLD_CALL = "build_targeted(N_TARGETED, SEED + 2, tdir)"
NEW_CALL = "build_targeted(N_TARGETED, SEED + 2, tdir, done_rate=0.75)"
assert src.count(OLD_CALL) == 1, "call site khong khop (%d)" % src.count(OLD_CALL)
src = src.replace(OLD_CALL, NEW_CALL, 1)
io.open(kp, "w", encoding="utf-8", newline="\n").write(src)

mp = os.path.join(DST, "kernel-metadata.json")
meta = json.load(io.open(mp, encoding="utf-8"))
meta["id"] = "khoadangnguye/ornith-gui-sft-v23a"
meta["title"] = "ornith-gui-sft-v23a"
io.open(mp, "w", encoding="utf-8", newline="\n").write(json.dumps(meta, indent=1))
print("id ->", meta["id"])
print("wrote", DST)
