"""traj_done_aug.py - R2: bo sung row DONE cho episode tra CHUA ket thuc bang DONE.

YEU CAU (bai toan R2 do @GPT de xuat 21/10, chua ai lam):
  "P(DONE) cua nguon gui-traj = 7,4% (60/816); 156/216 ep khong co DONE
   => de model hoc duoc, can data co bien ... de xuat R2: sinh file moi
   traj_done_aug.jsonl them 156 row DONE (dung lai anh buoc cuoi)"

LAM:
  1) doc traj.jsonl (816 row) + gom episode theo TEN FILE (`..._s<N>.png`);
  2) ep nao cuoi KHONG phai DONE => them 1 row DONE:
       {image: <anh buoc cuoi>, instruction: <instruction cuoi> + " When you are done, say DONE.",
        action: "DONE"}
     (giong DUNG format cua 60 row DONE hien co);
  3) ghi file augmented + STAGING dataset (jsonl + images/ + dataset-metadata.json)
     => `kaggle datasets version -p <staging>` xong la kernel van dung SLUG CU
     (khong doi kernel-metadata.json) va lay duoc 156 row DONE moi.
  4) verify: moi episode ket thuc bang DONE; moi row DONE tro toi anh co that.

Dung:
  python phase13-gui/traj_done_aug.py              # sinh file + staging + verify
  python phase13-gui/traj_done_aug.py --verify-only # chi verify
"""
import argparse
import io
import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_SRC = os.path.join(HERE, "out_traj")
DEFAULT_OUT = os.path.join(HERE, "traj_done_aug.jsonl")
DEFAULT_STAGE = os.path.join(HERE, "traj_ds_staging",
                             "khoadangnguye__ornith-gui-traj")
SLUG = "khoadangnguye/ornith-gui-traj"
DONE_SUFFIX = " When you are done, say DONE."
STEP_RE = re.compile(r"^(.*)_s(\d+)\.png$")


def log(m):
    print("[r2] %s" % m, flush=True)


def read_jsonl(p):
    rows = []
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def is_done(r):
    return (r.get("action") or "").strip().upper().startswith("DONE")


def group(rows):
    eps = {}
    for r in rows:
        m = STEP_RE.match(r.get("image") or "")
        key = m.group(1) if m else (r.get("image") or "")
        eps.setdefault(key, []).append(r)
    for k in eps:
        eps[k].sort(key=lambda r: int(STEP_RE.match(r["image"]).group(2))
                    if STEP_RE.match(r.get("image") or "") else 0)
    return eps


def build(src_dir, out_jsonl, stage_dir):
    src_jsonl = os.path.join(src_dir, "traj.jsonl")
    rows = read_jsonl(src_jsonl)
    eps = group(rows)
    added = []
    for key, rs in eps.items():
        last = rs[-1]
        if is_done(last):
            continue
        ins = (last.get("instruction") or "").strip()
        if not ins.endswith("DONE_SUFFIX".strip()):
            ins = ins + DONE_SUFFIX
        added.append({"image": last.get("image"), "instruction": ins,
                      "action": "DONE"})
    aug = rows + added
    with io.open(out_jsonl, "w", encoding="utf-8", newline="\n") as fh:
        for r in aug:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log("ghi %s: %d row (%d goc + %d DONE moi)" %
        (out_jsonl, len(aug), len(rows), len(added)))
    # ---- staging dataset (jsonl + images + metadata) ----
    if stage_dir:
        if os.path.isdir(stage_dir):
            shutil.rmtree(stage_dir)
        os.makedirs(stage_dir, exist_ok=True)
        shutil.copy2(out_jsonl, os.path.join(stage_dir, "traj.jsonl"))
        src_imgs = os.path.join(src_dir, "images")
        if os.path.isdir(src_imgs):
            dst_imgs = os.path.join(stage_dir, "images")
            shutil.copytree(src_imgs, dst_imgs)
            log("staging: copy %d anh" % len(os.listdir(dst_imgs)))
        meta = {"title": "Ornith GUI traj (R2: +%d DONE rows)" % len(added),
                "id": SLUG, "licenses": [{"name": "other"}]}
        with io.open(os.path.join(stage_dir, "dataset-metadata.json"), "w",
                     encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=1)
        log("staging: %s" % stage_dir)
    return aug, added


def verify(jsonl, src_dir):
    rows = read_jsonl(jsonl)
    eps = group(rows)
    bad_end, missing_img, no_done = [], [], 0
    for key, rs in eps.items():
        if not is_done(rs[-1]):
            bad_end.append(key)
    n_done = sum(1 for r in rows if is_done(r))
    imgs = os.path.join(src_dir, "images")
    for r in rows:
        rel = r.get("image") or ""
        base = os.path.basename(rel)
        if base and not os.path.exists(os.path.join(imgs, base)):
            missing_img.append(base)
    print("| chi so | gia tri |")
    print("|---|---|")
    print("| rows | %d |" % len(rows))
    print("| episodes | %d |" % len(eps))
    print("| row DONE | %d (%.1f%%) |" % (n_done, 100.0 * n_done / max(len(rows), 1)))
    print("| episode KHONG ket thuc bang DONE | %d |" % len(bad_end))
    print("| anh thieu | %d |" % len(missing_img))
    ok = (not bad_end) and (not missing_img)
    print("| KET QUA | %s |" % ("PASS" if ok else "FAIL"))
    if bad_end:
        log("ep chua co DONE: %s" % bad_end[:5])
    if missing_img:
        log("anh thieu: %s" % missing_img[:5])
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--stage", default=DEFAULT_STAGE)
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()
    if a.verify_only:
        return 0 if verify(a.out, a.src) else 1
    aug, added = build(a.src, a.out, a.stage)
    ok = verify(a.out, a.src)
    if a.stage and ok:
        log("=> len chay: kaggle datasets version -p \"%s\" -m \"R2: +%d DONE rows\""
            % (a.stage, len(added)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
