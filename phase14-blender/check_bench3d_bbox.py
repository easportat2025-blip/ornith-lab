"""check_bench3d_bbox.py - kiem tra dataset bench 3D: center phai nam trong bbox
(task vo doi duoc), bbox khong phai toan anh, va phan bo kich thuoc."""
import io
import json
import os

P = 'phase14-blender/bench3d_dataset/bench3d.jsonl'
rows = [json.loads(l) for l in io.open(P, encoding='utf-8') if l.strip()]
print('rows:', len(rows))
bad_center, bad_size, areas = 0, 0, []
for r in rows:
    b = r['bbox']
    c = r.get('center') or [None, None]
    if c[0] is not None:
        if not (b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3]):
            bad_center += 1
    w = b[2] - b[0]
    h = b[3] - b[1]
    areas.append(w * h / 1000.0 / 1000.0)
    if w < 12 or h < 12 or w > 700 or h > 700:
        bad_size += 1
        print('  bbox la:', r['instruction'], b)
areas.sort()
print('center ngoai bbox:', bad_center, '| bbox khong hop le:', bad_size)
print('dien tich bbox (pct): min %.2f p25 %.2f median %.2f p75 %.2f max %.2f' % (
    areas[0] * 100, areas[len(areas) // 4] * 100, areas[len(areas) // 2] * 100,
    areas[3 * len(areas) // 4] * 100, areas[-1] * 100))
from collections import Counter
print('mau:', Counter(r.get('color') for r in rows))
print('shape:', Counter(r.get('shape') for r in rows))
assert bad_center == 0, "co episode center ngoai bbox -> task vo doi duoc"
print("BENCH3D DATA OK")
