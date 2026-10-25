"""test_require_datasets.py - chong lai FALSE POSITIVE cua guard dataset
(GLM, 22/10).

Bug that: guard `require_datasets` (trong desktop-bench kernel) chi soi
    /kaggle/input/*/<slug>
nhưng Kaggle mount dataset cua acc KHAC o
    /kaggle/input/datasets/<owner>/<slug>   (2 cap)
=> 'ornbase-s1' ... co that bi bao THIEU => fail 2 run desktop-bench (mat slot
GPU) cho MOT LY DO SAI.

Test nay tao cay thu muc gia lap (1 cap + 2 cap) va kiem tra:
  - dataset o cap 1  => phai co (khong FAIL gia)
  - dataset o cap 2  => phai co (khong FAIL gia)
  - dataset that su  => phai bi bao THIEU (van bat loi that)

Dung: python phase14-desktop/test_require_datasets.py
"""
import io
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FAILS = []


def ok(cond, msg):
    print("  %s %s" % ("ok  " if cond else "FAIL", msg))
    if not cond:
        FAILS.append(msg)


def build_tree(base):
    """Cay input gia lap: 1 cap + 2 cap (datasets/<owner>/<slug>)."""
    for sub in ("khoadangnguye/ornith-gui-lora-v21",
                "dieniw/ornbase-s1",
                "dieniw/ornbase-s2",
                "datasets/khoadangnguye/ornith-gui-lora-v21",
                "datasets/dieniw/ornbase-s1",
                "datasets/dieniw/ornbase-s2",
                "dieniw/ornith-gui-xdotool"):
        os.makedirs(os.path.join(base, sub.replace("/", os.sep)), exist_ok=True)


def main():
    tmp = os.path.join(tempfile.gettempdir(), "glm_req_ds_test")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    build_tree(tmp)
    os.environ["DB_INPUT_ROOT"] = tmp

    # nap ham require_datasets tu kernel da build (dung thu code that)
    import re
    kp = os.path.join(ROOT, "phase13-gui", "kernel_desktop_bench",
                      "desktop_bench_kernel.py")
    src = io.open(kp, encoding="utf-8", errors="replace").read()
    i = src.find("def require_datasets")
    assert i > 0, "khong tim thay require_datasets trong kernel"
    j = src.find("\ndef write_apps", i)
    block = src[i:j if j > 0 else i + 2500]
    ns = {"os": os, "log": print, "SystemExit": SystemExit}
    exec(compile(block, "<guard>", "exec"), ns)
    require_datasets = ns["require_datasets"]

    print("== 1) dataset o CAP 1 va CAP 2 deu phai duoc nhan ==")
    try:
        require_datasets(["ornith-gui-lora-v21", "ornbase-s1", "ornbase-s2"])
        ok(True, "cap 1 + cap 2: khong FAIL gia")
    except SystemExit as e:
        ok(False, "FAIL GIA: %s" % str(e)[:120])

    print("== 2) dataset THAT SU THIEU van phai bi bat ==")
    try:
        require_datasets(["ornith-gui-lora-v21", "ornbase-s9-khong-co"])
        ok(False, "thieu dataset van khong bi bat")
    except SystemExit as e:
        ok("ornbase-s9-khong-co" in str(e), "bat duoc dataset thieu: %s" %
           str(e)[:90])

    print("== 3) layout 2 cap chuan cua Kaggle: datasets/<owner>/<slug> ==")
    os.makedirs(os.path.join(tmp, "datasets", "dieniw", "slug-x"),
                exist_ok=True)
    try:
        require_datasets(["slug-x"])
        ok(True, "datasets/<owner>/<slug>: nhan duoc")
    except SystemExit as e:
        ok(False, "datasets/<owner>/<slug> bi FAIL gia: %s" % str(e)[:90])

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FAILS:
        print("FAILED: %d -> %s" % (len(FAILS), FAILS))
        return 1
    print("ALL REQUIRE-DATASETS TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
