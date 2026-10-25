# -*- coding: utf-8 -*-
"""
patch_colab_utf8.py - colab_run_task.py: decode output cua CLI bang UTF-8
(errors="replace") thay vi cp1252 mac dinh cua Windows.

LY DO (22/10, @MiMo): output tu VM co ky tu non-ASCII (emoji/UTF-8) =>
UnicodeDecodeError cp1252 => mat context trong log (da gap 1 lan).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_run_task.py")

OLD = '''    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()'''

NEW = '''    # FIX 22/10 (MiMo): output VM co ky tu non-ASCII => cp1252 mac dinh cua
    # Windows nem decode duoc => mat context. Dung UTF-8 + replace.
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()'''

s = io.open(P, encoding="utf-8", newline="").read()
if 'errors="replace")' in s:
    print("da co encoding=utf-8")
    sys.exit(0)
if OLD not in s:
    print("FAIL: khong tim thay cli()")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(OLD, NEW, 1))
print("da sua decode sang UTF-8")
