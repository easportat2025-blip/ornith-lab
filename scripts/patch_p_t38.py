# -*- coding: utf-8 -*-
"""
patch_p_t38.py - sua success policy cho T38_recovery (port tu T25 desktop):
  click primary (decoy, khong phan hoi) tren hang target -> click backup
  (thuc su enable). Khong dung #nm/#apply (app khong co element do).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "b17_selftest.py")

OLD = '''def p_t38(pg):
    """T38: dat ten -> Apply (lan 1) -> neu app bao loi -> Apply LAN NUA (khong doi gia tri)."""
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    want = v.get("WANT") or ""
    pg.click("#nm")
    pg.fill("#nm", want)
    pg.click("#apply")
    pg.wait_for_timeout(120)
    pg.click("#apply")'''

NEW = '''def p_t38(pg):
    """T38: click primary (decoy, khong phan hoi) tren hang target -> click
    backup (thuc su enable). Doc code tu window.__spec.vars.CODE."""
    v = pg.evaluate("() => window.__spec && window.__spec.vars || {}")
    code = v.get("CODE") or ""
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr'))"
                ".find(t=>t.cells[1].textContent.trim()===code);"
                "if(tr) tr.querySelector('.p').click();}", code)
    pg.wait_for_timeout(120)
    pg.evaluate("(code) => {const tr=Array.from(document.querySelectorAll('#tb tr'))"
                ".find(t=>t.cells[1].textContent.trim()===code);"
                "if(tr) tr.querySelector('.b').click();}", code)
    pg.wait_for_timeout(120)'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD not in s:
    print("FAIL: khong tim thay p_t38 cu")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua p_t38")
