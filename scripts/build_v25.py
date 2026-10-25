# -*- coding: utf-8 -*-
"""
build_v25.py - kernel v25 = v24 + du lieu 'desktop-real replay' (MiMo).

Muc tieu: VA KHOANG CACH CHUYEN DOI MOI TRUONG (web 54.2% vs desktop 13.3%).
Trien khai: them 1 nguon du lieu vao mix + them vao base_n + log + recipe.
Fail-loud: neu dataset 'desktop-replay' chua ton tai tren Kaggle -> SystemExit
som (khong ton 2.5h GPU).

Chay lai sau khi @MiMo upload xong:
    python scripts/build_v25.py
ASCII-only.
"""
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
SRC = os.path.join(P13, "kernel_v24b")
DST = os.path.join(P13, "kernel_v25b")
DS_SLUG = "dieniw/ornith-desktop-replay-v1"      # san (MiMo tao)
DS_NAME = "ornith-desktop-replay-v1"              # ten thu muc mount


def sub(s, old, new, tag):
    if old not in s:
        raise SystemExit("KHONG khop: %s\n---\n%s" % (tag, old[:220]))
    if s.count(old) != 1:
        raise SystemExit("KHONG duy nhat (%d): %s" % (s.count(old), tag))
    print("  ok: " + tag)
    return s.replace(old, new, 1)


