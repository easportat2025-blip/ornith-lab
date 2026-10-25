# -*- coding: utf-8 -*-
"""
build_old_suite.py - dung lai bo task B15.5 BAN CU (truoc 15 fix) tu cac
mirror trong repo, de bo sung O CON THIEU cua thu nghiem 2x2.

Vi sao: v22 tang +50 diem tren B15.5 nhung do CHUNG 2 nguyen nhan (sua loi
sinh + sua 15 fix task) => khong tach duoc. Thu nghiem 2x2 can:
            | task CU  | task MOI
    v21      |  5,6%    |  (khong co)
    v22      |  (thieu) |  55,6%
=> can "model v22 tren task B15.5 CU" => do dataset task CU (dung version
cua dataset da publish truoc khi sua) va mount vao 1 kernel rieng.

Cach lay: 3 mirror trong repo (phase14-space/app/project, _push, _push_docker)
chua cac phien ban cu cua file task; mirror da bi dong bo boi 1 phan => lay
BAN CU NHAT (mtime nho nhat) cho tung file, roi kiem bang chuoi dac trung
(t13: 'Current value:', t14: 'press the End key', t16: 'statusEl', t17: 'UP and DOWN',
t18: 'Rejected') de bao dam la ban CU.
"""
import io
import json
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
MIRRORS = [
    "phase14-space/app/project/phase13-gui/bench_v15/tasks_v15_5",
    "phase14-space/_push/app/project/phase13-gui/bench_v15/tasks_v15_5",
    "phase14-space/_push_docker/app/project/phase13-gui/bench_v15/tasks_v15_5",
    "phase13-gui/bench_v15/tasks_v15_5",          # ban hien tai (new)
]
FILES = [
    "bench_v155.py", "checker.py", "dummy_actions_v155.json",
    "dummy_run_result.json", "self_test_report.json",
    "tasks/tasks.json", "tasks/t13_wizard.html", "tasks/t14_alerts.html",
    "tasks/t15_dialog.html", "tasks/t16_clipboard2.html",
    "tasks/t17_reorder.html", "tasks/t18_countsubmit.html",
]
# dau hieu "BAN MOI" (phai KHONG co trong ban CU)
NEW_MARKERS = {
    "tasks/t13_wizard.html": "Current value:",
    "tasks/t14_alerts.html": "press the End key",
    "tasks/t16_clipboard2.html": "Pasted into Target",   # fix statusEl -> status
    "tasks/t17_reorder.html": "one place at a time",
    # t18: thong bao "Rejected:" da co san o ban CU (chi khac o bien status ->
    # statusEl) => KHONG dung lam dau hieu "moi".
}
STAGE = os.path.join(ROOT, "phase13-gui", "old_bench_ds",
                     "khoadangnguye__ornith-gui-bench-v155-old")
SLUG = "khoadangnguye/ornith-gui-bench-v155-old"

out = {}
for rel in FILES:
    cands = []
    for m in MIRRORS:
        p = os.path.join(ROOT, m.replace("/", os.sep), rel.replace("/", os.sep))
        if os.path.exists(p):
            cands.append((os.path.getmtime(p), p))
    if not cands:
        print("KHONG TIM THAY:", rel)
        continue
    cands.sort()
    # uu tien ban CU: file cu nhat ma KHONG chua dau hieu "moi"
    pick = None
    for mt, p in cands:
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        mk = NEW_MARKERS.get(rel)
        if mk and mk in txt:
            continue
        pick = (mt, p, txt)
        break
    if pick is None:
        pick = (cands[0][0], cands[0][1],
                io.open(cands[0][1], encoding="utf-8", errors="replace").read())
        print("  (canh bao: khong tim thay ban cu cho %s -> dung ban moi nhat)" % rel)
    mt, p, txt = pick
    tag = "CU" if rel not in NEW_MARKERS else (
        "CU" if (NEW_MARKERS[rel] not in txt) else "MOI")
    print("  %-32s <- %-62s %s [%s]" % (
        rel, p.replace(ROOT + "\\", ""),
        __import__("time").strftime("%m-%d %H:%M", __import__("time").localtime(mt)),
        tag))
    out[rel] = txt

# --- GHI DE instruction cua tasks.json bang DUNG instruction run v21 da thay
# (nguon su that: result JSON cua run v21) => bo task CU khớp 100% voi
# suite ma v21 da chay (mirror co the la ban trung gian cho 1-2 task).
try:
    rp = os.path.join(ROOT, "phase13-gui", "out_bench_v155_v21", "b15_result.json")
    res = json.load(io.open(rp, encoding="utf-8"))
    v21 = {}
    for e in res.get("episodes") or []:
        v21.setdefault(e.get("task_id"), e.get("instruction", ""))
    tj = json.loads(out["tasks/tasks.json"])
    lst = tj["tasks"] if isinstance(tj, dict) and "tasks" in tj else tj
    n_fix_instr = 0
    for t in lst:
        tid = t.get("task_id")
        if tid in v21 and v21[tid] and t.get("instruction") != v21[tid]:
            t["instruction"] = v21[tid]
            n_fix_instr += 1
    out["tasks/tasks.json"] = json.dumps(tj, ensure_ascii=False, indent=2)
    print("  tasks.json: ghi de %d instruction = instruction run v21" % n_fix_instr)
except Exception as e:
    print("  (khong ghi de instruction tu run v21: %s)" % str(e)[:90])

# --- dua vao staging (layout giong dataset bench: top dir bench_v155/)
if os.path.isdir(STAGE):
    shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE, exist_ok=True)
zp = os.path.join(STAGE, "bench_v155_bundle.zip")
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for rel, txt in out.items():
        z.writestr("bench_v155/" + rel.replace("\\", "/"), txt)
meta = {"title": "Ornith GUI bench B15.5 - PHIEN BAN CU (doi chieu 2x2)",
        "id": SLUG, "licenses": [{"name": "other"}]}
with io.open(os.path.join(STAGE, "dataset-metadata.json"), "w",
             encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=1)
n = len(out)
print()
print("staging: %s (%d file, %.1f KB)"
      % (os.path.relpath(STAGE, ROOT), n, os.path.getsize(zp) / 1024.0))
print("slug    : %s" % SLUG)
print()
print("=== LENH (can key acc A) ===")
print('  kaggle datasets create -p "%s"' % os.path.relpath(STAGE, ROOT))
print("  # sau do: tao kernel bench_v155_v22_old (copy kernel_bench_v155_v22, "
      "doi dataset_sources sang slug tren) + push => do 'model v22 tren task CU'")
