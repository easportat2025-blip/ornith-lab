# -*- coding: utf-8 -*-
"""test_synth_new_modes.py - self-test cho 2 mode MOI cua gen_synth_targeted:
S9 (doi chien luoc khi hanh dong lap) + S10 (doc gia tri man hinh truoc khi go).

Nham DUNG nut that da do tren bench-v22 (22/10):
  C2_stuck_repeat 7->9 (lap hanh dong)  => S9
  C3_misread_text 7->9 (doc sai man hinh) => S10

Chay offline, khong GPU/key:
    python phase13-gui/test_synth_new_modes.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_synth_targeted import build_targeted, pick_families

FAILS = []


def ok(cond, msg):
    print("  %s %s" % ("ok  " if cond else "FAIL", msg))
    if not cond:
        FAILS.append(msg)


def main():
    d = tempfile.mkdtemp(prefix="synth_new_")
    rows = build_targeted(12, 4242, d, done_rate=0.0, families="S9S10")
    s9 = [r for r in rows if r["family"] == "S9"]
    s10 = [r for r in rows if r["family"] == "S10"]
    print("[test] S9/S10: %d row (S9=%d, S10=%d)" % (len(rows), len(s9), len(s10)))
    ok(len(s9) > 0 and len(s10) > 0, "ca 2 family moi co row")

    # ---- S9: buoc 2 phai DOI hanh dong (khong lap) ------------------------
    bad_loop = 0
    bad_step = 0
    for ep in set(r["episode"] for r in s9):
        rs = sorted([r for r in s9 if r["episode"] == ep], key=lambda r: r["step"])
        if len(rs) != 3:
            bad_step += 1
            continue
        a0, a1, a2 = rs[0]["action"], rs[1]["action"], rs[2]["action"]
        # buoc 1 (sau loi) phai KHAC buoc 0 (doi chien luoc) va buoc 2 phai
        # trung ve toa do voi buoc 0 (bam Apply lai)
        if a1 == a0 or a2 != a0:
            bad_loop += 1
    ok(bad_step == 0, "moi episode S9 co dung 3 buoc")
    ok(bad_loop == 0,
       "S9: buoc sau loi DOI hanh dong, buoc cuoi moi la Apply lai "
       "(anti-loop)")

    # ---- S9: anh buoc 2 phai CO banner loi (khac anh buoc 1) -------------
    from PIL import Image
    diff_ok = 0
    tot = 0
    for ep in set(r["episode"] for r in s9):
        rs = sorted([r for r in s9 if r["episode"] == ep], key=lambda r: r["step"])
        if len(rs) < 2:
            continue
        tot += 1
        a = Image.open(rs[0]["image"]).convert("RGB")
        b = Image.open(rs[1]["image"]).convert("RGB")
        pa, pb = a.load(), b.load()
        # vung banner loi [40,56,470,92] phai co pixel do (190,60,60)-ish
        red = 0
        for x in range(45, 465, 7):
            for y in range(58, 90, 4):
                r, g, bl = pb[x, y]
                if r > 130 and g < 90 and bl < 90:
                    red += 1
        if red >= 3:
            diff_ok += 1
    ok(tot > 0 and diff_ok == tot,
       "S9: anh buoc 2 co banner LOI do (model phai doc man hinh moi biet)")

    # ---- S10: gia tri FIELD A KHONG phai dong dau note --------------------
    bad_map = 0
    tot10 = 0
    for ep in set(r["episode"] for r in s10):
        rs = sorted([r for r in s10 if r["episode"] == ep], key=lambda r: r["step"])
        if len(rs) != 3:
            bad_map += 1
            continue
        tot10 += 1
        t_a = rs[0]["action"][len("TYPE "):]
        t_b = rs[1]["action"][len("TYPE "):]
        # doc note tren anh buoc 0: dong "A = <v>" va "B = <v>"
        # (ung vien = CHINH gia tri trong action + it nhieu gia tri ngau nhien
        #  de tranh 'match' nham)
        cands = [t_a, t_b] + _CANDIDATES[:20]
        vals = read_note_values(rs[0]["image"], cands)
        if not vals or vals.get("A") != t_a or vals.get("B") != t_b:
            bad_map += 1
        # va A phai KHONG bang dong DAU cua note (truong hop doi thu tu)
        first = vals.get("_first") if vals else None
        if vals and first and vals.get("A") == first:
            bad_map += 1
    ok(tot10 > 0 and bad_map == 0,
       "S10: mapping note -> field DUNG va thu tu note DA bi doi "
       "(model phai doc man hinh, khong the copy theo vi tri)")

    # ---- S10: instruction KHONG chua gia tri ------------------------------
    leak = [r for r in s10
            if r["action"].startswith("TYPE ") and
            r["action"][5:] in r["instruction"]]
    ok(not leak, "S10: instruction KHONG lo gia tri (chi man hinh moi co)")

    # ---- backward-compat: families mac dinh van 8 ------------------------
    fams, names = pick_families(None)
    ok(len(fams) == 8 and names[-1] == "S8",
       "backward-compat: mac dinh van 8 family cu (S9/S10 la opt-in)")
    fams, names = pick_families("ALL")
    ok(len(fams) == 10 and names[-2:] == ["S9", "S10"],
       "families='ALL' => 10 family")

    print("[test] %s" % ("PASS" if not FAILS else "FAIL (%d)" % len(FAILS)))
    return 0 if not FAILS else 1


def read_note_values(path, candidates=None):
    """Doc gia tri trong note box ('A = ...', 'B = ...') bang so sanh CROP that.

    Note box = [CW-250, CH-120, CW-14, CH-46]; dong 0 = "Values:", dong 1 =
    "B = ...", dong 2 = "A = ..." (thu tu DOI so voi thu tu field A/B).
    """
    from PIL import Image, ImageDraw
    if candidates is None:
        candidates = _CANDIDATES
    im = Image.open(path).convert("RGB")
    W, H = im.size
    px = im.load()
    region = (W - 250, H - 120, W - 14, H - 46)
    bg = (255, 248, 220)
    col = (60, 40, 20)
    x0 = region[0] + 6
    y0 = region[1] + 4

    def line_score(text, line_idx):
        """So pixel 'dam' trong 1 dong cua note voi duong mau cua text."""
        tmp = Image.new("RGB", (240, 14), bg)
        ImageDraw.Draw(tmp).text((2, 1), text, fill=col)
        tp = tmp.load()
        hit = 0
        for y in range(14):
            ry = y0 + line_idx * 14 + y
            if ry >= H:
                continue
            for x in range(230):
                if tp[x + 2, y] == bg:
                    continue
                rx = x0 + x
                if rx >= W:
                    continue
                r, g, bl = px[rx, ry]
                if abs(r - col[0]) < 40 and abs(g - col[1]) < 40 and \
                        abs(bl - col[2]) < 40:
                    hit += 1
        return hit

    out = {}
    for key, line_idx in (("B", 1), ("A", 2)):
        best, bestv = 0, None
        for cand in candidates:
            sc = line_score("%s = %s" % (key, cand), line_idx)
            if sc > best:
                best, bestv = sc, cand
        if best >= 12:
            out[key] = bestv
    # dong gia tri DAU TIEN trong note = dong 1 (B) => bang chung thu tu doi.
    # Phai lay ung vien diem CAO NHAT (nguong thap se false positive: tieu de
    # "B = " trung het nen "B = <gia tri sai>" cung khop).
    best, bestv = 0, None
    for cand in candidates:
        sc = line_score("B = %s" % cand, 1)
        if sc > best:
            best, bestv = sc, cand
    if best >= 12:
        out["_first"] = bestv
    return out


def _diff(a, b, tol=12):
    return any(abs(a[i] - b[i]) > tol for i in range(3))


# tap gia tri ung vien (dung cho OCR pixel): lay tu hop _mk_name/_mk_code
import random
_CANDIDATES = []
_rng = random.Random(99)
import gen_synth_targeted as _g
for _ in range(60):
    _CANDIDATES.append(_g._mk_name(_rng))
    _CANDIDATES.append(_g._mk_code(_rng, 5))
_CANDIDATES = list(dict.fromkeys(_CANDIDATES))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