def main():
    if not os.path.isdir(SRC):
        raise SystemExit("thieu nguon: %s" % SRC)
    if os.path.isdir(DST):
        shutil.rmtree(DST, ignore_errors=True)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns("__pycache__"))
    cp = os.path.join(DST, "gui_sft_v23.py")
    s = io.open(cp, encoding="utf-8").read()

    # 1) load du lieu desktop-replay (bat buoc -> fail-loud neu chua co)
    s = sub(s,
            '    # v24: duLieu LOOP-RECOVERY tren app THAT (@GLM 22/10) - nham 2 vong\n'
            '    # lap that su: ghi lai cung 1 field / lap 1 shortcut.\n',
            '    # v25: DU LIEU DESKTOP-REAL REPLAY (@MiMo) - va khoang cach chuyen\n'
            '    # doi moi truong (web 54.2% vs desktop 13.3%): 5 app desktop that\n'
            '    # (form / calc / table-sort / text-edit / 2048) voi GT trajectory.\n'
            '    dr_rows = load_ds_rows("__DS_NAME__", "traj.jsonl", required=True)\n'
            '    log(f"desktop-replay: {len(dr_rows)} row")\n'
            '    # v24: duLieu LOOP-RECOVERY tren app THAT (@GLM 22/10) - nham 2 vong\n'
            '    # lap that su: ghi lai cung 1 field / lap 1 shortcut.\n'.replace(
                "__DS_NAME__", DS_NAME),
            "them load desktop-replay")

    # 2) vao base_n
    s = sub(s,
            '              + len(pr_rows) + len(rec_rows))',
            '              + len(pr_rows) + len(rec_rows) + len(dr_rows))',
            "base_n += dr_rows")

    # 3) vao train_rows
    s = sub(s,
            '                  + t3d_rows + t3dh_rows + pr_rows + rec_rows + sp_rows)',
            '                  + t3d_rows + t3dh_rows + pr_rows + rec_rows\n'
            '                  + dr_rows + sp_rows)',
            "train_rows += dr_rows")

    # 4) log
    s = sub(s,
            '        f"targeted {len(tgt_rows)} + loop-recovery {len(rec_rows)}"',
            '        f"targeted {len(tgt_rows)} + loop-recovery {len(rec_rows)}"\n'
            '        f" + desktop-replay {len(dr_rows)}"',
            "log co dr_rows")

    # 5) recipe
    s = sub(s,
            '"recipe": "v24: dr0.75 + S1-S10 + R2 972 + loop-recovery 600 + '
            'policy-replay x2 + 3D 600 + selfplay"',
            '"recipe": "v25: v24 + desktop-replay + S11 (SCROLL/MOVE/DRAG) + '
            'policy-replay x2 + 3D 600 + selfplay"',
            "nhan recipe")

    # 5b) them S11 (GLM: 530 row SCROLL/MOVE/DRAG - 3 verb chua tung co trong
    #     data train) - cung kieu "gioi hanh dong" cua desktop
    s = sub(s,
            '    # v25: DU LIEU DESKTOP-REAL REPLAY (@MiMo) - va khoang cach chuyen\n'
            '    # doi moi truong (web 54.2% vs desktop 13.3%): 5 app desktop that\n'
            '    # (form / calc / table-sort / text-edit / 2048) voi GT trajectory.\n',
            '    # v25: DU LIEU DESKTOP-REAL REPLAY (@MiMo) - va khoang cach chuyen\n'
            '    # doi moi truong (web 54.2% vs desktop 13.3%): 5 app desktop that\n'
            '    # (form / calc / table-sort / text-edit / 2048) voi GT trajectory.\n',
            "vi tri load desktop-replay (giu nguyen)")
    s = sub(s,
            '    dr_rows = load_ds_rows("ornith-desktop-replay-v1", "traj.jsonl", required=True)\n'
            '    log(f"desktop-replay: {len(dr_rows)} row")\n',
            '    dr_rows = load_ds_rows("ornith-desktop-replay-v1", "traj.jsonl", required=True)\n'
            '    log(f"desktop-replay: {len(dr_rows)} row")\n'
            '    # v25b: S11 = SCROLL / MOVE / DRAG (@GLM) - 3 verb CHUA TON co\n'
            '    # trong data train (47 buoc SCROLL cua model tren desktop la\n'
            '    # "menh lenh ngoai data")\n'
            '    s11_rows = load_ds_rows("ornith-gui-synth-s11", "traj.jsonl", required=True)\n'
            '    log(f"synth-s11 (SCROLL/MOVE/DRAG): {len(s11_rows)} row")\n',
            "them load S11")
    s = sub(s, '              + len(pr_rows) + len(rec_rows) + len(dr_rows))',
            '              + len(pr_rows) + len(rec_rows) + len(dr_rows)\n'
            '              + len(s11_rows))', "base_n += s11_rows")
    s = sub(s, '                  + dr_rows + sp_rows)',
            '                  + dr_rows + s11_rows + sp_rows)', "train_rows += s11_rows")
    s = sub(s, '        f" + desktop-replay {len(dr_rows)}"',
            '        f" + desktop-replay {len(dr_rows)}"\n'
            '        f" + synth-s11 {len(s11_rows)}"', "log co s11_rows")

    io.open(cp, "w", encoding="utf-8", newline="\n").write(s)

    # 6) metadata: them dataset + doi id
    mp = os.path.join(DST, "kernel-metadata.json")
    m = json.load(io.open(mp, encoding="utf-8"))
    if DS_SLUG not in m["dataset_sources"]:
        m["dataset_sources"].append(DS_SLUG)
    m["id"] = "dieniw/ornith-gui-sft-v25"
    m["title"] = "ornith-gui-sft-v25"
    json.dump(m, io.open(mp, "w", encoding="utf-8", newline="\n"),
              ensure_ascii=False, indent=2)
    print("  ok: metadata (id=%s, %d dataset)" % (m["id"], len(m["dataset_sources"])))

    # 7) verify
    import py_compile
    py_compile.compile(cp, doraise=True)
    print("  ok: py_compile")
    checks = [
        ("v24 fixes giu nguyen (N_3D)", "N_3D = 600" in s),
        ("dr0.75 giu nguyen", "done_rate=0.75" in s),
        ("R2 khong truncate", "traj_rows[:400]" not in s),
        ("loop-recovery giu nguyen", "loop-recovery (synth-recipe)" in s),
        ("desktop-replay load", DS_NAME in s),
        ("dr_rows trong train_rows", "+ dr_rows + s11_rows + sp_rows" in s),
        ("S11 load", "ornith-gui-synth-s11" in s),
        ("s11_rows trong train_rows", "len(s11_rows)" in s),
        ("loader quet base", "os.walk(base)" in s),
    ]
    bad = 0
    for n, ok in checks:
        print("   %-28s %s" % (n, "PASS" if ok else "FAIL"))
        if not ok:
            bad += 1
    if bad:
        raise SystemExit("CO %d FAIL - khong push" % bad)
    print("\nSAN SANG (nhan dataset %s truoc khi push)" % DS_SLUG)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
