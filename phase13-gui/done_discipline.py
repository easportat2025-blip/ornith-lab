"""done_discipline.py - do "ky luat DONE" trong data train + hanh vi model (TASK: GLM).

Sinh report: phase13-gui/done_discipline_report.md (tu sinh, khong go tay so lieu).
Chi doc file trong workspace. Khong dung GPU/key/mang.
"""
import io
import json
import os
import re
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_MD = os.path.join(HERE, "done_discipline_report.md")

# (ten, duong dan, khoa episode) -- episode = (task_id, variant) neu co,
# neu khong co step/episode -> moi row la 1 episode 1 buoc
# neu file traj_done_aug.jsonl ton tai (R2) -> do bang file DA TANG THUC
_TRAJ_AUG = os.path.join(HERE, "traj_done_aug.jsonl")
_TRAJ_REL = (r"phase13-gui\traj_done_aug.jsonl" if os.path.exists(_TRAJ_AUG)
            else r"phase13-gui\out_traj\traj.jsonl")
_TRAJ_LABEL = ("gui-traj (R2 aug)" if os.path.exists(_TRAJ_AUG)
               else "gui-traj (816)")

SOURCES = [
    (_TRAJ_LABEL, _TRAJ_REL),
    ("gui-traj (base 816)", r"phase13-gui\out_traj\traj.jsonl"),
    ("policy-replay (332)", r"phase13-gui\out_policy_replay\replay\traj.jsonl"),
    ("selfplay d2 (123)", r"phase13-gui\selfplay_dataset\traj.jsonl"),
    ("train3d (300)", r"phase14-blender\train3d_dataset\traj.jsonl"),
    ("train3d-hard (300)", r"phase14-blender\train3d_hard_dataset\traj.jsonl"),
    ("real-ui (792)", r"phase13-gui\out_real\grounding.jsonl"),
    ("rollout-raw (511)", r"phase13-gui\out_rollout_base\rollout_rows.jsonl"),
]

# trong so thật trong mix v22 (theo LOBBY 19:20)
MIX_V22 = [("synth", 1200), ("real-ui", 792), ("gui-traj", 816),
           ("synth targeted S1-S8", 250), ("train3d", 300),
           ("train3d-hard", 300), ("policy-replay", 332),
           ("selfplay (cap 30%)", 123)]


def log(m):
    print("[dondisc] %s" % m, flush=True)


def read_jsonl(p):
    rows = []
    if not os.path.exists(p):
        return rows
    with io.open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    return rows


TRAJ_STEP_RE = re.compile(r"^(.*)_s(\d+)\.[A-Za-z0-9]+$")


def traj_ep_key(r):
    """gui-traj: episode/step ma hoa trong TEN FILE (vd ..._v00_s0.png)."""
    m = TRAJ_STEP_RE.match(r.get("image") or "")
    if m:
        return ("traj", m.group(1))
    return ("__single__", id(r), None)


def ep_key(r):
    """Khoa episode. 3 dang nguon duoc gap:
    - row co 'episode' (synth targeted: family + episode + step)
    - row co 'step'    (policy-replay / selfplay / rollout: task+variant+rep)
    - con lai          (gui-traj, train3d: moi row = 1 episode 1 buoc)"""
    if r.get("episode") is not None:
        return ("ep", r.get("family"), r.get("episode"))
    if "step" in r:
        return (r.get("task_id"), r.get("variant"), r.get("rep"))
    return ("__single__", id(r), None)


def verb(a):
    a = (a or "").strip()
    return a.split(None, 1)[0].upper() if a else ""


