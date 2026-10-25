# -*- coding: utf-8 -*-
"""
test_synth_long.py - self-test offline cho gen_synth_long (khong GPU/key).

    python phase13-gui/test_synth_long.py

Kiem tra:
  (a) action dung format + toa do trong [0,1000]
  (b) voi CLICK: pixel tai toa do thuoc element (khong nen/header/footer)
  (c) instruction khop gia tri can (TYPE chua gia tri action)
  (d) deterministic: 2 lan chay cung seed -> file + row giong het
  (e) dem row theo family + tong + do dai chuoi
  (f) KY Luat DONE: DONE chi o cuoi episode, khong o giua chuoi
  (g) >= 40% episode >= 8 buoc (muc tieu: buoc qua gioi han cua gen_synth_targeted)
"""
import hashlib
import os
import sys
import tempfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_synth_long import build_long, CW, CH, BG, HEADER, FOOTER, DEFAULT_DONE_RATE

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        FAILS.append(name)


def is_bg_or_chrome(px):
    def close(a, b, tol=10):
        return all(abs(a[i] - b[i]) <= tol for i in range(3))
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
    if cmd == "DONE":
        return ("DONE",)
    return None


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def episode_map(rows):
    ep = {}
    for r in rows:
        ep.setdefault((r["family"], r["episode"]), []).append(r)
    for v in ep.values():
        v.sort(key=lambda r: r["step"])
    return ep


