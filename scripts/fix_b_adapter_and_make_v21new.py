# -*- coding: utf-8 -*-
"""
fix_b_adapter_and_make_v21new.py - 2 viec (22/10, @MiMo):

(1) FIX adapter SAI tren acc B:
    acc B co 3 adapter:
      dieniw/ornith-gui-lora        (tao 20/10 06:31) -> adapter CU hon v21
      dieniw/ornith-gui-lora-v21    (tao 21/10 07:31) -> ban copy v21 THAT
      dieniw/ornith-gui-lora-v22    (tao 22/10 00:24)
    => kernel nao mount 'dieniw/ornith-gui-lora' (khong co -v21/-v22) thi
    KHONG phai v21 => ket qua do la KHONG hop le cho 2x2 (v21, task CU).
    Da phat hien: out_bench_v155_B (0/18) va out_bench_v16_B (6/24) deu
    bi lo nhieu => KHONG dung lam baseline.

(2) DUNG o THIEU cua 2x2: (v21, task MOI)
    kernel dieniw/ornith-gui-bench-v155-v21new
      adapter: dieniw/ornith-gui-lora-v21 (v21 that)
      task   : dieniw/ornith-gui-bench-v155 (da verify = ban MOI, 11/11 file)

Dung: python scripts/fix_b_adapter_and_make_v21new.py
ASCII-only source.
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")

# slug adapter "cu" tren acc B (khong phai v21)
OLD_ACC_B_LORA = "dieniw/ornith-gui-lora"
TRUE_V21 = "dieniw/ornith-gui-lora-v21"

FIX_KERNELS = ["kernel_bench_v155_B", "kernel_bench_v16_B"]

# (src dir, dst dir, id moi, ghi chu)
NEW_KERNELS = [
    ("kernel_bench_v155_v21", "kernel_bench_v155_v21new_B",
     "dieniw/ornith-gui-bench-v155-v21new",
     "O THIEU 2x2: (v21, task MOI) - tach 'sua task' vs 'sua data'"),
]

SWAP = {
    "khoadangnguye/gemma12b-wheels": "dieniw/gemma12b-wheels",
    "khoadangnguye/ornith-gui-lora-v21": TRUE_V21,
    "khoadangnguye/ornith-offline-browsers":
        "dieniw/ornith-offline-browsers",
    "khoadangnguye/ornith-gui-bench-v155": "dieniw/ornith-gui-bench-v155",
}


def audit():
    """Moi kernel-metadata.json trong repo: dang mount adapter nao?"""
    print("== AUDIT adapter tren toan repo ==")
    n_bad = 0
    for base, _dirs, files in os.walk(ROOT):
        if "kernel-metadata.json" not in files:
            continue
        p = os.path.join(base, "py_k_cache", "")  # placeholder (khong dung)
        mp = os.path.join(base, "kernel-metadata.json")
        try:
            md = json.load(io.open(mp, encoding="utf-8"))
        except Exception:
            continue
        ds = md.get("dataset_sources") or []
        loras = [d for d in ds if "gui-lora" in d]
        if not loras:
            continue
        rel = os.path.relpath(mp, ROOT)
        bad = [d for d in loras if d.endswith("ornith-gui-lora")]
        flag = "  <-- ADAPTER CU (khong phai v21)" if bad else ""
        if bad:
            n_bad += 1
        print("   %-58s %s%s" % (rel, ",".join(loras), flag))
    print("   => %d kernel dang mount adapter CU" % n_bad)
    return n_bad


def fix_metadata(d):
    mp = os.path.join(d, "kernel-metadata.json")
    if not os.path.exists(mp):
        return False
    md = json.load(io.open(mp, encoding="utf-8"))
    ds = md.get("dataset_sources") or []
    if OLD_ACC_B_LORA not in ds:
        return False
    md["dataset_sources"] = [TRUE_V21 if d == OLD_ACC_B_LORA else d
                              for d in ds]
    io.open(mp, "w", encoding="utf-8", newline="\n").write(
        json.dumps(md, ensure_ascii=False, indent=1))
    return True


def build_new():
    for src_name, dst_name, kid, note in NEW_KERNELS:
        src = os.path.join(P13, src_name)
        dst = os.path.join(P13, dst_name)
        if not os.path.isdir(src):
            print("!! thieu %s" % src_name)
            continue
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            if f.endswith(".py") or f.endswith(".json"):
                shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        mp = os.path.join(dst, "kernel-metadata.json")
        md = json.load(io.open(mp, encoding="utf-8"))
        md["dataset_sources"] = [SWAP.get(d, d)
                                  for d in md.get("dataset_sources", [])]
        md["id"] = kid
        md["title"] = kid.split("/")[-1]
        io.open(mp, "w", encoding="utf-8", newline="\n").write(
            json.dumps(md, ensure_ascii=False, indent=1))
        print("== %s -> %s" % (src_name, dst_name))
        print("   id  : %s" % kid)
        print("   note: %s" % note)
        for d in md["dataset_sources"]:
            print("      %s" % d)


def main():
    print("== (1) FIX adapter cu -> v21 that ==")
    for k in FIX_KERNELS:
        d = os.path.join(P13, k)
        if fix_metadata(d):
            print("   sua: %s (%s -> %s)" % (k, OLD_ACC_B_LORA, TRUE_V21))
        else:
            print("   khong can sua: %s" % k)
    print()
    print("== (2) DUNG o thieu (v21, task MOI) ==")
    build_new()
    print()
    audit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
