# -*- coding: utf-8 -*-
"""test_synth_targeted.py - self-test cho gen_synth_targeted (TASK-19).

Chay offline, khong GPU/key:
    python phase13-gui/test_synth_targeted.py

Kiem tra:
  (a) moi action dung format + toa do trong [0,1000] (CLICK/KEY/TYPE)
  (b) voi CLICK: pixel tai toa do thuoc element (khong phai nen/header/footer)
  (c) instruction nhac dung gia tri can (TYPE chua gia tri action)
  (d) deterministic: 2 lan chay cung seed -> file + row giong nhau
  (e) dem row theo family + tong
"""
import hashlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_synth_targeted import build_targeted, CW, CH

BG = (240, 240, 242)
HEADER = (52, 58, 70)
FOOTER = (228, 230, 235)


def is_bg_or_chrome(px):
    def close(a, b, tol=10):
        return all(abs(a[i]-b[i]) <= tol for i in range(3))
    return close(px, BG) or close(px, HEADER) or close(px, FOOTER)


# ---- pixel-level: chuoi co THAT SU tren man hinh? -----------------------
# Font mac dinh cua PIL CO anti-aliasing -> so bang "khac nen" (tol) thay vi
# so bang mau chu chinh xac.
_TEXT_COMBOS = [
    ((255, 248, 220), (60, 40, 20)),    # note box
    ((240, 240, 242), (30, 30, 30)),    # trang / label
    ((255, 255, 255), (30, 30, 30)),    # input trang
]


def _diff(a, b, tol=12):
    return any(abs(a[i] - b[i]) > tol for i in range(3))


def text_in_image(path, s):
    """True neu chuoi `s` THAT SU xuat hien tren anh (van tay, doc pixel)."""
    from PIL import Image, ImageDraw
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return False
    W, H = im.size
    px = im.load()
    for bg, col in _TEXT_COMBOS:
        tmp = Image.new("RGB", (700, 26), bg)
        ImageDraw.Draw(tmp).text((2, 2), s, fill=col)
        tp = tmp.load()
        pat = [(x, y) for y in range(26) for x in range(700)
               if _diff(tp[x, y], bg, 40)]
        if len(pat) < 4:
            continue
        y_first = min(p[1] for p in pat)
        x_first = min(p[0] for p in pat if p[1] == y_first)
        pat = [(x - x_first, y - y_first) for x, y in pat]
        for yy in range(H):
            for xx in range(W):
                if not _diff(px[xx, yy], bg, 12):
                    continue
                ok = True
                for dx, dy in pat:
                    qx, qy = xx + dx, yy + dy
                    if qx < 0 or qy < 0 or qx >= W or qy >= H or \
                            not _diff(px[qx, qy], bg, 12):
                        ok = False
                        break
                if ok:
                    return True
    return False


def parse_action(a):
    parts = a.split()
    if not parts:
        return None
    cmd = parts[0].upper()
    if cmd == "CLICK":
        if len(parts) != 3:
            return None
        try:
            x, y = int(parts[1]), int(parts[2])
        except ValueError:
            return None
        if not (0 <= x <= 1000 and 0 <= y <= 1000):
            return None
        return ("CLICK", x, y)
    if cmd == "TYPE":
        if len(parts) < 2:
            return None
        return ("TYPE", " ".join(parts[1:]))
    if cmd == "KEY":
        if len(parts) != 2:
            return None
        return ("KEY", parts[1])
    return None


