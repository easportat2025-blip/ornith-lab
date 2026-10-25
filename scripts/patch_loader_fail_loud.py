# -*- coding: utf-8 -*-
"""patch_loader_fail_loud.py - loader im lang BO QUA row khong resolve duoc anh
(de xuat cua @MiMo): dataset/upload sai -> train rut bot ma khong ai biet.
Sua: neu co row khong resolve -> raise SystemExit (fail loud).
Ap dung: kernel_v22 + kernel_v23 (+ kernel_v21 de tuong xung).
"""
import io

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
    # FAIL LOUD (de xuat cua @MiMo): row khong resolve duoc anh = dataset
    # upload sai layout (Kaggle bo qua thu muc con!) -> NUOC IM LANG, mat data.
    if len(out) < len(rows):
        raise SystemExit(
            "FAIL: %d/%d row khong resolve duoc anh o dataset '%s' "
            "(sai layout? thieu anh? Kaggle bo qua thu muc con khi upload) "
            "- KHONG train tiep" % (len(rows) - len(out), len(rows), substr))
    log(f"{substr}: {len(out)}/{len(rows)} rows ({fname})")
    return out'''

for p in ["phase13-gui/kernel_v23/gui_sft_v23.py",
          "phase13-gui/kernel_v22/gui_sft_v22.py",
          "phase13-gui/kernel_v21/gui_sft_v21.py"]:
    try:
        s = io.open(p, encoding="utf-8").read()
    except Exception as e:
        print("skip", p, e)
        continue
    o = s
    s = s.replace(OLD, NEW)
    if s != o:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("patched (fail-loud)", p)
    else:
        print("khong doi", p)
