"""rollout_curate.py - bien rollout_bundle.zip thanh du lieu SFT self-play.

TASK-18: rollout v1 chi giu episode WIN -> 0 dong khi model chua win. Kernel moi
(rollout v2/base) giu TAT CA step + nhan win / n_fail_checks / n_checks.
Quy trinh (MAIN_QUEST §3):
  1. Doc rollout_rows.jsonl tu bundle.
  2. Chon:
     - episode WIN: giu moi step (bo action lap lien tiep - model hay loop).
     - episode FAIL gan (n_fail_checks <= --max-fail): giu step TRUOC step cuoi
       (step cuoi chinh la action sai) + bo action lap.
  3. Dedupe (task_id, variant, step, action).
  4. Xuat 2 format:
     - traj.jsonl        : format recipe v18 (target = DONG ACTION) -> v21 dung
     - traj_reason.jsonl: format reasoning (think + action) -> thu nghiem sau
  5. shots.zip (chi anh duoc dung) + dataset-metadata.json (hhjiji/gui-selfplay)

Chay: python phase13-gui/rollout_curate.py [--bundle ...] [--cap 600] [--max-fail 2]
"""
import argparse
import io
import json
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEF_BUNDLE = os.path.join(HERE, "out_rollout", "rollout_bundle.zip")
THINK_RX = re.compile(r"^\s*THINK\s*:", re.I)
ACTION_RX = re.compile(r"^\s*(?:CLICK|TYPE|KEY|DONE)\b", re.I)


def extract_think(target):
    lines = [l.rstrip() for l in (target or "").splitlines() if l.strip()]
    think = [l for l in lines if THINK_RX.match(l)]
    if think:
        return "\n".join(think).strip()
    # khong co dong THINK: -> lay prose truoc dong action (reasoning cua model)
    prose = []
    for l in lines:
        if ACTION_RX.match(l):
            break
        prose.append(l)
    return "\n".join(prose).strip()


def load_bundle(path):
    if path.endswith(".zip") and os.path.exists(path):
        z = zipfile.ZipFile(path)
        txt = z.read("rollout_rows.jsonl").decode("utf-8")
        rows = [json.loads(l) for l in txt.splitlines() if l.strip()]
        summary = None
        try:
            summary = json.loads(z.read("rollout_summary.json").decode("utf-8"))
        except Exception:
            pass
        return rows, summary, z
    p = path if path.endswith(".jsonl") else os.path.join(
        os.path.dirname(path), "rollout_rows.jsonl")
    rows = [json.loads(l) for l in io.open(p, encoding="utf-8") if l.strip()]
    return rows, None, None


MASKED_RX = re.compile(r'^[\s\.\*\u2022\u00b7]+$')


