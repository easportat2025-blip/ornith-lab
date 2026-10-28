# -*- coding: utf-8 -*-
"""build_b18_suite.py - hard-weighted holdout suite B18.

B18 keeps two easy sanity tasks (note-order, error-retry) and makes the six
capability tasks hard by requiring the skills v25b still misses: scroll, drag,
Tab navigation, multi-step wizards, clipboard shortcuts, and distractor rows
below the fold.  Hard tasks get six random variants; easy tasks keep three.

Why a separate suite: B17 v3 scored 15/27 (55.6%) on v25b, above the W1
threshold (<=20%).  B18 is a new holdout; it is not used for v26 training.

Usage:
    python scripts/build_b18_suite.py
    python scripts/lint_task_static.py phase13-gui/bench_b18
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks")
DST = os.path.join(ROOT, "phase13-gui", "bench_b18", "tasks")

EASY_VARIANTS = [0, 1, 2]
HARD_VARIANTS = [0, 1, 2, 3, 4, 5]

# task_id -> variants.  T40 is rewritten below to require scrolling.
PLAN = [
    ("T30_note_order", EASY_VARIANTS),
    ("T33_error_retry", EASY_VARIANTS),
    ("T31_scroll_code", HARD_VARIANTS),
    ("T32_drag_slider", HARD_VARIANTS),
    ("T34_tab_nav", HARD_VARIANTS),
    ("T36_wizard_steps", HARD_VARIANTS),
    ("T39_clipboard", HARD_VARIANTS),
    ("T40_distractor", HARD_VARIANTS),
]


def t40_hard(html):
    """Turn T40 into a scroll + distractor task (target row 10..14)."""
    html = html.replace(
        '<div class="sub">Select the contact whose badge matches the note.</div>',
        '<div class="sub">Scroll the contact list to the bottom, then select '
        'the row whose badge matches the note.</div>')
    html = html.replace(
        'table{width:100%;border-collapse:collapse;background:#232833;'
        'border:1px solid #39404e;border-radius:10px;overflow:hidden}',
        'table{width:100%;border-collapse:collapse;background:#232833}\n'
        '  .panel{max-height:150px;overflow-y:auto;border:1px solid #39404e;'
        'border-radius:10px}')
    html = html.replace(
        '<table><tbody id="rows"></tbody></table>',
        '<div class="panel" id="panel"><table><tbody id="rows"></tbody>'
        '</table></div>')
    html = html.replace('const n=8;', 'const n=14;')
    html = html.replace(
        'const names=["Ari","Ben","Cleo","Dara","Enzo","Fay","Gus","Hana",'
        '"Ivo","Jo","Kai","Lena"];',
        'const names=["Ari","Ben","Cleo","Dara","Enzo","Fay","Gus","Hana",'
        '"Ivo","Jo","Kai","Lena","Mira","Noor"];')
    html = html.replace(
        'const tgt=rngIdx();\n'
        'function rngIdx(){return Math.floor(Math.random()*n);}',
        'const tgt=9+Math.floor(Math.random()*5);   // row 10..14: below fold')
    return html


def main():
    os.makedirs(DST, exist_ok=True)
    src_meta = json.load(io.open(os.path.join(SRC, "tasks.json"),
                                 encoding="utf-8"))
    by_id = {t["task_id"]: t for t in src_meta["tasks"]}
    tasks = []
    for tid, variants in PLAN:
        meta = dict(by_id[tid])
        app = meta["app"]
        src = os.path.join(SRC, app)
        dst = os.path.join(DST, app)
        if app == "t40_distractor.html":
            html = io.open(src, encoding="utf-8").read()
            html = t40_hard(html)
            with io.open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(html)
            print("   viet %-26s (scroll+distractor)" % app)
        else:
            shutil.copyfile(src, dst)
            print("   copy %-26s" % app)
        if tid == "T40_distractor":
            meta["instruction"] = (
                "Scroll the contact list to the bottom, then select the row "
                "whose badge matches the support note.")
            meta["capabilities"] = ["scroll", "read_note", "distractor",
                                    "click_row", "target_below_fold"]
        meta["variants"] = variants
        tasks.append(meta)

    shutil.copyfile(os.path.join(ROOT, "phase13-gui", "bench_b17",
                                 "checker.py"),
                    os.path.join(ROOT, "phase13-gui", "bench_b18",
                                 "checker.py"))
    print("   copy checker.py")

    tj = {"suite": "B18", "version": 1,
          "viewport": {"width": 1280, "height": 720},
          "action_space": ("CLICK x y (0..1000 normalized) | TYPE text | "
                           "KEY name | DONE | SCROLL n | MOVE x y | "
                           "DRAG x1 y1 x2 y2"),
          "tasks": tasks}
    with io.open(os.path.join(DST, "tasks.json"), "w", encoding="utf-8",
                 newline="\n") as fh:
        json.dump(tj, fh, ensure_ascii=False, indent=1)

    eps = sum(len(t["variants"]) for t in tasks)
    hard_eps = sum(len(t["variants"]) for t in tasks
                   if t["task_id"] not in ("T30_note_order", "T33_error_retry"))
    print("=> %d task | %d episodes (%d hard) | easy wins 6 -> %.1f%%"
          % (len(tasks), eps, hard_eps, 6.0 / eps * 100.0))
    print("=> lenh tiep: python scripts/lint_task_static.py "
          "phase13-gui/bench_b18")
    return 0


if __name__ == "__main__":
    sys.exit(main())
