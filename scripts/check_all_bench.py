# -*- coding: utf-8 -*-
"""
check_all_bench.py - KIEM TRA TOAN BO trang thai benchmark trong 1 LENH.

Chay het: lint task (3 bo) + self-test (3 bo) + gate truoc push + phan tich ket qua
da co. Exit 0 = moi thu deu xanh.

    python scripts/check_all_bench.py
    python scripts/check_all_bench.py --quick     # bo self-test (nhanh)
ASCII-only source.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
LINT_DIRS = [
    "phase13-gui/bench_v15/tasks_v15_5/tasks",
    "phase13-gui/bench_v15/tasks_v16_a/tasks",
    "phase14-desktop/tasks",
    "phase13-gui/kernel_desktop_bench/apps",
]
SELFTESTS = [
    ("phase13-gui/bench_v15/tasks_v15_5", "checker.py", 18),
    ("phase13-gui/bench_v15/tasks_v16_a", "checker_v16.py", 24),
    ("phase14-desktop/tasks", "checker_desktop.py", 15),
]
RESULTS = [
    ("phase13-gui/out_bench_v15/b15_result.json", "v18 (B15)"),
    ("phase13-gui/out_bench_v21/b15_result.json", "v21 (B15)"),
    ("phase13-gui/out_bench_v155_v21/b15_result.json", "v21 (B15.5)"),
    ("phase13-gui/out_bench_v16_v21/b15_result.json", "v21 (B16-A)"),
]


def run(args, cwd=None):
    p = subprocess.run(args, capture_output=True, cwd=cwd or ROOT, timeout=3600)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out + err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    bad = 0

    print("=" * 72)
    print("1) LINT TASK (loi da lam san trong SFT)")
    for d in LINT_DIRS:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            print("   -- %s (khong co)" % d)
            continue
        rc, out = run([PY, os.path.join(ROOT, "scripts", "lint_bench_tasks.py"), p])
        last = [l for l in out.strip().splitlines() if l.startswith("TONG loi")]
        tot = last[-1] if last else "?"
        print("   %-52s %s" % (d, tot))
        if "TONG loi: 0" not in tot:
            bad += 1
            print("      " + "\n      ".join(l for l in out.splitlines()
                                              if l.strip().startswith("[")))

    if not a.quick:
        print("=" * 72)
        print("2) SELF-TEST (checker 2 chieu: success + fail-rejected)")
        for d, script, exp in SELFTESTS:
            p = os.path.join(ROOT, d)
            if not os.path.isdir(p):
                print("   -- %s (khong co)" % d)
                continue
            rc, out = run([PY, script, "--self-test"], cwd=p)
            line = [l for l in out.splitlines() if l.startswith("[self-test]")]
            print("   %-52s %s" % (d, line[-1] if line else "khong co ket qua"))
            if rc != 0:
                bad += 1
                print("      " + "\n      ".join(out.splitlines()[-8:]))
        # 2b) self-test du lieu synth (S1-S8 cu + 2 mode moi S9/S10) + test
        # phan hoi cua app (chong bug dong #status chet)
        for rel, script in (("phase13-gui", "test_synth_targeted.py"),
                            ("phase13-gui", "test_synth_new_modes.py"),
                            ("phase13-gui", "test_app_feedback.py")):
            p = os.path.join(ROOT, rel.replace("/", os.sep))
            if not os.path.exists(os.path.join(p, script)):
                print("   -- %s (khong co)" % script)
                continue
            rc, out = run([PY, script], cwd=p)
            line = [l for l in out.splitlines() if l.startswith("[test]")]
            print("   %-52s %s" % (script, line[-1] if line else "khong co ket qua"))
            if rc != 0:
                bad += 1
                print("      " + "\n      ".join(out.splitlines()[-8:]))

    print("=" * 72)
    print("3) PHAN TICH KET QUA DA CO (commit_rate / stuck_rate / P(DONE))")
    for rel, label in RESULTS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print("   -- %-22s (chua co)" % label)
            continue
        rc, out = run([PY, os.path.join(ROOT, "scripts", "analyze_bench_result.py"), p])
        for l in out.splitlines():
            if any(k in l for k in ("wins=", "COMMIT RATE", "STUCK RATE",
                                    "win o task NHIEU BUOC")):
                print("   %-16s %s" % (label, l.strip()))
        if "ERROR" in out:
            print("   %-16s (result loi - xem log)" % label)

    print("=" * 72)
    print("KET QUA: %d muc bi FAIL" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
