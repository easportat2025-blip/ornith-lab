# -*- coding: utf-8 -*-
"""
scan_my_files.py - quet cac file nguon cua @MiMo de tim BIEN DONG BI NGUON
(ghi de khong doi mtime) + loi compile.

Tinh huong 22/10: scripts/test_gate_g11.py bi doi 'os.path.dirname' ->
'os.dirname' MA MTIME KHONG DOI => co thu gi do ghi de file trong workspace.
=> phai quet thuong xuyen, khong tin "vua ghi xong thi dung".

Dung: python scripts/scan_my_files.py
ASCII-only source.
"""
import io
import os
import py_compile
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"

FILES = [
    "scripts/klog.py", "scripts/check_dbench_kernel.py",
    "scripts/verify_bench_ds_version.py", "scripts/cmp_lora_weights.py",
    "scripts/cmp_ds_hashes.py", "scripts/lora_fingerprint.py",
    "scripts/test_gate_g11.py", "scripts/reorder_queue_b.py",
    "scripts/fix_b_adapter_and_make_v21new.py",
    "scripts/stage_v21_true_for_accB.py", "scripts/add_queue_b_measurements.py",
    "scripts/report_fixed_suite.py", "scripts/prepush_gate.py",
    "scripts/patch_gate_g11.py", "scripts/patch_report_grid.py",
    "scripts/patch_report_invalid.py",
    "phase14-desktop/harness.py", "phase14-desktop/test_infra_guard.py",
    "phase13-gui/make_desktop_bench.py",
    "phase13-gui/make_desktop_bench_split.py",
]

# mau cau can dung trong tung file (neu thieu => bi sua mat)
MUST = {
    "scripts/test_gate_g11.py": ["os.path.dirname(os.path.dirname(",
                                 "os.path.join(ROOT, \"phase13-gui\""],
    "scripts/lora_fingerprint.py": ["os.path.join(ROOT, \"scripts\"",
                                      "def fingerprint(path):"],
    "scripts/cmp_lora_weights.py": ["from safetensors.torch import safe_open"],
    "scripts/verify_bench_ds_version.py": ["def zip_hashes(zp):"],
    "phase14-desktop/harness.py": ["INFRA_ERRORS", "infra_errors.json",
                                   "(raw or \"\")[:2000]"],
    "phase13-gui/make_desktop_bench.py": ["thieu app file cho task",
                                          "GUARD OK"],
    "scripts/prepush_gate.py": ["G11 adapter LoRA da bi chung minh SAI"],
}


def main():
    n_bad = 0
    for rel in FILES:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            print("   [MISS] %s" % rel)
            n_bad += 1
            continue
        src = io.open(p, encoding="utf-8", errors="replace").read()
        prob = []
        for must in MUST.get(rel, []):
            if must not in src:
                prob.append("THIEU: %r" % must[:60])
        try:
            compile(src, rel, "exec")
        except SyntaxError as e:
            prob.append("SYNTAX: %s (line %s)" % (e.msg, e.lineno))
        # mau nguy hiem: 'os.dirname' (thi thieu .path)
        if "os.dirname(" in src:
            prob.append("CORRUPT: co 'os.dirname(' (thieu .path)")
        if ("os.path.join(HERE" in src and "HERE =" not in src
                and not rel.startswith("scripts/patch_")):
            prob.append("CORRUPT: os.path.join(HERE) - HERE khong ton tai?")
        print("   [%s] %s%s" % ("OK " if not prob else "BAD ", rel,
                               "" if not prob else "  -> " + "; ".join(prob)))
        if prob:
            n_bad += 1
    print("== %d file co van de ==" % n_bad)
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
