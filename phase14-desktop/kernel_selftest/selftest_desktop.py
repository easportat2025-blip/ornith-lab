"""selftest_desktop.py - chay 1 vong tren DESKTOP-ENV va ghi trai du lieu."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import env as E

WORK = E.WORK
os.makedirs(WORK, exist_ok=True)
E.start_display()

# --- 1) app: game 2048 (file:// trong display)
page = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks",
                    "game_2048.html")
E.open_app("file://" + page.replace("\\", "/"))
shot0 = os.path.join(WORK, "shots", "step00.png")
E.screenshot(shot0)
E.log("shot0 ok=%s size=%s" % (os.path.exists(shot0),
                                os.path.getsize(shot0) if os.path.exists(shot0) else 0))

# --- 2) vong action that (xdotool): them 1 tile roi nhieu phim mui ten
script = ["KEY left", "KEY up", "KEY right", "KEY down", "KEY left",
          "KEY up", "KEY right", "KEY down", "KEY left", "KEY up"]
rows = []
for i, a in enumerate(script):
    ok, desc = E.do_action(a)
    time.sleep(0.35)
    p = os.path.join(WORK, "shots", "step%02d.png" % (i + 1))
    E.screenshot(p)
    rows.append({"step": i, "action": a, "ok": ok, "desc": desc,
                 "shot": os.path.relpath(p, WORK).replace("\\", "/")})
    E.log("step %d %s -> %s" % (i, a, desc))

# --- 3) doc trang thai app (CDP) + luu trai du lieu
state = E.dom_state()
E.log("tabs: %s" % json.dumps(state)[:300])
with open(os.path.join(WORK, "traj.json"), "w", encoding="utf-8") as fh:
    json.dump({"rows": rows, "tabs": state}, fh, ensure_ascii=False, indent=1)
with open(os.path.join(WORK, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump({"n_steps": len(rows), "n_shots": len([f for f in
              os.listdir(os.path.join(WORK, "shots"))]),
               "tabs": len(state)}, fh, ensure_ascii=False, indent=1)
E.log("DONE %d steps" % len(rows))
