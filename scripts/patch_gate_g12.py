# -*- coding: utf-8 -*-
"""
patch_gate_g12.py - them gate G12 vao prepush_gate.py:
moi dataset ma CODE kernel yeu cau (require_datasets / load_ds_rows) deu phai
co THAT trong dataset_sources cua kernel-metadata.

LY DO (22/10, @MiMo): kernel desktop b3 chet sau 18' GPU:
  [dbench] FAIL: dataset thieu tren Kaggle (bi silent drop): ['ornith-gui-lora-v21']
vi metadata mount 'dieniw/ornith-gui-lora-v22' nhung code require lora-v21.
=> G9 (dataset attach ton tai) KHONG bat duoc vi ca 2 deu ton tai - chi
   KHAC NHAU TEN. => G12 bat dung loi nay TRUOC khi push.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "prepush_gate.py")

ANCHOR = '''    # ---- G11: KHONG MOUNT NHAM ADAPTER LoRA'''

G12 = '''    # ---- G12: dataset ma CODE yeu cau phai duoc ATTACH (cung ten).
    # (22/10: kernel b3 chet "FAIL: dataset thieu ... ['ornith-gui-lora-v21']"
    #  vi metadata mount lora-v22 con code require lora-v21 - G9 khong bat
    #  duoc vi ca 2 dataset deu TON TAI, chi khac ten.)
    try:
        _src = ""
        for _f in os.listdir(kdir):
            if _f.endswith(".py"):
                _src += io.open(os.path.join(kdir, _f), encoding="utf-8",
                                errors="replace").read()
        _req = set()
        for _m in re.finditer(r"require_datasets\\(\\s*\\[([^\\]]*)\\]", _src):
            for _n in re.findall(r"[\\"']([A-Za-z0-9_.-]{3,})[\\"']", _m.group(1)):
                _req.add(_n)
        if _req:
            _att = set()
            for _a in (attached or []):
                if "/" in _a:
                    _att.add(_a.split("/", 1)[1])
                else:
                    _att.add(_a)
            _miss = sorted(n for n in _req if n not in _att)
            if _miss:
                fail("G12 code yeu cau dataset %s nhung KERNEL KHONG attach "
                     "dataset do (dang attach: %s). Kaggle se bo qua dataset "
                     "khong ton tai => kernel chet giua run. Sua metadata hoac "
                     "code yeu cau cho khop."
                     % (", ".join(_miss),
                        ", ".join(sorted(_att)) or "(khong co)"))
            else:
                info("G12 required dataset: %s -> da attach"
                     % ", ".join(sorted(_req)))

'''

s = io.open(P, encoding="utf-8", newline="").read()
if "G12" in s:
    print("da co G12 -> khong sua")
    sys.exit(0)
if ANCHOR not in s:
    print("FAIL: khong tim thay anchor G11")
    sys.exit(1)
s = s.replace(ANCHOR, G12 + ANCHOR, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da them G12 vao:", P)
