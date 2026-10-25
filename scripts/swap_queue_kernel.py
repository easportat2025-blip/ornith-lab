# -*- coding: utf-8 -*-
"""swap_queue_kernel.py - doi 1 muc trong GPU QUEUE sang kernel moi (slug
moi + thu muc moi). Dung khi slug cu bi Kaggle 400 (state tre) ma kernel moi
da san (gate 0 FAIL) => watchdog tu push, khong can nguoi canh.

Dung:
    python scripts/swap_queue_kernel.py khoadangnguye/ornith-gui-desktop-bench-smoke \
        khoadangnguye/ornith-gui-desktop-bench-smoke2 phase13-gui/kernel_desktop_bench_smoke2
    python scripts/swap_queue_kernel.py --list
ASCII-only source.
"""
import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUES = [("scripts/gpu_queue.json", "A"), ("scripts/gpu_queue_B.json", "B")]


def load(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return []


def save(p, d):
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old_id", nargs="?")
    ap.add_argument("new_id", nargs="?")
    ap.add_argument("new_dir", nargs="?")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for rel, tag in QUEUES:
            print("-- acc %s" % tag)
            for it in load(os.path.join(ROOT, rel.replace("/", os.sep))):
                if isinstance(it, dict):
                    print("   %-48s %s" % (it.get("id"), it.get("dir")))
        return 0
    done = 0
    for rel, tag in QUEUES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        q = load(p)
        ch = False
        for it in q:
            if isinstance(it, dict) and it.get("id") == a.old_id:
                it["id"] = a.new_id
                it["dir"] = a.new_dir
                it["note"] = (it.get("note", "") +
                              " [slug doi vi slug cu bi Kaggle 400]").strip()
                ch = True
        if ch:
            save(p, q)
            done += 1
            print("acc %s: da doi muc sang %s (dir %s)" % (tag, a.new_id, a.new_dir))
    if not done:
        print("KHONG tim thay muc '%s' trong queue" % a.old_id)
        return 2
    print("=> watchdog se push muc moi (state moi => pushed=False)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