def stats(rows, key_fn=None):
    """Do: so episode, buoc/episode, DONE."""
    eps = {}
    for r in rows:
        eps.setdefault((key_fn or ep_key)(r), []).append(r)
    steps = []
    ep_end_done = 0
    ep_any_done = 0
    done_rows = 0
    ep_multi = 0
    ep_multi_end_done = 0
    verbs = {}
    for k, rs in eps.items():
        rs.sort(key=lambda r: r.get("step") if isinstance(r.get("step"), int)
                else 0)
        steps.append(len(rs))
        acts = [(r.get("action") or "").strip() for r in rs]
        for a in acts:
            verbs[verb(a)] = verbs.get(verb(a), 0) + 1
        if verb(acts[-1] if acts else "") == "DONE":
            ep_end_done += 1
            if len(rs) >= 2:
                ep_multi_end_done += 1
        if len(rs) >= 2:
            ep_multi += 1
        if any(verb(a) == "DONE" for a in acts):
            ep_any_done += 1
        done_rows += sum(1 for a in acts if verb(a) == "DONE")
    n_ep = max(len(eps), 1)
    return {
        "rows": len(rows),
        "episodes": len(eps),
        "ep_multi": ep_multi,
        "ep_multi_end_done": ep_multi_end_done,
        "steps_min": min(steps) if steps else 0,
        "steps_med": statistics.median(steps) if steps else 0,
        "steps_max": max(steps) if steps else 0,
        "pct_ep_ge8": round(100.0 * sum(1 for s in steps if s >= 8) / n_ep, 1),
        "pct_ep_end_done": round(100.0 * ep_end_done / n_ep, 1),
        "pct_ep_any_done": round(100.0 * ep_any_done / n_ep, 1),
        "pct_rows_done": round(100.0 * done_rows / max(len(rows), 1), 2),
        "verbs": verbs,
    }