def check_rows(rows, img_dir):
    errors = []
    n_click = 0
    n_click_ok = 0
    for i, r in enumerate(rows):
        # (a) format
        pa = parse_action(r["action"])
        if pa is None:
            errors.append("row %d bad action format: %r" % (i, r["action"]))
            continue
        # (c) instruction KHONG chua gia tri -> model phai DOC MAN HINH
        if pa[0] == "TYPE":
            val = pa[1]
            if val in r["instruction"]:
                errors.append("row %d TYPE value %r LEAKED into instruction"
                              % (i, val))
        # (b) pixel check for CLICK
        if pa[0] == "CLICK":
            n_click += 1
            x, y = pa[1], pa[2]
            px = int(round(x / 1000.0 * CW))
            py = int(round(y / 1000.0 * CH))
            try:
                from PIL import Image
                im = Image.open(r["image"]).convert("RGB")
                pix = im.getpixel((min(px, CW-1), min(py, CH-1)))
            except Exception as e:
                errors.append("row %d cannot read image: %s" % (i, e))
                continue
            if is_bg_or_chrome(pix):
                errors.append("row %d CLICK (%d,%d)->px(%d,%d) hits bg/chrome %s" %
                              (i, x, y, px, py, pix))
            else:
                n_click_ok += 1
    # (e) counts
    from collections import Counter
    fam_counts = Counter(r["family"] for r in rows)
    print("  rows total:", len(rows))
    print("  by family:", dict(sorted(fam_counts.items())))
    print("  CLICK total:", n_click, "pixel-ok:", n_click_ok)
    return errors


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    import tempfile

    def ck(name, cond, detail=""):
        if cond:
            print("  ok   %s" % name)
        else:
            print("  FAIL %s %s" % (name, detail))
            errs.append(name)

    tmp1 = tempfile.mkdtemp(prefix="synth1_")
    tmp2 = tempfile.mkdtemp(prefix="synth2_")
    seed = 12345
    n = 24

    print("[test] run 1 (seed=%d, n=%d)" % (seed, n))
    rows1 = build_targeted(n, seed, tmp1)
    errs = check_rows(rows1, tmp1)
    if errs:
        print("  ERRORS:")
        for e in errs[:20]:
            print("   ", e)
        print("  FAIL: %d errors" % len(errs))
        return 1

    # --- value discipline: model phai DOC MAN HINH ---
    typed = [r for r in rows1 if r["action"].startswith("TYPE ")]
    distinct = len(set(r["action"][5:] for r in typed))
    ck("value khong leak vao instruction",
       not any(r["action"][5:] in r["instruction"] for r in typed),
       str([r["action"][5:] for r in typed
            if r["action"][5:] in r["instruction"]][:3]))
    ck("nhieu gia tri khac nhau (khong the ghi nho)",
       distinct >= 0.8 * max(1, len(typed)),
       "%d distinct / %d rows" % (distinct, len(typed)))
    print("       distinct TYPE values: %d / %d rows" % (distinct, len(typed)))
    notdrawn = []
    for r in typed[:8]:
        val = r["action"][5:]
        if not text_in_image(r["image"], val):
            notdrawn.append(val)
    ck("gia tri THAT SU co tren man hinh", not notdrawn, str(notdrawn[:3]))

    print("[test] run 2 (determinism check)")
    rows2 = build_targeted(n, seed, tmp2)    # compare row metadata (image basename normalized)
    def norm_rows(rs):
        out = []
        for r in rs:
            out.append({
                "instruction": r["instruction"],
                "action": r["action"],
                "family": r["family"],
                "episode": r["episode"],
                "step": r["step"],
                "image_basename": os.path.basename(r["image"]),
            })
        return out
    if norm_rows(rows1) != norm_rows(rows2):
        print("  FAIL: row metadata differs between runs")
        return 1
    # compare image file content by basename
    hashes1 = {os.path.basename(r["image"]): file_hash(r["image"]) for r in rows1}
    hashes2 = {os.path.basename(r["image"]): file_hash(r["image"]) for r in rows2}
    if hashes1 != hashes2:
        print("  FAIL: image content differs between runs")
        mismatched = [k for k in hashes1 if hashes1[k] != hashes2.get(k)]
        print("   mismatched:", mismatched[:5])
        return 1
    print("  deterministic: OK (rows + image bytes identical)")

    # family coverage check
    from collections import Counter
    fams = Counter(r["family"] for r in rows1)
    expected = ["S%d" % i for i in range(1, 9)]
    missing = [f for f in expected if f not in fams]
    if missing:
        print("  WARN: families missing (n=%d too small?): %s" % (n, missing))
    else:
        print("  all 8 families present: OK")

    # --- DONE discipline (optional done_rate) ---
    def ep_map(rs):
        m = {}
        for r in rs:
            m.setdefault((r["family"], r["episode"]), []).append(r)
        for v in m.values():
            v.sort(key=lambda r: r["step"])
        return m

    def ck(name, cond, detail=""):
        if cond:
            print("  ok   %s" % name)
        else:
            print("  FAIL %s %s" % (name, detail))
            errs.append(name)

    base = ep_map(rows1)
    ck("default done_rate=0 -> no DONE row",
       not any(r["action"] == "DONE" for r in rows1))
    mid_done = [k for k, v in base.items()
                for r in v[:-1] if r["action"] == "DONE"]
    ck("no DONE in mid-chain", not mid_done, str(mid_done[:2]))

    tmp3 = tempfile.mkdtemp(prefix="synth3_")
    r100 = build_targeted(n, seed, tmp3, done_rate=1.0)
    em = ep_map(r100)
    ck("done_rate=1.0 -> every episode ends with DONE",
       all(v and v[-1]["action"] == "DONE" for v in em.values()),
       str([k for k, v in em.items() if not (v and v[-1]["action"] == "DONE")][:3]))
    ck("done_rate=1.0 -> DONE only as last row",
       all(all(r["action"] != "DONE" for r in v[:-1]) for v in em.values()))
    # the DONE image must differ from the previous step (success banner added)
    same = 0
    for k, v in em.items():
        if len(v) >= 2:
            a = open(v[-2]["image"], "rb").read()
            b = open(v[-1]["image"], "rb").read()
            if a == b:
                same += 1
    ck("DONE image shows a completed state (differs from last step)",
       same == 0, "%d identical" % same)
    # determinism of the new path
    tmp4 = tempfile.mkdtemp(prefix="synth4_")
    r100b = build_targeted(n, seed, tmp4, done_rate=1.0)
    ck("done_rate path deterministic",
       [(x["action"], x["instruction"], os.path.basename(x["image"]))
        for x in r100] ==
       [(x["action"], x["instruction"], os.path.basename(x["image"]))
        for x in r100b])

    if errs:
        print("[test] FAIL: %d check(s): %s" % (len(errs), errs))
        return 1
    print("[test] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
