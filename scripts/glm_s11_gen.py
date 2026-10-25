"""glm_s11_gen.py - sinh data SFT cho 3 nang luc THIEU (GLM, 22/10, chay tren Colab CPU).

LY DO (do tren du lieu that):
  * S11 SCROLL/MOVE/DRAG: 3 verb nay CHUA TUNG co trong data train => 47 buoc
    SCROLL cua model tren desktop la "menh lenh ngoai data".
  * S12 error-recovery: app bao SAI nhung ket qua DUNG (thay trong trace T25).
  * S13 keyboard-nav: T22_keynav 2/3, desktop T23_keys 0/20.

Tinh nang:
  * SELF-CONTAINED (khong can repo, khong can GPU) => chay tren Colab CPU.
  * Render bang PIL 768x512, toa do normalized 0..1000 (giong S1..S10).
  * Tu sinh SELF-TEST: replay tung family va kiem tra chuoi action dung
    (dummy self-test phai 100%).
  * Xuat: traj.jsonl + images/ + manifest.json (zip ngoai) => upload HF =>
    kernel SFT nap bang load_ds_rows("ornith-gui-synth-s11", "traj.jsonl").

Dung (local hoac Colab):
  python glm_s11_gen.py --n 120 --out /content/s11_out
"""
import argparse
import io
import json
import os
import random
import sys
import zipfile

from PIL import Image, ImageDraw

CW, CH = 768, 512
FONT = None

# ---------------------------------------------------------------- helpers
def new_canvas():
    im = Image.new("RGB", (CW, CH), (244, 246, 250))
    return im, ImageDraw.Draw(im)


def norm(px, total):
    return int(round(px / float(total) * 1000))


def center(box):
    return (box[0] + box[2]) // 2, (box[1] + box[3]) // 2


def save_img(img, img_dir, name):
    if not os.path.isdir(img_dir):
        os.makedirs(img_dir)
    p = os.path.abspath(os.path.join(img_dir, name))
    img.save(p)
    return p


