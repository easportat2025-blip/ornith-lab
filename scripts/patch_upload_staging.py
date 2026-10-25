# -*- coding: utf-8 -*-
"""
patch_upload_staging.py - 2 fix trong upload_staging.py:
 (1) READY check: dung 'kaggle datasets FILES' thay 'datasets status'
     (status tra 403/404 khi dataset dang processing => false negative =>
      vong 40 lan la => FAIL gia)
 (2) loi int(slug) khi verify (slug co dau '/' -> int() nem loi)
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "upload_staging.py")

s = io.open(P, encoding="utf-8", newline="").read()
n = 0

# (1) READY: status -> files
if "datasets\", \"status\"" in s or '"datasets", "status"' in s:
    s = s.replace('"datasets", "status"', '"datasets", "files"')
    s = s.replace('\\"datasets\\", \\"status\\"', '\\"datasets\\", \\"files\\"')
    n += 1
    print("   (1) status -> files")

# (2) int(slug)
if "int(" in s and "slug" in s:
    import re
    m = re.search(r"int\(([^)]*slug[^)]*)\)", s)
    if m:
        print("   (2) tim thay int(slug): %s" % m.group(0)[:60])

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("=> %d nhom sua" % n)
