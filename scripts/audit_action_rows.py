# -*- coding: utf-8 -*-
"""
audit_action_rows.py - quet 1 file traj.jsonl (data train) xem co bao nhieu row
bi lo bien "DONE" o do khong co action that.

LY DO (22/10, @MiMo): loader v24:
    act = r.get("action")
    if not act:
        pt = r.get("point")
        act = (f"CLICK {pt[0]} {pt[1]}" if pt else "DONE")
=> ROW THIEU 'action' VA THIEU 'point' => TARGET HUAN LUYEN = "DONE"
=> model hoc "khong biet lam gi -> DONE" => o bench: C1_no_action TANG,
   commit_rate GIAM (v24: 84,9% vs v22 100%) => DUNG lo loi: lo cac row do
   khoi data (hoac sua cho co action that).

Dung:
    python scripts/audit_action_rows.py <a.jsonl> [<b.jsonl> ...]
ASCII-only source.
"""
import io
import json
import os
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
VERB_RX = re.compile(r"^\s*(CLICK|TYPE|KEY|MOVE|DRAG|SCROLL|DONE)\b", re.I)


def audit(path):
    rows = []
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    n = len(rows)
    n_noact = 0
    n_done_target = 0
    n_empty_act = 0
    verbs = Counter()
    for r in rows:
        act = r.get("action")
        if act is None or str(act).strip() == "":
            n_empty_act += 1
            if not r.get("point"):
                n_done_target += 1
            continue
        m = VERB_RX.match(str(act))
        verbs[(m.group(1).upper() if m else "?")] += 1
    print("== %s" % os.path.basename(path))
    print("   n_row            : %d" % n)
    print("   action rong      : %d (%.1f%%)" % (n_empty_act,
                                                 100.0 * n_empty_act / max(n, 1)))
    print("   => TARGET 'DONE' : %d (%.1f%%)  <-- DANG DAY MODEL NGUNG"
          % (n_done_target, 100.0 * n_done_target / max(n, 1)))
    print("   verbs            : %s" % dict(verbs.most_common(8)))
    return n, n_done_target


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/audit_action_rows.py <a.jsonl> [...]")
        return 2
    tot = td = 0
    for p in sys.argv[1:]:
        if not os.path.exists(p):
            print("   (thieu) %s" % p)
            continue
        n, d = audit(p)
        tot += n
        td += d
    print("=" * 70)
    print("TONG: %d row, %d row target 'DONE' (%.1f%%)"
          % (tot, td, 100.0 * td / max(tot, 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
