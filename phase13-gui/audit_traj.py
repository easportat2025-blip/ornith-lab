# -*- coding: utf-8 -*-
# Audit chat luong data traj.jsonl (CPU-only, khong key, khong GPU)
# Chay: python phase13-gui/audit_traj.py
import json, os, collections, hashlib, sys

BASE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(BASE, "out_traj", "traj.jsonl")
IMG_DIR = os.path.join(BASE, "out_traj", "images")

rows = []
bad_json = []
with open(F, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            bad_json.append((i, str(e)[:80]))

print("rows parse OK:", len(rows), "| bad json:", len(bad_json))
for i, e in bad_json[:5]:
    print("  bad line", i, e)

REQ = ["image", "instruction", "action", "point", "bbox", "label"]
missing_field = collections.Counter()
for r in rows:
    for k in REQ:
        if k not in r:
            missing_field[k] += 1
print("thieu truong:", dict(missing_field) or "none")

def kind(r):
    return r["action"].split()[0]

# 1) kieu action + phan bo
print("action kinds:", dict(collections.Counter(kind(r) for r in rows)))

# 2) toa do hop le + point trong bbox + action khop point
oob, pt_not_in_bbox, act_mismatch, bad_bbox = [], [], [], []
for i, r in enumerate(rows):
    p, bb = r.get("point"), r.get("bbox")
    okp = (isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p))
    okb = (isinstance(bb, list) and len(bb) == 4 and all(isinstance(v, (int, float)) for v in bb))
    if not okp or not okb:
        bad_bbox.append(i)
        continue
    x, y = p
    x0, y0, x1, y1 = bb
    if not (0 <= x <= 1280 and 0 <= y <= 720):
        oob.append(i)
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        pt_not_in_bbox.append(i)
    parts = r["action"].split()
    if parts[0] == "CLICK" and len(parts) == 3:
        if int(parts[1]) != int(x) or int(parts[2]) != int(y):
            act_mismatch.append(i)
print("bbox/point sai dinh dang:", len(bad_bbox))
print("toa do ngoai man hinh 1280x720:", len(oob))
print("point KHONG nam trong bbox:", len(pt_not_in_bbox), pt_not_in_bbox[:10])
print("CLICK action khop point:", len(act_mismatch), "lech (index):", act_mismatch[:10])

# 3) TYPE: co phan biet chuoi/so khac nhau khong (chong ghi nho) + rori ria gia tri vao instruction
type_rows = [r for r in rows if kind(r) == "TYPE"]
type_payload = []
for r in type_rows:
    parts = r["action"].split(maxsplit=1)
    type_payload.append(parts[1] if len(parts) > 1 else "")
tc = collections.Counter(type_payload)
print("TYPE rows:", len(type_rows), "| gia tri phan biet:", len(tc),
      "| top:", tc.most_common(5))

# gia tri so trong instruction
import re
num_in_instr = [r for r in rows if re.search(r"\d", r["instruction"])]
print("instruction chua chu so:", len(num_in_instr), "/", len(rows))
for r in num_in_instr[:5]:
    print("   vd:", r["instruction"][:100])

# 4) trung lap
dup_key = collections.Counter((r["image"], r["action"]) for r in rows)
dups = [(k, v) for k, v in dup_key.items() if v > 1]
print("cap (image, action) trung:", len(dups), "| so row thua:", sum(v - 1 for _, v in dups), "| index vd:", dups[:5])
instr_c = collections.Counter(r["instruction"] for r in rows)
print("instruction trung lap (xuat hien >1):", sum(1 for v in instr_c.values() if v > 1),
      "| doc nhat:", len(instr_c))
print("instruction top:", instr_c.most_common(5))

# 5) anh ton tai + trung noi dung
img_names = [r["image"] for r in rows]
missing_img = sorted({n for n in img_names if not os.path.isfile(os.path.join(IMG_DIR, os.path.basename(n)))})
print("anh thieu tren dia:", len(missing_img), missing_img[:5])
files_on_disk = set(os.listdir(IMG_DIR)) if os.path.isdir(IMG_DIR) else set()
print("so file anh tren dia:", len(files_on_disk), "| anh dung trong jsonl:", len(set(img_names)),
      "| anh tren dia khong dung:", len(files_on_disk - {os.path.basename(n) for n in img_names}))