def main():
    tmp1 = tempfile.mkdtemp(prefix="long1_")
    tmp2 = tempfile.mkdtemp(prefix="long2_")
    seed, n = 4242, 24

    print("[test] run 1 (seed=%d, n=%d)" % (seed, n))
    rows = build_long(n, seed, tmp1)
    check("rows generated", len(rows) > 0, str(len(rows)))

    # (a) format + coords
    bad_fmt = 0
    for r in rows:
        if parse_action(r["action"]) is None:
            bad_fmt += 1
    check("(a) all actions valid format", bad_fmt == 0, "%d bad" % bad_fmt)

    # (c) instruction KHONG chua gia tri -> model phai DOC MAN HINH
    bad_val = 0
    for r in rows:
        pa = parse_action(r["action"])
        if pa and pa[0] == "TYPE" and pa[1] in r["instruction"]:
            bad_val += 1
    check("(c) instruction does NOT leak the value (model must read)",
          bad_val == 0, "%d leak" % bad_val)
    # (c2) nhieu gia tri khac nhau (khong the ghi nho)
    typed = [r for r in rows if r["action"].startswith("TYPE ")]
    distinct = len(set(r["action"][5:] for r in typed))
    check("(c2) many distinct values (no memorization)",
          distinct >= 0.8 * max(1, len(typed)),
          "%d distinct / %d rows" % (distinct, len(typed)))
    print("       distinct TYPE values: %d / %d rows" % (distinct, len(typed)))
    # (c3) gia tri THAT SU co tren man hinh (van tay - doc pixel)
    notdrawn = []
    for r in typed[:8]:
        val = r["action"][5:]
        if not text_in_image(r["image"], val):
            notdrawn.append(val)
    check("(c3) the value really is drawn on the screen",
          not notdrawn, str(notdrawn[:3]))

    # (b) pixel verification for CLICK
    from PIL import Image
    n_click, n_ok = 0, 0
    bad_px = []
    for i, r in enumerate(rows):
        pa = parse_action(r["action"])
        if not pa or pa[0] != "CLICK":
            continue
        n_click += 1
        px = int(round(pa[1] / 1000.0 * CW))
        py = int(round(pa[2] / 1000.0 * CH))
        im = Image.open(r["image"]).convert("RGB")
        pix = im.getpixel((min(px, CW - 1), min(py, CH - 1)))
        if is_bg_or_chrome(pix):
            bad_px.append((i, pa[1], pa[2], pix))
        else:
            n_ok += 1
    check("(b) every CLICK hits a real element", not bad_px,
          "%d bad: %s" % (len(bad_px), bad_px[:3]))
    print("       CLICK total: %d  pixel-ok: %d" % (n_click, n_ok))

    # (e) counts + chain length
    fam = Counter(r["family"] for r in rows)
    ep = episode_map(rows)
    lens = [len(v) for v in ep.values()]
    print("       rows by family:", dict(sorted(fam.items())))
    print("       episodes: %d  steps/ep min=%d max=%d avg=%.1f"
          % (len(lens), min(lens), max(lens), sum(lens) / len(lens)))
    check("(e) all 4 families present", len(fam) == 4, str(dict(fam)))
    check("(e) episodes >= 8 steps",
          sum(1 for n in lens if n >= 8) >= 0.4 * len(lens),
          "%d/%d" % (sum(1 for n in lens if n >= 8), len(lens)))

    # (e2) chain structure: each family has a fixed action pattern
    EXPECT = {
        "L1": ["CLICK", "TYPE", "CLICK", "TYPE", "CLICK", "TYPE",
               "CLICK", "CLICK", "DONE"],
        "L2": ["CLICK", "CLICK", "TYPE", "CLICK", "CLICK", "TYPE",
               "CLICK", "CLICK", "DONE"],
        "L3": ["CLICK", "CLICK", "CLICK", "CLICK", "CLICK", "CLICK",
               "KEY", "KEY", "CLICK", "KEY", "CLICK", "DONE"],
        "L4": ["CLICK", "CLICK", "TYPE", "CLICK", "TYPE", "CLICK",
               "TYPE", "CLICK", "DONE"],
    }
    bad_pattern = []
    for (f, _e), v in ep.items():
        kinds = [parse_action(r["action"])[0] for r in v
                 if parse_action(r["action"])]
        exp = EXPECT[f]
        if kinds != exp[:len(kinds)]:
            bad_pattern.append((f, kinds))
    check("(e2) every family follows its expected action chain",
          not bad_pattern, str(bad_pattern[:2]))

    # (f) DONE discipline: DONE only as the LAST row of its episode
    bad_done = []
    for key, v in ep.items():
        for j, r in enumerate(v):
            if r["action"] == "DONE" and j != len(v) - 1:
                bad_done.append((key, j, len(v)))
    check("(f) DONE only at the end of an episode", not bad_done, str(bad_done[:3]))
    n_done_eps = sum(1 for v in ep.values()
                      if v and v[-1]["action"] == "DONE")
    print("       episodes ending with DONE: %d/%d (done_rate=%.2f)"
          % (n_done_eps, len(ep), n_done_eps / max(1, len(ep))))
    check("(f) DONE present in some episodes", n_done_eps > 0, str(n_done_eps))
    # no DONE in the middle of a chain -> the model must not learn early DONE
    mid_done = sum(1 for v in ep.values()
                   for r in v[:-1] if r["action"] == "DONE")
    check("(f) no DONE in mid-chain", mid_done == 0, str(mid_done))

    # (d) determinism
    print("[test] run 2 (determinism)")
    rows2 = build_long(n, seed, tmp2)

    def norm_rows(rs):
        return [{"instruction": r["instruction"], "action": r["action"],
                 "family": r["family"], "episode": r["episode"],
                 "step": r["step"],
                 "basename": os.path.basename(r["image"])} for r in rs]
    check("(d) row metadata identical", norm_rows(rows) == norm_rows(rows2))
    h1 = {os.path.basename(r["image"]): file_hash(r["image"]) for r in rows}
    h2 = {os.path.basename(r["image"]): file_hash(r["image"]) for r in rows2}
    check("(d) image bytes identical", h1 == h2)

    # different seed -> different content
    rows3 = build_long(n, seed + 1, tempfile.mkdtemp(prefix="long3_"))
    check("(d) different seed -> different rows",
          norm_rows(rows) != norm_rows(rows3))

    # (g) done_rate parameter works
    r0 = build_long(8, 7, tempfile.mkdtemp(prefix="long0_"), done_rate=0.0)
    r1 = build_long(8, 7, tempfile.mkdtemp(prefix="long1b_"), done_rate=1.0)
    d0 = sum(1 for r in r0 if r["action"] == "DONE")
    d1 = sum(1 for r in r1 if r["action"] == "DONE")
    check("done_rate=0.0 -> no DONE row", d0 == 0, str(d0))
    check("done_rate=1.0 -> every episode ends with DONE", d1 > 0, str(d1))

    print("\n" + "=" * 50)
    if FAILS:
        print("FAILED: %d check(s): %s" % (len(FAILS), FAILS))
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
