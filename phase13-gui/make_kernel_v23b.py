"""Rebuild kernel_v23b = kernel_v23 + gen_synth_targeted MOI (co S9/S10), KHONG
them DONE boost (done_rate=0) + id moi.

LY DO (22/10): thi nghiem 2x2/3x3 dang mo:
  - kernel_v23  (DANG CHAY) : generator CU (khong S9/S10) + done_rate=0
  - kernel_v23a (cua @GLM)   : generator MOI (co S9/S10) + done_rate=0.75
=> v23 vs v23a lệch 2 thu => KHONG phai A/B sach.
  - kernel_v23b (KERNEL NAY): generator MOI (co S9/S10) + done_rate=0
=> 3 kernel, tach duoc 2 hieu ung:
  * v23  vs v23b : hieu ung cua S9/S10 (loop + misread)
  * v23b vs v23a : hieu ung cua DONE boost (done_rate 0 -> 0.75)

Dung: python phase13-gui/make_kernel_v23b.py
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "kernel_v23")
DST = os.path.join(HERE, "kernel_v23b")
MOD = os.path.join(HERE, "gen_synth_targeted.py")
MARK = "# ==== gen_synth_targeted.py (INLINE: Kaggle chi upload code_file) ===="
CODE = "gui_sft_v23.py"

if not os.path.isdir(SRC):
    print("thieu %s (kernel_v23 cua @DeepSeek/@GPT)" % SRC)
    raise SystemExit(1)

shutil.rmtree(DST, ignore_errors=True)
os.makedirs(DST, exist_ok=True)
for f in os.listdir(SRC):
    if f.endswith((".py", ".json")):
        shutil.copy2(os.path.join(SRC, f), os.path.join(DST, f))

kp = os.path.join(DST, CODE)
lines = io.open(kp, encoding="utf-8", errors="replace").read().splitlines()
i = next((k for k, l in enumerate(lines) if l.strip() == MARK), None)
if i is None:
    print("khong tim thay MARK trong %s" % kp)
    raise SystemExit(1)
j = next((k for k in range(i + 1, len(lines))
           if lines[k].startswith('if __name__ == "__main__":')), None)
if j is None:
    print("khong tim thay block __main__")
    raise SystemExit(1)
old_block = len(lines[i + 1:j])

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
print("   co S9/S10:", "S9" in "\n".join(body), "| S10:", "S10" in "\n".join(body))

new_lines = lines[:i + 1] + body + lines[j:]
src = "\n".join(new_lines) + "\n"

# done_rate: truyen 0.0 TUONG MINH (module moi co param; gate G5 doi call site
# phai truyen ro) => v23b KHONG co DONE boost, chi khac v23 o S9/S10.
CALL = "build_targeted(N_TARGETED, SEED + 2, tdir)"
NEW_CALL = "build_targeted(N_TARGETED, SEED + 2, tdir, done_rate=0.0)"
assert src.count(CALL) == 1, "call site khong khop (%d)" % src.count(CALL)
src = src.replace(CALL, NEW_CALL, 1)
print("call site: done_rate=0.0 (KHONG DONE boost - tach rieng hieu ung S9/S10)")
io.open(kp, "w", encoding="utf-8", newline="\n").write(src)

mp = os.path.join(DST, "kernel-metadata.json")
meta = json.load(io.open(mp, encoding="utf-8"))
meta["id"] = "khoadangnguye/ornith-gui-sft-v23b"
meta["title"] = "ornith-gui-sft-v23b"
io.open(mp, "w", encoding="utf-8", newline="\n").write(json.dumps(meta, indent=1))
print("id ->", meta["id"])
print("wrote", DST)
