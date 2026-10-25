"""space_logs.py - tai log runtime/build cua HF Space (dung file, tranh loi regex
PowerShell).

Dung: python scripts/space_logs.py <owner/slug> [runtime|build] [n]
"""
import os
import re
import sys
import urllib.request

slug = sys.argv[1]
ep = sys.argv[2] if len(sys.argv) > 2 else "runtime"
n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
tok = os.environ.get("HF_TOKEN", "")
h = {"Authorization": "Bearer " + tok} if tok else {}
url = "https://huggingface.co/api/spaces/%s/logs/%s" % (slug, ep)
try:
    req = urllib.request.Request(url, headers=h)
    d = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
except Exception as e:
    print("LOI:", e)
    raise SystemExit(1)
lines = []
for l in d.splitlines():
    m = re.search(r'"data":"(.*?)","timestamp"', l)
    if m:
        lines.append(m.group(1))
print("== %s (%d dong)" % (ep, len(lines)))
for x in lines[-n:]:
    print("  ", x[:200])
