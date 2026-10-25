"""check_bench_w1_w2.py - TU TINH TIEU CHI W1 (do kho) + W2 (nang luc) cho
1 bo bench (GLM, 22/10, theo PLAN.md muc W1/W2).

W1 (do kho - 6 tieu chi, thieu 1 = khong duoc dung lam chuan):
  1. model MANH NHAT trượt <= 20% (muc tieu <= 10%)
  2. model VUA DUOC TRAIN trượt <= 30%
  3. baseline yeu (v18) trượt <= 10%
  4. DO KHO TANG THAT: win(model manh nhat, bo CU) / win(model manh nhat, bo MOI)
     >= 3 (muc tieu >= 5)
  5. khong ro di dap an (0 task lo man hinh)  -> can review thu cong + heuristic
  6. >= 1/3 task la "bay" (loop-recovery / read-before-act / nhieu buoc)
W2 (bang nang luc): moi nang luc >= 1 task (ghi tag trong tasks.json / TASK_TABLE)

Dung:
  python phase13-gui/check_bench_w1_w2.py --new phase13-gui/out_bench_v22/b15_result.json \
      --old phase13-gui/out_bench_v21/b15_result.json \
      --trained phase13-gui/out_bench_v155_v22/b15_result.json \
      --baseline-v18 phase13-gui/out_bench_v18_think0/b15_result.json
  # bo --trained/--baseline-v18/--old neu chua co (chi do duoc phien co)
"""
import argparse
import collections
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# nang luc W2 (theo PLAN) + nang luc ap dung cho desktop (3D = N/A)
W2_ALL = ["read_before_act", "multi_step", "loop_recovery", "error_recovery",
          "clipboard", "keyboard_nav", "scroll", "distractor", "grounding_3d",
          # 2 verb MOI (B17, 24/10): MOVE (hover) + DRAG (keo slider) - truoc day
          # 2 verb nay CHUA TON TAI trong data train (47 buoc SCROLL cua model la
          # "menh lenh ngoai data") => can task do dat.
          "move", "drag"]
W2_DESKTOP = ["read_before_act", "multi_step", "loop_recovery", "error_recovery",
               "clipboard", "keyboard_nav", "scroll", "distractor",
               "move", "drag"]
TRAP_CAPS = {"loop_recovery", "read_before_act", "multi_step"}
CAPS_JSON = os.path.join(HERE, "web_task_caps.json")


def load_caps_map():
    try:
        d = json.load(io.open(CAPS_JSON, encoding="utf-8"))
        return {k: v for k, v in d.items() if not k.startswith("_")}
    except Exception:
        return {}


def load_result(p):
    if not p or not os.path.isfile(p):
        return None
    try:
        d = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None
    eps = d.get("episodes") or []
    n = len(eps)
    win = sum(1 for e in eps if e.get("win"))
    return {"path": p, "n": n, "win": win,
            "rate": (win / n) if n else 0.0,
            "by_task": collections.Counter(e.get("task_id") for e in eps if e.get("win")),
            "tasks": set(e.get("task_id") for e in eps),
            "raw": d}


def cap_table(d, desktop):
    """Bang nang luc: tu by_capability (desktop_result) hoac tu TASK_TABLE (bench)."""
    if d is None:
        return {}, []
    bc = d.get("by_capability")
    if bc:
        out = {}
        for k, c in bc.items():
            out[k] = {"tasks": c.get("n_tasks", 0), "ep": c.get("ep", 0),
                      "win": c.get("win", 0)}
        return out, []
    # bench web: dung map nang luc (web_task_caps.json) + ket qua theo task
    cmap = load_caps_map()
    out = {}
    eps = d.get("episodes") or []
    for e in eps:
        tid = e.get("task_id")
        for c in cmap.get(tid) or []:
            cc = out.setdefault(c, {"tasks": set(), "ep": 0, "win": 0})
            cc["tasks"].add(tid)
            cc["ep"] += 1
            if e.get("win"):
                cc["win"] += 1
    for c in out.values():
        c["n_tasks"] = len(c["tasks"])
        c["tasks"] = sorted(c["tasks"])
    return out, []