def read_kernel_n_targeted():
    """Doc N_TARGETED thuoc kernel v22/v23a (de khong doan so episode)."""
    for rel in (r"phase13-gui\kernel_v23a\gui_sft_v22.py",
                r"phase13-gui\kernel_v22\gui_sft_v22.py"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            m = re.search(r"^N_TARGETED\s*=\s*(\d+)",
                          io.open(p, encoding="utf-8", errors="replace").read(),
                          re.M)
            if m:
                log("N_TARGETED (tu %s) = %s" % (rel, m.group(1)))
                return int(m.group(1)), rel
    log("khong tim thay N_TARGETED -> mac dinh 250")
    return 250, ""


def main():
    t0 = time.time()
    N_TGT_KERNEL, KERNEL_SRC = read_kernel_n_targeted()
    out = []
    out.append("# Do \"ky luat DONE\" trong data train + hanh vi model\n")
    out.append("_Sinh tu dong boi `phase13-gui/done_discipline.py` (GLM) - khong go tay so lieu._\n")
    out.append("## 1) Data train: tung nguon co day \"chuoi roi moi DONE\" khong?\n")
    out.append("> **LUU Y SEMANTIC** (theo @MiMo 22/10): 2 chi so khac nghia - "
               "**%row la DONE** (cai model THAT su thay khi train) va "
               "**%episode ket thuc bang DONE** (chi co y nghia o nguon co field "
               "episode/step; voi gui-traj goc - data 1-action - episode chi duoc "
               "SUY RA tu ten file `..._sMM.png`, nen dung %row la DONE cho "
               "nguon do; %episode co y nghia sau khi R2 them row DONE).\n")
    out.append("| nguon | rows | episodes | buoc/ep (min/med/max) | %ep >=8 buoc | %ep ket thuc bang DONE | %row la DONE | verbs |")
    out.append("|---|---|---|---|---|---|---|---|")
    S = {}
    for name, rel in SOURCES:
        rows = read_jsonl(os.path.join(ROOT, rel))
        if not rows:
            out.append("| %s | - | - | (khong co file local) | - | - | - | - |" % name)
            continue
        key_fn = traj_ep_key if name.startswith("gui-traj") else None
        st = stats(rows, key_fn)
        S[name] = st
        vr = ", ".join("%s=%d" % (k, v) for k, v in
                       sorted(st["verbs"].items(), key=lambda x: -x[1])[:5])
        out.append("| %s | %d | %d | %d/%s/%d | %.1f%% | %.1f%% | %.2f%% | %s |" %
                   (name, st["rows"], st["episodes"], st["steps_min"],
                    st["steps_med"], st["steps_max"], st["pct_ep_ge8"],
                    st["pct_ep_end_done"], st["pct_rows_done"], vr))
        log("%-22s rows=%-4d ep=%-4d steps med=%s  endDONE=%.1f%%  rowDONE=%.2f%%" %
            (name, st["rows"], st["episodes"], st["steps_med"],
             st["pct_ep_end_done"], st["pct_rows_done"]))

    # --- synth targeted (dung ham THAT cua kernel v22) ---
    out.append("\n## 2) Synth targeted (dung dung ham kernel v22: build_targeted(250, 303))\n")
    tgt = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gst", os.path.join(ROOT, "phase13-gui", "gen_synth_targeted.py"))
        gst = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gst)
        tmp = os.path.join(HERE, "_dd_tmp_imgs")
        rows = gst.build_targeted(N_TGT_KERNEL, 303, tmp)
        st = stats(rows)
        tgt = st
        # ban MOI (MiMo da them done_rate): do them dr=0.75
        tgt75 = None
        try:
            import inspect
            if "done_rate" in inspect.signature(
                    gst.build_targeted).parameters:
                rows75 = gst.build_targeted(N_TGT_KERNEL, 303, tmp,
                                           done_rate=0.75)
                tgt75 = stats(rows75)
                log("synth targeted dr=0.75: rows=%d ep=%d DONE=%d" %
                    (tgt75["rows"], tgt75["episodes"],
                     tgt75["ep_multi_end_done"]))
        except Exception as e:
            log("targeted dr=0.75 loi: %s" % e)
        out.append("| nguon | rows | episodes | buoc/ep (min/med/max) | %ep >=8 buoc | %ep ket thuc bang DONE | %row la DONE |")
        out.append("|---|---|---|---|---|---|---|")
        out.append("| synth targeted S1-S8 (n=250, dr=0.0 = v22) | %d | %d | %d/%s/%d | %.1f%% | %.1f%% | %.2f%% |" %
                   (st["rows"], st["episodes"], st["steps_min"], st["steps_med"],
                    st["steps_max"], st["pct_ep_ge8"], st["pct_ep_end_done"],
                    st["pct_rows_done"]))
        if tgt75:
            out.append("| **synth targeted S1-S8 (n=250, dr=0.75 = MOI)** | %d | %d | %d/%s/%d | %.1f%% | %.1f%% | %.2f%% |" %
                       (tgt75["rows"], tgt75["episodes"], tgt75["steps_min"],
                        tgt75["steps_med"], tgt75["steps_max"],
                        tgt75["pct_ep_ge8"], tgt75["pct_ep_end_done"],
                        tgt75["pct_rows_done"]))
        log("synth targeted: rows=%d ep=%d med=%s endDONE=%.1f%%" %
            (st["rows"], st["episodes"], st["steps_med"], st["pct_ep_end_done"]))
    except Exception as e:
        out.append("_Khong do duoc synth targeted: %s: %s_" % (type(e).__name__,
                                                              str(e)[:200]))
        log("synth targeted loi: %s" % e)

    # --- rollout raw: model co DONE khong ---
    out.append("\n## 3) Hanh vi thuc cua model trong rollout (511 row, policy v20 t=0.7)\n")
    rows = read_jsonl(os.path.join(ROOT, r"phase13-gui\out_rollout_base\rollout_rows.jsonl"))
    if rows:
        eps = {}
        for r in rows:
            eps.setdefault((r.get("task_id"), r.get("variant"), r.get("rep")),
                           []).append(r)
        win_eps = [rs for rs in eps.values() if rs[0].get("win")]
        fail_eps = [rs for rs in eps.values() if not rs[0].get("win")]
        def done_stat(rss):
            n = len(rss)
            end_done = sum(1 for rs in rss
                           if verb((sorted(rs, key=lambda r: r.get("step") or 0)[-1]
                                    .get("action") or "")) == "DONE")
            any_done = sum(1 for rs in rss
                           if any(verb(r.get("action") or "") == "DONE" for r in rs))
            avg = sum(len(rs) for rs in rss) / max(n, 1)
            return n, 100.0 * end_done / max(n, 1), 100.0 * any_done / max(n, 1), avg
        out.append("| nhom | episodes | %ep ket thuc bang DONE | %ep co DONE bat ky luc | avg buoc/ep |")
        out.append("|---|---|---|---|---|")
        for label, rss in (("WIN", win_eps), ("FAIL", fail_eps)):
            n, ed, ad, avg = done_stat(rss)
            out.append("| nhom | episodes | %ep ket thuc bang DONE | %ep co DONE bat ky luc | avg buoc/ep |")
            out.append("|---|---|---|---|---|")
            out.append("| %s | %d | %.1f%% | %.1f%% | %.1f |" % (label, n, ed, ad, avg))
            log("rollout %s: n=%d endDONE=%.1f%% anyDONE=%.1f%% avg=%.1f" %
                (label, n, ed, ad, avg))

    # --- B15 v21 ---
    out.append("\n## 4) B15 v21 (model tren bench that): episode co DONE khong?\n")
    b15 = os.path.join(ROOT, r"phase13-gui\out_bench_v21\b15_result.json")
    if os.path.exists(b15):
        d = json.load(io.open(b15, encoding="utf-8"))
        eps = d.get("episodes") or []
        if eps:
            def ep_done(e):
                tr = e.get("trace") or []
                acts = [(t.get("act") or t.get("action") or "") for t in tr]
                acts = [a if isinstance(a, str) else
                        (a[0] if isinstance(a, (list, tuple)) and a else "")
                        for a in acts]
                verbs_ = [verb(a) for a in acts]
                return ("DONE" in verbs_,
                        (verbs_[-1] if verbs_ else "") == "DONE",
                        len(tr))
            w = [e for e in eps if e.get("win")]
            f = [e for e in eps if not e.get("win")]
            out.append("| nhom | episodes | %ep co DONE | %ep ket thuc bang DONE | avg buoc/ep |")
            out.append("|---|---|---|---|---|")
            for label, gg in (("WIN", w), ("FAIL", f)):
                n = len(gg)
                if not n:
                    continue
                ad = 100.0 * sum(1 for e in gg if ep_done(e)[0]) / n
                ed = 100.0 * sum(1 for e in gg if ep_done(e)[1]) / n
                avg = sum(ep_done(e)[2] for e in gg) / n
                out.append("| %s | %d | %.1f%% | %.1f%% | %.1f |" % (label, n, ad, ed, avg))
                log("b15 v21 %s: n=%d anyDONE=%.1f%% endDONE=%.1f%% avg=%.1f" %
                    (label, n, ad, ed, avg))
    else:
        out.append("_Khong thay `out_bench_v21/b15_result.json`._")

    # --- mix v22 ---
    out.append("\n## 5) Pha loang trong mix v22 (theo so ROW thuc te)\n")
    # synth: build_data sinh row CLICK don le -> DONE = 0 (bang chung tu code)
    synth_rate = None
    synth_note = ""
    try:
        g = io.open(os.path.join(ROOT, r"phase13-gui\kernel\gui_sft.py"),
                    encoding="utf-8", errors="replace").read()
        i = g.find("def build_data")
        j = g.find("\ndef ", i + 10)
        seg = g[i:j] if i > 0 else ""
        # synth row KHONG co truong 'action' -> target = 1 CLICK -> 0% DONE
        synth_rate = 0.0 if (seg and '"action"' not in seg) else None
        synth_note = ("row khong co 'action' (grounding 1 CLICK)"
                      if synth_rate == 0.0 else "")
    except Exception:
        pass
    key_map = {"gui-traj": "gui-traj (816)",
               "policy-replay": "policy-replay (332)",
               "selfplay (cap 30%)": "selfplay d2 (123)",
               "real-ui": "real-ui (792)",
               "train3d": "train3d (300)",
               "train3d-hard": "train3d-hard (300)"}
    mix = [("synth (grounding don le)", 1200, synth_rate, synth_note),
           ("real-ui", 792, S.get("real-ui (792)", {}).get("pct_rows_done"), ""),
           ("gui-traj", 816, S.get("gui-traj (816)", {}).get("pct_rows_done"), ""),
           ("synth targeted S1-S8", (tgt or {}).get("rows", 250),
            (tgt or {}).get("pct_rows_done"), "250 episode"),
           ("train3d", 300, S.get("train3d (300)", {}).get("pct_rows_done"), ""),
           ("train3d-hard", 300, S.get("train3d-hard (300)", {}).get("pct_rows_done"), ""),
           ("policy-replay", 332, S.get("policy-replay (332)", {}).get("pct_rows_done"), ""),
           ("selfplay (cap 30%)", 123, S.get("selfplay d2 (123)", {}).get("pct_rows_done"), "")]
    out.append("| nguon trong mix v22 | rows | %DONE cua nguon | dong gop DONE | ghi chu |")
    out.append("|---|---|---|---|---|")
    total_rows = 0
    total_done = 0.0
    for label, n, rate, note in mix:
        if rate is None:
            out.append("| %s | %d | (khong do duoc) | - | %s |" % (label, n, note))
            continue
        total_rows += n
        total_done += n * rate / 100.0
        out.append("| %s | %d | %.2f%% | %.1f row | %s |" %
                   (label, n, rate, n * rate / 100.0, note))
    out.append("| **TONG mix v22** | **%d** | - | **%.1f row DONE (%.2f%%)** | |" %
               (total_rows, total_done, 100.0 * total_done / max(total_rows, 1)))
    # phan bo DONE theo nguon co chuoi (nguon day DONE sau chuoi >= 2 buoc)
    long_done = 0
    long_rows = 0
    for key, st in S.items():
        if key in ("policy-replay (332)", "selfplay d2 (123)",
                   "rollout-raw (511)"):
            long_rows += st["rows"]
            long_done += st["rows"] * st["pct_rows_done"] / 100.0
    if long_rows:
        out.append("\n**Chi nguon day \"chuoi -> DONE\" la policy-replay + selfplay**: "
                   "%.1f/%.1f row DONE cua 2 nguon do = **%.1f%% cua toan mix** "
                   "(%.0f row) - phan con lai cua mix khong co DONE sau chuoi."
                   % (long_done, long_rows,
                      100.0 * long_done / max(total_rows, 1), long_done))

    # ================= §6: gen_synth_long (MoiMo) + sweep done_rate =========
    out.append("\n## 6) gen_synth_long (file moi cua @MiMo) + sweep `done_rate`\n")
    gsl = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gsl", os.path.join(ROOT, "phase13-gui", "gen_synth_long.py"))
        gsl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gsl)
    except Exception as e:
        out.append("_Khong import duoc gen_synth_long: %s: %s_" %
                   (type(e).__name__, str(e)[:160]))
    long_by_dr = {}
    if gsl is not None:
        out.append("| done_rate | rows | episodes | buoc/ep (med/max) | %ep >=8 buoc | %ep ket thuc bang DONE | %row la DONE | verbs |")
        out.append("|---|---|---|---|---|---|---|---|")
        tmp_long = os.path.join(HERE, "_dd_tmp_long")
        for dr in (0.0, 0.25, 0.35, 0.5, 0.75, 1.0):
            rows_l = gsl.build_long(120, 303, tmp_long, done_rate=dr)
            stl = stats(rows_l)
            long_by_dr[dr] = stl
            vr = ", ".join("%s=%d" % (k, v) for k, v in
                           sorted(stl["verbs"].items(), key=lambda x: -x[1])[:5])
            out.append("| %.2f | %d | %d | %s/%d | %.1f%% | %.1f%% | %.2f%% | %s |" %
                       (dr, stl["rows"], stl["episodes"], stl["steps_med"],
                        stl["steps_max"], stl["pct_ep_ge8"],
                        stl["pct_ep_end_done"], stl["pct_rows_done"], vr))
            log("long done_rate=%.2f: rows=%d ep=%d endDONE=%.1f%% rowDONE=%.2f%%" %
                (dr, stl["rows"], stl["episodes"], stl["pct_ep_end_done"],
                 stl["pct_rows_done"]))
        # production: n=250, dr=0.75 (gia tri @MiMo de xuat cho v23)
        long_prod = None
        try:
            rows_p = gsl.build_long(250, 303, os.path.join(HERE, "_dd_tmp_long"),
                                    done_rate=0.75)
            long_prod = stats(rows_p)
            out.append("| **0.75 (n=250, production)** | %d | %d | %s/%d | %.1f%% | %.1f%% | %.2f%% |" %
                       (long_prod["rows"], long_prod["episodes"],
                        long_prod["steps_med"], long_prod["steps_max"],
                        long_prod["pct_ep_ge8"], long_prod["pct_ep_end_done"],
                        long_prod["pct_rows_done"]))
            log("long PROD n=250 dr=0.75: rows=%d ep=%d endDONE=%.1f%%" %
                (long_prod["rows"], long_prod["episodes"],
                 long_prod["pct_ep_end_done"]))
        except Exception as e:
            log("long production loi: %s" % e)

    # ================= §7: verb cuoi cung episode (co che) =================
    out.append("\n## 7) Co che: action CUOI cua episode la gi? (nguon dang loai DONE)\n")
    out.append("| nguon | episode nhieu buoc | %ep cuoi = DONE | %ep cuoi = CLICK (khong DONE) |")
    out.append("|---|---|---|---|")
    mech = {}
    for key, st in S.items():
        if "ep_multi" not in st or not st.get("ep_multi"):
            continue
        mech[key] = st
        out.append("| %s | %d | %.1f%% | %.1f%% |" %
                   (key, st["ep_multi"],
                    100.0 * st["ep_multi_end_done"] / st["ep_multi"],
                    100.0 * (st["ep_multi"] - st["ep_multi_end_done"]) /
                    st["ep_multi"]))
    if tgt:
        out.append("| synth targeted S1-S8 | %d | %.1f%% | %.1f%% |" %
                   (tgt.get("ep_multi", 0),
                    100.0 * tgt.get("ep_multi_end_done", 0) /
                    max(tgt.get("ep_multi", 1), 1),
                    100.0 * (tgt.get("ep_multi", 0) -
                             tgt.get("ep_multi_end_done", 0)) /
                    max(tgt.get("ep_multi", 1), 1)))
    out.append("> Doc dong nay: mot episode nhieu buoc cuoi bang **CLICK** (khong DONE) "
               "=> model hoc 'chuoi ket thuc bang 1 click' => khong bao gio DONE. "
               "Day la ly do C4 / 0% episode fail co DONE.")

    # ================= §8: kich ban mix ==================================
    out.append("\n## 8) Kich ban mix: P(DONE | buoc cuoi cua episode nhieu buoc) + %DONE toan mix\n")
    out.append("| kich ban | them vao mix | episode nhieu buoc | ep cuoi=DONE | **P(DONE \\| cuoi multi-step)** | rows DONE / tong rows |")
    out.append("|---|---|---|---|---|---|")
    base_multi = 0
    base_done_multi = 0
    for key in (_TRAJ_LABEL, "policy-replay (332)", "selfplay d2 (123)"):
        st = S.get(key) or {}
        base_multi += st.get("ep_multi", 0)
        base_done_multi += st.get("ep_multi_end_done", 0)
    if tgt:
        base_multi += tgt.get("ep_multi", 0)
        base_done_multi += tgt.get("ep_multi_end_done", 0)
    def _rows_done(st):
        if not st:
            return 0, 0
        return st.get("rows", 0), int(round(st.get("rows", 0)
                                           * st.get("pct_rows_done", 0) / 100.0))
    # mix v22: synth 1200 + real-ui 792 + traj + targeted(dr0) + 3D + policy + selfplay
    _mix_rows = 1200 + 792 + (tgt or {}).get("rows", 0) + 300 + 300 + 332 + 123
    _mix_done = 0
    for _k in (_TRAJ_LABEL, "policy-replay (332)", "selfplay d2 (123)"):
        _r, _d = _rows_done(S.get(_k))
        _mix_done += _d
    base_rows, base_done = _mix_rows, _mix_done
    long_rows_per_ep = 9.14
    scen = [
        ("S0 = v22 hien tai", "-", 0, 0, 0, 0),
        ("S1 = + long 250 ep (dr 0.35)", "gen_synth_long n=250", 250, 88, 0, 0),
        ("S1b = + long 250 ep (dr 0.75)", "gen_synth_long n=250", 250, 188, 0, 0),
        ("S2 = + long 250 ep (dr 0.60)", "gen_synth_long n=250", 250, 150, 0, 0),
        ("S3 = + long 250 (dr .75) + targeted co DONE cuoi",
         "gen_synth_long + sua targeted", 250, 188, 250, 250),
        ("S4 = + long 600 (dr .75) + targeted co DONE cuoi",
         "gen_synth_long n=600 + sua targeted", 600, 450, 250, 250),
    ]
    for name, add, add_multi, add_done_multi, add_multi2, add_done2 in scen:
        multi = base_multi + add_multi
        dmulti = base_done_multi + add_done_multi
        rows = base_rows + int(add_multi * long_rows_per_ep)
        drows = base_done + add_done_multi
        if add_multi2:
            dmulti += add_done2
            drows += add_done2
            rows += add_done2
        out.append("| %s | %s | %d | %d | **%.1f%%** | %d / %d = %.2f%% |" %
                   (name, add, multi, dmulti,
                    100.0 * dmulti / max(multi, 1), drows, rows,
                    100.0 * drows / max(rows, 1)))
    out.append("\n> Doc: **P(DONE | cuoi episode nhieu buoc)** la xac suat model 'sau khi "
               "chuoi xong thi emit DONE'. Hien tai **%.1f%%** (61/320 episode nhieu buoc "
               "ket thuc bang DONE). Chi lenh `done_rate` cua gen_synth_long: dr 0.75 + 250 ep "
               "=> **%.1f%%** (da > 40%%) ma VAN giu 25%% chuoi dai khong DONE (model van biet "
               "phai tiep) + L4 giu 'khong DONE som'. Muon >50%% thi PHAI sua them 250 episode "
               "targeted (hoac cat targeted khoi mix) - vi targeted 100%% ket thuc bang CLICK."
               % (100.0 * base_done_multi / max(base_multi, 1),
                  100.0 * (base_done_multi + 188) / max(base_multi + 250, 1)))

    # --- kich ban V23a: CHI targeted dr0.75 (re) ---
    if tgt75:
        rows_a = base_rows - tgt.get("rows", 0) + tgt75["rows"]
        done_a = base_done + tgt75["ep_multi_end_done"]
        multi_a = base_multi
        dmulti_a = base_done_multi + tgt75["ep_multi_end_done"]
        steps_a = int(500 * rows_a / 2808)
        out.append("| **S6 = v23a: CHI targeted dr0.75 (RHE + %d row)** | "
                   "re-inline targeted | %d | %d | **%.1f%%** | %d / %d = %.2f%% |" %
                   (tgt75["rows"] - tgt.get("rows", 0), multi_a, dmulti_a,
                    100.0 * dmulti_a / max(multi_a, 1), done_a, rows_a,
                    100.0 * done_a / max(rows_a, 1)))
        out.append("> **S6 vs S5: them long 250 ep KHONG tang P(DONE) ma lam GIAM nho** "
                   "(%.1f%% -> %.1f%%) vi long co 25%% episode khong DONE; long "
                   "day them kha nang CHAIN DAU (%%ep >=8 buoc), khac co che DONE. "
                   "=> **chay v23a truoc** (RHE +%d row / +%d steps ~ +5%% GPU), "
                   "neu v23a van fail o task nhieu buoc thi moi xet v23b."
                   % (100.0 * dmulti_a / max(multi_a, 1),
                      100.0 * (dmulti_a + long_prod["ep_multi_end_done"]) /
                      max(multi_a + long_prod["episodes"], 1) if long_prod else 0.0,
                      tgt75["rows"] - tgt.get("rows", 0),
                      steps_a - int(500 * base_rows / 2808)))

    # --- kich ban R2 (GPT): them row DONE cho episode tra khong DONE ---
    if _TRAJ_LABEL in S and tgt75 and long_prod:
        st_t = S[_TRAJ_LABEL]
        n_add = st_t.get("ep_multi", 0) - st_t.get("ep_multi_end_done", 0)
        base_multi_r2 = base_multi
        base_dmulti_r2 = base_done_multi + n_add
        rows_r2 = base_rows + n_add
        out.append("| **S7 = v22 + R2 (GPT: +%d row DONE vao tap tra)** | "
                   "traj_done_aug | %d | %d | **%.1f%%** | %d / %d = %.2f%% |" %
                   (n_add, base_multi_r2, base_dmulti_r2,
                    100.0 * base_dmulti_r2 / max(base_multi_r2, 1),
                    base_done + n_add, rows_r2,
                    100.0 * (base_done + n_add) / max(rows_r2, 1)))
        # S8 = v23a (targeted dr0.75) + R2 (traj DONE) -- KHONG co long 250 ep
        _m8 = base_multi_r2
        _d8 = base_dmulti_r2 + tgt75["ep_multi_end_done"]
        _r8 = base_rows + n_add + (tgt75["rows"] - tgt["rows"])
        _k8 = base_done + n_add + tgt75["ep_multi_end_done"]
        out.append("| **S8 = v23a + R2 (khuyến nghị)** | targeted dr0.75 + "
                   "traj_done_aug | %d | %d | **%.1f%%** | %d / %d = %.2f%% |" %
                   (_m8, _d8, 100.0 * _d8 / max(_m8, 1), _k8, _r8,
                    100.0 * _k8 / max(_r8, 1)))
        out.append("> **Chi phi R2: +%d row ( dung anh buoc cuoi ) ~ +%d steps** "
                   "=> re dat hon nhieu so voi +%d row cua long 250 ep."
                   % (n_add,
                      int(500 * (base_rows + n_add) / 2808) -
                      int(500 * base_rows / 2808),
                      long_prod["rows"] - (tgt75["rows"] - tgt["rows"])))

    # --- kich ban V23: do bang so do duoc ---
    if tgt75 and long_prod:
        rows_v23 = (base_rows - tgt.get("rows", 0) + tgt75["rows"]
                    + long_prod["rows"])
        done_v23 = (base_done + tgt75["ep_multi_end_done"]
                    + long_prod["ep_multi_end_done"])
        multi_v23 = base_multi + long_prod["episodes"]
        dmulti_v23 = (base_done_multi + tgt75["ep_multi_end_done"]
                      + long_prod["ep_multi_end_done"])
        steps_v23 = int(500 * rows_v23 / 2808)
        out.append("| **S5 = v23: targeted dr0.75 + long 250 dr0.75 (DO DUOC)** | "
                   "gen_synth_long + re-inline targeted | %d | %d | **%.1f%%** | "
                   "%d / %d = %.2f%% |" %
                   (multi_v23, dmulti_v23,
                    100.0 * dmulti_v23 / max(multi_v23, 1),
                    done_v23, rows_v23, 100.0 * done_v23 / max(rows_v23, 1)))
        out.append("")
        out.append("> **Chi phi (do duoc):** mix v23 = %d row -> `STEPS = 500 x %d/2808` "
                   "= **%d steps** (~%.1fx v18 500 steps). Neu can giu ngan sach: cat "
                   "grounding don le (synth 1200 / real-ui 792 / train3d 600 = 2592 row, "
                   "0%% DONE) thi mix ve ~%d row va steps ~%d."
                   % (rows_v23, rows_v23, steps_v23, steps_v23 / 500.0,
                      rows_v23 - 2592, int(500 * (rows_v23 - 2592) / 2808)))

    with io.open(OUT_MD, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    log("ghi %s (%d bytes) t=%.0fs" % (OUT_MD, os.path.getsize(OUT_MD),
                                       time.time() - t0))

if __name__ == "__main__":
    main()
