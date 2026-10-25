# -*- coding: utf-8 -*-
"""gen_synth_targeted.py - sinh data synth TARGETED danh 8 failure mode (TASK-19).

Module API (giong gui_sft.py):
    build_targeted(n, seed, img_dir, done_rate=0.0) -> list[row]
    row = {"image": abs_path, "instruction": str, "action": str,
           "family": "S1".."S8", "episode": id, "step": k}

done_rate: ty le episode co them 1 row DONE o CUOI (mac dinh 0.0 = hanh vi
cua ban, output IDENTICAL voi truoc). DONE row them vao sau buoc submit,
anh lai cua buoc cuoi + bang "done" xanh => model thay "sau Submit thi DONE".
Do GLM do (done_discipline_report.md): targeted 250 ep co 0% DONE la nguon
"pha loang" lon nhat => khong co DONE o giua chuoi, chi DONE o cuoi.

PIL 768x512, toa do normalized 0..1000 (x=px/768*1000, y=py/512*1000).
Deterministic: random.Random(seed) -> cung seed cho cung anh + row.
ASCII-only source (bai hoc cp1252).
"""
import os
import random
from PIL import Image, ImageDraw

CW, CH = 768, 512
DEFAULT_DONE_RATE = 0.0

# Thong diep hien thi khi task da xong (dung khi them row DONE cuoi episode).
DONE_MSG = {
    "S1": "Logged in successfully.",
    "S2": "Code verified.",
    "S3": "Alert opened.",
    "S4": "Transfer verified.",
    "S5": "Form sent.",
    "S6": "Slider set.",
    "S7": "Batch submitted.",
    "S8": "Form accepted.",
    # 22/10: 2 mode moi nham nut that da do tren bench-v22 (loop + misread)
    "S9": "Order applied.",
    "S10": "Form submitted.",
}


def with_success(src_path, out_path, msg):
    """Copy an image and draw a green 'done' banner -> trang thai HOAN TAT."""
    im = Image.open(src_path).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([40, 54, 470, 88], fill=(26, 77, 46))
    d.text((52, 66), msg, fill=(220, 255, 230))
    im.save(out_path)
    return os.path.abspath(out_path)
PALETTE = {
    "red": (208, 52, 44), "green": (46, 158, 68),
    "blue": (30, 111, 217), "yellow": (201, 161, 10),
    "purple": (122, 59, 189), "orange": (217, 122, 30),
    "teal": (20, 160, 160),
}



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


def new_canvas():
    img = Image.new("RGB", (CW, CH), (240, 240, 242))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, CW, 48], fill=(52, 58, 70))
    d.text((16, 16), "Mock App", fill=(255, 255, 255))
    d.rectangle([0, CH - 36, CW, CH], fill=(228, 230, 235))
    return img, d


def save_img(img, img_dir, name):
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(img_dir, name)
    img.save(path)
    return os.path.abspath(path)


