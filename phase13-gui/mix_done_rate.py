"""mix_done_rate.py - tinh "%row la DONE" cua mix train tren MIX THAT cua kernel
(GLM, 22/10) - de chot 1 con so duy nhat thay vi 2 uoc luong khac nhau.

Nguon su that:
  - out_sft_v22/gui_result.json  : n_train + n_targeted/n_train3d/n_policy_replay/
                                   n_selfplay THAT cua kernel v22 (da train xong)
  - file local traj (goc + R2 aug) : so row + so row DONE
  - gen_synth_targeted (dr 0.75) : do bang ham THAT cua kernel (N_TARGETED episode)
  - policy-replay / selfplay / train3d : do tu file local

Cong thuc (v23a + R2) = mix v22 - targeted(dr0) + targeted(dr0.75) + (traj R2 - traj goc)

Dung: python phase13-gui/mix_done_rate.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def log(m):
    print("[mix] %s" % m, flush=True)


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
                    pass
    return rows


def done_n(rows):
    return sum(1 for r in rows
               if (r.get("action") or "").strip().upper().startswith("DONE"))


def measure_targeted(n_ep, dr):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gst", os.path.join(HERE, "gen_synth_targeted.py"))
    gst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gst)
    out = os.path.join(HERE, "_mix_tmp_imgs")
    rows = gst.build_targeted(n_ep, 303, out, done_rate=dr)
    return len(rows), done_n(rows)


def main():
    # --- mix THAT cua kernel v22 (tu gui_result.json) ---
    gr = os.path.join(HERE, "out_sft_v22", "gui_result.json")
    n_train = None
    comp = {}
    if os.path.exists(gr):
        d = json.load(io.open(gr, encoding="utf-8", errors="replace"))
        n_train = d.get("n_train")
        for k in ("n_targeted", "n_train3d", "n_policy_replay", "n_selfplay"):
            if d.get(k) is not None:
                comp[k] = d[k]
        log("mix v22 THAT: n_train=%s %s" % (n_train, comp))
    else:
        log("khong thay %s -> dung uoc luong" % gr)
    if n_train is None:
        n_train = 5802

    # --- nguon do duoc ---
    traj_base = read_jsonl(os.path.join(HERE, "out_traj", "traj.jsonl"))
    traj_aug = read_jsonl(os.path.join(HERE, "traj_done_aug.jsonl"))
    if not traj_aug:
        traj_aug = traj_base
    pol = read_jsonl(os.path.join(ROOT, "phase13-gui", "out_policy_replay",
                                 "replay", "traj.jsonl"))
    self_d = read_jsonl(os.path.join(HERE, "selfplay_dataset", "traj.jsonl"))
    t3d = read_jsonl(os.path.join(ROOT, "phase14-blender", "train3d_dataset",
                                  "traj.jsonl"))
    t3dh = read_jsonl(os.path.join(ROOT, "phase14-blender",
                                   "train3d_hard_dataset", "traj.jsonl"))
    n_tgt = comp.get("n_targeted", 1944)
    # so episode cua targeted trong kernel = n_targeted row / ~4.07 row moi ep
    n_ep_tgt = 500
    try:
        m = re.search(r"^N_TARGETED\s*=\s*(\d+)",
                      io.open(os.path.join(HERE, "kernel_v23a",
                                          "gui_sft_v22.py"),
                              encoding="utf-8", errors="replace").read(), re.M)
        if m:
            n_ep_tgt = int(m.group(1))
    except Exception:
        pass
    tgt_rows_075, tgt_done_075 = measure_targeted(n_ep_tgt, 0.75)
    log("targeted dr0.75 (%d ep): %d row / %d DONE" %
        (n_ep_tgt, tgt_rows_075, tgt_done_075))

    # --- DONE rows cua mix v22 (tu file local) ---
    done_v22 = (done_n(traj_base) + done_n(pol) + done_n(self_d)
                + done_n(t3d) + done_n(t3dh))
    rows_v22 = n_train
    # --- v23a + R2 ---
    rows_v23a = rows_v22 - n_tgt + tgt_rows_075 + (len(traj_aug) - len(traj_base))
    done_v23a = (done_v22 - done_n(traj_base) + done_n(traj_aug)
                 + (tgt_done_075 - 0))
    # targeted dr0 co 0 DONE nen cong them tat ca DONE cua targeted dr0.75
    rows_v23a = rows_v22 - n_tgt + tgt_rows_075 + (len(traj_aug) - len(traj_base))
    done_v23a = done_v22 - done_n(traj_base) + done_n(traj_aug) + tgt_done_075
    steps_v23a = int(500 * rows_v23a / 2808)

    print("\n| phien ban | mix rows | row DONE | **%row la DONE** | steps (500*rows/2808) |")
    print("|---|---|---|---|---|")
    print("| v22 (traj goc) | %d | %d | **%.2f%%** | %d |" %
          (rows_v22, done_v22, 100.0 * done_v22 / rows_v22,
           int(500 * rows_v22 / 2808)))
    print("| **v23a + R2** | %d | %d | **%.2f%%** | %d |" %
          (rows_v23a, done_v23a, 100.0 * done_v23a / rows_v23a, steps_v23a))
    print("\nGHI CHU:")
    print("  - %row la DONE la chi so model THAT thay khi train (khong phai %episode).")
    print("  - So tren day lay mix THAT cua kernel v22 (n_train=%d tu gui_result.json)," % rows_v22)
    print("    targeted do bang ham THAT cua kernel (N_TARGETED=%d ep -> %d row)." %
          (n_ep_tgt, tgt_rows_075))
    print("  - KHI kernel v23a train xong: doc lai gui_result.json de lay con so")
    print("    CHINH XAC (nguon su that, khong uoc luong).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
