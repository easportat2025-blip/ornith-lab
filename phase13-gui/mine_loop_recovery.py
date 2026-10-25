"""mine_loop_recovery.py - dao "loop recovery spec" tu cac trace THAT BAI.

Y tuong (22/10): do tren bench-v22 cho thay **nút thắt thật là LOOP**
(model lap >=3 lan cung 1 hanh dong va khong doi chien lua), khong phai thieu
mau DONE. Muon sua thi can du lieu day "**sau khi hanh dong lap khong doi gi,
thi doi chien luwa**".

Tool nay quet 1 file ket qua (b15_result.json / desktop_result.json), tim moi
episode co LOOP, va xuat ra:
  - task, buoc bat dau loop, hanh dong bi lap, va **raw reasoning** tai buoc do
    (mo ta man hinh theo chinh model) => team dung ngay de viet "recovery" row
  - 1 bang tom tat theo task: so ep loop, hanh dong lap pho bien nhat
  - ghi ra file markdown de dua vao quy trinh sinh du lieu

Dung:
  python phase13-gui/mine_loop_recovery.py phase13-gui/out_bench_v22/b15_result.json \
      --out phase13-gui/out_bench_v22/loop_recovery_spec.md
"""
import argparse
import collections
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log(m):
    print("[mine] %s" % m, flush=True)


def steps_of(e):
    tr = e.get("trace") or []
    if tr:
        return tr
    return [{"step": s.get("step"), "act": s.get("action")}
            for s in (e.get("trajectory") or [])]


def act_of(s):
    for k in ("act", "action"):
        if s.get(k):
            return str(s[k]).strip()
    return ""


def signature(act):
    """Phan loai CHU KY LOOP (2023 du lieu that tren B15 + B15.5):
    A 'go lap trong cung 1 o'  - TYPE x lap: model khong click o ke tiep
    B 'lap 1 phim tat'         - KEY x lap: model khong lam not chuoi recipe
    C 'lap click cung toa do'  - CLICK x y lap: click khong an, lap lai
    D 'action rong (truncate)' - het token, khong parse ra hanh dong
    """
    a = (act or "").strip()
    if not a:
        return "D: action rong (truncate)", "them token khi eval / train suc tich hon"
    v = a.split()[0].upper()
    if v == "TYPE":
        return ("A: go lap trong cung 1 o",
                "sau khi go xong o nay phai CLICK o ke tiep (khong go lai o cu)")
    if v == "KEY":
        return ("B: lap 1 phim tat",
                "phai lam du chuoi phim tat (ctrl+a -> ctrl+c -> click dich -> ctrl+v)")
    if v == "CLICK":
        return ("C: lap click cung toa do",
                "click khong doi gi -> DOI chieu luwa (keo/ban phim/doi vung), khong click lai")
    return ("E: lap %s" % v, "doi muc tieu thay vi lap lai")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-repeat", type=int, default=3)
    a = ap.parse_args()
    p = os.path.abspath(a.result)
    if not os.path.isfile(p):
        log("khong thay %s" % p)
        return 1
    d = json.load(io.open(p, encoding="utf-8"))
    eps = d.get("episodes") or []
    log("%s | %d episode" % (os.path.basename(p), len(eps)))

    out = []
    out.append("# Loop recovery spec (sinh tu %s)\n" % os.path.basename(p))
    out.append("> Muc tieu: day model **doi chien lua** khi hanh dong lap khong "
               "lam doi gi. Cot 'raw tai buoc lap' la mo ta man hinh do chinh "
               "model dua ra => dung ngay lam nen cho 1 'recovery' row.\n")

    per_task = collections.defaultdict(collections.Counter)
    per_sig = collections.Counter()
    sig_fix = {}
    rows = []
    for e in eps:
        if e.get("win"):
            continue
        ss = steps_of(e)
        acts = [act_of(s) for s in ss]
        if not acts:
            continue
        c = collections.Counter(acts)
        act, k = c.most_common(1)[0]
        if k < a.min_repeat:
            continue
        first = acts.index(act)
        raw = ""
        for s in ss:
            if s.get("step") == first and s.get("raw"):
                raw = str(s["raw"])
                break
        if not raw:
            raw = str(ss[first].get("raw") or "") if ss else ""
        sig, fix = signature(act)
        per_sig[sig] += 1
        sig_fix[sig] = fix
        rows.append((e.get("task_id"), first, act, k, len(acts), raw, sig, fix))
        per_task[e.get("task_id")][act] += 1

    out.append("## 1) Tom tat theo CHU KY LOOP (loai loi can sua)\n")
    out.append("| chu ky | so ep | fix can day |")
    out.append("|---|---|---|")
    for sig, n in per_sig.most_common():
        out.append("| %s | %d | %s |" % (sig, n, sig_fix.get(sig, "")))
    out.append("")

    out.append("## 2) Tom tat theo task\n")
    out.append("| task | so ep loop | hanh dong lap pho bien nhat | so lan |")
    out.append("|---|---|---|---|")
    for t in sorted(per_task):
        act, k = per_task[t].most_common(1)[0]
        out.append("| %s | %d | `%s` | %d |" % (t, sum(per_task[t].values()),
                                                act, k))
    out.append("")

    out.append("## 3) Chi tiet tung episode loop (nguon de viet recovery row)\n")
    for t, first, act, k, n, raw, sig, fix in rows:
        out.append("### %s — buoc %d lap `%s` (%d/%d buoc) — %s" %
                   (t, first, act, k, n, sig))
        raw1 = " ".join(raw.split())[:400]
        out.append("- raw tai buoc lap: `%s`" % raw1)
        out.append("- **recovery mong doi**: %s — KHONG lap lai `%s`" % (fix, act))
        out.append("")

    md = a.out or os.path.join(os.path.dirname(p), "loop_recovery_spec.md")
    os.makedirs(os.path.dirname(os.path.abspath(md)), exist_ok=True)
    with io.open(md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    log("ghi %s (%d episode loop)" % (md, len(rows)))
    print("\n".join(out[:40]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
