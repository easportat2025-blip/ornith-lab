# -*- coding: utf-8 -*-
"""use_v23b.py - chuyen sang kernel v23b (ban cua @GLM: rebalance + module
S9/S10 cho 2 chu ky lap) + them guard fail-loud (de xuat @MiMo) + dua vao queue A.
"""
import io
import json
import os
import shutil

SRC = "phase13-gui/kernel_v23b"
DST = "phase13-gui/kernel_v23"
V23B = "phase13-gui/kernel_v23b"

OLD = '''    out = []
    for r in rows:
        p = _resolve(r["image"])
        if p:
            r = dict(r)
            r["image"] = p
            out.append(r)
    log(f"{substr}: {len(out)}/{len(rows)} rows ({fname})")
    return out'''
NEW = '''    out = []
    for r in rows:
        p = _resolve(r["image"])
        if p:
            r = dict(r)
            r["image"] = p
            out.append(r)
    # FAIL LOUD (de xuat cua @MiMo): row khong resolve duoc anh = dataset upload
    # sai layout (Kaggle bo qua thu muc con) -> mat data ma khong ai biet.
    if len(out) < len(rows):
        raise SystemExit(
            "FAIL: %d/%d row khong resolve duoc anh o dataset '%s' "
            "(sai layout? thieu anh?) - KHONG train tiep"
            % (len(rows) - len(out), len(rows), substr))
    log(f"{substr}: {len(out)}/{len(rows)} rows ({fname})")
    return out'''

# 1) lay code v23b + them guard
code_p = os.path.join(V23B, "gui_sft_v23.py")
s = io.open(code_p, encoding="utf-8").read()
if OLD in s:
    s = s.replace(OLD, NEW)
    print("them guard fail-loud vao v23b")
else:
    print("v23b: da co guard hoac khong khop")
io.open(os.path.join(V23B, "gui_sft_v23.py"), "w", encoding="utf-8",
        newline="\n").write(s)

# 2) metadata: id moi + dung dataset (traj R2 phai co anh phang)
md = json.load(io.open(os.path.join(V23B, "kernel-metadata.json"),
                       encoding="utf-8"))
print("v23b id:", md.get("id"), "| datasets:", len(md.get("dataset_sources", [])))
md["id"] = "khoadangnguye/ornith-gui-sft-v23b"
md["title"] = "ornith-gui-sft-v23b"
json.dump(md, io.open(os.path.join(V23B, "kernel-metadata.json"), "w",
                      encoding="utf-8"), ensure_ascii=False, indent=1)

# 3) queue A: doi muc sft-v23 -> sft-v23b
p = "scripts/gpu_queue.json"
q = json.load(io.open(p, encoding="utf-8"))
for i in q:
    if i.get("id") == "khoadangnguye/ornith-gui-sft-v23":
        i["id"] = "khoadangnguye/ornith-gui-sft-v23b"
        i["dir"] = V23B
        i["note"] = ("train v23b (GLM: rebalance + S9/S10 2 chu ky lap; "
                     "DeepSeek: guard fail-loud)")
json.dump(q, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("queue A:", [i["id"].split("/")[-1] for i in q][:8])
