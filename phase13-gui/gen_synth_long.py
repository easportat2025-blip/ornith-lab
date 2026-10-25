# -*- coding: utf-8 -*-
"""
gen_synth_long.py - synth data LONG-HORIZON (chuoi nhieu buoc) cho v23.

Y DO (do duoc tren out_bench_v21/b15_result.json, xem LOBBY 20/10 19:40):
  - 20/21 episode FAIL o task nhieu buoc KHONG BAO GIO emit DONE -> chay het
    budget (avg 8.2 step vs max_steps 7-9) roi chet.
  - Task 1 buoc: 10/10 win, deu emit DONE o buoc cuoi.
  => thieu du lieu day "lam du chuoi 8-12 buoc ROI MOI DONE".
  - gen_synth_targeted.py (TASK-19) hien co 0% episode >= 8 buoc (avg 3.88)
    va KHONG co row DONE nao -> model khong thay "sau submit thi DONE" trong
    ngo canh chuoi dai.

Module nay BO SUNG, KHONG THAY THE gen_synth_targeted.py:
    from gen_synth_long import build_long
    rows = build_long(n, seed, img_dir)
    row = {"image": abs_path, "instruction": str, "action": str,
           "family": "L1".."L4", "episode": id, "step": k}

API giong het gen_synth_targeted.build_targeted nen kernel chi can them
1 import. PIL 768x512, toa do normalized 0..1000, deterministic.

done_rate = ty le episode co row DONE cuoi (mac dinh 0.35). Cac episode con
lai ket thuc bang click submit (khong DONE) -> "pha loang" cua ky luat DONE.
Doi gia tri nay theo do luong cua GLM (done_discipline_report.md).

ASCII-only source.
"""
import os
import random
from PIL import Image, ImageDraw

CW, CH = 768, 512
BG = (240, 240, 242)
HEADER = (52, 58, 70)
FOOTER = (228, 230, 235)
PRIMARY = (30, 111, 217)
GHOST = (120, 120, 130)
FIELD = (255, 255, 255)
FOCUSED = (180, 210, 255)
CHECK = (200, 200, 210)
SRCBOX = (230, 245, 230)
TEXT = (30, 30, 30)
DIM = (120, 120, 130)
OK_BG = (26, 77, 46)

FAMILIES = ["L1", "L2", "L3", "L4"]
DEFAULT_DONE_RATE = 0.75



# ---- value pools (procedural) -------------------------------------------
# Muc tieu: hang NGHIN gia tri khac nhau + instruction KHONG chua gia tri
# => model buoc DOC MAN HINH, khong the ghi nho hay copy tu instruction.
_FIRST = ["ada", "bob", "cara", "dan", "emma", "finn", "gina", "hugo",
          "iris", "jade", "kai", "lena", "milo", "nora", "omar", "pia",
          "quinn", "rosa", "sami", "tara", "uma", "vera", "wren", "xena",
          "yuri", "zane", "aria", "bram", "clara", "dmitri", "elena",
          "gwen", "jasper", "kirra", "luca", "mara", "nils", "olga",
          "pavel", "rune", "sigrid", "tova", "ulf", "willa", "yara",
          "zola", "abbie", "bristol"]
_LAST = ["adler", "brand", "cole", "dunn", "egan", "frost", "gale",
         "hunt", "ivers", "jones", "kerr", "lane", "moss", "nolan",
         "owen", "pike", "reyes", "silva", "tate", "ulmer", "vane",
         "ward", "young", "abbott", "carver", "dalton", "easton",
         "fisher", "gannon", "harper", "jensen", "keller", "lawson",
         "merton", "osborn", "pratt", "ranson", "sutton", "turner",
         "upton", "vance", "wolfe", "ashby", "bellamy", "crane"]
