# -*- coding: utf-8 -*-
"""
check_dbench_log.py - kiem tra log 1 run DESKTOP-BENH (acc B) co that:
  1) "apps written" phai co DU 4 app cua @MiMo (t21_form_desktop, t22_calc,
     t23_table_sort, t24_text_edit) + t25/t26
  2) co dong "GUARD OK" (guard fail-loud da chay)
  3) KHONG co dong "[INFRA]" (khong episode nao bi lo vi app/browser)
  4) neu co dong "FAIL: dataset thieu" -> ket qua khong hop le

Dung: python scripts/check_dbench_log.py phase13-gui/out_desktop_bench_b3/ornith-gui-desktop-bench-b3.log
ASCII-only source.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NEED_APPS = ["t21_form_desktop.html", "t22_calc.html", "t23_table_sort.html",
             "t24_text_edit.html", "t25_recovery.html", "t26_clipboard.html"]


def read_lines(p):
    raw = io.open(p, encoding="utf-8", errors="replace").read()
    out = []
    for m in re.finditer(r'\{"stream_name":"(stdout|stderr)","time":([0-9.]+),'
                         r'"data":"(.*?)"\}', raw, re.S):
        d = m.group(3)
        try:
            d = d.encode("utf-8").decode("unicode_escape", errors="replace")
        except Exception:
            pass
        out.append((float(m.group(2)), m.group(1), d))
    if not out:
        out = [(0.0, "raw", l) for l in raw.splitlines()]
    return out


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/check_dbench_log.py <log>")
        return 2
    p = sys.argv[1]
    if not os.path.exists(p):
        print("khong ton tai:", p)
        return 1
    lines = read_lines(p)
    blob = "".join(s for _t, _st, s in lines)
    ok = True
    # 1) apps written
    m = re.search(r"apps written: \[(.*?)\]", blob, re.S)
    if m:
        written = set(re.findall(r"'([^']+)'", m.group(1)))
        miss = [a for a in NEED_APPS if a not in written]
        print("[%s] apps written: %d file%s"
              % ("OK " if not miss else "FAIL", len(written),
                 "" if not miss else "  THIEU: %s" % ", ".join(miss)))
        ok = ok and not miss
    else:
        print("[?? ] khong tim thay dong 'apps written' (kernel chet truoc do?)")
        ok = False
    # 2) guard
    has_guard = "GUARD OK" in blob
    print("[%s] guard fail-loud: %s" % ("OK " if has_guard else "FAIL",
                                       "da chay" if has_guard else "KHONG thay"))
    ok = ok and has_guard
    # 3) infra
    n_infra = blob.count("[INFRA]")
    print("[%s] loi ha tang: %d episode bi lo%s"
          % ("OK " if n_infra == 0 else "FAIL", n_infra,
             "" if n_infra == 0 else "  (app/browser)"))
    ok = ok and n_infra == 0
    # 4) fail dataset
    bad_ds = "FAIL: dataset thieu" in blob
    print("[%s] dataset thieu: %s" % ("OK " if not bad_ds else "FAIL",
                                      "co" if bad_ds else "khong"))
    ok = ok and not bad_ds
    # 5) ket qua
    wins = re.findall(r"(\w+) v(\d)\s+WIN", blob)
    print("   task WIN: %s" % (", ".join("%s v%s" % w for w in wins) or "(chua co)"))
    print("== %s ==" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