def select(rows, max_fail, exclude_variants=()):
    """Chon row theo uu tien: WIN truoc, FAIL gan sau; bo action lap lien tiep.

    Bo them (TASK-20, chot sau khi soi data rollout thuc):
      - episode LOOP: <=2 action phan biet (model ket 2 toa do) -> bo ca episode
        (train vao se KHONG day them cai loop).
      - TYPE giu chu che (dots/asterisk/bullet) -> model doc nham mat khau ->
        bo row do.
      - 1 action lap >2 lan trong episode -> giu lai 1 lan.
    """
    eps = {}
    for r in rows:
        key = (r.get("task_id"), r.get("variant"), r.get("rep"))
        eps.setdefault(key, []).append(r)
    keep = []
    n_dup_step = 0
    n_drop_last = 0
    n_loop_ep = 0
    n_masked = 0
    n_repeat = 0
    for key, rs in eps.items():
        if key[1] in exclude_variants:
            continue
        rs.sort(key=lambda r: r.get("step") or 0)
        win = bool(rs[0].get("win"))
        nfail = rs[0].get("n_fail_checks")
        if nfail is None:
            nfail = 99
        if not win and nfail > max_fail:
            continue
        acts = [(r.get("action") or "").strip() for r in rs]
        # loop detection: so o toa do (bucket 50 don vi) + verb, khong so
        # chuoi chinh xac (model doi 1-2 don vi cung la 1 cho)
        buckets = set()
        for a in acts:
            m = re.match(r'^CLICK\s+(\d+)\s+(\d+)$', a, re.I)
            if m:
                buckets.add(("CLICK", int(m.group(1)) // 50, int(m.group(2)) // 50))
            elif a:
                buckets.add((a.split()[0].upper(),))
        if not win and len(buckets) <= 2 and len(rs) >= 3:
            n_loop_ep += 1
            continue
        seen_act = {}
        prev = None
        # FIX (review GLM A2): "bo step cuoi cua episode fail" phai so sanh
        # voi chi so ACTION CUOI, khong phai row cuoi (row cuoi co the la
        # prose -> action sai cuoi lai duoc giu lai -> train nhieu action sai).
        act_idx = [j for j, rr in enumerate(rs)
                   if (rr.get("action") or "").strip()
                   and rr.get("mode") in ("action", "legacy")]
        last_act_i = act_idx[-1] if act_idx else -1
        for i, r in enumerate(rs):
            act = (r.get("action") or "").strip()
            if not act or r.get("mode") not in ("action", "legacy"):
                continue
            if act == prev:
                n_dup_step += 1
                continue
            prev = act
            if act.upper().startswith("TYPE") and MASKED_RX.match(act[4:].strip()):
                n_masked += 1
                continue
            seen_act[act] = seen_act.get(act, 0) + 1
            if seen_act[act] > 2:
                n_repeat += 1
                continue
            if not win and i == last_act_i:
                n_drop_last += 1
                continue
            keep.append((0 if win else 1, nfail, r))
    keep.sort(key=lambda x: (x[0], x[1], x[2].get("task_id") or "",
                             x[2].get("variant") or 0, x[2].get("step") or 0))
    return [x[2] for x in keep], (n_dup_step, n_drop_last, n_loop_ep,
                                  n_masked, n_repeat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=DEF_BUNDLE)
    ap.add_argument("--cap", type=int, default=600)
    ap.add_argument("--max-fail", type=int, default=2)
    ap.add_argument("--exclude-variants", default="2",
                    help="variant bi loai khoi TRAIN de giu held-out (default 2)")
    ap.add_argument("--stage", default=os.path.join(HERE, "selfplay_dataset"),
                    help="thu muc staging dataset")
    ap.add_argument("--out-jsonl", default="gui-selfplay-d2.jsonl")
    a = ap.parse_args()
    excl = set()
    for t in (a.exclude_variants or "").split(","):
        t = t.strip()
        if t:
            excl.add(int(t))

    rows, summary, z = load_bundle(a.bundle)
    print("doc %d row tu %s" % (len(rows), a.bundle))
    if summary:
        print("summary kernel: win_rate=%.3f episodes=%s rows=%s (win=%s fail=%s)"
              % (summary.get("win_rate", -1), summary.get("episodes"),
                 summary.get("n_rows"), summary.get("n_rows_win"),
                 summary.get("n_rows_fail")))

    sel, stats = select(rows, a.max_fail, excl)
    n_dup_step, n_drop_last, n_loop_ep, n_masked, n_repeat = stats
    print("exclude variants (held-out):", sorted(excl))
    seen = set()
    kept = []
    n_dup = 0
    for r in sel:
        act = (r.get("action") or "").strip()
        key = (r.get("task_id"), r.get("variant"), r.get("step"), act)
        if key in seen:
            n_dup += 1
            continue
        seen.add(key)
        kept.append({
            "task_id": r.get("task_id"), "variant": r.get("variant"),
            "step": r.get("step"), "rep": r.get("rep"),
            "image": r["image"], "instruction": r.get("instruction", ""),
            "action": act, "think": extract_think(r.get("target")),
            "win": bool(r.get("win")),
            "n_fail_checks": r.get("n_fail_checks"),
            "n_checks": r.get("n_checks"),
            "src": "sp-base-d2",
        })
    # FIX (review GLM B3/B2): cap theo nhom (win 65% / fail 35%) de near-miss
    # khong bi cat het; n_win tinh SAU khi cat.
    win_rows = [r for r in kept if r["win"]]
    fail_rows = [r for r in kept if not r["win"]]
    cap_w = int(a.cap * 0.65)
    cap_f = max(0, a.cap - cap_w)
    kept = win_rows[:cap_w] + fail_rows[:cap_f]
    n_win = sum(1 for r in kept if r["win"])
    print("curate: giu %d (win %d / fail %d) | bo: lap-liep=%d step-cuoi-fail=%d "
          "loop-ep=%d masked=%d repeat=%d dup=%d | cap=%d max_fail=%d"
          % (len(kept), n_win, len(kept) - n_win, n_dup_step, n_drop_last,
             n_loop_ep, n_masked, n_repeat, n_dup, a.cap, a.max_fail))

    outdir = os.path.join(HERE, "selfplay")
    os.makedirs(outdir, exist_ok=True)
    out1 = os.path.join(outdir, a.out_jsonl)
    with io.open(out1, "w", encoding="utf-8", newline="\n") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("ghi", out1)

    stage = a.stage
    os.makedirs(stage, exist_ok=True)
    # format v18: target = DONG ACTION
    with io.open(os.path.join(stage, "traj.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in kept:
            fh.write(json.dumps({
                "image": r["image"], "instruction": r["instruction"],
                "action": r["action"], "task_id": r["task_id"],
                "variant": r["variant"], "step": r["step"],
                "win": r["win"], "src": r["src"],
            }, ensure_ascii=False) + "\n")
    # format reasoning (thu nghiem sau)
    with io.open(os.path.join(stage, "traj_reason.jsonl"), "w", encoding="utf-8",
                 newline="\n") as fh:
        for r in kept:
            fh.write(json.dumps({
                "image": r["image"], "instruction": r["instruction"],
                "action": r["action"], "think": r["think"],
                "task_id": r["task_id"], "variant": r["variant"],
                "step": r["step"], "win": r["win"], "src": r["src"],
            }, ensure_ascii=False) + "\n")
    n_shots = 0
    if z is not None:
        # QUAN TRONG: kaggle CLI KHONG upload file trong subdir -> phai dung zip.
        # Zip nay phai chua anh o TOP LEVEL (ten basename) va ten zip la "shots.zip"
        # -> Kaggle giai nen ra <dataset>/shots/<ten>.png, dung voi
        # traj.jsonl: "image": "shots/<ten>.png"  (resolve base/rel -> OK).
        # Neu zip chua "shots/xxx.png" -> Kaggle tao shots/shots/xxx.png -> KHONG khop.
        with zipfile.ZipFile(os.path.join(stage, "shots.zip"), "w",
                             zipfile.ZIP_DEFLATED) as zs:
            for r in kept:
                rel = r["image"]
                try:
                    data = z.read(rel)
                except KeyError:
                    print("THIEU anh:", rel)
                    continue
                zs.writestr(os.path.basename(rel), data)
                n_shots += 1
        print("shots.zip: %d anh (top-level)" % n_shots)
    # FIX (review GLM A3): id phai trung dataset that tren acc A
    # ("khoadangnguye/gui-selfplay") — kernel v22 mount chinh slug nay.
    meta = {"title": "Ornith GUI selfplay D2 (base rollout)",
            "id": os.environ.get("SELFPLAY_DATASET_ID",
                                 "khoadangnguye/gui-selfplay"),
            "licenses": [{"name": "other"}]}
    with io.open(os.path.join(stage, "dataset-metadata.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("stage %s: traj.jsonl %d + traj_reason.jsonl %d + shots.zip %d anh"
          % (stage, len(kept), len(kept), n_shots))

    per = {}
    for r in kept:
        d = per.setdefault(r["task_id"], [0, 0])
        d[0] += 1
        d[1] += 1 if r["win"] else 0
    print("row theo task (n, win):", json.dumps(per, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
