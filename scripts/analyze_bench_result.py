# -*- coding: utf-8 -*-
"""
analyze_bench_result.py - phan tich ket qua bench GUI (B15/B15.5/B16) theo 1
format, de so sanh cac recipe (v18 / v21 / v22 / v23a) bang cung tieu chi.

Dung:
    python scripts/analyze_bench_result.py phase13-gui/out_bench_v21/b15_result.json
    python scripts/analyze_bench_result.py <a.json> --baseline <b.json>

Bao cao:
  1. tong quan (n, wins, win_rate) + by_task
  2. mode distribution (action / legacy / none)
  3. COMMIT RATE  = step co action hop le / tong step   (do model co "commit" khong)
  4. STUCK RATE   = episode lap >= 3 lan cung mot action  (theo GLM)
  5. P(DONE) theo nguon du lieu (gom episode DUNG: theo field episode, hoac
     suy tu TEN FILE cho gui-traj)
  6. failure clusters (cung 10 cum cua TASK-17)
  7. so sanh voi baseline (neu co --baseline)
ASCII-only source.
"""
import argparse
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

MULTI_TASKS = {"T01_signup", "T02_login", "T05_shortcut", "T06_tabcode",
                "T07_scroll", "T08_errorfix", "T12_pagecode",
                "T13_wizard", "T14_alerts", "T15_dialog", "T16_clipboard2",
                "T17_reorder", "T18_countsubmit", "T19_wizardsum",
                "T21_hiddenval", "T22_keynav", "T23_undoredo",
                "T24_multifilter", "T26_distractorlist"}


def load(p):
    return json.load(io.open(p, encoding="utf-8", errors="replace"))


def ep_key(r, src):
    """Key episode DUNG.

    - Data sinh boi MiMo (gen_synth_*) co field 'episode' + 'family' -> dung.
    - gui-traj KHONG co field episode: episode = (task, viewport, variant),
      va moi row la MOT BUOC cua episode. Key phai bo hau toan "_sMM"
      (buoc) - giu "_vNN_sMM" se GOM NHAM cac task khac nhau
      (da sai: 127 ep/30,7% thay vi 216 ep/27,8%).
    """
    if r.get("episode") is not None and (r.get("family") or r.get("src")):
        return (src, r.get("family"), r.get("episode"))
    im = os.path.basename(r.get("image") or "")
    stem = os.path.splitext(im)[0]        # bo duoi .png truoc
    m = re.match(r"^(.*)_s\d+$", stem)     # roi bo "_sMM" (buoc)
    key = m.group(1) if m else stem
    return (src, key)


