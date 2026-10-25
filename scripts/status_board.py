# -*- coding: utf-8 -*-
"""
status_board.py - BANG TRANG THAI 1 LENH: ai dang chay, cai gi bi chan, can
chay lenh gi de unblock.

Dung:
    python scripts/status_board.py            # kiem tra dataset remote (can key)
    python scripts/status_board.py --fast     # khong goi Kaggle API
ASCII-only source.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAGS = 0x08000000 if os.name == "nt" else 0

# slug dataset bench 2 suite x 2 acc
BENCH_DATASETS = [
    "khoadangnguye/ornith-gui-bench-v155", "dieniw/ornith-gui-bench-v155",
    "khoadangnguye/ornith-gui-bench-v16", "khoadangnguye/ornith-gui-bench-v16b",
    "dieniw/ornith-gui-bench-v16", "dieniw/ornith-gui-bench-v16b",
]
STAGE_ROOT = os.path.join(ROOT, "phase13-gui", "bench_ds_staging")


def load(p, d=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def kaggle_user():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run(["kaggle", "config", "view"], capture_output=True,
                           env=env, timeout=60, creationflags=FLAGS)
        out = ((p.stdout or b"").decode("utf-8", "replace") +
               (p.stderr or b"").decode("utf-8", "replace"))
        for line in out.splitlines():
            if line.strip().lower().startswith("username:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("KAGGLE_USERNAME", "?")


def ds_exists(owner, slug):
    """(state, n) bang 'kaggle datasets files' (decisive hon 'status').

    state: exists | empty | missing | private | unknown
    - 'missing' chi khi dataset thuoc CHINH acc dang chay voi (key dung) va
      API tra loi 403/404 (voi acc khac thi chi co nghia 'khong doc duoc').
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        p = subprocess.run(["kaggle", "datasets", "files", "%s/%s" % (owner, slug)],
                           capture_output=True, env=env, timeout=120,
                           creationflags=FLAGS)
    except Exception:
        return "unknown", 0
    out = (p.stdout or b"").decode("utf-8", "replace")
    blob = (out + (p.stderr or b"").decode("utf-8", "replace")).lower()
    if p.returncode == 0:
        n = 0
        for line in out.splitlines():
            parts = line.strip().split()
            if parts and "." in parts[0] and parts[0].lower() not in (
                    "name", "size", "creationdate", "file"):
                n += 1
        return ("exists", n) if n else ("empty", 0)
    if "403" in blob or "404" in blob or "not found" in blob:
        me = kaggle_user().lower()
        if me and me != "?" and owner.lower() == me:
            return "missing", 0
        return "private", 0
    return "unknown", 0


