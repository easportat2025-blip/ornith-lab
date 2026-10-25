"""space_status.py - xem trang thai build/runtime cua 1 HF Space + tail log.

Dung: python scripts/space_status.py <owner/slug> [--token-env HF_TOKEN]
"""
import json
import os
import re
import sys
import urllib.request

slug = sys.argv[1]
tok = os.environ.get("HF_TOKEN", "")


def get(url):
    h = {"Authorization": "Bearer " + tok} if tok else {}
    r = urllib.request.Request(url, headers=h)
    return urllib.request.urlopen(r, timeout=60).read().decode("utf-8", "replace")


d = json.loads(get("https://huggingface.co/api/spaces/" + slug))
rt = d.get("runtime", {})
print("stage:", rt.get("stage"), "| hw:", rt.get("hardware", {}).get("current"),
      "| sha:", (rt.get("sha") or "")[:8])
print("domains:", [(x.get("domain"), x.get("stage"))
                    for x in rt.get("domains", [])])
try:
    log = get("https://huggingface.co/api/spaces/%s/logs/build" % slug)
    lines = []
    for l in log.splitlines():
        m = re.search(r'"data":"(.*?)","timestamp"', l)
        if m:
            lines.append(m.group(1))
    print("--- build log (%d dong) ---" % len(lines))
    for l in lines[-14:]:
        print("  ", l[:170])
except Exception as e:
    print("build log loi:", e)