hashes = collections.Counter()
for n in sorted(set(img_names)):
    p = os.path.join(IMG_DIR, os.path.basename(n))
    if os.path.isfile(p):
        hashes[hashlib.md5(open(p, "rb").read()).hexdigest()] += 1
print("anh trung noi dung (md5 giong nhau):", sum(v - 1 for v in hashes.values() if v > 1))

# 6) DONE rows + co chuoi buoc (instruction cung anh, nhieu action) khong
done_rows = [r for r in rows if kind(r) == "DONE"]
img_c = collections.Counter(os.path.basename(r["image"]) for r in rows)
multi = {k: v for k, v in img_c.items() if v > 1}
print("DONE rows:", len(done_rows))
print("anh co >1 row (nham chuoi nhieu buoc):", len(multi), "| max buc tren 1 anh:", max(multi.values()) if multi else 1)
# kiem tra moi anh nhieu buoc co DONE khong
img_done = {os.path.basename(r["image"]) for r in done_rows}
imgs_multi_no_done = [k for k in multi if k not in img_done]
print("anh nhieu buoc NHUNG khong co DONE:", len(imgs_multi_no_done), imgs_multi_no_done[:5])

# 7) label rong
empty_label = sum(1 for r in rows if not str(r.get("label", "")).strip())
print("label rong:", empty_label)

# 8) chuoi action co thu tu tren cung anh (kiem tra point rieng biet, khong trung toa do)
same_pt = 0
by_img = collections.defaultdict(list)
for r in rows:
    by_img[os.path.basename(r["image"])].append(r)
for k, rs in by_img.items():
    if len(rs) > 1:
        pts = [tuple(r["point"]) for r in rs if kind(r) != "DONE"]
        if len(pts) != len(set(pts)):
            same_pt += 1
print("anh nhieu buoc ma trung toa do diem click:", same_pt)

# 9) ep trinh (chuoi buoc): anh cung template tru _s<so> = 1 ep
import re as _re
ep_of = lambda n: _re.sub(r"_s\d+(?=\.[a-zA-Z]+$)", "", os.path.basename(n))
eps = collections.defaultdict(list)
for r in rows:
    eps[ep_of(r["image"])].append(r)
print("so episode:", len(eps))
steps = sorted(len(v) for v in eps.values())
print("buoc/ep: min", steps[0], "max", steps[-1], "trung binh", round(sum(steps)/len(steps), 2))
no_done_ep = [k for k, v in eps.items() if not any(kind(r) == "DONE" for r in v)]
done_not_last = [k for k, v in eps.items()
                 if any(kind(r) == "DONE" for r in v) and kind(v[-1]) != "DONE"]
print("ep KHONG co DONE:", len(no_done_ep), no_done_ep[:5])
print("ep co DONE NHUNG khong phai buoc cuoi:", len(done_not_last), done_not_last[:5])

# 10) gia tri phan biet trong TYPE + KEY (chong ghi nho)
key_payload = [r["action"].split(maxsplit=1)[1] for r in rows if kind(r) == "KEY" and len(r["action"].split()) > 1]
print("KEY gia tri phan biet:", collections.Counter(key_payload).most_common())
print("TYPE gia tri phan biet:", len(set(type_payload)), "| top:", collections.Counter(type_payload).most_common(5))

# 11) gia tri username/password co phan biet khong (trong instruction)
pairs = set()
for r in rows:
    m = _re.search(r"username (\S+) and password (\S+?)[.,]", r["instruction"])
    if m:
        pairs.add(m.groups())
print("cap (user, pass) phan biet trong instruction:", len(pairs), list(pairs)[:5])
tgt = collections.Counter(m.group(1) for r in rows
                          for m in [_re.search(r"(?:counter to|counter show(?:s)?) (\d+)", r["instruction"])] if m)
print("gia tri counter target phan biet:", len(tgt), tgt.most_common())
