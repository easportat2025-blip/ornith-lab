"""make_s11_dataset_staging.py - dong goi data S11/S12/S13 thanh DATASET KAGGLE
(GLM, 22/10) de kernel SFT nap duoc (giong cach R2/synth-recipe).

Input : phase13-gui/synth_s11/  (traj.jsonl + images/) - sinh boi
        scripts/glm_s11_gen.py (CPU, 0 GPU)
Output: phase13-gui/s11_ds_staging/khoadangnguye__ornith-gui-synth-s11/
        + ban acc B: phase13-gui/acc_b_staging/dieniw__ornith-gui-synth-s11

Trong kernel SFT nap bang 1 dong:
    s11_rows = load_ds_rows("ornith-gui-synth-s11", "traj.jsonl", required=True)

Dung:
  python phase13-gui/make_s11_dataset_staging.py
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "synth_s11")
DST = os.path.join(HERE, "s11_ds_staging",
                   "khoadangnguye__ornith-gui-synth-s11")
DST_B = os.path.join(HERE, "acc_b_staging",
                     "dieniw__ornith-gui-synth-s11")


def build(dst, slug, title):
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(os.path.join(dst, "images"), exist_ok=True)
    rows = []
    for line in io.open(os.path.join(SRC, "traj.jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        # dam bao duong dan tuong doi (images/<file>) - _resolve() se giai
        r["image"] = "images/" + os.path.basename(r["image"])
        rows.append(r)
    with io.open(os.path.join(dst, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_img = 0
    for f in os.listdir(os.path.join(SRC, "images")):
        if f.lower().endswith(".png"):
            shutil.copy2(os.path.join(SRC, "images", f),
                         os.path.join(dst, "images", f))
            n_img += 1
    with io.open(os.path.join(dst, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"title": title, "id": slug,
                             "licenses": [{"name": "other"}]}, indent=1))
    sz = sum(os.path.getsize(os.path.join(dst, "images", f))
             for f in os.listdir(os.path.join(dst, "images")))
    print("  %-58s %-40s %4d row %4d anh %5.1f MB" %
          (os.path.basename(dst), slug, len(rows), n_img, sz / 1e6))


def main():
    if not os.path.isfile(os.path.join(SRC, "traj.jsonl")):
        print("!! chua co %s (chay glm_s11_gen.py truoc)" % SRC)
        return 1
    build(DST, "khoadangnguye/ornith-gui-synth-s11",
          "Ornith GUI synth S11/S12/S13 (scroll/move/drag + error-recovery + keyboard-nav)")
    build(DST_B, "dieniw/ornith-gui-synth-s11",
          "Ornith GUI synth S11/S12/S13 (copy acc B)")
    print()
    print("upload (acc A): python scripts/upload_staging.py phase13-gui/s11_ds_staging/khoadangnguye__ornith-gui-synth-s11")
    print("upload (acc B): python scripts/upload_staging.py phase13-gui/acc_b_staging/dieniw__ornith-gui-synth-s11 --acc B")
    print("nap trong kernel SFT: s11_rows = load_ds_rows(\"ornith-gui-synth-s11\", \"traj.jsonl\", required=True)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
