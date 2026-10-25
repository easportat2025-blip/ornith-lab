# -*- coding: utf-8 -*-
"""gen_recipe_recovery.py - sinh data SFT cho 2 CHU KY LOOP THAT su (GLM, 22/10).

Do du lieu that tren bench-v22 (B15 + B15.5):
  - Chu ky A 'go lap trong cung 1 o'  (T13_wizard, T15_dialog: TYPE x x10)
      => model go 1 o roi go lai o do, khong CLICK o ke tiep.
  - Chu ky C 'lap click cung toa do' (T16/T05/T09/T12...)
      => model click 1 control khong an roi click lai, khong DOI CHIEN LUWA.

Script nay sinh row SFT tren APP THAT cua ta (khong phai app ve):
  - RA (recipe A): form nhieu o (t21_form) -> day 'go xong o nay -> CLICK o
    ke tiep' (dung 4 o, dung thu tu).
  - RC (recovery C): t25_recovery -> day 'click khong an -> THO control khac'.
Anh chup THAT cua app (Playwright/CDP, headless) => hinh dung nhu obs cua model.

Format row (giong gui_sft / gen_synth_targeted):
  {"image": "<abs path>", "instruction": str, "action": "CLICK x y" | "TYPE s",
   "point": [x, y], "bbox": [x1,y1,x2,y2], "label": str,
   "family": "RA"/"RC", "episode": id, "step": k}
Toa do chuan hoa 0..1000 (x = px/innerWidth*1000).

Dung:
  python phase13-gui/gen_recipe_recovery.py --out phase13-gui/synth_recipe --episodes 20
Khong can GPU / key / mang (chromium cua Playwright local).
"""
import argparse
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
APPS = os.path.join(ROOT, "phase13-gui", "kernel_desktop_bench", "apps")
TASKS_JSON = os.path.join(APPS, "desktop_tasks.json")


def log(m):
    print("[gen] %s" % m, flush=True)


def norm(x, y, w, h):
    return [int(round(x / max(w, 1) * 1000)), int(round(y / max(h, 1) * 1000))]


def rect_norm(sel):
    """-> ([x,y] center, [x1,y1,x2,y2]) normalized 0..1000 (doc DOM that)."""
    js = ("(function(){const e=document.querySelector('%s');if(!e)return null;"
          "const r=e.getBoundingClientRect();"
          "return {cx:r.left+r.width/2,cy:r.top+r.height/2,"
          "x1:r.left,y1:r.top,x2:r.right,y2:r.bottom,"
          "w:window.innerWidth,h:window.innerHeight};})()" % sel)
    try:
        v = page.evaluate(js)
    except Exception:
        return None, None
    if not v:
        return None, None
    p = norm(v["cx"], v["cy"], v["w"], v["h"])
    b = [int(round(v["x1"] / v["w"] * 1000)), int(round(v["y1"] / v["h"] * 1000)),
         int(round(v["x2"] / v["w"] * 1000)), int(round(v["y2"] / v["h"] * 1000))]
    return p, b


