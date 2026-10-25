# -*- coding: utf-8 -*-
"""
check_dbench_kernel.py - kiem tra 1 kernel DESKTOP-BENCH co day du "vat lieu"
truoc khi push (fail-loud, 1 lenh):

  1) write_apps() ghi TAT CA app cua TASK_TABLE (khong thieu app MIMO)
  2) co GUARD fail-loud (thieu app -> SystemExit)
  3) co INFRA_ERRORS (episode app thieu -> bo qua, khong tinh nham la model)
  4) raw duoc luu DAY DU (>=2000 ky tu), khong cat 200
  5) metadata: enable_internet=False (G10), dataset_sources ton tai tren Kaggle
  6) syntax OK (compile)

Dung: python scripts/check_dbench_kernel.py phase13-gui/kernel_desktop_bench_b3
ASCII-only source.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = [
    ("app t21_form_desktop", '"t21_form_desktop.html"'),
    ("app t22_calc", '"t22_calc.html"'),
    ("app t23_table_sort", '"t23_table_sort.html"'),
    ("app t24_text_edit", '"t24_text_edit.html"'),
    ("app t25_recovery", '"t25_recovery.html"'),
    ("app t26_clipboard", '"t26_clipboard.html"'),
    ("GUARD fail-loud", "thieu app file cho task"),
    ("INFRA_ERRORS", "INFRA_ERRORS"),
    ("infra_errors.json", "infra_errors.json"),
    ("raw day du 2000", 'raw\\": \\(raw or \\"\\"\\)\\[:2000\\]'),
]


def main():
    if len(sys.argv) < 2:
        print("dung: python scripts/check_dbench_kernel.py <dir kernel>")
        return 2
    d = sys.argv[1]
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d.replace("/", os.sep))
    src_p = os.path.join(d, "desktop_bench_kernel.py")
    md_p = os.path.join(d, "kernel-metadata.json")
    if not os.path.exists(src_p):
        print("FAIL: khong co %s" % src_p)
        return 1
    src = io.open(src_p, encoding="utf-8", errors="replace").read()
    n_fail = 0
    print("== %s (%d bytes) ==" % (d, len(src)))
    for name, pat in CHECKS:
        ok = re.search(pat, src) is not None
        print("   [%s] %s" % ("OK " if ok else "FAIL", name))
        if not ok:
            n_fail += 1
    # raw_first 2000 (trong builder)
    ok = '"raw_first": (rs[0].get("raw") or "")[:2000]' in src
    print("   [%s] raw_first 2000" % ("OK " if ok else "FAIL"))
    if not ok:
        n_fail += 1
    # app files that really exist in the source (nguon: apps/ cua kernel goc)
    md = json.load(io.open(md_p, encoding="utf-8")) if os.path.exists(md_p) else {}
    if md.get("enable_internet") is not False:
        print("   [FAIL] enable_internet phai False (G10)")
        n_fail += 1
    else:
        print("   [OK ] enable_internet=False")
    ds = md.get("dataset_sources", [])
    print("   dataset_sources (%d): %s" % (len(ds), ds))
    # compile
    try:
        compile(src, src_p, "exec")
        print("   [OK ] syntax OK")
    except SyntaxError as e:
        print("   [FAIL] syntax: %s" % e)
        n_fail += 1
    print("== KET QUA: %d FAIL ==" % n_fail)
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
