# -*- coding: utf-8 -*-
"""
lint_task_static.py - KIEM TRA CHAT LUONG TASK (khong can browser, <1s/suite).

LY DO (22/10, @MiMo): 2x2 da chung minh "+50 diem = 78% do SUA TASK" va
"ceiling cua toi uu data chi ~+11 diem" => gia tri lon nhat con lai la
VIET TASK MOI DUNG CHUAN. Mot task sai (do instruction noi sai man hinh /
checker doc state khong ton tai / target bi an) lam HONG CA PHEP DO cua moi
model => phai chan truoc khi task vao suite.

Kiem tra (TAT CA static, khong can Playwright):
  S1 TASK/HTML ton tai          - tasks.json co task_id, HTML co dung ten
  S2 LITERAL trong instruction   - moi chuoi trong nhay '...' phai ton tai
                                  trong HTML (hoac la placeholder render duoc)
  S3 PLACEHOLDER render duoc    - token IN_HOA trong instruction phai co
                                  trong SPEC_JS/HTML (agent thay "MINCHARS"
                                  thi KHONG giai duoc)
  S4 CHECKER co task            - checker.py phai co entry cho task_id
  S5 STATE HOOK khop             - reward/state ma checker doc phai duoc app
                                  gan (window.__state / __score / __form_state)
  S6 LO DAP AN                  - instruction khong chua "expected ..."
  S7 CAU LENH MAU THUAN          - "while the count is wrong"...
  S8 TASK CO THE GIAI           - instruction co it nhat 1 muc tieu kiem
                                  tra (co so/tu khoa) va khong rong

Dung:
    python scripts/lint_task_static.py phase13-gui/bench_v15/tasks_v15_5
    python scripts/lint_task_static.py phase13-gui/bench_v15/tasks_v16_a
Exit 0 = sach, 1 = co loi (can sua truoc khi eval).
ASCII-only source.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LEAK_RX = re.compile(r"expected\s+", re.I)
CONTRA_RX = re.compile(r"while the count is wrong|it rejects you", re.I)
# token placeholder trong instruction (MINCHARS, DYNLABEL, REFCODE, TARGETCOUNT)
PH_RX = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\b")
# literal trong nhay don
QUOTE_RX = re.compile(r"'([^'\n]{2,60})'|\"([^\"\n]{2,60})\"")
# state hook ma checker/app dung
STATE_RX = re.compile(r"window\.__([A-Za-z_][A-Za-z0-9_]*)")
# cac hook hay gap
KNOWN_HOOKS = ("state", "score", "form_state", "spec", "targets", "keys",
                "grid", "form")


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def find_files(base):
    """Tim (tasks.json, checker.py, tasks/*.html) theo 2 cach bo cuc."""
    cands = [
        (os.path.join(base, "tasks.json"),
         os.path.join(base, "checker.py"), os.path.join(base, "tasks")),
        (os.path.join(base, "tasks", "tasks.json"),
         os.path.join(base, "checker.py"), os.path.join(base, "tasks")),
        (os.path.join(base, "tasks", "tasks.json"),
         os.path.join(base, "tasks", "checker.py"), os.path.join(base, "tasks")),
    ]
    for tj, ck, hd in cands:
        if os.path.exists(tj):
            return tj, (ck if os.path.exists(ck) else ""), hd
    return None, None, None


def lint(base, verbose=True):
    base = os.path.abspath(base)
    tj, ck, hd = find_files(base)
    if not tj:
        print("FAIL: khong tim thay tasks.json trong", base)
        return 1
    tasks = json.load(io.open(tj, encoding="utf-8"))
    tasks = tasks["tasks"] if isinstance(tasks, dict) else tasks
    checker = read(ck) if ck else ""
    problems = []
    warns = []
    for t in tasks:
        tid = t.get("task_id") or "?"
        instr = t.get("instruction") or ""
        html_p = os.path.join(hd, tid.lower() + ".html")
        html = read(html_p)
        if not html:
            problems.append((tid, "S1 thieu file HTML: %s" % html_p))
            continue
        # S2 literal trong instruction phai co trong HTML
        for m in QUOTE_RX.finditer(instr):
            lit = (m.group(1) or m.group(2) or "").strip()
            if len(lit) < 3:
                continue
            if lit in html:
                continue
            if any(lit in h for h in (checker,)):
                continue
            # co phai la placeholder render duoc?
            if PH_RX.fullmatch(lit):
                continue
            # literal CHUA placeholder (VD 'Selected: TARGETCOUNT / ...')
            # -> so bang regex: placeholder -> .*
            if PH_RX.search(lit):
                _pat = PH_RX.sub(".*", lit)
                _pat = re.escape(_pat).replace("\\.\\*", ".*")
                try:
                    if re.search(_pat, html, re.S) or re.search(_pat, checker,
                                                               re.S):
                        continue
                except Exception:
                    pass
            problems.append((tid, "S2 instruction nhoi %r nhung khong co trong "
                                 "HTML (task do co do sai thu do?)" % lit))
        # S3 placeholder phai render duoc
        for m in PH_RX.finditer(instr):
            ph = m.group(1)
            if ph in ("THINK", "ACTION", "KEY", "CLICK", "TYPE", "DONE",
                      "SCROLL", "MOVE", "DRAG", "KEEP", "NOTE", "AND", "END",
                      "STEP", "ONLY", "TRUE", "PRESS", "ENTER", "TAB", "ESC"):
                continue
            if (ph in html) or (ph in checker):
                continue
            warns.append((tid, "S3 placeholder %r khong thay trong HTML/checker "
                              "=> agent se thay chuoi literal (khong giai duoc)"
                          % ph))
        # S4 checker co task
        if checker and (tid not in checker):
            problems.append((tid, "S4 checker.py khong co entry cho task "
                                 "=> diem luon 0"))
        # S5 state hook: app phai gan hook ma checker doc
        app_hooks = set(STATE_RX.findall(html))
        ck_hooks = set(STATE_RX.findall(checker))
        if ck_hooks and not (ck_hooks & (app_hooks | set(KNOWN_HOOKS))):
            problems.append((tid, "S5 checker doc state %s nhung app khong gan"
                                 % sorted(ck_hooks)))
        # S6/S7
        if LEAK_RX.search(instr):
            problems.append((tid, "S6 instruction lo dap an ('expected ...')"))
        if CONTRA_RX.search(instr):
            problems.append((tid, "S7 cau lenh mau thuan (agent se khong bam)"))
        # S8
        if not instr.strip():
            problems.append((tid, "S8 instruction rong"))
        elif len(instr.split()) < 8:
            warns.append((tid, "S8 instruction qua ngan (<8 tu) - kiem tra lai "
                          "co du thong tin de agent lam dung khong"))
    if verbose:
        print("== %s (%d task)" % (base, len(tasks)))
        for tid, msg in problems:
            print("   [FAIL] %-16s %s" % (tid, msg))
        for tid, msg in warns:
            print("   [WARN] %-16s %s" % (tid, msg))
        print("   => %d loi, %d canh bao" % (len(problems), len(warns)))
    return 1 if problems else 0


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/lint_task_static.py <thu muc suite> [...]")
        return 2
    rc = 0
    for d in sys.argv[1:]:
        rc |= lint(d)
    return rc


if __name__ == "__main__":
    sys.exit(main())
