"""Tao 2 ban SPLIT cua kernel desktop-bench (chay song song tren 2 acc A/B) de
giam thoi gian wall-clock (cung tong so buoc, nua thoi gian).

Tong so buoc 8 task x 20 ep xuong ~4048 buoc => 11-22h GPU tren 1 acc.
Chia 4 task/ban: 2 ban chay song song => ~6-11h (van dung so episode/task = 20).

LUU Y ACC (22/10): acc B KHONG attach duoc dataset PRIVATE cua acc A
(Kaggle bo qua dataset khong ton tai khi push) => ban "b" (acc B) tro toi
ban COPY cua acc B:
    phase13-gui/acc_b_staging/dieniw__ornith-gui-lora-v21
    phase13-gui/acc_b_staging/dieniw__ornith-offline-browsers
Upload 2 dataset do truoc roi moi push ban b.

Dung: python phase13-gui/make_desktop_bench_split.py
"""
import io
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "kernel_desktop_bench")

SPLITS = {
    # split A -> acc A (da push): dung dataset private cua acc A
    "a": ("T20_2048,T21_form,T22_calc,T24_text_edit", "khoadangnguye", {}),
    # split B -> acc B: doi 2 dataset sang ban copy cua acc B
    # (them T25_recovery: task do LOOP-recovery + read-before-act)
    "b": ("T21_form_desktop,T22_order,T23_keys,T23_table_sort,T25_recovery,"
          "T26_clipboard,T27_errorecover,T28_distractor",
          "dieniw", {
        "khoadangnguye/gemma12b-wheels": "dieniw/gemma12b-wheels",
        "khoadangnguye/ornith-gui-lora-v21": "dieniw/ornith-gui-lora-v21",
        "khoadangnguye/ornith-offline-browsers":
            "dieniw/ornith-offline-browsers",
        "khoadangnguye/ornith-gui-xdotool": "dieniw/ornith-gui-xdotool",
    }),
    # FIX 22/10 (MiMo): b3 = ban SAI + guard + adapter v22.
    # Ly do: run b2 (v21) da ghi "apps written" KHONG co 4 app cua @MiMo
    # => task co trong bang nhung khong co file => KHONG mo browser => anh X11
    # DEN => model thay "black screen" => DONE reward=-1 => 40/120 ep bi tinh
    # NHAM la model that. => b3 dung source moi (co guard fail-loud) + v22.
    "b3": ("T21_form_desktop,T22_order,T23_keys,T23_table_sort,T25_recovery,"
           "T26_clipboard,T27_errorecover,T28_distractor",
           "dieniw", {
        "khoadangnguye/gemma12b-wheels": "dieniw/gemma12b-wheels",
        "khoadangnguye/ornith-gui-lora-v21": "dieniw/ornith-gui-lora-v22",
        "khoadangnguye/ornith-offline-browsers":
            "dieniw/ornith-offline-browsers",
        "khoadangnguye/ornith-gui-xdotool": "dieniw/ornith-gui-xdotool",
    }),
}

# FIX 22/10 (MiMo): b3 chay 5 episode/task (validate nhanh).
EPISODES = {"b3": 5}
for tag, (tasks, acc, dsmap) in SPLITS.items():
    dst = os.path.join(HERE, "kernel_desktop_bench_%s" % tag)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    src = io.open(os.path.join(SRC, "desktop_bench_kernel.py"),
                  encoding="utf-8", errors="replace").read()
    m = re.search(r'os\.environ\.get\("DB_TASKS", "([^"]*)"\)', src)
    assert m, "khong tim thay placeholder DB_TASKS"
    src = (src[:m.start()]
           + 'os.environ.get("DB_TASKS", "%s")' % tasks
           + src[m.end():])
    # FIX 22/10 (MiMo): so episode co the gian khac nhau (b3 = 5 de validate
    # nhanh; acc B con ~12.4h GPU quota).
    eps = EPISODES.get(tag, 20)
    src = src.replace('os.environ.get("DB_EPISODES", "20")',
                      'os.environ.get("DB_EPISODES", "%d")' % eps)
    # FIX 22/10 (MiMo): adapter PHAI khai bao giong adapter ma split mount.
    # (b3 chet: code require_datasets doi lora-v21 nhung metadata mount lora-v22
    #  => "FAIL: dataset thieu tren Kaggle" sau 18' GPU.)
    _ad = dsmap.get("khoadangnguye/ornith-gui-lora-v21",
                    "khoadangnguye/ornith-gui-lora-v21").split("/")[-1]
    assert 'ADAPTER_NAME = "ornith-gui-lora-v21"' in src, \
        "builder khong co ADAPTER_NAME (can chay lai make_desktop_bench.py)"
    src = src.replace('ADAPTER_NAME = "ornith-gui-lora-v21"',
                      'ADAPTER_NAME = "%s"' % _ad)
    print("   adapter: %s" % _ad)
    io.open(os.path.join(dst, "desktop_bench_kernel.py"), "w",
            encoding="utf-8", newline="\n").write(src)
    meta = json.load(io.open(os.path.join(SRC, "kernel-metadata.json"),
                             encoding="utf-8"))
    if dsmap:
        meta["dataset_sources"] = [dsmap.get(d, d)
                                   for d in meta["dataset_sources"]]
    meta["id"] = "%s/ornith-gui-desktop-bench-%s" % (acc, tag)
    meta["title"] = "ornith-gui-desktop-bench-%s" % tag
    io.open(os.path.join(dst, "kernel-metadata.json"), "w", encoding="utf-8",
            newline="\n").write(json.dumps(meta, indent=1))
    print("wrote %-46s tasks=%s acc=%s" % (dst, tasks, acc))
print("=> push ca 2 (acc A + acc B chay song song)")