def center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def draw_button(d, box, color, label=""):
    d.rectangle(box, fill=color)
    d.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], outline=(30, 30, 30))
    if label:
        d.text((box[0] + 6, box[1] + (box[3]-box[1])//2 - 6), label,
               fill=(255, 255, 255))


def draw_input(d, box, value="", highlight=False, placeholder=""):
    fill = (255, 255, 255)
    outline = (90, 120, 200) if highlight else (160, 160, 170)
    d.rectangle(box, fill=fill, outline=outline, width=2)
    txt = value if value else placeholder
    color = (30, 30, 30) if value else (150, 150, 160)
    d.text((box[0] + 6, box[1] + (box[3]-box[1])//2 - 6), txt, fill=color)


def draw_note(d, box, lines):
    d.rectangle(box, fill=(255, 248, 220), outline=(180, 160, 90))
    y = box[1] + 4
    for ln in lines:
        d.text((box[0] + 6, y), ln, fill=(60, 40, 20))
        y += 14


# ---------- S1: read_note_login ----------
def gen_s1(rng, img_dir, ep_id):
    user = _mk_user(rng)
    pw = _mk_pass(rng)
    # layout
    note_box = [CW - 230, 56, CW - 16, 110]
    user_field = [60, 130, 320, 165]
    pass_field = [60, 195, 320, 230]
    login_btn = [60, 260, 200, 295]
    rows = []
    # step0: type username (empty form, note visible)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "user: " + user, "pass: " + pw])
    draw_input(d, user_field, "", highlight=True, placeholder="username")
    draw_input(d, pass_field, "", placeholder="password")
    draw_button(d, login_btn, (30, 111, 217), "Login")
    p = save_img(img, img_dir, "s1_%d_0.png" % ep_id)
    rows.append((p, "Type the username shown in the note box into the username field.",
                 "TYPE " + user))
    # step1: type password (username filled)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "user: " + user, "pass: " + pw])
    draw_input(d, user_field, user)
    draw_input(d, pass_field, "", highlight=True, placeholder="password")
    draw_button(d, login_btn, (30, 111, 217), "Login")
    p = save_img(img, img_dir, "s1_%d_1.png" % ep_id)
    rows.append((p, "Type the password shown in the note box into the password field.",
                 "TYPE " + pw))
    # step2: click login
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "user: " + user, "pass: " + pw])
    draw_input(d, user_field, user)
    draw_input(d, pass_field, "*" * len(pw))
    cx, cy = center(login_btn)
    draw_button(d, login_btn, (30, 111, 217), "Login")
    p = save_img(img, img_dir, "s1_%d_2.png" % ep_id)
    rows.append((p, "Click the Login button to submit the form.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S2: code_tab_submit ----------
def gen_s2(rng, img_dir, ep_id):
    code = _mk_code(rng)
    # tab buttons
    tab_code = [60, 56, 180, 90]
    tab_home = [190, 56, 310, 90]
    code_box = [60, 100, 320, 150]
    input_field = [60, 200, 320, 235]
    submit_btn = [60, 265, 200, 300]
    rows = []
    # step0: click Home tab (code shown on Code tab; now switch to Home)
    img, d = new_canvas()
    draw_button(d, tab_code, (120, 120, 130), "Code")
    draw_button(d, tab_home, (30, 111, 217), "Home")
    d.text((code_box[0] + 4, code_box[1] + 4), "Code: " + code, fill=(30, 30, 30))
    draw_input(d, input_field, "", placeholder="enter code")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    cx, cy = center(tab_home)
    p = save_img(img, img_dir, "s2_%d_0.png" % ep_id)
    rows.append((p, "Click the Home tab to switch to the input page.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step1: type code
    img, d = new_canvas()
    draw_button(d, tab_code, (120, 120, 130), "Code")
    draw_button(d, tab_home, (30, 111, 217), "Home")
    d.text((code_box[0] + 4, code_box[1] + 4), "Code: " + code, fill=(30, 30, 30))
    draw_input(d, input_field, "", highlight=True, placeholder="enter code")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s2_%d_1.png" % ep_id)
    rows.append((p, "Type the code shown on the page into the input field.",
                 "TYPE " + code))
    # step2: click submit
    img, d = new_canvas()
    draw_button(d, tab_code, (120, 120, 130), "Code")
    draw_button(d, tab_home, (30, 111, 217), "Home")
    d.text((code_box[0] + 4, code_box[1] + 4), "Code: " + code, fill=(30, 30, 30))
    draw_input(d, input_field, code)
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s2_%d_2.png" % ep_id)
    rows.append((p, "Click the Submit button to verify the code.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S3: scroll_reveal_click ----------
def gen_s3(rng, img_dir, ep_id):
    item_label = "Item %d" % rng.randrange(10, 1000)
    rows = []
    # step0: scroll down (list with "keep scrolling" message)
    img, d = new_canvas()
    d.text((60, 70), "List (showing 1-8 of 100)", fill=(30, 30, 30))
    for i in range(8):
        d.text((60, 95 + i * 22), "Entry %d" % (i + 1), fill=(60, 60, 60))
    d.text((60, 95 + 8 * 22 + 4), "More entries loading... keep scrolling.", fill=(180, 100, 20))
    p = save_img(img, img_dir, "s3_%d_0.png" % ep_id)
    rows.append((p, "Scroll the list to the bottom to reveal the last entry.",
                 "KEY End"))
    # step1: click revealed item
    img, d = new_canvas()
    d.text((60, 70), "List (showing 93-100 of 100)", fill=(30, 30, 30))
    item_box = [60, 95, 320, 125]
    d.rectangle(item_box, fill=(30, 111, 217))
    d.text((item_box[0] + 6, item_box[1] + 6), item_label, fill=(255, 255, 255))
    cx, cy = center(item_box)
    p = save_img(img, img_dir, "s3_%d_1.png" % ep_id)
    rows.append((p, "Click the last entry that was revealed.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S4: copy_paste_verify ----------
def gen_s4(rng, img_dir, ep_id):
    src_text = "%s-%s-%s" % (_mk_code(rng, 3), _mk_code(rng, 3),
                             _mk_code(rng, 1))
    src_box = [60, 80, 260, 120]
    dst_box = [60, 170, 260, 205]
    verify_btn = [60, 240, 180, 275]
    rows = []
    # step0: click source
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    cx, cy = center(src_box)
    p = save_img(img, img_dir, "s4_%d_0.png" % ep_id)
    rows.append((p, "Click the source box.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step1: ctrl+a
    img, d = new_canvas()
    d.rectangle(src_box, fill=(180, 210, 255), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_1.png" % ep_id)
    rows.append((p, "Select all text in the source box with Ctrl+A.",
                 "KEY ctrl+a"))
    # step2: ctrl+c
    img, d = new_canvas()
    d.rectangle(src_box, fill=(180, 210, 255), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_2.png" % ep_id)
    rows.append((p, "Copy the selected text with Ctrl+C.",
                 "KEY ctrl+c"))
    # step3: click target
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, "", highlight=True, placeholder="target")
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    cx, cy = center(dst_box)
    p = save_img(img, img_dir, "s4_%d_3.png" % ep_id)
    rows.append((p, "Click the target box to focus it.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step4: ctrl+v
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, src_text)
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_4.png" % ep_id)
    rows.append((p, "Paste the copied text into the target box with Ctrl+V.",
                 "KEY ctrl+v"))
    # step5: click verify
    img, d = new_canvas()
    d.rectangle(src_box, fill=(230, 245, 230), outline=(80, 120, 80))
    d.text((src_box[0] + 6, src_box[1] + 6), src_text, fill=(30, 30, 30))
    draw_input(d, dst_box, src_text)
    cx, cy = center(verify_btn)
    draw_button(d, verify_btn, (30, 111, 217), "Verify")
    p = save_img(img, img_dir, "s4_%d_5.png" % ep_id)
    rows.append((p, "Click the Verify button to confirm the transfer.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S5: fill_all_fields ----------
def gen_s5(rng, img_dir, ep_id):
    name = _mk_name(rng)
    email = _mk_email(rng)
    qty = str(rng.randrange(1, 10))
    note_box = [CW - 250, 56, CW - 16, 128]
    term_box = [60, 250, 80, 275]
    name_field = [60, 80, 300, 115]
    email_field = [60, 135, 300, 170]
    qty_field = [60, 190, 150, 225]
    submit_btn = [60, 290, 200, 325]
    rows = []
    # step0: type name (field highlighted)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, "", highlight=True, placeholder="Full name")
    draw_input(d, email_field, "", placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(160, 160, 170))
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_0.png" % ep_id)
    rows.append((p, "Type the full name shown in the note into the Full name field.",
                 "TYPE " + name))
    # step1: type email
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, name)
    draw_input(d, email_field, "", highlight=True, placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(160, 160, 170))
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_1.png" % ep_id)
    rows.append((p, "Type the email shown in the note into the Email field.",
                 "TYPE " + email))
    # step2: type qty
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, "", highlight=True, placeholder="Qty")
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(160, 160, 170))
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_2.png" % ep_id)
    rows.append((p, "Type the quantity shown in the note into the Qty field.",
                 "TYPE " + qty))
    # step3: click terms checkbox
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, qty)
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(200, 200, 210), outline=(90, 120, 200), width=2)
    cx, cy = center(term_box)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_3.png" % ep_id)
    rows.append((p, "Tick the 'I agree to terms' checkbox.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step4: click submit
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, qty)
    d.text((term_box[0] + 22, term_box[1] + 4), "I agree to terms", fill=(30, 30, 30))
    d.rectangle(term_box, fill=(30, 111, 217))
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s5_%d_4.png" % ep_id)
    rows.append((p, "Click the Submit button to send the form.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S6: slider_to_target ----------
def gen_s6(rng, img_dir, ep_id):
    target = rng.randrange(15, 96)
    track = [120, 200, 640, 240]
    thumb_x = 120 + int((track[2]-track[0]) * 0.15)
    rows = []
    # step0: click track at target%
    img, d = new_canvas()
    d.text((60, 150), "Set slider to %d%%" % target, fill=(30, 30, 30))
    d.rectangle(track, fill=(200, 200, 210), outline=(120, 120, 130))
    # thumb current
    d.ellipse([thumb_x-8, track[1]-4, thumb_x+8, track[3]+4], fill=(30, 111, 217))
    d.text((track[0], track[3]+8), "current: 15%%" % (), fill=(60, 60, 60)) if False else None
    d.text((track[0], track[3] + 8), "current: 15%", fill=(60, 60, 60))
    click_x = track[0] + int((track[2]-track[0]) * target / 100.0)
    click_y = (track[1] + track[3]) // 2
    p = save_img(img, img_dir, "s6_%d_0.png" % ep_id)
    rows.append((p, "Click the slider track at the position shown on the page.",
                 "CLICK %d %d" % (norm(click_x, CW), norm(click_y, CH))))
    # step1: fine-tune with arrow
    img, d = new_canvas()
    d.text((60, 150), "Set slider to %d%%" % target, fill=(30, 30, 30))
    d.rectangle(track, fill=(200, 200, 210), outline=(120, 120, 130))
    d.ellipse([click_x-8, track[1]-4, click_x+8, track[3]+4], fill=(30, 111, 217))
    d.text((track[0], track[3] + 8), "current: %d%%" % target, fill=(60, 60, 60))
    arrow = "ArrowRight" if target > 50 else "ArrowLeft"
    p = save_img(img, img_dir, "s6_%d_1.png" % ep_id)
    rows.append((p, "Press %s to fine-tune the slider to the exact value shown." % arrow,
                 "KEY " + arrow))
    return rows


# ---------- S7: counter_to_n ----------
def gen_s7(rng, img_dir, ep_id):
    target = rng.randrange(2, 10)
    inc_btn = [60, 130, 150, 170]
    sub_btn = [60, 200, 180, 235]
    rows = []
    for step in range(target):
        img, d = new_canvas()
        d.text((60, 70), "Target: %d" % target, fill=(30, 30, 30))
        d.text((60, 95), "Current: %d" % step, fill=(60, 60, 60))
        cx, cy = center(inc_btn)
        draw_button(d, inc_btn, (30, 111, 217), "+1")
        draw_button(d, sub_btn, (120, 120, 130), "Submit")
        p = save_img(img, img_dir, "s7_%d_%d.png" % (ep_id, step))
        rows.append((p, "Click the +1 button to increment the counter to the target shown.",
                     "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # final: submit
    img, d = new_canvas()
    d.text((60, 70), "Target: %d" % target, fill=(30, 30, 30))
    d.text((60, 95), "Current: %d" % target, fill=(30, 120, 30))
    draw_button(d, inc_btn, (120, 120, 130), "+1")
    cx, cy = center(sub_btn)
    draw_button(d, sub_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s7_%d_%d.png" % (ep_id, target))
    rows.append((p, "Click the Submit button.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S8: error_recovery_full ----------
def gen_s8(rng, img_dir, ep_id):
    name = _mk_name(rng)
    email = _mk_email(rng)
    qty = str(rng.randrange(1, 10))
    note_box = [CW - 250, 130, CW - 16, 202]
    name_field = [60, 80, 300, 115]
    email_field = [60, 135, 300, 170]
    qty_field = [60, 190, 150, 225]
    submit_btn = [60, 250, 200, 285]
    rows = []
    # step0: submit empty (reveal errors)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, "", placeholder="Full name")
    draw_input(d, email_field, "", placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_0.png" % ep_id)
    rows.append((p, "Click Submit on the empty form to reveal validation errors.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    # step1: type name (errors shown)
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    d.text((60, 56), "Errors: name required, email required, qty required", fill=(180, 30, 30))
    draw_input(d, name_field, "", highlight=True, placeholder="Full name")
    draw_input(d, email_field, "", placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_1.png" % ep_id)
    rows.append((p, "Type the full name shown in the note into the Full name field.",
                 "TYPE " + name))
    # step2: type email
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    d.text((60, 56), "Errors: email required, qty required", fill=(180, 30, 30))
    draw_input(d, name_field, name)
    draw_input(d, email_field, "", highlight=True, placeholder="Email")
    draw_input(d, qty_field, "", placeholder="Qty")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_2.png" % ep_id)
    rows.append((p, "Type the email shown in the note into the Email field.",
                 "TYPE " + email))
    # step3: type qty
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    d.text((60, 56), "Errors: qty required", fill=(180, 30, 30))
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, "", highlight=True, placeholder="Qty")
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_3.png" % ep_id)
    rows.append((p, "Type the quantity shown in the note into the Qty field.",
                 "TYPE " + qty))
    # step4: submit again
    img, d = new_canvas()
    draw_note(d, note_box, ["Note:", "name: " + name, "email: " + email, "qty: " + qty])
    draw_input(d, name_field, name)
    draw_input(d, email_field, email)
    draw_input(d, qty_field, qty)
    cx, cy = center(submit_btn)
    draw_button(d, submit_btn, (30, 111, 217), "Submit")
    p = save_img(img, img_dir, "s8_%d_4.png" % ep_id)
    rows.append((p, "Click Submit again after fixing all fields.",
                 "CLICK %d %d" % (norm(cx, CW), norm(cy, CH))))
    return rows


# ---------- S9: doi chien luoc khi hanh dong lap (nham C2_stuck_repeat) ----------
# Bench-v22 tren B15 cho C2_stuck_repeat 7->9: model lap mot hanh dong (vi du
# bam Apply 7 lan) thay vi doi hanh dong. Bai nay day: bam Apply -> trang
# bao LOI xuat hien -> thay bang tick checkbox -> bam Apply lai thanh cong.
# Anh buoc 2 co BANNER DO, nen chi model DOC MAN HINH moi biet can doi.
def gen_s9(rng, img_dir, ep_id):
    name = _mk_name(rng)
    qty = str(rng.randrange(2, 40))
    # layout
    err_box = [40, 56, 470, 92]
    title = [40, 100, 420, 128]
    field = [60, 140, 320, 175]
    agree_box = [60, 195, 82, 217]          # checkbox (chua tick)
    agree_lbl = [92, 196, 380, 218]
    apply_btn = [60, 245, 200, 280]
    rows = []
    ERR = "Nothing changed: you must tick 'I agree' before applying."

    # step0: form san, chua tick -> bam Apply (hanh dong nao, hop le)
    img, d = new_canvas()
    d.text((40, 104), "Order form", fill=(30, 30, 30))
    draw_input(d, field, name, highlight=True, placeholder="item name")
    d.rectangle(agree_box, fill=(255, 255, 255), outline=(60, 60, 70), width=2)
    d.text((92, 199), "I agree to the terms", fill=(30, 30, 30))
    draw_button(d, apply_btn, (30, 111, 217), "Apply")
    p = save_img(img, img_dir, "s9_%d_0.png" % ep_id)
    rows.append((p, "Fill the item name and apply the order. If the page says "
                    "something is missing, fix that first instead of pressing "
                    "Apply again.",
                 "CLICK %d %d" % (norm(center(apply_btn)[0], CW),
                                  norm(center(apply_btn)[1], CH))))

    # step1: banner LOI xuat hien -> TICK checkbox (DOI HANH DONG, khong lap)
    img, d = new_canvas()
    d.rectangle(err_box, fill=(250, 226, 226), outline=(190, 60, 60))
    d.text((48, 68), ERR, fill=(150, 30, 30))
    d.text((40, 104), "Order form", fill=(30, 30, 30))
    draw_input(d, field, name, placeholder="item name")
    d.rectangle(agree_box, fill=(255, 255, 255), outline=(190, 60, 60), width=2)
    d.text((92, 199), "I agree to the terms", fill=(30, 30, 30))
    draw_button(d, apply_btn, (30, 111, 217), "Apply")
    p = save_img(img, img_dir, "s9_%d_1.png" % ep_id)
    rows.append((p, "The page reported that something is missing. Do it before "
                    "applying again.",
                 "CLICK %d %d" % (norm(center(agree_box)[0], CW),
                                  norm(center(agree_box)[1], CH))))

    # step2: da tick -> bam Apply lai (lan nay moi dung)
    img, d = new_canvas()
    d.text((40, 104), "Order form", fill=(30, 30, 30))
    draw_input(d, field, name, placeholder="item name")
    d.rectangle(agree_box, fill=(30, 111, 217), outline=(30, 30, 30), width=2)
    d.text((100, 199), "X", fill=(255, 255, 255))
    d.text((112, 199), "I agree to the terms", fill=(30, 30, 30))
    draw_button(d, apply_btn, (30, 111, 217), "Apply")
    p = save_img(img, img_dir, "s9_%d_2.png" % ep_id)
    rows.append((p, "The agreement is ticked now, so the order can be applied.",
                 "CLICK %d %d" % (norm(center(apply_btn)[0], CW),
                                  norm(center(apply_btn)[1], CH))))
    return rows


# ---------- S10: doc gia tri tren man hinh truoc khi go (nham C3_misread_text) ----------
# Bench-v22: C3_misread_text 7->9 (model bo qua note box va go nham).
# Bai nay: 2 field TEN CHUNG ("Field A"/"Field B"), gia tri nam o note box,
# va THU TU TRONG NOTE KHONG khop thu tu field (A = gia tri thu 2).
# => model chi dung neu DOC MAN HINH; instruction KHONG chua gia tri.
def gen_s10(rng, img_dir, ep_id):
    va = _mk_name(rng)
    vb = _mk_code(rng, 5)
    note_box = [CW - 250, CH - 120, CW - 14, CH - 46]   # goc phai duoi
    fld_a = [60, 140, 330, 176]
    fld_b = [60, 205, 330, 241]
    sub_btn = [60, 265, 200, 300]
    rows = []
    # note: B truoc, A sau -> thu tu KHONG khop field
    note_lines = ["Values:", "B = " + vb, "A = " + va]

    # step0: Field A (highlight) -> go gia tri A (doc tu note, dong thu 3)
    img, d = new_canvas()
    d.text((40, 104), "Fill both fields with the values listed in the note.",
           fill=(30, 30, 30))
    draw_input(d, fld_a, "", highlight=True, placeholder="Field A")
    draw_input(d, fld_b, "", placeholder="Field B")
    draw_button(d, sub_btn, (30, 111, 217), "Submit")
    draw_note(d, note_box, note_lines)
    p = save_img(img, img_dir, "s10_%d_0.png" % ep_id)
    rows.append((p, "Fill Field A and Field B with the values listed in the "
                    "note box, then submit.",
                 "TYPE " + va))

    # step1: Field B (highlight) -> go gia tri B (dong thu 2 cua note)
    img, d = new_canvas()
    d.text((40, 104), "Fill both fields with the values listed in the note.",
           fill=(30, 30, 30))
    draw_input(d, fld_a, va, placeholder="Field A")
    draw_input(d, fld_b, "", highlight=True, placeholder="Field B")
    draw_button(d, sub_btn, (30, 111, 217), "Submit")
    draw_note(d, note_box, note_lines)
    p = save_img(img, img_dir, "s10_%d_1.png" % ep_id)
    rows.append((p, "Fill Field A and Field B with the values listed in the "
                    "note box, then submit.",
                 "TYPE " + vb))

    # step2: submit
    img, d = new_canvas()
    d.text((40, 104), "Fill both fields with the values listed in the note.",
           fill=(30, 30, 30))
    draw_input(d, fld_a, va, placeholder="Field A")
    draw_input(d, fld_b, vb, placeholder="Field B")
    draw_button(d, sub_btn, (30, 111, 217), "Submit")
    draw_note(d, note_box, note_lines)
    p = save_img(img, img_dir, "s10_%d_2.png" % ep_id)
    rows.append((p, "Both fields are filled with the values from the note, so "
                    "the form can be submitted.",
                 "CLICK %d %d" % (norm(center(sub_btn)[0], CW),
                                  norm(center(sub_btn)[1], CH))))
    return rows


FAMILIES = [gen_s1, gen_s2, gen_s3, gen_s4, gen_s5, gen_s6, gen_s7, gen_s8]
FAMILY_NAMES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
# Bench-v22 tren B15: 12/36 = 33,3%; cluster C4_no_submit BAT BIEN (11->12) =>
# "thieu DONE" KHONG phai nut that. Hai cluster tang: C2_stuck_repeat (7->9)
# va C3_misread_text (7->9) => dut lich sang LOOP + DOC SAI MAN HINH.
# => S9: "doi chien luoc khi hanh dong lap" (thay bang loi, khong bam lai).
# => S10: "doc gia tri tren man hinh truoc khi go" (gia tri nam o note, THU TU
#        note KHONG khop thu tu field + nhan KHONG phai ten field => chi doc
#        man hinh moi biet).
FAMILIES_NEW = [gen_s9, gen_s10]
FAMILY_NAMES_NEW = ["S9", "S10"]
FAMILIES_ALL = FAMILIES + FAMILIES_NEW
FAMILY_NAMES_ALL = FAMILY_NAMES + FAMILY_NAMES_NEW


def pick_families(which=None):
    """-> (list ham, list ten) theo `which` (mac dinh: 8 family cu)."""
    if which is None:
        return list(FAMILIES), list(FAMILY_NAMES)
    if isinstance(which, str):
        w = which.strip().upper()
        if w == "ALL":
            return list(FAMILIES_ALL), list(FAMILY_NAMES_ALL)
        if w in ("S9S10", "NEW", "S9,S10"):
            return list(FAMILIES_NEW), list(FAMILY_NAMES_NEW)
        want = [x.strip().upper() for x in which.split(",") if x.strip()]
    else:
        want = [str(x).strip().upper() for x in which]
    fams, names = [], []
    for f, nm in zip(FAMILIES_ALL, FAMILY_NAMES_ALL):
        if nm in want:
            fams.append(f)
            names.append(nm)
    if not fams:
        raise SystemExit("khong co family nao khop: %r" % (which,))
    return fams, names


def build_targeted(n, seed, img_dir, done_rate=DEFAULT_DONE_RATE, families=None):
    """Sinh n episode targeted, phan bo deu 8 family. Tra ve list row.

    done_rate: ty le episode duoc them 1 row DONE o CUOI (mac dinh 0.0 ->
    hanh vi cu, output byte-identical voi truoc khi sua).

    families (22/10, BACKWARD-COMPAT mac dinh = 8 family cu):
      None      -> 8 family cu (GHI NGUYEN, dung cho kernel da build)
      "ALL"     -> 10 family (them S9 = doi chien luoc, S10 = doc man hinh)
      "S9S10"   -> chi 2 family moi (A/B test)
      list[str] -> cac family theo ten
    """
    fams, fnames = pick_families(families)
    rng = random.Random(seed)
    rows = []
    ep_counter = 0
    # distribute episodes across families
    base = n // len(fams)
    rem = n % len(fams)
    counts = [base + (1 if i < rem else 0) for i in range(len(fams))]
    for fi, fam in enumerate(fams):
        for _ in range(counts[fi]):
            ep_id = ep_counter
            ep_counter += 1
            # re-seed per episode for determinism but consume rng for variety
            ep_seed = rng.randrange(10**9)
            ep_rng = random.Random(ep_seed)
            steps = fam(ep_rng, img_dir, ep_id)
            fname = fnames[fi]
            for k, (path, instr, action) in enumerate(steps):
                rows.append({
                    "image": path,
                    "instruction": instr,
                    "action": action,
                    "family": fname,
                    "episode": ep_id,
                    "step": k,
                })
            # them row DONE o cuoi (anh = anh buoc cuoi + bang "done" xanh)
            if done_rate > 0 and steps and ep_rng.random() < done_rate:
                msg = DONE_MSG.get(fname, "Task complete.")
                last_path, _last_instr, _last_act = steps[-1]
                dpath = with_success(last_path,
                                     os.path.join(img_dir,
                                                  "s_%s_%d_done.png" % (fname, ep_id)),
                                     msg)
                rows.append({
                    "image": dpath,
                    "instruction": "The task is finished. %s" % msg,
                    "action": "DONE",
                    "family": fname,
                    "episode": ep_id,
                    "step": len(steps),
                })
    return rows


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="/tmp/synth_out")
    a = ap.parse_args()
    rows = build_targeted(a.n, a.seed, a.out)
    print("total rows:", len(rows))
    from collections import Counter
    print("by family:", dict(Counter(r["family"] for r in rows)))
    print("sample:", rows[0])