_CITY = ["lisbon", "kyoto", "oslo", "prague", "quito", "sofia", "tbilisi",
         "utrecht", "vienna", "warsaw", "xian", "yerevan", "zagreb",
         "accra", "bamako", "cardiff", "durban", "edmonton", "fresno",
         "genoa", "hobart", "ibadan", "jeddah", "kyiv", "lima", "napier",
         "osaka", "porto", "quebec", "rabat", "sapporo", "tucson", "verona",
         "weifang", "xalapa", "zurich", "aarhus", "bruges", "cork",
         "dublin", "eindhoven", "florence", "geneva", "helsinki"]
_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_DOMAIN = ["example.com", "mail.test", "corp.io", "inbox.dev",
           "postbox.net", "quick.org"]


def _mk_user(rng):
    return "%s%d" % (rng.choice(_FIRST), rng.randrange(10, 100))


def _mk_name(rng):
    return "%s %s" % (rng.choice(_FIRST).capitalize(), rng.choice(_LAST).capitalize())


def _mk_email(rng):
    return "%s%d@%s" % (rng.choice(_FIRST), rng.randrange(10, 1000),
                         rng.choice(_DOMAIN))


def _mk_pass(rng):
    n = rng.choice([6, 7, 8])
    return "".join(rng.choice(_ALPHA) for _ in range(n))


def _mk_code(rng, n=4):
    return "".join(rng.choice(_ALPHA) for _ in range(n))


def _mk_city(rng):
    return rng.choice(_CITY).capitalize()


def norm(px, total):
    return max(0, min(1000, int(round(px / total * 1000))))


def r2n(r):
    """r la BOX [x1,y1,x2,y2] -> toa do normalized cua tam box."""
    return [norm((r[0] + r[2]) / 2.0, CW), norm((r[1] + r[3]) / 2.0, CH)]


def new_canvas():
    img = Image.new("RGB", (CW, CH), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CW, 48], fill=HEADER)
    d.text((16, 16), "Mock App", fill=(255, 255, 255))
    d.rectangle([0, CH - 36, CW, CH], fill=FOOTER)
    return img, d


def save_img(img, img_dir, name):
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(img_dir, name)
    img.save(path)
    return os.path.abspath(path)


