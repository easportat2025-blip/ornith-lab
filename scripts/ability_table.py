# -*- coding: utf-8 -*-
"""ability_table.py - bang nang luc (PLAN.md W2) cho MOI file result
+ cot "ep roi vi loi ha tang" (man hinh den / infra_errors.json).

Bo sung cho: scripts/audit_desktop_result.py (logic man hinh den) va
scripts/cmp_runs.py (so sanh 2 run).

Dung:
  python scripts/ability_table.py [--dir phase13-gui] [--out ...md]
Scans phase13-gui/out_*/**/*result*.json. ASCII-only source.
"""
import argparse
import glob
import io
import json
import os
import sys

BLACK = ("black", "completely black", "blank screen", "no content")

# W2: (so, ten nang luc, tag task) - task thuc te tim thay se duoc bao cao
ABILITIES = [
    (1, "Doc truoc khi hanh dong",
     ["T21_hiddenval", "T25_compute"]),
    (2, "Nhieu buoc (>=8 hanh dong)",
     ["T23_undoredo", "T22_order", "T13_wizard", "T19_wizardsum"]),
    (3, "Pha vong lap (loop-recovery)", []),
    (4, "Phuc hoi sau loi",
     ["T25_recovery", "T08_errorfix"]),
    (5, "Clipboard (select-copy-paste)",
     ["T26_clipboard", "T16_clipboard2"]),
    (6, "Dieu huong bang phim",
     ["T22_keynav", "T23_keys"]),
    (7, "Scroll / doc ngoai viewport",
     ["T07_scroll", "T23_table_sort"]),
    (8, "Distractor",
     ["T20_distractor", "T26_distractorlist"]),
    (9, "3D grounding (bbox)", []),       # boi LOAI file bench3d_result.json
    (10, "Desktop that (X11)", []),       # boi LOAI file desktop_result.json
]
T2A = {}
for _no, _name, _tags in ABILITIES:
    for _t in _tags:
        T2A[_t] = _no


def truthy(v):
    return v is True or str(v).lower() in ("true", "1", "1.0")


def kind_of(path):
    b = os.path.basename(path)
    if b == "desktop_result.json":
        return "desktop"
    if b == "bench3d_result.json":
        return "3d"
    return "web"


def scan(path):
    d = json.load(io.open(path, encoding="utf-8", errors="replace"))
    eps = d.get("episodes") or []
    if not isinstance(eps, list):
        eps = []
    kind = kind_of(path)
    # win: web/desktop = field 'win'; 3d = field 'hit'
    wins, black, tasks = 0, 0, {}
    for e in eps:
        w = e.get("win") if "win" in e else e.get("hit")
        if truthy(w):
            wins += 1
        raw = (e.get("raw_first") or "").lower()
        is_black = any(bk in raw for bk in BLACK)
        if is_black:
            black += 1
        t = e.get("task_id") or ("3d" if kind == "3d" else "?")
        a = tasks.setdefault(t, [0, 0, 0])
        a[1] += 1
        if truthy(w):
            a[0] += 1
        if is_black:
            a[2] += 1
    infra = 0
    ie = d.get("infra_errors")
    if isinstance(ie, list):
        infra = len(ie)
    elif isinstance(ie, dict):
        infra = sum(len(v) if isinstance(v, list) else 1 for v in ie.values())
    return {
        "path": path, "kind": kind, "n": len(eps), "wins": wins,
        "black": black, "infra": infra, "tasks": tasks,
        "suite": d.get("suite") or "", "adapter": d.get("adapter") or "",
        "win_rate_top": d.get("win_rate"),
    }


def ability_of(row, tid):
    if row["kind"] == "desktop":
        return 10
    if row["kind"] == "3d":
        return 9
    return T2A.get(tid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="phase13-gui")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(
        args.dir, "out_*", "**", "*result*.json"), recursive=True))
    rows, skipped = [], []
    for p in files:
        try:
            rows.append(scan(p))
        except Exception as e:
            skipped.append("%s (%s)" % (os.path.basename(p), type(e).__name__))
    for r in rows:
        # aggregate theo nang luc
        ab = {}
        for tid, (w, n, _b) in r["tasks"].items():
            no = ability_of(r, tid)
            if no:
                a = ab.setdefault(no, [0, 0])
                a[0] += w
                a[1] += n
        r["abil"] = ab

    md = ["# Bang nang luc (PLAN.md W2) + loi ha tang",
          "",
          "Sinh boi `scripts/ability_table.py` (scan %s/out_*/**/*result*.json)."
          % args.dir,
          "",
          "Cot A1..A10 = wins/ep cua tung nang luc trong file do "
          "(khong phu cover = '-'). `loi` = ep loi ha tang "
          "(man hinh den va/hoac infra_errors).",
          "",
          "## 1. Tung file result",
          "",
          "| file | loai | suite | adapter | n_ep | win | win% | loi |"
          " A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 | A10 |",
          "|" + "---|" * 18]
    for r in sorted(rows, key=lambda x: x["path"]):
        name = os.path.relpath(os.path.dirname(r["path"]),
                               args.dir).replace("\\", "/")
        wr = r.get("win_rate_top")
        if wr is None:
            wr = "%.0f%%" % (100.0 * r["wins"] / r["n"]) if r["n"] else "-"
        elif isinstance(wr, (int, float)):
            wr = "%.1f%%" % (100.0 * wr)
        cells = []
        for no, _n, _t in ABILITIES:
            a = r["abil"].get(no)
            cells.append("%d/%d" % (a[0], a[1]) if a else "-")
        md.append("| %s | %s | %s | %s | %d | %d | %s | %d | %s |"
                  % (name, r["kind"], r["suite"], r["adapter"], r["n"],
                     r["wins"], wr, r["black"] + r["infra"],
                     " | ".join(cells)))

    md += ["", "## 2. Coverage W2 (task tag -> task thuc te trong ket qua)",
           "",
           "| # | nang luc | task tag W2 | task tim thay (file/web+desktop) |",
           "|" + "---|" * 4]
    seen_tasks = set()
    for r in rows:
        for tid in r["tasks"]:
            seen_tasks.add(tid)
    for no, name, tags in ABILITIES:
        found = sorted({tid for r in rows for tid in r["tasks"]
                        if ability_of(r, tid) == no})
        md.append("| %d | %s | %s | %s |"
                  % (no, name, ", ".join(tags) or "(loai file)",
                     ", ".join(found) or "**CHUA CO TASK**"))

    md += ["", "## 3. Loi ha tang chi tiet (ep manhinh den / infra_errors)", ""]
    for r in sorted(rows, key=lambda x: x["path"]):
        if r["black"] or r["infra"]:
            name = os.path.basename(os.path.dirname(r["path"]))
            md.append("- **%s**: %d ep den + %d infra_errors"
                      % (name, r["black"], r["infra"]))
            for tid, (w, n, b) in sorted(r["tasks"].items()):
                if b:
                    md.append("  - %s: %d/%d ep den (win %d/%d)"
                              % (tid, b, n, w, n))
    if skipped:
        md += ["", "Bo qua (khong phai result episodes): "
               + ", ".join(skipped)]
    md += ["", "## 4. Canh bao W2", ""]
    for no, name, tags in ABILITIES:
        n_files = sum(1 for r in rows if no in r["abil"])
        if not n_files:
            md.append("- Nang luc %d (%s): **0 file result nao cover**"
                      % (no, name))

    out = args.out or os.path.join(args.dir, "ability_table.md")
    with io.open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("Da ghi %s (%d file result, %d bo qua)"
          % (out, len(rows), len(skipped)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