def shot(path):
    page.screenshot(path=path)
    return os.path.exists(path) and os.path.getsize(path) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "phase13-gui",
                                                  "synth_recipe"))
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    out_dir = os.path.abspath(a.out)
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    tasks = json.load(io.open(TASKS_JSON, encoding="utf-8"))
    rows = []
    ep_id = 0

    from playwright.sync_api import sync_playwright
    t0 = time.time()
    with sync_playwright() as pw:
        # window-size giong HARNESS (--window-size=1280,720) + no_viewport =>
        # anh co DUNG kich thuoc nhu obs cua model tren Kaggle (1264x625)
        b = pw.chromium.launch(headless=True,
                               args=["--window-size=1280,720"])
        ctx = b.new_context(no_viewport=True, viewport=None)
        global page
        page = ctx.new_page()

        def open_app(file):
            page.goto("file://" + os.path.abspath(os.path.join(APPS, file))
                      .replace("\\", "/"))
            page.wait_for_timeout(220)

        # ---------------- FAMILY RA: form nhieu o (t21_form) ----------------
        instr = tasks["T21_form"]["instruction"]
        for ep in range(a.episodes):
            open_app("t21_form.html")
            spec = page.evaluate("() => window.__spec")
            steps = [("#u", "TYPE %s" % spec["user"], "username field",
                      spec["user"]),
                     ("#e", "TYPE %s" % spec["email"], "email field",
                      spec["email"]),
                     ("#p", "TYPE %s" % spec["pass"], "password field",
                      spec["pass"]),
                     ("#c", "TYPE %s" % spec["pass"], "confirm password field",
                      spec["pass"])]
            k = 0
            for sel, act, label, val in steps:
                p, bbx = rect_norm(sel)
                if not p:
                    continue
                img = os.path.join(img_dir, "RA_ep%03d_s%02d.png" % (ep_id, k))
                if shot(img):
                    rows.append({"image": img, "instruction": instr,
                                 "action": "CLICK %d %d" % (p[0], p[1]),
                                 "point": p, "bbox": bbx, "label": label,
                                 "family": "RA", "episode": ep_id, "step": k})
                    k += 1
                    img2 = os.path.join(img_dir, "RA_ep%03d_s%02d.png" % (ep_id, k))
                    if shot(img2):
                        rows.append({"image": img2, "instruction": instr,
                                     "action": act, "point": p, "bbox": bbx,
                                     "label": label, "family": "RA",
                                     "episode": ep_id, "step": k})
                        k += 1
                # gõ thi (khong sinh row) - chi de app o dung trang thai
                page.click(sel)
                page.fill(sel, val)
            ep_id += 1

        # ---------------- FAMILY RC: recovery (t25_recovery) ----------------
        instr2 = tasks["T25_recovery"]["instruction"]
        for ep in range(a.episodes):
            open_app("t25_recovery.html")
            st = page.evaluate("() => window.__recovery")
            tid = st["target_id"]
            decoy = [i for i in range(3) if i != tid][0]
            # buoc 1: thu 1 control KHONG AN (decoy) - day "probe"
            p, bbx = rect_norm("#b%d" % decoy)
            if p:
                img = os.path.join(img_dir, "RC_ep%03d_s00.png" % ep_id)
                if shot(img):
                    rows.append({"image": img, "instruction": instr2,
                                 "action": "CLICK %d %d" % (p[0], p[1]),
                                 "point": p, "bbox": bbx,
                                 "label": "control that does not respond",
                                 "family": "RC", "episode": ep_id, "step": 0})
                page.click("#b%d" % decoy)
            # buoc 2: DOI CHIEN LUWA -> control DUNG
            p2, bbx2 = rect_norm("#b%d" % tid)
            if p2:
                img2 = os.path.join(img_dir, "RC_ep%03d_s01.png" % ep_id)
                if shot(img2):
                    rows.append({"image": img2, "instruction": instr2,
                                 "action": "CLICK %d %d" % (p2[0], p2[1]),
                                 "point": p2, "bbox": bbx2,
                                 "label": "control that matches the code",
                                 "family": "RC", "episode": ep_id, "step": 1})
                page.click("#b%d" % tid)
            ep_id += 1
        # ---------------- FAMILY RB: chuoi phim tat (clipboard) ----------------
        instr3 = tasks.get("T26_clipboard", {}).get("instruction", "")
        if instr3:
            for ep in range(a.episodes):
                open_app("t26_clipboard.html")
                tg = page.evaluate("() => JSON.stringify(window.__targets)")
                tg = json.loads(tg) if tg else {}
                src_p, src_b = rect_norm("#src")
                dst_p, dst_b = rect_norm("#dst")
                seq = []
                if src_p:
                    seq.append(("CLICK %d %d" % (src_p[0], src_p[1]), src_p,
                                src_b, "source box"))
                seq.append(("KEY Control+a", src_p, src_b, "select all"))
                seq.append(("KEY Control+c", src_p, src_b, "copy"))
                if dst_p:
                    seq.append(("CLICK %d %d" % (dst_p[0], dst_p[1]), dst_p,
                                dst_b, "target box"))
                seq.append(("KEY Control+v", dst_p, dst_b, "paste"))
                for k, (act, pt, bx, label) in enumerate(seq):
                    img = os.path.join(img_dir, "RB_ep%03d_s%02d.png" % (ep_id, k))
                    if not shot(img):
                        continue
                    rows.append({"image": img, "instruction": instr3,
                                 "action": act, "point": pt, "bbox": bx,
                                 "label": label, "family": "RB",
                                 "episode": ep_id, "step": k})
                # thuc hien chuoi de app o trang thai dung (cho lan sau)
                try:
                    page.click("#src")
                    page.keyboard.press("Control+a")
                    page.keyboard.press("Control+c")
                    page.click("#dst")
                    page.keyboard.press("Control+v")
                except Exception:
                    pass
                ep_id += 1
        b.close()

    rows_path = os.path.join(out_dir, "rows.jsonl")
    with io.open(rows_path, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    fam = {}
    for r in rows:
        fam[r["family"]] = fam.get(r["family"], 0) + 1
    log("sinh %d row trong %d episode | %s | %.1fs" %
        (len(rows), ep_id, fam, time.time() - t0))
    log("ghi %s" % rows_path)
    log("images: %d" % len(os.listdir(img_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
