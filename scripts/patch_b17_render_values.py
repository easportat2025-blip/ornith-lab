# -*- coding: utf-8 -*-
"""
patch_b17_render_values.py - FIX LON: 8 app B17 hien thi literal "{CODE_B}"
thay vi gia tri that => task khong giai duoc tu man hinh (model chi nhin anh).

FIX: (1) thay {VAR} trong HTML bang <span id="vVAR"></span>
     (2) JS populate span sau khi tao window.__spec.vars
     => gia tri hien thi dung, khong can sua tay tung app.

Dung: python scripts/patch_b17_render_values.py
ASCII-only source.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "build_b17_apps.py")

s = io.open(P, encoding="utf-8", newline="").read()

# 1) body: {VAR} -> <span id="vVAR"></span> trong page() call
#    Chi sua trong cac chuoi HTML (body), khong sua script.
#    Ma: tim cac placeholder {UPPER} trong cac body string cua APPS.
old_body_pattern = None
# thay tat ca '{NAME_A}' -> '<span id="vNAME_A"></span>' v.v. trong toan file
# (chi cac token IN HOA >=4 ky tu)
def repl(m):
    ph = m.group(1)
    return '<span id="v%s"></span>' % ph

# chi ap dung cho chuoi HTML (cac dong co <div class="note">...{VAR}...)
# don gian: thay tat ca {UPPER} trong file (ca body va script) - nhung
# script co window.__spec={vars:{CODE:CODE,...}} khong dung {VAR} => an toan
s2 = re.sub(r"\{([A-Z][A-Z0-9_]{1,})\}", repl, s)
n = s.count("{") - s2.count("{")
# 2) sau window.__spec = {vars: {...}}; them JS populate span
#    tim moi dong 'window.__spec={vars:{...}};' hoac 'window.__spec = {vars: {...}};'
import re
pat = re.compile(r"(window\.__spec\s*=\s*\{vars:\{[^}]*\}[^}]*\};)")
def inject(m):
    return (m.group(1) + "\nObject.keys(window.__spec.vars).forEach(function(k){"
            "var e=document.getElementById('v'+k); if(e) e.textContent="
            "window.__spec.vars[k];});")
s2 = pat.sub(inject, s2)
io.open(P, "w", encoding="utf-8", newline="").write(s2)
print("da thay %d placeholder -> <span id=vVAR> + inject populate" % n)
print("=> chay lai: python scripts/build_b17_apps.py")
