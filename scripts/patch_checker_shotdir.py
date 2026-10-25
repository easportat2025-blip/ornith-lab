# -*- coding: utf-8 -*-
"""
patch_checker_shotdir.py - checker_desktop.run_task: them tham so tuy chon
shot_dir ( chup anh TRUOC moi buoc ) de sinh data desktop-replay.

KHONG pha API hien co: tham so moi o CUOI + default None => moi noi goi
run_task(page, tid, pol, max_steps) van chay y het.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "phase14-desktop", "tasks", "checker_desktop.py")

s = io.open(P, encoding="utf-8", newline="").read()
if "shot_dir=None" in s:
    print("da co shot_dir -> bo qua")
    sys.exit(0)

OLD_SIG = "def run_task(page, task_id, policy_fn, max_steps=20):"
NEW_SIG = ("def run_task(page, task_id, policy_fn, max_steps=20, shot_dir=None):")
if OLD_SIG not in s:
    print("FAIL: khong tim thay run_task")
    sys.exit(1)
s = s.replace(OLD_SIG, NEW_SIG, 1)

OLD_LOOP = """        trajectory.append({"step": step, "action": action})
        if action == "DONE":
            break"""
NEW_LOOP = """        trajectory.append({"step": step, "action": action})
        if action == "DONE":
            break
        # FIX 22/10 (MiMo): chup anh TRUOC khi thuc hien action (quan sat cua
        # model) - dung de sinh data desktop-replay (policy-replay format).
        if shot_dir:
            import os as _os
            _os.makedirs(shot_dir, exist_ok=True)
            page.screenshot(path=_os.path.join(
                shot_dir, "%s_s%02d.png" % (task_id, step)))"""
if OLD_LOOP not in s:
    print("FAIL: khong tim thay vong trai")
    sys.exit(1)
s = s.replace(OLD_LOOP, NEW_LOOP, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da them shot_dir vao checker_desktop.run_task")