# --------------------------------------------------------------------------
# Generic screen renderer.
# cfg keys (all optional):
#   title, note:[lines], tabs:[(label,active)], fields:[(key,label,value,focused)],
#   checks:[(key,label,checked)], buttons:[(key,label,primary)],
#   big:(text,sub), message:(text), listitems:[(key,text,hidden,picked)],
#   counter:(current,target), source:(key,text), targetbox:(key,value),
#   done_ok:(text)
# returns (img, pos) with pos[key] = normalized [x,y]
# --------------------------------------------------------------------------
def render(cfg):
    img, d = new_canvas()
    pos = {}
    y = 62
    if cfg.get("title"):
        d.text((24, y), cfg["title"], fill=TEXT)
        y += 24
    if cfg.get("message"):
        txt = cfg["message"]
        d.rectangle([24, y, CW - 24, y + 22], fill=(255, 235, 235),
                    outline=(200, 120, 120))
        d.text((30, y + 6), txt, fill=(170, 30, 30))
        y += 30
    if cfg.get("done_ok"):
        d.rectangle([24, y, CW - 24, y + 24], fill=OK_BG)
        d.text((32, y + 7), cfg["done_ok"], fill=(220, 255, 230))
        y += 32
    if cfg.get("big"):
        big, sub = cfg["big"]
        d.text((24, y), big, fill=(30, 30, 30))
        if sub:
            d.text((24, y + 24), sub, fill=DIM)
        y += 52
    if cfg.get("counter"):
        cur, tgt = cfg["counter"]
        d.text((24, y), "Target: %s" % tgt, fill=TEXT)
        d.text((24, y + 20), "Current: %s" % cur, fill=DIM)
        y += 48
    if cfg.get("tabs"):
        x = 24
        for lbl, active in cfg["tabs"]:
            box = [x, y, x + 76, y + 28]
            d.rectangle(box, fill=PRIMARY if active else GHOST)
            d.text((x + 8, y + 8), lbl, fill=(255, 255, 255))
            if active:
                pos["tab:" + lbl] = r2n(box)
            x += 84
        y += 40
    if cfg.get("note"):
        lines = cfg["note"]
        w = 200
        h = 14 * len(lines) + 12
        box = [CW - 24 - w, 58, CW - 24, 58 + h]
        d.rectangle(box, fill=(255, 248, 220), outline=(180, 160, 90))
        yy = box[1] + 5
        for ln in lines:
            d.text((box[0] + 6, yy), ln, fill=(60, 40, 20))
            yy += 14
    for key, label, value, focused in cfg.get("fields", []):
        box = [24, y, 330, y + 30]
        d.rectangle(box, fill=FOCUSED if focused else FIELD,
                    outline=PRIMARY if focused else (160, 160, 170), width=2)
        d.text((box[0] + 6, y + 8), label, fill=(90, 90, 100))
        if value:
            d.text((box[0] + 116, y + 8), value, fill=TEXT)
        pos[key] = r2n(box)
        y += 38
    for key, label, checked in cfg.get("checks", []):
        box = [24, y, 44, y + 20]
        d.rectangle(box, fill=PRIMARY if checked else CHECK,
                    outline=(90, 90, 100))
        if checked:
            d.text((box[0] + 4, box[1] + 4), "x", fill=(255, 255, 255))
        d.text((50, y + 4), label, fill=TEXT)
        pos[key] = r2n(box)
        y += 30
    if cfg.get("source"):
        key, text = cfg["source"]
        box = [24, y, 300, y + 30]
        d.rectangle(box, fill=SRCBOX, outline=(80, 120, 80))
        d.text((box[0] + 6, y + 8), "source", fill=(90, 90, 100))
        d.text((box[0] + 80, y + 8), text, fill=TEXT)
        pos[key] = r2n(box)
        y += 40
    if cfg.get("targetbox"):
        key, value = cfg["targetbox"]
        box = [24, y, 300, y + 30]
        d.rectangle(box, fill=FOCUSED if value else FIELD,
                    outline=PRIMARY if value else (160, 160, 170), width=2)
        d.text((box[0] + 6, y + 8), "target", fill=(90, 90, 100))
        if value:
            d.text((box[0] + 80, y + 8), value, fill=TEXT)
        pos[key] = r2n(box)
        y += 40
    for key, text, hidden, picked in cfg.get("listitems", []):
        box = [24, y, 330, y + 24]
        if hidden:
            d.rectangle(box, fill=(245, 245, 248))
        elif picked:
            d.rectangle(box, fill=PRIMARY)
            d.text((box[0] + 6, y + 6), text, fill=(255, 255, 255))
        else:
            d.rectangle(box, fill=(238, 240, 245))
            d.text((box[0] + 6, y + 6), text, fill=TEXT)
        if not hidden:
            pos[key] = r2n(box)
        y += 28
    for key, label, primary in cfg.get("buttons", []):
        box = [24, y, 24 + 96, y + 30]
        d.rectangle(box, fill=PRIMARY if primary else GHOST)
        d.text((box[0] + 8, y + 8), label, fill=(255, 255, 255))
        pos[key] = r2n(box)
        y += 40
    return img, pos


def click(pos, key):
    p = pos[key]
    return "CLICK %d %d" % (int(p[0]), int(p[1]))