def _caps_of(cap, task_id):
    """Cac nang luc cua 1 task (tu bang nang luc da tinh)."""
    out = []
    for c, v in (cap or {}).items():
        ts = v.get("tasks") or []
        if task_id in ts:
            out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True, help="result cua bo MOI (model manh nhat)")
    ap.add_argument("--old", default=None, help="result cua bo CU (cung model)")
    ap.add_argument("--trained", default=None, help="result model vua train tren bo moi")
    ap.add_argument("--baseline-v18", default=None, help="result v18 tren bo moi")
    ap.add_argument("--desktop", action="store_true", help="bo desktop (3D = N/A)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    new = load_result(a.new)
    if not new:
        print("[w1] khong doc duoc: %s" % a.new)
        return 2
    old = load_result(a.old) if a.old else None
    trained = load_result(a.trained) if a.trained else None
    v18 = load_result(a.baseline_v18) if a.baseline_v18 else None

    rows = []
    def add(no, name, thr, val, unit="%", ok=None, note=""):
        rows.append((no, name, thr, val, unit, ok, note))

    # --- W1 ---
    add("W1.1", "model manh nhat trượt", "<= 20% (muc tieu <=10%)",
        100 * new["rate"], ok=(new["rate"] <= 0.20))
    if trained:
        add("W1.2", "model vua train trượt", "<= 30%",
            100 * trained["rate"], ok=(trained["rate"] <= 0.30))
    else:
        add("W1.2", "model vua train trượt", "<= 30%", None,
            ok=None, note="CHUA DO (can GPU)")
    if v18:
        add("W1.3", "baseline v18 trượt", "<= 10%",
            100 * v18["rate"], ok=(v18["rate"] <= 0.10))
    else:
        add("W1.3", "baseline v18 trượt", "<= 10%", None, ok=None,
            note="CHUA DO (can GPU)")
    if old and old["n"] and new["n"]:
        hard = (old["rate"] / new["rate"]) if new["rate"] > 0 else 999
        add("W1.4", "do kho tang (cu/moi)", ">= 3x (muc tieu >= 5x)", hard, "x",
            ok=(hard >= 3.0),
            note="cu %.1f%% -> moi %.1f%%" % (100 * old["rate"], 100 * new["rate"]))
    else:
        add("W1.4", "do kho tang (cu/moi)", ">= 3x (muc tieu >= 5x)", None, "x",
            ok=None, note="CHUA DO (can ket qua cua bo CUNG)")
    add("W1.5", "khong ro di dap an", "0 task lo dap an", None, ok=None,
        note="can REVIEW thu cong (heuristic: instruction co chua gia tri? xem duoi)")
    # W1.6: trap tasks
    cap, _ = cap_table(new.get("raw"), a.desktop)
    n_task = len(new["tasks"]) or 1
    if cap:
        n_trap = len([t for t in new["tasks"]
                      if any(c in TRAP_CAPS for c in _caps_of(cap, t))])
        frac = n_trap / max(len(new["tasks"]), 1)
        add("W1.6", "co 'bay' (loop/read/nhieu buoc)", ">= 1/3 task",
            100 * frac, ok=(frac >= 1.0 / 3.0),
            note="%d/%d task la bay" % (n_trap, len(new["tasks"])))
    else:
        add("W1.6", "co 'bay' (loop/read/nhieu buoc)", ">= 1/3 task",
            None, ok=None, note="CHUA TINH (thieu map nang luc)")

    # --- W2 ---
    want = W2_DESKTOP if a.desktop else W2_ALL
    cov = []
    miss = []
    for w in want:
        hit = [k for k in cap if w in k or k in w]
        if hit:
            cov.append("%s(%s)" % (w, ",".join(sorted(hit))))
        else:
            miss.append(w)

    out = ["# W1 / W2 - %s" % os.path.basename(a.new), "",
           "## W1 (do kho)", "",
           "| # | tieu chi | nguong | gia tri | ket qua | ghi chu |",
           "|---|---|---|---|---|---|"]
    for no, name, thr, val, unit, ok, note in rows:
        v = ("%.1f%s" % (val, unit)) if isinstance(val, (int, float)) else "-"
        st = "PASS" if ok else ("FAIL" if ok is False else "CHUA DO")
        out.append("| %s | %s | %s | %s | %s | %s |" %
                   (no, name, thr, v, st, note))
    out += ["", "## W2 (bang nang luc)", "",
            "| nang luc | trang thai |", "|---|---|"]
    for c in cov:
        out.append("| %s | CO |" % c)
    for m in miss:
        out.append("| %s | **THIEU** |" % m)
    if not cap:
        out.append("| (khong co bang nang luc trong result) | can them tag |")
    out += ["", "## GHI CHU", "",
            "- W1.5 (khong ro dap an) **luon can review thu cong** - tool khong the tu chung minh.",
            "- Chi so so sanh duoc giua CUNG mot bo task: ket qua tren bo da sua task "
            "khong so truc tiep voi bo cu.",
            "- W1.4 can ket qua cua bo CU voi CUNG model mau + cung so episode.",
            "- `win_rate` do bang TRANG THAI APP CUOI (khong phai reward tung buoc) "
            "=> luon bao cao them loop/stuck_rate.",
            ""]
    md = "\n".join(out)
    print(md)
    if a.out:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
        print("[w1] ghi %s" % a.out)
    fails = [r for r in rows if r[5] is False]
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