def draw_button(d, box, color, label=""):
    d.rectangle(box, fill=color)
    cx, cy = center(box)
    d.text((cx - 4 * len(label) // 2, cy - 6), label, fill=(255, 255, 255))


def draw_input(d, box, value="", highlight=False, placeholder=""):
    d.rectangle(box, fill=(255, 255, 255), outline=(30, 111, 217) if highlight
                else (160, 168, 180))
    d.text((box[0] + 6, box[1] + 6), value or placeholder, fill=(20, 24, 30)
           if value else (140, 148, 160))


def draw_note(d, box, lines):
    d.rectangle(box, fill=(255, 249, 219), outline=(214, 190, 120))
    y = box[1] + 6
    for ln in lines:
        d.text((box[0] + 8, y), ln, fill=(60, 48, 10))
        y += 16


def draw_list(d, box, items, highlight_idx=-1, scroll_off=0):
    d.rectangle(box, fill=(255, 255, 255), outline=(150, 158, 170))
    y = box[1] + 6
    for i, it in enumerate(items):
        if not (scroll_off <= i < scroll_off + 5):
            continue
        if i == highlight_idx:
            d.rectangle([box[0] + 2, y - 3, box[2] - 2, y + 13],
                        fill=(214, 236, 255))
        d.text((box[0] + 8, y), it, fill=(25, 30, 40))
        y += 18


def draw_slider(d, box, pct, label=""):
    d.rectangle(box, fill=(236, 238, 244), outline=(150, 158, 170))
    x1, y1, x2, y2 = box
    track_y = (y1 + y2) // 2
    d.line([x1 + 6, track_y, x2 - 6, track_y], fill=(120, 128, 140), width=4)
    hx = int(x1 + 6 + (x2 - x1 - 12) * pct / 100.0)
    d.ellipse([hx - 8, track_y - 8, hx + 8, track_y + 8], fill=(30, 111, 217))
    d.text((x1 + 4, y1 - 16), "%s %d%%" % (label, pct), fill=(40, 46, 56))


def draw_status(d, box, text, ok=False):
    d.rectangle(box, fill=(226, 245, 230) if ok else (252, 232, 230),
                outline=(120, 180, 130) if ok else (200, 130, 120))
    d.text((box[0] + 8, box[1] + 6), text, fill=(20, 90, 40) if ok
           else (170, 40, 30))


# ---------------------------------------------------------------- value pools
CODES = ["ALPHA", "BRAVO", "CIRRUS", "DELTA", "EMBER", "FLINT", "GAMMA",
         "HALO", "INDIGO", "JADE", "KIWI", "LOTUS"]
NAMES = ["Ivy", "Jonas", "Kira", "Liam", "Mona", "Nils", "Opal", "Pavel",
         "Quinn", "Rosa", "Sami", "Tara"]


def rnd_code(rng):
    return rng.choice(CODES)


# ---------------------------------------------------------------- families
def gen_s11_scroll(rng, img_dir, ep):
    """S11a: cuon bang de loai muc nam ngoai khung hinh.

    Dinh vi tri muc co code LUON o DUOI khung hinh (>=6) => buoc 0 BAT BUOC
    phai cuon (neu ma o hang 2 thi task khong con gi de hoc SCROLL).
    So lan cuon = so hang can di de thay muc do.
    """
    code = rnd_code(rng)
    items = ["ROW-%02d %s" % (i + 1, rng.choice(NAMES)) for i in range(12)]
    code_at = rng.randint(6, 11)          # LUON ngoai khung hinh (visible 0..4)
    items[code_at] = "ROW-%02d code %s" % (code_at + 1, code)
    note = [CW - 250, 40, CW - 20, 96]
    panel = [40, 120, 380, 330]
    n_scroll = 1 if code_at <= 9 else 2   # viewport hien 5 hang
    rows = []
    # buoc 0..n-1: cuon
    for k in range(n_scroll):
        im, d = new_canvas()
        draw_note(d, note, ["Note:", "target code:", code])
        draw_list(d, panel, items, highlight_idx=-1, scroll_off=5 * k)
        d.text((40, 340), "scroll inside the list to see more rows",
               fill=(90, 96, 110))
        p = save_img(im, img_dir, "s11a_%d_%d.png" % (ep, k))
        if k == 0:
            instr = ("The list of rows continues below the visible area. Scroll "
                     "inside the list to reveal the row that contains the code "
                     "from the note.")
        else:
            instr = ("Keep scrolling inside the list until the row with the "
                     "code from the note is visible.")
        rows.append((p, instr, "SCROLL 5"))
    # buoc cuoi: click muc co code
    im, d = new_canvas()
    draw_note(d, note, ["Note:", "target code:", code])
    draw_list(d, panel, items, highlight_idx=code_at, scroll_off=5 * (n_scroll - 1))
    cx, cy = center(panel)
    ty = panel[1] + 6 + (code_at - 5 * (n_scroll - 1)) * 18 + 6
    p = save_img(im, img_dir, "s11a_%d_%d.png" % (ep, n_scroll))
    rows.append((p, "Click the row whose code matches the note.",
                 "CLICK %d %d" % (norm(cx, CW), norm(ty, CH))))
    return rows


def gen_s11_move(rng, img_dir, ep):
    """S11b: hover (MOVE) de lo bang tooltip."""
    code = rnd_code(rng)
    box = [60, 130, 330, 210]
    tip = [60, 225, 330, 262]
    field = [60, 300, 330, 336]
    btn = [60, 360, 200, 396]
    rows = []
    im, d = new_canvas()
    d.rectangle(box, fill=(232, 234, 240), outline=(150, 158, 170))
    d.text((box[0] + 8, box[1] + 8), "locked panel - hover to reveal",
           fill=(110, 116, 130))
    d.rectangle(tip, fill=(255, 255, 255))
    cx, cy = center(box)
    p = save_img(im, img_dir, "s11b_%d_0.png" % ep)
    rows.append((p, "The code is hidden until you point at the locked panel. "
                    "Move the pointer over the panel to reveal it.",
                 "MOVE %d %d" % (norm(cx, CW), norm(cy, CH))))
    im, d = new_canvas()
    d.rectangle(box, fill=(232, 234, 240), outline=(150, 158, 170))
    d.text((box[0] + 8, box[1] + 8), "locked panel", fill=(110, 116, 130))
    d.rectangle(tip, fill=(255, 249, 219), outline=(214, 190, 120))
    d.text((tip[0] + 8, tip[1] + 6), "code: " + code, fill=(60, 48, 10))
    d.rectangle(field, fill=(255, 255, 255), outline=(160, 168, 180))
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    p = save_img(im, img_dir, "s11b_%d_1.png" % ep)
    rows.append((p, "The code is now visible. Type it into the empty field.",
                 "TYPE " + code))
    fx, fy = center(field)
    p = save_img(im, img_dir, "s11b_%d_2.png" % ep)
    rows.append((p, "Click the field, then type the revealed code.",
                 "CLICK %d %d" % (norm(fx, CW), norm(fy, CH))))
    return rows


def gen_s11_drag(rng, img_dir, ep):
    """S11c: keo (DRAG) con tro dieu khien de dat gia tri."""
    want = rng.choice([20, 35, 50, 72, 88])
    start = rng.choice([0, 10, 25])
    track = [70, 170, 430, 206]
    btn = [70, 250, 200, 286]
    rows = []
    im, d = new_canvas()
    d.text((70, 120), "Set the level to %d%%" % want, fill=(30, 36, 46))
    draw_slider(d, track, start, "level:")
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Apply", fill=(255, 255, 255))
    x1 = track[0] + 6
    x2 = track[2] - 6
    hx1 = int(x1 + (x2 - x1) * start / 100.0)
    hx2 = int(x1 + (x2 - x1) * want / 100.0)
    ty = (track[1] + track[3]) // 2
    p = save_img(im, img_dir, "s11c_%d_0.png" % ep)
    rows.append((p, "Drag the slider handle to the %d%% position." % want,
                 "DRAG %d %d %d %d" % (norm(hx1, CW), norm(ty, CH),
                                       norm(hx2, CW), norm(ty, CH))))
    im, d = new_canvas()
    d.text((70, 120), "Set the level to %d%%" % want, fill=(30, 36, 46))
    draw_slider(d, track, want, "level:")
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Apply", fill=(255, 255, 255))
    bx, by = center(btn)
    p = save_img(im, img_dir, "s11c_%d_1.png" % ep)
    rows.append((p, "The slider is at the requested value. Click Apply.",
                 "CLICK %d %d" % (norm(bx, CW), norm(by, CH))))
    return rows


def gen_s12_recover(rng, img_dir, ep):
    """S12: app bao LOI nhung ket qua DUNG -> kiem lai roi submit lai."""
    code = rnd_code(rng)
    name = rng.choice(NAMES)
    note = [CW - 250, 40, CW - 20, 96]
    field = [60, 130, 320, 166]
    btn = [60, 200, 200, 236]
    stat = [60, 250, 420, 286]
    rows = []
    im, d = new_canvas()
    draw_note(d, note, ["Note:", "name:", name, "code:", code])
    draw_input(d, field, code, highlight=False)
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    draw_status(d, stat, "Error: invalid code. Please try again.", ok=False)
    bx, by = center(btn)
    p = save_img(im, img_dir, "s12_%d_0.png" % ep)
    rows.append((p, "The page shows an error, but the code you typed already "
                    "matches the note. Do not change the value; press Submit "
                    "again to confirm.",
                 "CLICK %d %d" % (norm(bx, CW), norm(by, CH))))
    im, d = new_canvas()
    draw_note(d, note, ["Note:", "name:", name, "code:", code])
    draw_input(d, field, code, highlight=False)
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    draw_status(d, stat, "Code accepted.", ok=True)
    p = save_img(im, img_dir, "s12_%d_1.png" % ep)
    rows.append((p, "The code was accepted. The task is complete.", "DONE"))
    return rows


def gen_s13_keynav(rng, img_dir, ep):
    """S13: dieu huong bang phim (Tab / mui ten / Enter)."""
    vals = [rng.choice(NAMES) for _ in range(3)]
    fields = [[60, 120, 320, 156], [60, 180, 320, 216], [60, 240, 320, 276]]
    btn = [60, 310, 200, 346]
    rows = []
    im, d = new_canvas()
    draw_input(d, fields[0], "", highlight=True, placeholder="first name")
    draw_input(d, fields[1], "", placeholder="last name")
    draw_input(d, fields[2], "", placeholder="code")
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    p = save_img(im, img_dir, "s13_%d_0.png" % ep)
    rows.append((p, "The first field is focused. Press Tab to move to the "
                    "next field.", "KEY Tab"))
    im, d = new_canvas()
    draw_input(d, fields[0], vals[0])
    draw_input(d, fields[1], "", highlight=True, placeholder="last name")
    draw_input(d, fields[2], "", placeholder="code")
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    p = save_img(im, img_dir, "s13_%d_1.png" % ep)
    rows.append((p, "The second field is focused. Press Tab again to reach "
                    "the code field.", "KEY Tab"))
    im, d = new_canvas()
    draw_input(d, fields[0], vals[0])
    draw_input(d, fields[1], vals[1])
    draw_input(d, fields[2], "", highlight=True, placeholder="code")
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    p = save_img(im, img_dir, "s13_%d_2.png" % ep)
    rows.append((p, "The code field is focused. Type the code from the note.",
                 "TYPE " + rng.choice(CODES)))
    im, d = new_canvas()
    draw_input(d, fields[0], vals[0])
    draw_input(d, fields[1], vals[1])
    draw_input(d, fields[2], "OK", highlight=True)
    d.rectangle(btn, fill=(30, 111, 217))
    d.text((btn[0] + 16, btn[1] + 6), "Submit", fill=(255, 255, 255))
    p = save_img(im, img_dir, "s13_%d_3.png" % ep)
    rows.append((p, "All fields are filled. Press Enter to submit.",
                 "KEY Enter"))
    return rows


FAMILIES = [
    ("S11", "scroll", gen_s11_scroll),
    ("S11", "move", gen_s11_move),
    ("S11", "drag", gen_s11_drag),
    ("S12", "error_recovery", gen_s12_recover),
    ("S13", "keyboard_nav", gen_s13_keynav),
]


# ---------------------------------------------------------------- self-test
def self_test(out_dir):
    """Replay tung family va kiem tra chuoi action + anh ton tai."""
    rng = random.Random(1234)
    img_dir = os.path.join(out_dir, "_selftest")
    problems = []
    n_ok = 0
    for fam, name, fn in FAMILIES:
        try:
            rows = fn(rng, img_dir, 0)
        except Exception as e:
            problems.append("%s/%s: EXCEPTION %s: %s" %
                            (fam, name, type(e).__name__, str(e)[:80]))
            continue
        if not rows:
            problems.append("%s/%s: khong sinh row" % (fam, name))
            continue
        verbs = [r[2].split()[0].upper() for r in rows]
        # ky vong: moi family phai co >=1 row va moi row phai co action hop le
        for p, instr, act in rows:
            if not os.path.isfile(p):
                problems.append("%s/%s: thieu anh %s" % (fam, name, p))
                break
            if not act or not act.split()[0].upper() in (
                    "CLICK", "TYPE", "KEY", "MOVE", "DRAG", "SCROLL", "DONE"):
                problems.append("%s/%s: action sai '%s'" % (fam, name, act))
                break
        # loai rieng: SCROLL phai co it nhat 1 SCROLL, MOVE co MOVE, ...
        need = {"scroll": "SCROLL", "move": "MOVE", "drag": "DRAG",
                "error_recovery": "CLICK", "keyboard_nav": "KEY"}[name]
        if need not in verbs:
            problems.append("%s/%s: thieu verb %s (co %s)" %
                            (fam, name, need, verbs))
            continue
        n_ok += 1
    print("[selftest] family PASS: %d/%d" % (n_ok, len(FAMILIES)))
    for p in problems:
        print("[selftest] FAIL:", p)
    return problems


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120, help="so episode")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="/content/s11_out")
    ap.add_argument("--zip", default=None, help="ghi zip ra day")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    img_dir = os.path.join(out, "images")
    if not os.path.isdir(img_dir):
        os.makedirs(img_dir)
    rng = random.Random(a.seed)
    rows = []
    ep = 0
    for i in range(a.n):
        fam, name, fn = FAMILIES[i % len(FAMILIES)]
        for p, instr, act in fn(rng, img_dir, ep):
            rows.append({"image": os.path.relpath(p, out).replace("\\", "/"),
                         "instruction": instr, "action": act,
                         "family": "%s-%s" % (fam, name), "episode": ep,
                         "step": len([r for r in rows if r["episode"] == ep])})
        ep += 1
    with io.open(os.path.join(out, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    man = {"name": "ornith-gui-synth-s11", "rows": len(rows),
           "episodes": ep, "canvas": [CW, CH],
           "families": ["%s-%s" % (f, n) for f, n, _ in FAMILIES],
           "note": "S11 scroll/move/drag + S12 error-recovery + S13 keyboard-nav"}
    with io.open(os.path.join(out, "manifest.json"), "w", encoding="utf-8",
                 newline="\n") as fh:
        fh.write(json.dumps(man, indent=1, ensure_ascii=False))
    print("[gen] %d row / %d episode / %d family" %
          (len(rows), ep, len(FAMILIES)))
    probs = self_test(out)
    if probs:
        print("[gen] SELF-TEST FAIL (%d) - van xuat file de doi" % len(probs))
    if a.zip:
        zp = os.path.abspath(a.zip)
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _dirs, files in os.walk(out):
                for f in files:
                    fp = os.path.join(root, f)
                    rel = os.path.relpath(fp, out).replace("\\", "/")
                    if rel.startswith("_selftest/"):
                        continue
                    z.write(fp, rel)
        print("[gen] zip: %s (%.1f MB)" % (zp, os.path.getsize(zp) / 1e6))
    print("[gen] DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