# --------------------------------------------------------------------------
# Families. Each returns list of (cfg, instruction, action_spec) where
# action_spec = ("click", key) | ("type", text) | ("key", name) | ("done",)
# --------------------------------------------------------------------------
def fam_l1(rng):
    """Long form: 3 fields + checkbox + submit + DONE (9 steps)."""
    name = _mk_name(rng)
    email = _mk_email(rng)
    city = _mk_city(rng)
    note = ["Full name: " + name, "Email: " + email, "City: " + city]
    steps = []
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", "", True),
        ("f_email", "Email", "", False),
        ("f_city", "City", "", False)]},
        "Click the Full name field.",
        ("click", "f_name")))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", "", True),
        ("f_city", "City", "", False)]},
        "Type the full name shown in the note.",
        ("type", name)))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", "", False),
        ("f_city", "City", "", True)]},
        "Click the Email field.",
        ("click", "f_email")))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", email, False),
        ("f_city", "City", "", True)]},
        "Type the email address shown in the note.",
        ("type", email)))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", email, False),
        ("f_city", "City", "", True)]},
        "Click the City field.",
        ("click", "f_city")))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", email, False),
        ("f_city", "City", city, False)]},
        "Type the city shown in the note.",
        ("type", city)))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", email, False),
        ("f_city", "City", city, False)],
        "checks": [("agree", "I agree to the terms", False)],
        "buttons": [("submit", "Submit", True)]},
        "Tick the 'I agree to the terms' checkbox.",
        ("click", "agree")))
    steps.append(({"title": "Registration form", "note": note, "fields": [
        ("f_name", "Full name", name, False),
        ("f_email", "Email", email, False),
        ("f_city", "City", city, False)],
        "checks": [("agree", "I agree to the terms", True)],
        "buttons": [("submit", "Submit", True)]},
        "Click the Submit button.",
        ("click", "submit")))
    steps.append(({"title": "Registration form", "done_ok": "Registered successfully.",
                   "fields": [("f_name", "Full name", name, False),
                              ("f_email", "Email", email, False),
                              ("f_city", "City", city, False)]},
        "The form is submitted and shows success. The task is complete.",
        ("done",)))
    return steps


