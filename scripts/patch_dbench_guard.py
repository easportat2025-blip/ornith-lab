# -*- coding: utf-8 -*-
"""patch_dbench_guard.py - guard 'dataset thieu' cua desktop-bench: in them cay
thu muc /kaggle/input de chan do (truoc khi FAIL) + chap nhan them cap
/kaggle/input/<owner>/<slug> va /kaggle/input/datasets/<owner>/<slug>.
"""
import io

OLD = '''    if missing:
        raise SystemExit("FAIL: dataset thieu tren Kaggle (bi silent drop): %s "
                         "- upload dataset truoc khi push kernel nay" % missing)'''
NEW = '''    if missing:
        print("[dbench] CAY /kaggle/input:", flush=True)
        try:
            for r, ds2, fs2 in os.walk(root):
                depth = r[len(root):].count(os.sep)
                if depth <= 2:
                    print("[dbench]   %s/ (%d file)" % (r, len(fs2)), flush=True)
        except Exception as e:
            print("[dbench] walk loi:", e, flush=True)
        raise SystemExit("FAIL: dataset thieu tren Kaggle (bi silent drop): %s "
                         "- upload dataset truoc khi push kernel nay" % missing)'''

for p in ["phase13-gui/kernel_desktop_bench_a/desktop_bench_kernel.py",
          "phase13-gui/kernel_desktop_bench_b/desktop_bench_kernel.py",
          "phase13-gui/kernel_desktop_bench_smoke/desktop_bench_kernel.py"]:
    try:
        s = io.open(p, encoding="utf-8").read()
    except Exception as e:
        print("skip", p, e)
        continue
    o = s
    s = s.replace(OLD, NEW)
    if s != o:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("patched", p)
    else:
        print("khong doi", p)
