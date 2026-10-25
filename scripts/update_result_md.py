# -*- coding: utf-8 -*-
"""update_result_md.py - cap nhat result.md (nhat ky ket qua theo ngay).

Phan "AUTO" (sinh tu dong tu du lieu that: ket qua bench + gate + train + queue)
duoc viet lai moi lan chay. Phan "NHAT KY" (ghi chu thu cong) duoc GIU NGUYEN.

Dung: python scripts/update_result_md.py [--date 2026-10-21]
"""
import io
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "result.md")
AUTO_START = "<!-- AUTO:BEGIN -->"
AUTO_END = "<!-- AUTO:END -->"
DIARY_START = "<!-- DIARY:BEGIN -->"
HIST_START = "<!-- HISTORY:BEGIN -->"
HIST_END = "<!-- HISTORY:END -->"
DIARY_END = "<!-- DIARY:END -->"

HEAD = """# KET QUA ORNITH - nhat ky theo ngay

> File nay cap nhat **tu dong** (phan AUTO) + **ghi chu thu cong** (phan NHAT KY).
> Sinh boi `scripts/update_result_md.py` - chay lai sau moi vong train/gate.
> **LUU Y: may RTX cua user KHONG co internet** -> moi thu can chuan bi offline
> (xem muc "CHAY OFFLINE" o duoi + `scripts/prepare_offline_bundle.py`).

"""


def sh(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=ROOT)
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return "ERR " + str(e)[:80]


def collect_bench():
    out = sh([sys.executable, os.path.join("scripts", "collect_results.py")])
    return out.strip()


def collect_gate():
    p = os.path.join(ROOT, "phase13-gui", "gate_results.jsonl")
    rows = []
    if not os.path.exists(p):
        return rows
    for line in io.open(p, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("verdict") in ("3D",):
            rows.append("%s | %s | %s" % (d.get("label", "?"),
                                          d.get("verdict"),
                                          json.dumps(d.get("summary_3d", {}),
                                                     ensure_ascii=False)[:90]))
        else:
            rows.append("%s | GATE %s (%d/%d) | %s" % (
                d.get("label", "?"), d.get("verdict"), d.get("npass", 0),
                d.get("ntot", 0), " ; ".join(d.get("checks", [])[:3])))
    return rows


def collect_train():
    p = os.path.join(ROOT, "phase13-gui", "out_sft_v22", "gui_result.json")
    if not os.path.exists(p):
        p2 = os.path.join(ROOT, "phase13-gui", "out_sft_v21", "gui_result.json")
        p = p2 if os.path.exists(p2) else p
    if not os.path.exists(p):
        return "chua co ket qua train"
    d = json.load(io.open(p, encoding="utf-8"))
    keys = ["acc_before", "acc_after", "acc_train_sub", "acc_targeted_sub",
            "acc_selfplay_sub", "acc_train3d_sub", "acc_traj_sub",
            "acc_real_after", "n_train", "steps", "seed", "recipe", "t_sec"]
    lines = []
    for k in keys:
        if k in d:
            v = d[k]
            lines.append("  %-20s %s" % (k, ("%.4f" % v) if isinstance(v, float)
                                         else str(v)[:100]))
    return "\n".join(lines)


def collect_queue():
    lines = []
    for f, lbl in (("scripts/gpu_queue_state.json", "A"),
                   ("scripts/gpu_queue_B_state.json", "B")):
        p = os.path.join(ROOT, f)
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        for k, v in d.items():
            if isinstance(v, dict) and k.startswith(("khoadangnguye", "dieniw")):
                lines.append("  [%s] %-44s %-9s pushed=%s" % (
                    lbl, k.split("/")[-1], v.get("status"), v.get("pushed")))
    return "\n".join(lines[:26])


def build_auto(date):
    parts = ["<!-- AUTO:BEGIN -->"]
    parts.append("## %s" % date)
    parts.append("\n### 1) Benchmark (tu dong thu thap)\n```")
    parts.append(collect_bench() or "(chua co ket qua)")
    parts.append("```")
    g = collect_gate()
    parts.append("\n### 2) Gate da cham\n```")
    parts.append("\n".join(g[-14:]) if g else "(chua co gate nao chay)")
    parts.append("```")
    parts.append("\n### 3) Lan train gan nhat (v22)\n```")
    parts.append(collect_train())
    parts.append("```")
    parts.append("\n### 4) Hang doi GPU\n```")
    parts.append(collect_queue())
    parts.append("```")
    parts.append("\n_Cap nhat luc: %s_" % time.strftime("%H:%M:%S"))
    parts.append("<!-- AUTO:END -->")
    return "\n".join(parts)


def main():
    date = None
    if "--date" in sys.argv:
        i = sys.argv.index("--date")
        date = sys.argv[i + 1]
    date = date or time.strftime("%Y-%m-%d")

    old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    diary = ""
    if DIARY_START in old and DIARY_END in old:
        a = old.index(DIARY_START) + len(DIARY_START)
        b = old.index(DIARY_END)
        diary = old[a:b].strip()

    # LUU LICH SU: phan AUTO cu (ngay khac) -> archive, giu lai thanh "## <date>"
    hist = ""
    if AUTO_START in old and AUTO_END in old:
        a = old.index(AUTO_START)
        b = old.index(AUTO_END) + len(AUTO_END)
        old_auto = old[a:b]
        m = re.search(r"##\s*(\d{4}-\d{2}-\d{2})", old_auto)
        if m and m.group(1) != date:
            # tach phan AUTO cu thanh muc ngay -> luu vao HISTORY
            body = old_auto
            body = body.replace(AUTO_START, "").replace(AUTO_END, "").strip()
            if body:
                hist = body + "\n\n"
        old = old[:a] + old[b:]

    auto = build_auto(date)
    if HIST_START in old and HIST_END in old:
        a = old.index(HIST_START) + len(HIST_START)
        b = old.index(HIST_END)
        old = old[:a] + "\n" + hist + old[a:b].strip() + old[b:]
    else:
        old = old + "\n" + HIST_START + "\n" + hist + HIST_END + "\n"
    new = old + "\n" + auto + "\n\n" + DIARY_START + "\n" + diary + "\n" + DIARY_END + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(new)
    print("result.md cap nhat (%d dong)" % len(new.splitlines()))


if __name__ == "__main__":
    main()
