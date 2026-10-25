# -*- coding: utf-8 -*-
"""make_synth_recipe_dataset.py - dong goi data synth (recipe/recovery) thanh
1 DATASET Kaggle giong het dataset traj (GLM, 22/10).

Input : phase13-gui/synth_recipe/  (rows.jsonl + images/*.png) - sinh boi
        gen_recipe_recovery.py (0 GPU, local).
Output: phase13-gui/synth_recipe_ds_staging/khoadangnguye__ornith-gui-synth-recipe/
        - traj.jsonl   : row {image: "images/<file>", instruction, action,
                              point, bbox, label, family, episode, step}
                          (duong dan TUONG DOI - gui_sft._resolve() giai theo
                          dataset dir, giong dataset traj)
        - images/      : 400 anh 1280x720
        - dataset-metadata.json : id = khoadangnguye/ornith-gui-synth-recipe

Sau khi upload, kernel SFT nap bang 1 dong:
    sr_rows = load_ds_rows("ornith-gui-synth-recipe", "traj.jsonl", required=True)

Dung:
  python phase13-gui/make_synth_recipe_dataset.py
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "synth_recipe")
DST = os.path.join(ROOT, "phase13-gui", "synth_recipe_ds_staging",
                   "khoadangnguye__ornith-gui-synth-recipe")
SLUG = "khoadangnguye/ornith-gui-synth-recipe"


def log(m):
    print("[pkg] %s" % m, flush=True)


def main():
    rows_p = os.path.join(SRC, "rows.jsonl")
    img_src = os.path.join(SRC, "images")
    if not os.path.isfile(rows_p):
        log("khong thay %s (chay gen_recipe_recovery.py truoc)" % rows_p)
        return 1
    shutil.rmtree(DST, ignore_errors=True)
    os.makedirs(os.path.join(DST, "images"), exist_ok=True)

    rows = []
    for line in io.open(rows_p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        name = os.path.basename(r["image"])
        r["image"] = "images/" + name
        rows.append(r)
    with io.open(os.path.join(DST, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    for f in os.listdir(img_src):
        if f.lower().endswith(".png"):
            shutil.copy2(os.path.join(img_src, f),
                         os.path.join(DST, "images", f))
    io.open(os.path.join(DST, "dataset-metadata.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps({
                "title": "Ornith GUI synth recipe/recovery (desktop-env apps)",
                "id": SLUG, "licenses": [{"name": "other"}]}, indent=1))
    n_img = len(os.listdir(os.path.join(DST, "images")))
    sz = sum(os.path.getsize(os.path.join(DST, "images", f))
             for f in os.listdir(os.path.join(DST, "images")))
    log("DST: %s" % DST)
    log("rows: %d | images: %d (%.1f MB) | traj.jsonl: %.1f KB" %
        (len(rows), n_img, sz / 1e6,
         os.path.getsize(os.path.join(DST, "traj.jsonl")) / 1024))
    log("upload: python scripts/upload_staging.py "
        "phase13-gui/synth_recipe_ds_staging/khoadangnguye__ornith-gui-synth-recipe")
    log("nap trong kernel SFT: sr_rows = load_ds_rows(\"ornith-gui-synth-recipe\", "
        "\"traj.jsonl\", required=True)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
