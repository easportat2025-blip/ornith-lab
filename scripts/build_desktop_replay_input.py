# -*- coding: utf-8 -*-
"""
build_desktop_replay_input.py - dong goi INPUT cho task Colab "desktop-replay":
  5 app desktop (HTML) + 5 dummy policy (GT) + tasks.json (instruction)
=> 1 file .zip => host HF public (hf_host_data.py) => Colab tai bang urllib
   (quy tac: KHONG dung colab upload - endpoint 500).

App/task (dung 5 app cua @MiMo, task 26):
  T20_2048        t20_2048.html          (game_2048)
  T21_form_desktop t21_form_desktop.html
  T22_calc        t22_calc.html
  T23_table_sort  t23_table_sort.html
  T24_text_edit   t24_text_edit.html

Dung:
    python scripts/build_desktop_replay_input.py
    python scripts/hf_host_data.py --repo kkouadn/ornith-colab-data phase13-gui/colab_staging/desktop_replay_in.zip
ASCII-only source.
"""
import io
import json
import os
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
STAGE = os.path.join(ROOT, "phase13-gui", "colab_staging")
WORK = os.path.join(STAGE, "desktop_replay_in")
HARNESS = os.path.join(ROOT, "phase14-desktop", "harness.py")
DUMMY = os.path.join(ROOT, "phase14-desktop", "tasks", "dummy_mimo.py")
APP_DIRS = [os.path.join(ROOT, "phase14-desktop", "tasks"),
            os.path.join(ROOT, "phase13-gui", "kernel_desktop_bench", "apps")]

TASKS = [
    ("T20_2048", "t20_2048.html",
     "You are playing 2048 on the desktop. Use the arrow keys to move the "
     "tiles and try to reach a score of 40. Stop when the score is high "
     "enough.", "Dummy2048"),
    ("T21_form_desktop", "t21_form_desktop.html",
     "Fill the account setup form on the desktop using the values shown in "
     "the note (username, email and password), type the password again in "
     "the confirm field, tick the terms checkbox, then press Register.",
     "DummyFormDesktop"),
    ("T22_calc", "t22_calc.html",
     "Answer the two arithmetic questions shown on the desktop page, type "
     "each answer in its field, then submit.", "DummyCalc"),
    ("T23_table_sort", "t23_table_sort.html",
     "The data table on the desktop does not fit on the screen. Scroll down "
     "to the bottom to see all rows, reorder them so the score column is "
     "descending, select the top row, then confirm.", "DummyTableSort"),
    ("T24_text_edit", "t24_text_edit.html",
     "Replace the text in the editor on the desktop with the exact target "
     "text shown on the page, then save the document.", "DummyTextEdit"),
    ("T23_table_sort", "t23_table_sort.html",
     "The data table on the desktop does not fit on the screen. Scroll down "
     "to the bottom to see all rows, reorder them so the score column is "
     "descending, select the top row, then confirm.", "DummyTableSort"),
]


def extract_block(src, header, stop_prefixes):
    """Lay 1 khoi code (tu `header` den khi gap 1 dong bat dau bang stop)."""
    i = src.find(header)
    if i < 0:
        return ""
    j = len(src)
    for sp in stop_prefixes:
        k = src.find("\n" + sp, i + len(header))
        if k > 0:
            j = min(j, k + 1)
    return src[i:j]


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK, exist_ok=True)
    # 1) app HTML
    n_app = 0
    for _tid, app, _instr, _d in TASKS:
        found = None
        for d in APP_DIRS:
            p = os.path.join(d, app)
            if os.path.isfile(p):
                found = p
                break
        if not found:
            print("FAIL: thieu app", app)
            return 1
        shutil.copy2(found, os.path.join(WORK, app))
        n_app += 1
    # 2b) app 2048: checker_desktop.APP_FILES map T20_2048 -> "game_2048.html"
    # con harness/task table dung "t20_2048.html" => dua CA HAI ten vao zip.
    g2048 = None
    for d in APP_DIRS:
        for nm in ("game_2048.html", "t20_2048.html"):
            p = os.path.join(d, nm)
            if os.path.isfile(p):
                g2048 = p
                break
        if g2048:
            break
    if g2048:
        for nm in ("game_2048.html", "t20_2048.html"):
            shutil.copy2(g2048, os.path.join(WORK, nm))
            print("copy app 2048 -> %s" % nm)
    # 3) dummy_mimo.py (4 policy) - nguyen ven
    shutil.copy2(DUMMY, os.path.join(WORK, "dummy_mimo.py"))
    # 3) Dummy2048 + _slide tu harness -> dummy_2048.py (cdp_eval -> _page_state)
    h = io.open(HARNESS, encoding="utf-8", errors="replace").read()
    d2048 = extract_block(h, "class Dummy2048:", ["class ", "def "])
    slide = extract_block(h, "def _slide(", ["class ", "def "])
    if not d2048 or not slide:
        print("FAIL: khong tach duoc Dummy2048/_slide tu harness")
        return 1
    code = ("# -*- coding: utf-8 -*-\n"
            "\"\"\"dummy_2048.py - policy GT cho T20_2048 (trich tu harness).\n"
            "Doi cdp_eval -> _page_state (Colab dung Playwright evaluate).\n"
            "\"\"\"\nimport json\n\n\n"
            + slide + "\n\n" + d2048 +
            "\n\ndef cdp_eval(expr):\n    return _page_state(expr)\n")
    with io.open(os.path.join(WORK, "dummy_2048.py"), "w",
                 encoding="utf-8", newline="\n") as fh:
        fh.write(code)
    # 4) tasks.json
    tj = {"tasks": [{"task_id": t, "app": a, "instruction": i, "dummy": d}
                    for t, a, i, d in TASKS]}
    with io.open(os.path.join(WORK, "tasks.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(tj, fh, ensure_ascii=False, indent=1)
    # 4b) checker_desktop.py (runner THAT cua bench - dung de sinh traj)
    chk = os.path.join(ROOT, "phase14-desktop", "tasks", "checker_desktop.py")
    if os.path.isfile(chk):
        shutil.copy2(chk, os.path.join(WORK, "checker_desktop.py"))
        print("copy checker_desktop.py")
    else:
        print("!! thieu checker_desktop.py")
    # 5) zip
    zp = os.path.join(STAGE, "desktop_replay_in.zip")
    os.makedirs(STAGE, exist_ok=True)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(WORK)):
            z.write(os.path.join(WORK, f), f)
    print("staging: %s (%d app + dummy_mimo + dummy_2048 + tasks.json)"
          % (WORK, n_app))
    print("zip    : %s (%.1f KB)" % (zp, os.path.getsize(zp) / 1024.0))
    print("=> lenh host HF:")
    print("   python scripts/hf_host_data.py --repo kkouadn/ornith-colab-data "
          "phase13-gui/colab_staging/desktop_replay_in.zip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