def section(t):
    print("=" * 78)
    print(t)
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    a = ap.parse_args()
    now = time.strftime("%H:%M:%S")
    print("STATUS BOARD %s | acc CLI = %s" % (now, kaggle_user()))

    # ---- 1) queue / kernel state
    section("1) HANG DOI GPU (watchdog)")
    for qf, sf, tag in (("scripts/gpu_queue.json", "scripts/gpu_queue_state.json", "A"),
                        ("scripts/gpu_queue_B.json", "scripts/gpu_queue_B_state.json", "B")):
        q = load(os.path.join(ROOT, qf.replace("/", os.sep)), [])
        st = load(os.path.join(ROOT, sf.replace("/", os.sep)), {})
        print("-- acc %s --" % tag)
        for it in q:
            if not isinstance(it, dict):
                continue
            kid = it.get("id", "?")
            s = st.get(kid, {})
            flags = []
            if it.get("paused"):
                flags.append("PAUSED")
            if s.get("pushed"):
                flags.append("pushed")
            if str(s.get("status", "")).upper() in ("RUNNING", "QUEUED"):
                flags.append("RUNNING")
            nt = s.get("next_try") or 0
            if nt and nt > time.time():
                flags.append("backoff %.0fs" % (nt - time.time()))
            print("   %-46s %-12s %s" % (kid[:46], s.get("status", "?"),
                                         " ".join(flags)))

    # ---- 2) dataset bench: staging local + remote
    section("2) DATASET BENCH (2 suite x 2 acc) - remote co version task da sua?")
    for slug in BENCH_DATASETS:
        owner, name = slug.split("/", 1)
        sp = os.path.join(STAGE_ROOT, "%s__%s" % (owner, name))
        zp = os.path.join(sp, "bench_v155_bundle.zip")
        if not os.path.exists(zp):
            zp = os.path.join(sp, "bench_v16_bundle.zip")
        local = "staging OK" if os.path.exists(zp) else "THIEU staging"
        if a.fast:
            print("   %-44s %-14s (fast: khong kiem remote)" % (slug, local))
            continue
        stt, n = ds_exists(owner, name)
        # so voi local: remote phai co file (bundle zip)
        print("   %-44s %-14s remote=%s%s" % (
            slug, local, stt, (" (%d file)" % n) if n else ""))

    # ---- 3) ket qua bench co san
    section("3) KET QUA BENCH DA CO")
    for rel, label in (("phase13-gui/out_bench_v15/b15_result.json", "v18"),
                       ("phase13-gui/out_bench_v21/b15_result.json", "v21"),
                       ("phase13-gui/out_bench_v22/b15_result.json", "v22"),
                       ("phase13-gui/out_bench_v155_v21/b15_result.json", "v21 B15.5"),
                       ("phase13-gui/out_bench_v16_v21/b15_result.json", "v21 B16-A"),
                       ("phase13-gui/out_bench_v155_v22/b15_result.json", "v22 B15.5"),
                       ("phase13-gui/out_bench_v16_v22/b15_result.json", "v22 B16-A")):
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            print("   %-12s (chua co)" % label)
            continue
        try:
            d = load(p, {})
            eps = d.get("episodes") or []
            wins = sum(1 for e in eps if e.get("win"))
            print("   %-12s %d ep, win %d (%.1f%%) | %s"
                  % (label, len(eps), wins,
                     100.0 * wins / max(1, len(eps)),
                     time.strftime("%H:%M", time.localtime(
                         os.path.getmtime(p)))))
        except Exception as e:
            print("   %-12s (doc loi: %s)" % (label, e))

    # ---- 4) artifact san sang (dang cho upload/push)
    if not a.fast:
        section("3b) DATASET: staging local vs da publish (khop = dung ban)")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "cpt", os.path.join(ROOT, "scripts", "check_published_tasks.py"))
            cpt = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cpt)
            jobs = list(cpt.BENCH_DATASETS)
            tj_stage = "phase13-gui/traj_ds_staging/khoadangnguye__ornith-gui-traj"
            if os.path.isdir(os.path.join(ROOT, tj_stage.replace("/", os.sep))):
                jobs.append(("khoadangnguye/ornith-gui-traj", tj_stage, None))
            for ds, st, top in jobs:
                owner = ds.split("/")[0]
                env_d = cpt.acc_env("A" if owner == "khoadangnguye"
                                    else ("B" if owner == "dieniw" else None),
                                    owner)
                ok = cpt.check_sizes(ds, st, env_d, top)
                print("   [%s] %s" % ("OK   " if ok else
                                       ("STALE" if ok is False else "KHONG DOC"), ds))
        except Exception as e:
            print("   (khong kiem duoc: %s)" % str(e)[:120])

    section("4) ARTIFACT SAN SANG (can 1 lenh upload/push moi chay) + LENH CU THE")
    art = [
        ("*** dataset traj R2 (DANG CHAN 5 RUN SFT) ***",
         "python scripts/publish_traj_r2.py --upload",
         "phase13-gui/traj_ds_staging/khoadangnguye__ornith-gui-traj"),
        ("6 dataset bench (task da sua)",
         "python scripts/rebuild_bench_datasets_multi.py --upload",
         "phase13-gui/bench_ds_staging/*"),
        ("bo task B15.5 BAN CU (o 2x2)",
         'kaggle datasets create -p "phase13-gui/old_bench_ds/'
         'khoadangnguye__ornith-gui-bench-v155-old"',
         "phase13-gui/old_bench_ds/*"),
        ("kernel 2x2 (v22 tren task CU)",
         "kaggle kernels push -p phase13-gui/kernel_bench_v155_v22_old",
         "phase13-gui/kernel_bench_v155_v22_old"),
        ("du lieu SFT 600 row (RA/RC/RB)",
         "python scripts/upload_staging.py "
         "phase13-gui/synth_recipe_ds_staging/khoadangnguye__ornith-gui-synth-recipe",
         "phase13-gui/synth_recipe_ds_staging/*"),
        ("bundle xdotool offline (acc A)",
         "python scripts/upload_staging.py phase13-gui/x11tools_dataset",
         "phase13-gui/x11tools_dataset"),
        ("bundle xdotool offline (acc B)",
         "python scripts/upload_staging.py "
         "phase13-gui/acc_b_staging/dieniw__ornith-gui-xdotool --acc B",
         "phase13-gui/acc_b_staging/*"),
    ]
    for name, cmd, path in art:
        p = os.path.join(ROOT, path.replace("*", "").rstrip("/\\").replace("/", os.sep))
        local = os.path.exists(p)
        state = "SAN SANG" if local else "THIEU staging local"
        # voi artifact la DATASET: kiem remote da upload chua
        if "dataset" in name.lower() and local:
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "cpt2", os.path.join(ROOT, "scripts", "check_published_tasks.py"))
                cpt = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cpt)
                slug = None
                mp = os.path.join(p, "dataset-metadata.json")
                if os.path.exists(mp):
                    slug = (json.load(io.open(mp, encoding="utf-8-sig"))
                            .get("id") or "")
                if slug:
                    owner = slug.split("/")[0]
                    env_d = cpt.acc_env("A" if owner == "khoadangnguye"
                                        else ("B" if owner == "dieniw" else None),
                                        owner)
                    # so KICH THUOC (khong phai dem file: dataset co the co
                    # file nhung SAI ban - vd traj R2 con 20 anh cu)
                    rel_staging = path.replace("*", "").rstrip("/\\")
                    ok = cpt.check_sizes(slug, rel_staging, env_d, None)
                    if ok is True:
                        state = "DA UPLOAD (khop staging)"
                    elif ok is False:
                        state = "CHUA/SAI BAN (STALE)"
                    else:
                        state += " (khong doc duoc remote)"
            except Exception as e:
                state += " (khong kiem remote: %s)" % str(e)[:40]
        print("   [%s] %s" % (state, name))
        print("        %s" % cmd)

    # ---- 5) viec can lam
    section("5) VIEC CON PHAI LAM (thu tu)")
    print("""   0) *** DANG CHAN 5 RUN SFT v23b *** @DeepSeek:
         python scripts/publish_traj_r2.py --upload
      (dataset khoadangnguye/ornith-gui-traj hien THIEU ANH => loader drop het row
       => traj_rows=0 => guard chan. Script da dung san + verify 972/972 row resolve
       theo dung logic loader. Chi can key acc A - @MiMo KHONG dung key cua agent khac.)
   1) xong: python scripts/check_published_tasks.py --all-bench  (phai 6/6 khop)
   2) 2 phep do da MO PAUSE (watchdog se push khi co slot GPU):
      - khoadangnguye/ornith-gui-bench-v16-v22       (B16-A tren task DA SUA)
      - khoadangnguye/ornith-gui-bench-v155-v22-old  (o 2x2: v22 tren task CU)
   3) khi ket qua ve: python scripts/report_fixed_suite.py  (bang 2x2 + verdict + delta)
   4) @GLM/@DeepSeek: python scripts/build_xdotool_bundle.py --push (neu apt van treo)
   5) @GLM: quyet dinh recipe moi - kernel_v23a (cua GLM, 0 FAIL) hay kernel_v23 (cu trong queue,
      dang 409 + recipe CU khong co done_rate) => bo queue entry sft-v23 neu khong dung""")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
