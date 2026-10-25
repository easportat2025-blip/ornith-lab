# -*- coding: utf-8 -*-
"""detect_task_fixes.py - CHUNG MINH run dung task CU hay task MOI.

Van de: khi task benchmark duoc sua (15 fix), phai biet run moi co that su
dung ban da sua khong. Khong nen tin "da upload dataset" - phai kiem
truc tiep tu file ket qua (instruction + man hinh model thay trong trace).

Cach:
  1) Instruction quyet dinh (neu task sua instruction):
     instruction cua task trong file ket qua moi  vs  tasks.json (ban MOI)
     -> so san bang regex (placeholder DYNLABEL/REFCODE/... da duoc thay).
     - khop ban MOI  => PROOF_NEW
     - khop ban CU   => PROOF_OLD (doi chieu instruction cu lay tu file ket qua
       cu cua cung suite)
  2) Neu instruction khong doi (chi sua DOM), dung FINGERPRINT DOM:
     chuoi xuat hien tren MAN HINH (vd "Current values: f1 = "). Fingerprint
     co trong file ket qua CU => khong chung minh (chu co san o ban cu);
     xuat hien o file ket qua MOI => PROOF_NEW.
  3) Task nao khong co fingerprint dac biet -> UNKNOWN (khong ket luan duoc).

Dung:
  python scripts/detect_task_fixes.py <result.json> [--suite B15.5|B16-A]
  python scripts/detect_task_fixes.py <result.json> --old <old_result.json>
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# suite -> (tasks.json cua ban MOI, file ket qua CU de doi chieu)
SUITES = {
    "B15.5": ("phase13-gui/bench_v15/tasks_v15_5/tasks/tasks.json",
              "phase13-gui/out_bench_v155_v21/b15_result.json"),
    "B16-A": ("phase13-gui/bench_v15/tasks_v16_a/tasks/tasks.json",
              "phase13-gui/out_bench_v16_v21/b15_result.json"),
    "B15": ("phase13-gui/bench_v15/tasks/tasks.json", None),
}

# placeholder trong tasks.json -> regex so san
PLACEHOLDERS = ["MINCHARS", "DYNLABEL", "REFCODE", "TARGETCOUNT"]
# token CHU HOA >=4 ky tu co that khong phai placeholder -> giu nguyen
UPPER_KEEP = {"DOWN", "UP", "AND", "END", "KEY", "STEP", "ONLY", "NOTE", "TRUE"}
EXTRA_PATTERNS = [
    r"ALERT-[A-Z0-9]{2,}",
    r"RF-\d{3,}",
    r"\b\d{3,}\b",
]

# fingerprint DOM (xuat hien tren MAN HINH cua ban da sua).
# gia tri = (chuoi tim, co_bien_co_trong_ban_cu_khong)
#   True  -> ban CU cung co chuoi nay => khong chung minh duoc
#   False -> ban CU KHONG co => xuat hien o run moi = PROOF_NEW
DOM_FINGERPRINTS = {
    "T13_wizard": [("validation", None)],
    "T14_alerts": [("press the End key", None), ("Load alert button", None)],
    "T15_dialog": [("press the End key", None), ("no mouse wheel", None)],
    "T16_clipboard2": [("Copied: ", None), ("Pasted into Target", None)],
    "T17_reorder": [("Move up", None), ("Move down", None)],
    "T18_countsubmit": [("Selected:", None)],
    "T19_wizardsum": [("Step 1", None), ("Step 2", None)],
    "T21_hiddenval": [("Hide code", None)],
    "T22_keynav": [("KEY enter", None)],
    "T23_undoredo": [("Current values: f1 = ", False)],
    "T24_multifilter": [("Filters applied: ", False)],
    "T25_compute": [("A + B", None)],
    "T26_distractorlist": [("Target item: ", False), ("Target list: ", False)],
}


def load_json(p):
    return json.load(io.open(p, encoding="utf-8"))


def load_tasks(p):
    d = load_json(p)
    tasks = d["tasks"] if isinstance(d, dict) and "tasks" in d else d
    return {t["task_id"]: t.get("instruction", "") for t in tasks}


def load_eps(p):
    d = load_json(p)
    return as_eps(d)


def as_eps(d):
    """File ket qua co the la dict {"episodes": [...]} hoac thang list episode."""
    if isinstance(d, dict):
        return d.get("episodes") or []
    if isinstance(d, list):
        return d
    return []


def to_regex(instr):
    """instruction (co placeholder da render hoac chua render) -> regex so san."""
    pat = re.escape(instr or "")
    # placeholder da render: ALERT-7X, RF-4821, so >=3 chu so
    pat = re.sub(re.escape(r"ALERT\-[A-Z0-9]{2,}"), ".+?", pat)
    pat = re.sub(re.escape(r"RF\-\d{3,}"), ".+?", pat)
    pat = re.sub(r"\\\d{3,}", ".+?", pat)
    # placeholder chua render (trong tasks.json)
    for ph in PLACEHOLDERS:
        pat = pat.replace(re.escape(ph), ".+?")
    # token CHU HOA >=4 ky tu (tru whitelist) -> placeholder
    def _tok(m):
        w = m.group(0)
        return ".+?" if w not in UPPER_KEEP else w
    pat = re.sub(r"(?<![A-Za-z0-9])[A-Z]{4,}(?![A-Za-z0-9])", _tok, pat)
    return re.compile("^" + pat + "$", re.S)


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def norm_key(s):
    """Chuan hoa instruction de so sanh 2 ban (template vs render).

    Thay placeholder bang '#':
      - token CHU HOA >=4 ky tu (tru whitelist): MINCHARS/DYNLABEL/REFCODE/...
      - ALERT-7X, RF-4821
      - so >=2 chu so
    So sanh bang EQUALITY chuoi chuan hoa (chinh xac hon regex - regex de
    v0: instruction render khong doi giong het so voi template).
    """
    s = norm(s)
    # THU TU QUAN TRONG: ALERT-7X / RF-4821 phai duoc thay TRUOC, neu khong
    # token CHU HOA "ALERT" bi doi truoc thanh '#' -> "#-7X" (sai).
    s = re.sub(r"(?<![A-Za-z0-9])ALERT-[A-Z0-9]+", "#", s)
    s = re.sub(r"(?<![A-Za-z0-9])RF-\d+", "#", s)

    def _up(m):
        return "#" if m.group(0) not in UPPER_KEEP else m.group(0)
    s = re.sub(r"(?<![A-Za-z0-9])[A-Z]{4,}(?![A-Za-z0-9])", _up, s)
    s = re.sub(r"(?<![A-Za-z0-9])\d{2,}(?![A-Za-z0-9])", "#", s)
    return s


def same_text(a, b):
    """2 instruction co cung noi dung khong (sau khi chuan hoa placeholder).

    Equality la chinh; them fallback tuong do chuoi (>=0.93) cho case chi
    khac o placeholder/chu so (vi du 'MINCHARS' vs '8', 'N' vs 'MINCHARS')
    - truong hop do strict equality that bai nhung van LA cung noi dung.
    """
    if a == b:
        return True
    try:
        import difflib
        return difflib.SequenceMatcher(None, a, b).ratio() >= 0.93
    except Exception:
        return False


def classify(tid, new_tmpl, eps_new, eps_old):
    """-> (verdict, chi tiet)"""
    instrs = [norm(e.get("instruction", "")) for e in eps_new
              if e.get("task_id") == tid]
    if not instrs:
        return "ABSENT", "task khong co episode trong run nay"
    key_new = norm_key(new_tmpl)
    n_new = sum(1 for i in instrs if same_text(norm_key(i), key_new))

    old_tmpl = ""
    if eps_old:
        olds = [norm(e.get("instruction", "")) for e in eps_old
                if e.get("task_id") == tid]
        if olds:
            old_tmpl = olds[0]
    key_old = norm_key(old_tmpl) if old_tmpl else None
    n_old = (sum(1 for i in instrs if same_text(norm_key(i), key_old))
             if key_old else 0)
    if n_new == len(instrs):
        if key_old is not None and n_old == len(instrs):
            # instruction giong nhau o ca 2 ban -> khong phan bi duoc bang
            # instruction -> phai dua vao fingerprint DOM
            fps = DOM_FINGERPRINTS.get(tid, [])
            decisive, both, miss = [], [], []
            for fp, _flag in fps:
                s = fp
                cnt_new = sum(json.dumps(e, ensure_ascii=False).count(s)
                              for e in eps_new if e.get("task_id") == tid)
                cnt_old = sum(json.dumps(e, ensure_ascii=False).count(s)
                              for e in eps_old if e.get("task_id") == tid)
                if cnt_new and not cnt_old:
                    decisive.append("%s(x%d, ban cu x0)" % (s, cnt_new))
                elif cnt_new:
                    both.append("%s(x%d, ban cu x%d)" % (s, cnt_new, cnt_old))
                else:
                    miss.append("%s(x0)" % s)
            if decisive:
                return "PROOF_NEW", ("fingerprint DOM CHI CO O BAN MOI: "
                                     + "; ".join(decisive))
            if both:
                return "UNKNOWN", ("fingerprint DOM co o ca 2 ban (khong quyet "
                                   "dinh): %s" % "; ".join(both))
            if fps:
                return "UNKNOWN", ("instruction giong ban CU va khong thay "
                                   "fingerprint DOM (%s)" % ", ".join(miss))
            return "UNKNOWN", "instruction giong ban CU, khong co fingerprint"
        return "PROOF_NEW", "instruction khop ban MOI (%d/%d ep)" % (n_new, len(instrs))
    if key_old is not None and n_old == len(instrs):
        return "PROOF_OLD", "instruction khop ban CU (%d/%d ep)" % (n_old, len(instrs))
    return "UNKNOWN", ("instruction khong khop ban MOI (0/%d) va khong khop "
                       "ban CU" % len(instrs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--suite", default=None)
    ap.add_argument("--old", default=None, help="file ket qua cu de doi chieu")
    a = ap.parse_args()

    rp = a.result if os.path.isabs(a.result) else os.path.join(ROOT, a.result)
    res = load_json(rp)
    eps_new = as_eps(res)
    suite = (res.get("suite") if isinstance(res, dict) else "") or ""
    wins = res.get("wins") if isinstance(res, dict) else None
    tids_in_run = []
    for e in eps_new:
        if e.get("task_id") not in tids_in_run:
            tids_in_run.append(e.get("task_id"))

    print("=" * 78)
    print("DETECT TASK FIXES")
    print("  file  : %s" % os.path.relpath(rp, ROOT))
    print("  suite(ghi trong file): %s | n_ep = %d | wins = %s"
          % (suite, len(eps_new), wins))
    tids_in_run = []
    for e in eps_new:
        if e.get("task_id") not in tids_in_run:
            tids_in_run.append(e.get("task_id"))
    # TU SUY SUITE tu tap task_id trong run (field "suite" trong file ket qua
    # khong chinh xac: run B16-A lai ghi suite=B15)
    best, best_ov, best_tid = None, 0, None
    for s, (tp, _op) in SUITES.items():
        fp = os.path.join(ROOT, tp)
        if not os.path.exists(fp):
            continue
        tids = set(load_tasks(fp).keys())
        ov = len(tids & set(tids_in_run))
        if ov > best_ov:
            best, best_ov, best_tid = s, ov, tp
    if not best:
        print("  KHONG tim thay tasks.json nao khop task_id trong run")
        return 2
    print("  suite(suy tu task_id): %s | khop %d/%d task"
          % (best, best_ov, len(tids_in_run)))
    tpath = best_tid
    new_tasks = load_tasks(os.path.join(ROOT, tpath))
    old_p = a.old
    if not old_p:
        op = SUITES[best][1]
        if op:
            old_p = op
    eps_old = []
    if old_p:
        op = old_p if os.path.isabs(old_p) else os.path.join(ROOT, old_p)
        if os.path.exists(op):
            eps_old = load_eps(op)
            print("  doi chieu voi ban CU: %s (%d ep)"
                  % (os.path.relpath(op, ROOT), len(eps_old)))
        else:
            print("  KHONG tim thay file ket qua CU: %s" % old_p)
    print("-" * 78)
    counts = {"PROOF_NEW": 0, "PROOF_OLD": 0, "UNKNOWN": 0, "ABSENT": 0}
    for tid in sorted(new_tasks):
        if tid not in tids_in_run:
            continue
        v, d = classify(tid, new_tasks[tid], eps_new, eps_old)
        counts[v] = counts.get(v, 0) + 1
        print("%-20s %-10s %s" % (tid, v, d))
    print("-" * 78)
    tot = sum(counts[k] for k in ("PROOF_NEW", "PROOF_OLD", "UNKNOWN"))
    if tot:
        print("TONG: %d task | PROOF_NEW %d | PROOF_OLD %d | UNKNOWN %d"
              % (tot, counts["PROOF_NEW"], counts["PROOF_OLD"], counts["UNKNOWN"]))
        if counts["PROOF_NEW"] == tot:
            print("=> KET LUAN: run nay DUNG TASK MOI (tat ca task da sua)")
        elif counts["PROOF_OLD"] == tot:
            print("=> KET LUAN: run nay DUNG TASK CU (chua co hieu luc cua fix)")
        else:
            print("=> KET LUAN: HON HOP - xem bang tren")
    return 0


if __name__ == "__main__":
    sys.exit(main())
