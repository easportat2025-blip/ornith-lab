# -*- coding: utf-8 -*-
"""
cmp_cells.py - so 2+ ket qua cung MOT cell (cung model + cung task) de tim
task "flaky" (ket qua lap khong ong dinh).

Y do: cung model (do_sample=False => greedy) + cung task (khong random) van
cho 2 task lat co trong 2 lan chay => khac biet o ENV (pixel/cai dat) =>
=> so SANH PAI THEO TASK (co bang), KHONG so tong win_rate (gop task lai
=> 2 task lat bien mat trong nhieu).

Dung:
    python scripts/cmp_cells.py <a.json> <b.json> [...]
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(p):
    d = json.load(io.open(p, encoding="utf-8", errors="replace"))
    eps = d.get("episodes") if isinstance(d, dict) else d
    out = {}
    for e in (eps or []):
        t = e.get("task_id") or "?"
        won = 1 if (e.get("win") or e.get("success")) else 0
        out.setdefault(t, [0, 0])
        out[t][0] += 1
        out[t][1] += won
    n = sum(v[0] for v in out.values())
    w = sum(v[1] for v in out.values())
    return out, n, w


def main():
    if len(sys.argv) < 3:
        print("dung: python scripts/cmp_cells.py <a.json> <b.json> [...]")
        return 2
    cells = []
    for p in sys.argv[1:]:
        try:
            cells.append((p,) + load(p))
        except Exception as e:
            print("   %s -> LOI %s" % (p, e))
    if len(cells) < 2:
        return 2
    print("SO SANH %d lan chay CUNG 1 CELL" % len(cells))
    for p, _t, n, w in cells:
        print("   %-52s %d/%d = %.1f%%" % (os.path.basename(os.path.dirname(p)),
                                           w, n, 100.0 * w / max(n, 1)))
    tasks = sorted(set(t for _p, tt, _n, _w in cells for t in tt))
    print("-" * 78)
    print("   %-22s %s" % ("task", "  ".join("cell%d" % (i + 1)
                                            for i in range(len(cells)))))
    flaky = []
    for t in tasks:
        vals = []
        for _p, tt, _n, _w in cells:
            c, wn = tt.get(t, (0, 0))
            vals.append("%d/%d" % (wn, c))
        line = "   %-22s %s" % (t, "  ".join(vals))
        if len(set(vals)) > 1:
            line += "   <== KHAC"
            flaky.append(t)
        print(line)
    print("-" * 78)
    print("=> TASK KHAC GIUA 2 LAN CHAY: %s"
          % (", ".join(flaky) if flaky else "(khong co)"))
    print("=> y nghia: cung model+cung task => nhiu ENV (flaky); "
          "khac model => model that tot hon tren task do")
    print("=> nen so SANH THEO TASK (paired); tong win_rate se an mat "
          "thay doi tren tung task")
    return 0


if __name__ == "__main__":
    sys.exit(main())
