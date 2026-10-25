"""test_viewport_fix.py - kiem tra fix OFFSET 86px cua harness.py (GLM, 21/10).

Voi viewport that (0, 86, 1280, 634) tren man hinh X11 1280x720:
  1) crop_to_viewport: anh chup man hinh -> cat ve 1280x634 (bo thanh cong cu)
  2) to_screen_action: toa do model (theo viewport) -> toa do man hinh
     => click tren CSS phai tro dung vi tri tren man hinh.
Chay offline: python phase14-desktop/test_viewport_fix.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ENV_WORK", os.path.join(HERE, "_test_env"))

spec = importlib.util.spec_from_file_location("harness_t",
                                              os.path.join(HERE, "harness.py"))
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

fails = 0


def ok(cond, msg):
    global fails
    if cond:
        print("  ok   " + msg)
    else:
        print("  FAIL " + msg)
        fails += 1


print("== 1) crop_to_viewport (bo thanh cong cu 86px) ==")
from PIL import Image
W, Hh = 1280, 720
img = Image.new("RGB", (W, Hh), (10, 10, 10))
# vung viewport: 86..720 ; vung thanh cong cu: 0..86
for y in range(86, 720):
    for x in range(0, 1280, 64):
        img.putpixel((x, y), (0, 200, 0))
for y in range(0, 86):
    for x in range(0, 1280, 64):
        img.putpixel((x, y), (200, 0, 0))
src = os.path.join(HERE, "_t_full.png")
dst = os.path.join(HERE, "_t_crop.png")
img.save(src)
H._VP = (0, 86, 1280, 634)
ok(H.crop_to_viewport(src, dst), "crop chay khong loi")
im = Image.open(dst)
ok(im.size == (1280, 634), "anh cat kich thuoc %s (mong doi 1280x634)" % (im.size,))
px = im.getpixel((64, 5))
ok(px[1] > px[0], "vung dau anh la XANH (viewport), khong phai DO (thanh cong cu)")
px_full = Image.open(src).getpixel((64, 40))
ok(px_full[0] > px_full[1], "anh goc o 40px la DO (thanh cong cu) -> bi cat")
H._VP = None
H.crop_to_viewport(src, dst)
ok(Image.open(dst).size == (1280, 720),
   "khong co viewport -> giu nguyen anh man hinh")
for p in (src, dst):
    try:
        os.remove(p)
    except Exception:
        pass

print("== 2) to_screen_action (dich toa do viewport -> man hinh) ==")
H._VP = (0, 86, 1280, 634)
cases = [
    ("CLICK 500 500", "CLICK 500 560"),
    ("CLICK 0 0", "CLICK 0 119"),
    ("CLICK 1000 1000", "CLICK 1000 1000"),
    ("MOVE 250 750", "MOVE 250 780"),
    ("DRAG 100 200 300 400", "DRAG 100 296 300 472"),
    ("TYPE hello", "TYPE hello"),
    ("KEY ctrl+a", "KEY ctrl+a"),
    ("SCROLL 3", "SCROLL 3"),
]
for a, want in cases:
    got = H.to_screen_action(a)
    ok(got == want, "to_screen_action(%r) = %r (mong doi %r)" % (a, got, want))

print("== 3) khong co viewport -> khong doi ==")
H._VP = None
ok(H.to_screen_action("CLICK 500 500") == "CLICK 500 500",
   "khong co viewport -> action giu nguyen")
H._VP = (0, 86, 1280, 634)
print("== 4) regex khong khop -> giu nguyen ==")
ok(H.to_screen_action("CLICK 500") == "CLICK 500", "action khong hop regex giu nguyen")

print("\n%s" % ("ALL VIEWPORT TESTS PASSED" if fails == 0
                else ("%d CHECK(S) FAILED" % fails)))
sys.exit(0 if fails == 0 else 1)
