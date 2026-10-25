"""desktop_bench_preflight.py - 1 LENH kiem tra moi thu truoc khi push
desktop-bench kernel (GLM, 22/10).

Gom tat ca gate/test cua project vao 1 lenh, in 1 bang, ket luan 1 dong.
Chi doc, khong can key/GPU/mang (prepush_gate co the can key cho G9 -> bo qua
neu khong co).

Dung:
  python phase13-gui/desktop_bench_preflight.py
  python phase13-gui/desktop_bench_preflight.py phase13-gui/kernel_desktop_bench_a
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
PY = sys.executable

DEFAULT_DIRS = ["phase13-gui/kernel_desktop_bench",
                "phase13-gui/kernel_desktop_bench_smoke",
                "phase13-gui/kernel_desktop_bench_a",
                "phase13-gui/kernel_desktop_bench_b"]


def run(args, label, cwd=ROOT):
    try:
        p = subprocess.run([PY] + args, capture_output=True, cwd=cwd,
                           timeout=1800)
        out = (p.stdout or b"").decode("utf-8", "replace")
        err = (p.stderr or b"").decode("utf-8", "replace")
        return p.returncode, out + err
    except Exception as e:
        return -1, str(e)


def verdict(rc, out, ok_patterns, bad_patterns=()):
    """ok_patterns: bat buoc co it nhat 1; bad_patterns: co => FAIL."""
    for b in bad_patterns:
        if b in out:
            return False, "co %r" % b
    for o in ok_patterns:
        if o in out:
            return True, o
    return False, "khong thay %s" % (ok_patterns or ["?"])


def main():
    dirs = sys.argv[1:] or DEFAULT_DIRS
    rows = []
    print("== 1) py_compile kernel ==")
    for d in dirs:
        f = os.path.join(d, "desktop_bench_kernel.py")
        rc, out = run(["-m", "py_compile", f], "compile")
        rows.append(("compile %s" % os.path.basename(d), rc == 0,
                     "rc=%s" % rc))

    print("== 2) prepush_gate (0 FAIL) ==")
    for d in dirs:
        rc, out = run(["scripts/prepush_gate.py", d], "gate")
        ok = ("FAIL" not in out.split("KET QUA")[-1]
              or "KET QUA: 0 FAIL" in out)
        rows.append(("gate %s" % os.path.basename(d), ok,
                     [l for l in out.splitlines() if "KET QUA" in l][:1]))

    print("== 3) check_inline_sync (MATCH) ==")
    rc, out = run(["phase13-gui/check_inline_sync.py"] + dirs, "sync")
    # [MISS] cho module SFT (gen_synth_*) la BINH THUONG: desktop kernel khong
    # inline module do. Chi [STALE]/LECH moi la loi.
    ok = ("LECH" not in out) and ("[STALE]" not in out)
    rows.append(("inline sync (%d kernel)" % len(dirs), ok,
                 "harness sha=%s" % (out.split("sha=")[-1].split()[0]
                                     if "sha=" in out else "?")))

    print("== 4) check_reward_js (0 loi) ==")
    for d in dirs:
        if not os.path.isdir(os.path.join(ROOT, d, "apps")):
            # variant (smoke/split) khong ship thu muc apps (kernel ghi app
            # luc runtime) => check tren kernel chinh, khong phai o day.
            continue
        rc, out = run(["phase13-gui/check_reward_js.py", d], "rewardjs")
        ok = "0 loi" in out
        rows.append(("reward js %s" % os.path.basename(d), ok,
                     [l for l in out.splitlines() if "KET QUA" in l][:1]))

    print("== 4b) app HTML cua MOI task phai co TRONG KERNEL (Kaggle chi upload code_file) ==")
    import ast
    import re as _re
    for d in dirs:
        kf = os.path.join(ROOT, d, "desktop_bench_kernel.py")
        if not os.path.isfile(kf):
            rows.append(("app inline %s" % os.path.basename(d), False,
                         "khong co file kernel"))
            continue
        ksrc = io.open(kf, encoding="utf-8", errors="replace").read()
        tbl = None
        for node in ast.parse(ksrc).body:
            if isinstance(node, ast.Assign) and \
                    getattr(node.targets[0], "id", "") == "TASK_TABLE":
                tbl = ast.literal_eval(node.value)
                break
        miss = []
        apps_dir = os.path.join(ROOT, "phase13-gui", "kernel_desktop_bench",
                                "apps")
        for tid, tv in (tbl or {}).items():
            fn = tv.get("app")
            if not fn:
                continue
            ap = os.path.join(apps_dir, fn)
            if not os.path.isfile(ap):
                miss.append("%s(app khong co)" % tid)
                continue
            s = io.open(ap, encoding="utf-8", errors="replace").read()
            m = _re.search(r"<title>([^<]{3,60})</title>", s)
            probe = (m.group(1).strip() if m else "")
            if probe and probe not in ksrc:
                miss.append("%s(%s)" % (tid, fn))
        rows.append(("app inline %s" % os.path.basename(d), not miss,
                     ("thieu: " + ", ".join(miss)) if miss else
                     "%d app trong kernel" % len(tbl or {})))

    print("== 5) lint_bench_tasks (0 loi) ==")
    for d in dirs:
        rc, out = run(["scripts/lint_bench_tasks.py", d], "lint")
        low = out.lower()
        ok = ("0 loi" in low) or ("khong phat hien loi" in low) \
            or ("khong co loi" in low)
        rows.append(("lint %s" % os.path.basename(d), ok,
                     [l for l in out.splitlines()
                      if "KET QUA" in l or "loi" in l.lower()][:1]))

    print("== 6) check_kernel_slugs (chi 4 kernel desktop) ==")
    rc, out = run(["phase13-gui/check_kernel_slugs.py", "--only",
                   "desktop_bench"], "slugs")
    ok = ("0 kernel CAN XEM LAI" in out) or ("OK: khong co trung" in out)
    rows.append(("kernel slugs (desktop)", ok,
                 [l for l in out.splitlines()
                  if "CAN XEM LAI" in l or "OK: khong co trung" in l][:1]))

    print("== 7) test_preflight + test_viewport_fix ==")
    rc, out = run(["phase14-desktop/test_preflight.py"], "t1")
    ok = "ALL PREFLIGHT TESTS PASSED" in out
    rows.append(("test_preflight", ok, "16 check"))
    rc, out = run(["phase14-desktop/test_viewport_fix.py"], "t2")
    ok = "ALL VIEWPORT TESTS PASSED" in out
    rows.append(("test_viewport_fix", ok, "15 check"))

    print()
    print("| check | ket qua | chi tiet |")
    print("|---|---|---|")
    nfail = 0
    for name, ok, det in rows:
        det = det if isinstance(det, str) else (det[0] if det else "")
        if not ok:
            nfail += 1
        print("| %s | %s | %s |" % (name, "PASS" if ok else "**FAIL**",
                                   str(det).replace("|", "/")[:90]))
    print()
    if nfail:
        print("=> PREFLIGHT FAIL (%d muc) - DO PUSH TRUOC" % nfail)
        return 1
    print("=> PREFLIGHT PASS: du dieu kien push (prepush_gate 0 FAIL, inline "
          "MATCH, reward js 0 loi, slug khong trung, 2 test PASS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
