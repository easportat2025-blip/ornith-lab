# -*- coding: utf-8 -*-
"""
host_colab_result.py - KIEM TRA + host 1 file .zip ket qua Colab len HF public
(quy tac: ket qua -> zip 1 file -> host -> bao bus).

Kiem tra (fail-loud, truoc khi host):
  1) zip mo duoc, co traj.jsonl
  2) moi row: co image + instruction + action hop le
  3) moi row: file anh ton tai TRONG zip
  4) anh khong rong (>=1KB), la PNG that
  5) thong ke: so row / so episode / so task / phan bo verb
=> neu loi -> khong host, bao loi (khong doan).

Dung:
    python scripts/host_colab_result.py phase13-gui/colab_out/desktop_replay.zip \
        --repo kkouadn/ornith-colab-data
ASCII-only source.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACT_RX = re.compile(r"^(CLICK|TYPE|KEY|MOVE|DRAG|SCROLL|DONE)\b", re.I)


def check_zip(path):
    print("== %s (%.1f MB)" % (path, os.path.getsize(path) / 1048576.0))
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if "traj.jsonl" not in names:
        print("FAIL: zip khong co traj.jsonl (co: %s)" % names[:6])
        return None
    rows = []
    with z.open("traj.jsonl") as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    pngs = set(n for n in names if n.lower().endswith(".png"))
    n_bad_img = n_bad_act = n_empty = 0
    verbs = Counter()
    tasks = Counter()
    eps = set()
    for r in rows:
        img = r.get("image") or ""
        base = img.split("/")[-1]
        if base not in pngs:
            n_bad_img += 1
        if not (r.get("instruction") or "").strip():
            n_empty += 1
        a = (r.get("action") or "").strip()
        m = ACT_RX.match(a)
        if not m:
            n_bad_act += 1
        else:
            verbs[m.group(1).upper()] += 1
        tasks[r.get("task_id")] += 1
        # episode = (task_id, step==0) - moi episode co 1 buoc step=0
        if (r.get("step") or 0) == 0:
            eps.add((r.get("task_id"), r.get("image")))    # anh rong?
    n_small = 0
    for n in list(pngs)[:400]:
        try:
            if z.getinfo(n).file_size < 1024:
                n_small += 1
        except Exception:
            pass
    print("   n_row        : %d" % len(rows))
    print("   n_episode    : %d | n_task: %d" % (len(eps), len(tasks)))
    print("   n_png        : %d | anh <1KB (trong 400 mau): %d"
          % (len(pngs), n_small))
    print("   verbs        : %s" % dict(verbs.most_common(10)))
    print("   per task     : %s" % dict(tasks.most_common(12)))
    prob = []
    if n_bad_img:
        prob.append("%d row troi anh (khong co trong zip)" % n_bad_img)
    if n_bad_act:
        prob.append("%d row action khong hop le" % n_bad_act)
    if n_empty:
        prob.append("%d row instruction rong" % n_empty)
    if n_small:
        prob.append("%d anh <1KB" % n_small)
    if not rows:
        prob.append("0 row")
    if prob:
        print("   => FAIL: " + "; ".join(prob))
        return None
    print("   => OK: du lieu hop le")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--repo", default="kkouadn/ornith-colab-data")
    ap.add_argument("--no-host", action="store_true")
    a = ap.parse_args()
    p = a.zip if os.path.isabs(a.zip) else os.path.join(
        ROOT, a.zip.replace("/", os.sep))
    if not os.path.exists(p):
        print("FAIL: khong ton tai", p)
        return 1
    rows = check_zip(p)
    if rows is None:
        return 1
    if a.no_host:
        return 0
    print("\n=> host len HF:", a.repo)
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts", "hf_host_data.py"),
                        "--repo", a.repo, p])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
