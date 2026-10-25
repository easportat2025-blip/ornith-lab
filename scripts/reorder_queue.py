# -*- coding: utf-8 -*-
# reorder_queue.py - dua len dau cac muc GPU quan trong (train), smoke CPU xuong sau
import io
import json

P = "scripts/gpu_queue.json"
q = json.load(io.open(P, encoding="utf-8"))


def prio(i):
    k = i.get("id", "")
    if "sft-v23" in k:
        return 0
    if "desktop-bench" in k:
        return 3
    if "bench-v22" in k or "v22-old" in k:
        return 1
    if "smoke" in k:
        return 9
    return 2


q.sort(key=prio)
json.dump(q, io.open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("thu tu moi (A):")
for i in q[:10]:
    print("   %-44s p=%d" % (i["id"].split("/")[-1], prio(i)))