def analyze(path):
    d = load(path)
    eps = d.get("episodes") or []
    out = {"path": path, "suite": d.get("suite"), "n": len(eps),
           "wins": 0, "by_task": {}, "modes": Counter(), "steps": 0,
           "none": 0, "stuck": 0, "stuck_fail": 0, "stuck_fail_eps": 0,
           "clusters": Counter(),
           "multi_wins": 0, "multi_n": 0, "p_done": None}
    if not eps:
        out["error"] = d.get("error") or d.get("msg") or "no episodes"
        return out
    out["wins"] = sum(1 for e in eps if e.get("win"))
    byt = defaultdict(lambda: [0, 0])
    for e in eps:
        byt[e["task_id"]][1] += 1
        if e.get("win"):
            byt[e["task_id"]][0] += 1
        tr = e.get("trace") or []
        for s in tr:
            out["modes"][s.get("mode") or "?"] += 1
        acts = [str(s.get("act") or "") for s in tr]
        out["steps"] += len(tr)
        out["none"] += sum(1 for a in acts if a.upper() in ("", "NONE"))
        # stuck: >=3 lan cung mot action
        is_stuck = (len(acts) >= 3 and
                    len(set(a for a in acts if a)) <= max(1, len(acts) // 3))
        if is_stuck:
            out["stuck"] += 1
            # dinh nghia moi (22/10, theo @GLM): chi tinh stuck tren ep FAIL
            # (ep thang 100% nhung bi flag stuck la tin hieu sai)
            if not e.get("win"):
                out["stuck_fail"] += 1
                out["stuck_fail_eps"] += 1
        if e["task_id"] in MULTI_TASKS:
            out["multi_n"] += 1
            if e.get("win"):
                out["multi_wins"] += 1
        if not e.get("win"):
            for c in clusters_of(e):
                out["clusters"][c] += 1
    out["by_task"] = {k: "%d/%d" % tuple(v) for k, v in sorted(byt.items())}
    out["commit_rate"] = (out["steps"] - out["none"]) / max(1, out["steps"])
    out["stuck_rate"] = out["stuck"] / max(1, len(eps))
    out["stuck_fail_rate"] = out["stuck_fail"] / max(1, out["stuck_fail_eps"])
    return out


def clusters_of(e):
    tr = e.get("trace") or []
    acts = [str(s.get("act") or "") for s in tr]
    modes = [s.get("mode") or "?" for s in tr]
    reason = e.get("reason") or ""
    st = e.get("state") or {}
    failed = [k for k, v in (st.get("tests") or {}).items() if not v]
    out = []
    if any(m == "none" for m in modes):
        out.append("C1_no_action")
    if len(acts) >= 3 and len(set(a for a in acts if a)) <= max(1, len(acts) // 3):
        out.append("C2_stuck_repeat")
    if any("matches note" in f for f in failed) or any("== code" in f for f in failed) \
            or any("== source" in f for f in failed) or any("== shown code" in f for f in failed):
        out.append("C3_misread_text")
    if any("submitted" in f for f in failed) or any("correct flag" in f for f in failed) \
            or any("saved" in f for f in failed) or any("confirmed" in f for f in failed):
        out.append("C4_no_submit")
    if any("paste" in f for f in failed) or any("copy" in f for f in failed):
        out.append("C5_clipboard")
    if any("scrolled" in f for f in failed) or any("last item" in f for f in failed):
        out.append("C6_scroll")
    if any("passwords match" in f for f in failed) or any("terms checked" in f for f in failed):
        out.append("C7_form")
    if any("errors were shown" in f for f in failed) or any("valid submit" in f for f in failed):
        out.append("C8_errorfix")
    if any("value == target" in f for f in failed) or any("dataset value" in f for f in failed):
        out.append("C9_slider")
    return out or ["C0_other"]


def p_done_of(traj_path):
    """P(DONE) cua mot nguon du lieu. TRA VE CA HAI chi so (semantic khac nhau):

      row_done / n_rows   = "%row la DONE"  <-- CAI MODEL THUC SU THAY KHI TRAIN
      ep_done  / n_eps    = "%episode ket thuc bang DONE" (gom episode theo
                            (task, viewport, variant) bo hau toan "_sMM")
      Voi data 1-action (gui-traj goc) HAI so nay KHAC NHAU va deu dung nghia
      rieng - dung nham nham.
    """
    if not traj_path or not os.path.exists(traj_path):
        return None
    rows = [json.loads(l) for l in io.open(traj_path, encoding="utf-8") if l.strip()]
    row_done = sum(1 for r in rows
                   if str(r.get("action") or "").strip().upper() == "DONE")
    eps = defaultdict(list)
    for r in rows:
        eps[ep_key(r, "src")].append(r)
    ep_done = sum(1 for v in eps.values()
                  if any(str(x.get("action") or "").strip().upper() == "DONE"
                         for x in v))
    return {"rows": len(rows), "row_done": row_done,
            "eps": len(eps), "ep_done": ep_done}


def show(o, label):
    print("=" * 72)
    print("%s :: %s" % (label, o["path"]))
    if o.get("error"):
        print("   ERROR: %s" % o["error"])
        return
    print("   suite=%s  n=%d  wins=%d (%.1f%%)" %
          (o["suite"], o["n"], o["wins"], 100.0 * o["wins"] / max(1, o["n"])))
    print("   modes      : %s" % dict(o["modes"]))
    print("   COMMIT RATE: %.1f%%  (%d step, %d khong commit)" %
          (100 * o["commit_rate"], o["steps"], o["none"]))
    print("   STUCK RATE : %.1f%%  (%d episode lap >=3 lan cung 1 action)" %
          (100 * o["stuck_rate"], o["stuck"]))
    print("   STUCK(FAIL): %.1f%%  (%d/%d episode FAIL bi lap)" %
          (100 * o["stuck_fail_rate"], o["stuck_fail"], o["stuck_fail_eps"]))
    if o["multi_n"]:
        print("   win o task NHIEU BUOC: %d/%d (%.1f%%)" %
              (o["multi_wins"], o["multi_n"], 100.0 * o["multi_wins"] / o["multi_n"]))
    print("   by_task    : %s" % o["by_task"])
    print("   clusters   : %s" % dict(sorted(o["clusters"].items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--traj", default=None,
                    help="nguon du lieu de tinh P(DONE) (vd out_traj/traj.jsonl)")
    a = ap.parse_args()
    o = analyze(a.result)
    show(o, "RESULT")
    if a.traj:
        pd = p_done_of(a.traj)
        if pd:
            print("\nP(DONE) cua %s" % a.traj)
            print("   [A] %%row la DONE (cai model THUC SU thay khi train) : %d/%d = %.1f%%"
                  % (pd["row_done"], pd["rows"],
                     100.0 * pd["row_done"] / max(1, pd["rows"])))
            print("   [B] %%episode ket thuc bang DONE (gom theo task+variant): %d/%d = %.1f%%"
                  % (pd["ep_done"], pd["eps"],
                     100.0 * pd["ep_done"] / max(1, pd["eps"])))
            print("   -> [A] va [B] KHAC NHAU khi nguon du lieu la 1-action (moi row la 1 cap doc lap).")
    if a.baseline:
        b = analyze(a.baseline)
        show(b, "BASELINE")
        if not (o.get("error") or b.get("error")):
            print("=" * 72)
            print("DELTA (result - baseline)")
            print("   win_rate     : %+.1f điểm" %
                  (100.0 * (o["wins"] / o["n"] - b["wins"] / b["n"])))
            print("   commit_rate  : %+.1f điểm" %
                  (100 * (o["commit_rate"] - b["commit_rate"])))
            print("   stuck_rate   : %+.1f điểm" %
                  (100 * (o["stuck_rate"] - b["stuck_rate"])))
            print("   clusters     :")
            keys = sorted(set(o["clusters"]) | set(b["clusters"]))
            for k in keys:
                dv = o["clusters"].get(k, 0) - b["clusters"].get(k, 0)
                if dv:
                    print("      %-16s %+d" % (k, dv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
