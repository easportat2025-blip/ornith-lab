"""selftest_suites.py - verify B15.5 + B16-A suite tren Kaggle THAT (CPU).

Muc dich: suite tu chay browser NOI BO nen can kiem chung trong moi truong
Kaggle (root, headless, clipboard) TRUOC khi ton GPU slot cho gate.
Tieu chi: moi task x 3 variant phai PASS voi success-policy (dummy actions).
Fail -> exit code != 0 (fail LOUD).
"""
import glob
import json
import os
import subprocess
import sys

WORK = "/kaggle/working"
os.makedirs(WORK, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
# TASK-22: Kaggle chi upload code_file -> dummy actions phai EMBED.
# (noi dung gan 6KB, them bang generator make_selftest_kernel.py)
ACTIONS = {
    "dummy_actions_v155.json": "{\n \"T13_wizard@0\": [\n  \"CLICK 322.2 440.3\",\n  \"CLICK 500 275\",\n  \"TYPE Alexanderthegreat\",\n  \"CLICK 500 398.6\",\n  \"TYPE user@example.com\",\n  \"CLICK 322.2 493.1\",\n  \"CLICK 500 275\",\n  \"TYPE Berlin\",\n  \"CLICK 500 372.2\",\n  \"TYPE 30\",\n  \"CLICK 322.2 440.3\",\n  \"CLICK 305.1 234\",\n  \"CLICK 356.5 290.3\"\n ],\n \"T13_wizard@1\": [\n  \"CLICK 322.2 440.3\",\n  \"CLICK 500 275\",\n  \"TYPE Alexanderthegreat\",\n  \"CLICK 500 398.6\",\n  \"TYPE user@example.com\",\n  \"CLICK 322.2 493.1\",\n  \"CLICK 500 275\",\n  \"TYPE Berlin\",\n  \"CLICK 500 372.2\",\n  \"TYPE 30\",\n  \"CLICK 322.2 440.3\",\n  \"CLICK 305.1 234\",\n  \"CLICK 356.5 290.3\"\n ],\n \"T13_wizard@2\": [\n  \"CLICK 322.2 440.3\",\n  \"CLICK 500 275\",\n  \"TYPE Alexanderthegreat\",\n  \"CLICK 500 398.6\",\n  \"TYPE user@example.com\",\n  \"CLICK 322.2 493.1\",\n  \"CLICK 500 275\",\n  \"TYPE Berlin\",\n  \"CLICK 500 372.2\",\n  \"TYPE 30\",\n  \"CLICK 322.2 440.3\",\n  \"CLICK 305.1 234\",\n  \"CLICK 356.5 290.3\"\n ],\n \"T14_alerts@0\": [\n  \"CLICK 500 207\",\n  \"KEY End\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 500 629.2\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 500 500.1\"\n ],\n \"T14_alerts@1\": [\n  \"CLICK 500 207\",\n  \"KEY End\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 500 629.2\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 500 500.1\"\n ],\n \"T14_alerts@2\": [\n  \"CLICK 500 207\",\n  \"KEY End\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 500 629.2\",\n  \"CLICK 10 10\",\n  \"CLICK 10 10\",\n  \"CLICK 500 500.1\"\n ],\n \"T15_dialog@0\": [\n  \"CLICK 255.9 189.6\",\n  \"CLICK 10 10\",\n  \"CLICK 500 493.8\",\n  \"KEY End\",\n  \"CLICK 282 857.6\",\n  \"CLICK 690.6 857.6\",\n  \"CLICK 335.9 311.8\",\n  \"TYPE RF-4821\",\n  \"CLICK 246.4 385.4\",\n  \"CLICK 380.1 545.1\"\n ],\n \"T15_dialog@1\": [\n  \"CLICK 255.9 189.6\",\n  \"CLICK 10 10\",\n  \"CLICK 500 493.8\",\n  \"KEY End\",\n  \"CLICK 282 857.6\",\n  \"CLICK 690.6 857.6\",\n  \"CLICK 335.9 311.8\",\n  \"TYPE RF-7305\",\n  \"CLICK 246.4 385.4\",\n  \"CLICK 380.1 545.1\"\n ],\n \"T15_dialog@2\": [\n  \"CLICK 255.9 189.6\",\n  \"CLICK 10 10\",\n  \"CLICK 500 493.8\",\n  \"KEY End\",\n  \"CLICK 282 857.6\",\n  \"CLICK 690.6 857.6\",\n  \"CLICK 335.9 311.8\",\n  \"TYPE RF-1188\",\n  \"CLICK 246.4 385.4\",\n  \"CLICK 380.1 545.1\"\n ],\n \"T16_clipboard2@0\": [\n  \"CLICK 319.1 233.3\",\n  \"KEY ctrl+a\",\n  \"KEY ctrl+c\",\n  \"CLICK 680.9 233.3\",\n  \"KEY ctrl+v\",\n  \"CLICK 319.1 384.7\",\n  \"KEY ctrl+a\",\n  \"KEY ctrl+c\",\n  \"CLICK 680.9 384.7\",\n  \"KEY ctrl+v\",\n  \"CLICK 561.9 482.6\"\n ],\n \"T16_clipboard2@1\": [\n  \"CLICK 319.1 233.3\",\n  \"KEY ctrl+a\",\n  \"KEY ctrl+c\",\n  \"CLICK 680.9 233.3\",\n  \"KEY ctrl+v\",\n  \"CLICK 319.1 384.7\",\n  \"KEY ctrl+a\",\n  \"KEY ctrl+c\",\n  \"CLICK 680.9 384.7\",\n  \"KEY ctrl+v\",\n  \"CLICK 561.9 482.6\"\n ],\n \"T16_clipboard2@2\": [\n  \"CLICK 319.1 233.3\",\n  \"KEY ctrl+a\",\n  \"KEY ctrl+c\",\n  \"CLICK 680.9 233.3\",\n  \"KEY ctrl+v\",\n  \"CLICK 319.1 384.7\",\n  \"KEY ctrl+a\",\n  \"KEY ctrl+c\",\n  \"CLICK 680.9 384.7\",\n  \"KEY ctrl+v\",\n  \"CLICK 561.9 482.6\"\n ],\n \"T17_reorder@0\": [\n  \"CLICK 435.2 429.2\",\n  \"CLICK 435.2 348.6\",\n  \"CLICK 435.2 268.1\",\n  \"CLICK 435.2 348.6\",\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 429.2\",\n  \"CLICK 161.5 599.3\"\n ],\n \"T17_reorder@1\": [\n  \"CLICK 435.2 268.1\",\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 429.2\",\n  \"CLICK 435.2 348.6\",\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 429.2\",\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 590.3\",\n  \"CLICK 161.5 679.9\"\n ],\n \"T17_reorder@2\": [\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 429.2\",\n  \"CLICK 435.2 348.6\",\n  \"CLICK 435.2 670.8\",\n  \"CLICK 435.2 590.3\",\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 429.2\",\n  \"CLICK 435.2 509.7\",\n  \"CLICK 435.2 590.3\",\n  \"CLICK 161.5 760.4\"\n ],\n \"T18_countsubmit@0\": [\n  \"CLICK 178.1 205.6\",\n  \"CLICK 245.4 205.6\",\n  \"CLICK 312.6 205.6\",\n  \"CLICK 379.8 205.6\",\n  \"CLICK 198.3 352.1\"\n ],\n \"T18_countsubmit@1\": [\n  \"CLICK 178.1 205.6\",\n  \"CLICK 245.4 205.6\",\n  \"CLICK 312.6 205.6\",\n  \"CLICK 379.8 205.6\",\n  \"CLICK 447 205.6\",\n  \"CLICK 514.3 205.6\",\n  \"CLICK 198.3 352.1\"\n ],\n \"T18_countsubmit@2\": [\n  \"CLICK 178.1 205.6\",\n  \"CLICK 245.4 205.6\",\n  \"CLICK 312.6 205.6\",\n  \"CLICK 379.8 205.6\",\n  \"CLICK 447 205.6\",\n  \"CLICK 514.3 205.6\",\n  \"CLICK 581.5 205.6\",\n  \"CLICK 198.3 352.1\"\n ]\n}",
    "dummy_actions_v16.json": "{\n \"T19_wizardsum@0\": [\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 321.9 218.8\",\n  \"TYPE 14\",\n  \"CLICK 449 218.8\"\n ],\n \"T19_wizardsum@1\": [\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 321.9 218.8\",\n  \"TYPE 16\",\n  \"CLICK 449 218.8\"\n ],\n \"T19_wizardsum@2\": [\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 262.8 275.7\",\n  \"CLICK 321.9 218.8\",\n  \"TYPE 17\",\n  \"CLICK 449 218.8\"\n ],\n \"T20_distractor@0\": [\n  \"CLICK 383.6 263.2\"\n ],\n \"T20_distractor@1\": [\n  \"CLICK 280.5 263.2\"\n ],\n \"T20_distractor@2\": [\n  \"CLICK 486.7 263.2\"\n ],\n \"T21_hiddenval@0\": [\n  \"CLICK 277.2 281.3\",\n  \"CLICK 321.9 218.8\",\n  \"TYPE K\",\n  \"CLICK 449 218.8\"\n ],\n \"T21_hiddenval@1\": [\n  \"CLICK 277.2 281.3\",\n  \"CLICK 321.9 218.8\",\n  \"TYPE 4\",\n  \"CLICK 449 218.8\"\n ],\n \"T21_hiddenval@2\": [\n  \"CLICK 277.2 281.3\",\n  \"CLICK 321.9 218.8\",\n  \"TYPE W\",\n  \"CLICK 449 218.8\"\n ],\n \"T22_keynav@0\": [\n  \"KEY ArrowDown\",\n  \"KEY ArrowRight\",\n  \"KEY ArrowRight\",\n  \"KEY Enter\"\n ],\n \"T22_keynav@1\": [\n  \"KEY ArrowDown\",\n  \"KEY ArrowDown\",\n  \"KEY Enter\"\n ],\n \"T22_keynav@2\": [\n  \"KEY ArrowRight\",\n  \"KEY Enter\"\n ],\n \"T23_undoredo@0\": [\n  \"CLICK 317.2 210.4\",\n  \"TYPE aaa\",\n  \"CLICK 487.8 210.4\",\n  \"TYPE bbb\",\n  \"CLICK 658.4 210.4\",\n  \"TYPE ccc\",\n  \"CLICK 264.8 272.9\",\n  \"CLICK 264.8 272.9\",\n  \"CLICK 330 272.9\"\n ],\n \"T23_undoredo@1\": [\n  \"CLICK 317.2 210.4\",\n  \"TYPE aaa\",\n  \"CLICK 487.8 210.4\",\n  \"TYPE bbb\",\n  \"CLICK 658.4 210.4\",\n  \"TYPE ccc\",\n  \"CLICK 264.8 272.9\",\n  \"CLICK 264.8 272.9\",\n  \"CLICK 330 272.9\"\n ],\n \"T23_undoredo@2\": [\n  \"CLICK 317.2 210.4\",\n  \"TYPE aaa\",\n  \"CLICK 487.8 210.4\",\n  \"TYPE bbb\",\n  \"CLICK 658.4 210.4\",\n  \"TYPE ccc\",\n  \"CLICK 264.8 272.9\",\n  \"CLICK 264.8 272.9\",\n  \"CLICK 330 272.9\"\n ],\n \"T24_multifilter@0\": [\n  \"CLICK 276.5 218.8\",\n  \"CLICK 462.2 218.8\",\n  \"CLICK 500 276.4\",\n  \"CLICK 293.8 334\"\n ],\n \"T24_multifilter@1\": [\n  \"CLICK 276.5 218.8\",\n  \"CLICK 462.2 218.8\",\n  \"CLICK 500 276.4\",\n  \"CLICK 293.8 334\"\n ],\n \"T24_multifilter@2\": [\n  \"CLICK 276.5 218.8\",\n  \"CLICK 462.2 218.8\",\n  \"CLICK 500 276.4\",\n  \"CLICK 293.8 334\"\n ],\n \"T25_compute@0\": [\n  \"CLICK 330.1 302.1\",\n  \"TYPE 8\",\n  \"CLICK 269 359\"\n ],\n \"T25_compute@1\": [\n  \"CLICK 330.1 302.1\",\n  \"TYPE 10\",\n  \"CLICK 269 359\"\n ],\n \"T25_compute@2\": [\n  \"CLICK 330.1 302.1\",\n  \"TYPE 10\",\n  \"CLICK 269 359\"\n ],\n \"T26_distractorlist@0\": [\n  \"CLICK 355.5 227\",\n  \"CLICK 251 436\"\n ],\n \"T26_distractorlist@1\": [\n  \"CLICK 644.5 279.8\",\n  \"CLICK 251 436\"\n ],\n \"T26_distractorlist@2\": [\n  \"CLICK 355.5 332.6\",\n  \"CLICK 251 436\"\n ]\n}",
}


def sh(cmd, timeout=1800):
    print("+ " + cmd, flush=True)
    p = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    print(out[-3000:], flush=True)
    if err.strip():
        print("STDERR:", err[-1500:], flush=True)
    return p.returncode


def find_suite(name):
    for root, _dirs, files in os.walk("/kaggle/input"):
        if name in files:
            return os.path.dirname(os.path.join(root, name))
    return None


def install_playwright():
    """Dung OFFLINE browsers setup (nhu bench kernel) — image Kaggle THIEU lib
    chromium (libatk-1.0.so.0...) nen pip install playwright se fail launch.
    Snippet trong dataset hhjiji/ornith-offline-browsers: copy browser -> /tmp,
    replay deps (142 file) + ldconfig, verify V1-V6."""
    import sys
    helper = None
    for root, _dirs, files in os.walk("/kaggle/input"):
        if "setup_playwright_offline.py" in files:
            helper = root
            break
    if not helper:
        print("KHONG thay setup_playwright_offline.py - that", flush=True)
        return False
    sys.path.insert(0, helper)
    from setup_playwright_offline import setup_playwright_offline
    info = setup_playwright_offline()
    print("offline browsers OK: %s" % str(info)[:300], flush=True)
    return True


def run_suite(label, module_file, actions_file, out_json):
    d = find_suite(module_file)
    if not d:
        print("[%s] KHONG TIM THAY %s trong /kaggle/input" % (label, module_file),
              flush=True)
        return None
    print("[%s] suite dir: %s" % (label, d), flush=True)
    # TASK-22: Kaggle CHI upload code_file -> file phu (dummy actions) phai
    # duoc EMBED trong script roi ghi ra /kaggle/working.
    af = os.path.join(WORK, actions_file)
    if not os.path.exists(af):
        import json as _json
        blob = ACTIONS.get(actions_file)
        if blob is None:
            print("[%s] thieu actions %s" % (label, actions_file), flush=True)
            return None
        with open(af, "w", encoding="utf-8") as fh:
            fh.write(blob)
    cmd = ("cd %s && python %s --dummy %s --out %s"
           % (d, module_file, af, out_json))
    rc = sh(cmd, timeout=3600)
    if rc != 0 or not os.path.exists(out_json):
        print("[%s] RUN FAIL rc=%s" % (label, rc), flush=True)
        return {"ok": False, "n": 0, "n_pass": 0, "per_task": {}}
    res = json.load(open(out_json, encoding="utf-8"))
    per = {}
    for r in res:
        k = r.get("task_id")
        d2 = per.setdefault(k, [0, 0])
        d2[0] += 1
        d2[1] += 1 if r.get("success") else 0
    n = len(res)
    n_pass = sum(1 for r in res if r.get("success"))
    print("[%s] %d/%d PASS" % (label, n_pass, n), flush=True)
    for k in sorted(per):
        print("   %-18s %d/%d %s" % (k, per[k][1], per[k][0],
                                     "" if per[k][1] == per[k][0] else "<<< FAIL"),
              flush=True)
        if per[k][1] != per[k][0]:
            for r in res:
                if r.get("task_id") == k and not r.get("success"):
                    print("      v%s reason: %s" % (r.get("variant"),
                                                  str(r.get("reason"))[:200]),
                          flush=True)
    return {"ok": n_pass == n and n > 0, "n": n, "n_pass": n_pass,
            "per_task": {k: v for k, v in per.items()}}


def main():
    if not install_playwright():
        print("SELFTEST FAIL: khong setup duoc offline browser", flush=True)
        return 1
    report = {}
    report["b155"] = run_suite("b155", "bench_v155.py",
                               "dummy_actions_v155.json",
                               os.path.join(WORK, "b155_dummy.json"))
    report["b16"] = run_suite("b16", "bench_v16.py",
                              "dummy_actions_v16.json",
                              os.path.join(WORK, "b16_dummy.json"))
    with open(os.path.join(WORK, "selftest_report.json"), "w",
              encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    bad = [k for k, v in report.items()
           if not v or not v.get("ok")]
    if bad:
        print("SELFTEST FAIL: " + ", ".join(bad), flush=True)
        return 1
    print("SELFTEST OK (b155 + b16)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