def fam_l2(rng):
    """Long navigation: read code on tab A, move between tabs, submit (9)."""
    code = _mk_code(rng)
    pin = _mk_code(rng, 4)
    tabs_code = [("Code", True), ("Home", False), ("Extra", False)]
    tabs_home = [("Code", False), ("Home", True), ("Extra", False)]
    tabs_extra = [("Code", False), ("Home", False), ("Extra", True)]
    steps = []
    steps.append(({"title": "Verification", "tabs": tabs_code,
                   "note": ["Code: " + code]},
        "Read the code on the Code tab.",
        ("click", "tab:Code")))
    steps.append(({"title": "Verification", "tabs": tabs_home,
                   "note": ["Code: " + code],
                   "fields": [("f_code", "Verification code", "", True)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the Home tab.",
        ("click", "tab:Home")))
    steps.append(({"title": "Verification", "tabs": tabs_home,
                   "note": ["Code: " + code],
                   "fields": [("f_code", "Verification code", code, False)],
                   "buttons": [("submit", "Submit", True)]},
        "Type the verification code shown in the note.",
        ("type", code)))
    steps.append(({"title": "Verification", "tabs": tabs_extra,
                   "note": ["Code: " + code, "PIN: " + pin],
                   "fields": [("f_pin", "PIN", "", True)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the Extra tab.",
        ("click", "tab:Extra")))
    steps.append(({"title": "Verification", "tabs": tabs_extra,
                   "note": ["Code: " + code, "PIN: " + pin],
                   "fields": [("f_pin", "PIN", "", True)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the PIN field.",
        ("click", "f_pin")))
    steps.append(({"title": "Verification", "tabs": tabs_extra,
                   "note": ["Code: " + code, "PIN: " + pin],
                   "fields": [("f_pin", "PIN", pin, False)],
                   "buttons": [("submit", "Submit", True)]},
        "Type the PIN shown in the note.",
        ("type", pin)))
    steps.append(({"title": "Verification", "tabs": tabs_home,
                   "note": ["Code: " + code, "PIN: " + pin],
                   "fields": [("f_code", "Verification code", code, False),
                              ("f_pin", "PIN", pin, False)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the Home tab again.",
        ("click", "tab:Home")))
    steps.append(({"title": "Verification", "tabs": tabs_home,
                   "note": ["Code: " + code, "PIN: " + pin],
                   "fields": [("f_code", "Verification code", code, False),
                              ("f_pin", "PIN", pin, False)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the Submit button.",
        ("click", "submit")))
    steps.append(({"title": "Verification", "done_ok": "Verified.",
                   "fields": [("f_code", "Verification code", code, False),
                              ("f_pin", "PIN", pin, False)]},
        "The request was submitted successfully. The task is complete.",
        ("done",)))
    return steps


def fam_l3(rng):
    """Long mixed: counter -> filter -> copy/paste -> submit (12)."""
    src_text = "%s-%s-%s" % (_mk_code(rng, 3), _mk_code(rng, 3),
                             _mk_code(rng, 1))
    tgt = rng.choice([3, 4, 5])
    steps = []
    for i in range(3):
        steps.append(({"title": "Batch: step 1 of 3 - count",
                       "counter": (str(i), str(tgt)),
                       "buttons": [("inc", "+1", True), ("submit", "Submit", False)]},
            "Click the +1 button to increment the counter.",
            ("click", "inc")))
    steps.append(({"title": "Batch: step 2 of 3 - filter",
                   "buttons": [("filt", "Size: large", True),
                               ("filt2", "Color: red", False)],
                   "listitems": [("item_apple", "Apple (large)", False, False),
                                 ("item_cherry", "Cherry (small)", False, False)]},
        "Click the 'Size: large' filter.",
        ("click", "filt")))
    steps.append(({"title": "Batch: step 2 of 3 - filter",
                   "buttons": [("filt", "Size: large", True),
                               ("filt2", "Color: red", False)],
                   "listitems": [("item_apple", "Apple (large)", False, True),
                                 ("item_cherry", "Cherry (small)", False, False)]},
        "Click the 'Apple' item.",
        ("click", "item_apple")))
    steps.append(({"title": "Batch: step 3 of 3 - copy",
                   "source": ("src", src_text),
                   "targetbox": ("dst", "")},
        "Click the source box to select its text.",
        ("click", "src")))
    steps.append(({"title": "Batch: step 3 of 3 - copy",
                   "source": ("src", src_text),
                   "targetbox": ("dst", "")},
        "Select all the text in the source box.",
        ("key", "ctrl+a")))
    steps.append(({"title": "Batch: step 3 of 3 - copy",
                   "source": ("src", src_text),
                   "targetbox": ("dst", "")},
        "Copy the selected text.",
        ("key", "ctrl+c")))
    steps.append(({"title": "Batch: step 3 of 3 - copy",
                   "source": ("src", src_text),
                   "targetbox": ("dst", "")},
        "Click the target box.",
        ("click", "dst")))
    steps.append(({"title": "Batch: step 3 of 3 - copy",
                   "source": ("src", src_text),
                   "targetbox": ("dst", "")},
        "Paste the copied text into the target box.",
        ("key", "ctrl+v")))
    steps.append(({"title": "Batch: step 3 of 3 - copy",
                   "source": ("src", src_text),
                   "targetbox": ("dst", src_text),
                   "buttons": [("submit", "Submit", True)]},
        "Click the Submit button.",
        ("click", "submit")))
    steps.append(({"title": "Batch", "done_ok": "Batch submitted.",
                   "source": ("src", src_text),
                   "targetbox": ("dst", src_text)},
        "The batch was submitted successfully. The task is complete.",
        ("done",)))
    return steps


def fam_l4(rng):
    """Wizard, 4 pages, NO early DONE (11 steps)."""
    v1 = _mk_code(rng, 5)
    v2 = _mk_code(rng, 5)
    v3 = _mk_code(rng, 5)
    ans_note = ["A1: " + v1, "A2: " + v2, "A3: " + v3]
    steps = []
    steps.append(({"title": "Wizard - Page 1 of 4", "note": ans_note,
                   "message": "Answer all four pages before submitting.",
                   "buttons": [("next", "Next", True)]},
        "Click Next on page 1 to go to page 2.",
        ("click", "next")))
    steps.append(({"title": "Wizard - Page 2 of 4", "note": ans_note,
                   "fields": [("f1", "Answer 1", "", True)],
                   "buttons": [("next", "Next", True)]},
        "Click the Answer 1 field.",
        ("click", "f1")))
    steps.append(({"title": "Wizard - Page 2 of 4", "note": ans_note,
                   "fields": [("f1", "Answer 1", v1, False)],
                   "buttons": [("next", "Next", True)]},
        "Type the answer shown in the note for page 2.",
        ("type", v1)))
    steps.append(({"title": "Wizard - Page 3 of 4", "note": ans_note,
                   "fields": [("f2", "Answer 2", "", True)],
                   "buttons": [("next", "Next", True)]},
        "Click the Answer 2 field.",
        ("click", "f2")))
    steps.append(({"title": "Wizard - Page 3 of 4", "note": ans_note,
                   "fields": [("f2", "Answer 2", v2, False)],
                   "buttons": [("next", "Next", True)]},
        "Type the answer shown in the note for page 3.",
        ("type", v2)))
    steps.append(({"title": "Wizard - Page 4 of 4", "note": ans_note,
                   "fields": [("f3", "Answer 3", "", True)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the Answer 3 field.",
        ("click", "f3")))
    steps.append(({"title": "Wizard - Page 4 of 4", "note": ans_note,
                   "fields": [("f3", "Answer 3", v3, False)],
                   "buttons": [("submit", "Submit", True)]},
        "Type the answer shown in the note for page 4.",
        ("type", v3)))
    steps.append(({"title": "Wizard - Page 4 of 4", "note": ans_note,
                   "fields": [("f3", "Answer 3", v3, False)],
                   "buttons": [("submit", "Submit", True)]},
        "Click the Submit button.",
        ("click", "submit")))
    steps.append(({"title": "Wizard", "note": ans_note, "done_ok": "All four pages answered.",
                   "fields": [("f3", "Answer 3", v3, False)]},
        "The wizard was submitted successfully. The task is complete.",
        ("done",)))
    return steps


FAM_FUNCS = {"L1": fam_l1, "L2": fam_l2, "L3": fam_l3, "L4": fam_l4}


def build_long(n, seed, img_dir, done_rate=DEFAULT_DONE_RATE):
    """n episode long-horizon, phan bo deu 4 family. Tra ve list row."""
    rng = random.Random(seed)
    rows = []
    base = n // len(FAMILIES)
    rem = n % len(FAMILIES)
    counts = [base + (1 if i < rem else 0) for i in range(len(FAMILIES))]
    ep_id = 0
    for fi, fam in enumerate(FAMILIES):
        for _ in range(counts[fi]):
            ep_rng = random.Random(rng.randrange(10 ** 9))
            steps = FAM_FUNCS[fam](ep_rng)
            # done_rate: episode co row DONE cuoi hay khong
            with_done = ep_rng.random() < done_rate
            for k, (cfg, instr, spec) in enumerate(steps):
                img, pos = render(cfg)
                kind = spec[0]
                if kind == "click":
                    action = click(pos, spec[1])
                elif kind == "type":
                    action = "TYPE " + spec[1]
                elif kind == "key":
                    action = "KEY " + spec[1]
                else:
                    action = "DONE"
                if kind == "done" and not with_done:
                    # bo row DONE -> episode ket thuc bang click submit
                    continue
                path = save_img(img, img_dir, "%s_%d_%d.png" % (fam, ep_id, k))
                rows.append({
                    "image": path,
                    "instruction": instr,
                    "action": action,
                    "family": fam,
                    "episode": ep_id,
                    "step": k,
                })
            ep_id += 1
    return rows


if __name__ == "__main__":
    import argparse
    from collections import Counter
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="/tmp/synth_long")
    ap.add_argument("--done-rate", type=float, default=DEFAULT_DONE_RATE)
    a = ap.parse_args()
    rows = build_long(a.n, a.seed, a.out, a.done_rate)
    print("total rows:", len(rows))
    print("by family:", dict(Counter(r["family"] for r in rows)))
    lens = Counter()
    seen = set()
    for r in rows:
        if r["episode"] in seen:
            continue
        seen.add(r["episode"])
    print("sample:", rows[0])
