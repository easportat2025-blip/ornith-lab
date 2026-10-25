# -*- coding: utf-8 -*-
"""ds_files_all.py - liet ke TOAN BO file cua 1 dataset Kaggle (phan trang).

Ly do: `kaggle datasets files` mac dinh chi tra 20 file -> verify tuong
"dataset chi co 20 file" trong khi that ra co 531.

Dung:
    python scripts/ds_files_all.py khoadangnguye/ornith-gui-synth-s11
    python scripts/ds_files_all.py khoadangnguye/ornith-gui-synth-s11 --images
ASCII-only source. Khong ghi key ra file.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
FLAGS = 0x08000000 if os.name == "nt" else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--images", action="store_true",
                    help="chi dem file trong images/")
    args = ap.parse_args()

    from upload_staging import env_for  # noqa: E402

    owner, slug = args.dataset.split("/", 1)
    env, has_key = env_for(owner)
    if not has_key:
        print("FAIL: khong co key cho owner %s" % owner)
        return 2

    files = []
    token = ""
    for _ in range(20):
        cmd = ["kaggle", "datasets", "files", args.dataset,
               "--page-size", "200", "--format", "json"]
        if token:
            cmd += ["--page-token", token]
        p = subprocess.run(cmd, capture_output=True, env=env,
                           timeout=180, creationflags=FLAGS)
        out = (p.stdout or b"").decode("utf-8", "replace").strip()
        err = (p.stderr or b"").decode("utf-8", "replace").strip()
        if p.returncode != 0:
            print("FAIL rc=%d: %s" % (p.returncode, (err or out)[:400]))
            return 1
        # CLI in: warning line + "Next Page Token = ..." + JSON array.
        i, j = out.find("["), out.rfind("]")
        if i < 0 or j < i:
            print("FAIL: output khong co JSON array: %s" % out[:300])
            return 1
        try:
            batch = json.loads(out[i:j + 1])
        except Exception as e:
            print("FAIL: JSON loi (%s): %s" % (e, out[i:i + 300]))
            return 1
        token = ""
        for line in out.splitlines():
            if line.startswith("Next Page Token ="):
                token = line.split("=", 1)[1].strip()
        if not batch:
            break
        files.extend(batch)
        if not token:
            break

    names = [f.get("name") or f.get("fileName") or "" for f in files]
    n_img = sum(1 for n in names if n.startswith("images/"))
    print("dataset : %s" % args.dataset)
    print("n_file  : %d" % len(names))
    print("n_images: %d" % n_img)
    print("co traj : %s" % ("YES" if "traj.jsonl" in names else "NO"))
    sizes = sum(int(f.get("totalBytes") or f.get("size") or 0) for f in files)
    print("tong    : %.1f MB" % (sizes / 1048576.0))
    if args.images:
        for n in sorted(names):
            if n.startswith("images/"):
                print(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
