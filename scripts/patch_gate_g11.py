# -*- coding: utf-8 -*-
"""
patch_gate_g11.py - them gate G11 vao prepush_gate.py: chan kernel mount
NHAM adapter LoRA (slug giong nhau nhung weights khac).

LY DO (22/10, @MiMo): acc B co 3 adapter:
    dieniw/ornith-gui-lora       -> weights KHAC v21 (max|diff|=0.11)  <== BAY
    dieniw/ornith-gui-lora-v21   -> weights GIONH v21
    dieniw/ornith-gui-lora-v22   -> weights GIONH v22
2 kernel da mount 'dieniw/ornith-gui-lora' => ket qua do la cua MODEL KHAC
=> khong dung lam baseline ma khong ai biet.

G11 quy tac:
  1) slug adapter nam trong 'traps' (da do weights, bi chung minh KHAC) -> FAIL
  2) slug adapter chua co trong scripts/lora_fingerprints.json -> WARN
     (chua chung minh trong so; hay chay scripts/lora_fingerprint.py --slug <slug>)
  3) kernel co 'expected_adapter' trong metadata -> phai co DUNG slug do.

ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "prepush_gate.py")
REG = os.path.join(ROOT, "scripts", "lora_fingerprints.json")

ANCHOR = '''    # ---- G9: MOI dataset trong metadata deu phai TON TAI tren Kaggle.'''

G11 = '''    # ---- G11: KHONG MOUNT NHAM ADAPTER LoRA (slug giong, weights khac).
    # (22/10: acc B co 'dieniw/ornith-gui-lora' = adapter CU (max|diff|=0.11
    #  so v21) va 'dieniw/ornith-gui-lora-v21' = v21 THAT. 2 kernel da mount
    #  nham -> ket qua do la cua MODEL KHAC, khong dung lam baseline ma
    #  khong ai biet. => chan tai thoi diem PUSH.)
    try:
        _fps = json.load(io.open(os.path.join(HERE, "lora_fingerprints.json"),
                                 encoding="utf-8"))
    except Exception:
        _fps = {}
    _traps = {}
    for _slug, _info in _fps.items():
        if "BAI" in (_info.get("note") or ""):
            _traps[_slug] = _info.get("note") or ""
    _adapters = [d for d in (attached or [])
                 if "/" in d and "gui-lora" in d.split("/", 1)[1].lower()]
    if _adapters:
        _bad = [a for a in _adapters if a in _traps]
        if _bad:
            fail("G11 adapter LoRA da bi chung minh SAI (weights khac): %s - "
                 "%s. Khong dung adapter nay cho phep do (ket qua se cua model "
                 "khac ma khong ai biet). Dung slug co version suffix dung."
                 % (", ".join(_bad),
                    " | ".join(_traps[a] for a in _bad)))
        _unk = [a for a in _adapters if a not in _fps]
        if _unk:
            warn("G11 adapter chua co trong lora_fingerprints.json (chua chung "
                 "minh trong so): %s. Hay chay: python scripts/lora_fingerprint.py "
                 "--slug %s --register" % (", ".join(_unk), _unk[0]))
        else:
            info("G11 adapter: %s (da chung minh trong so)"
                 % ", ".join(sorted(_adapters)))
        _exp = (_md or {}).get("expected_adapter")
        if _exp and _exp not in (attached or []):
            fail("G11 kernel khai bao expected_adapter='%s' nhung khong attach "
                 "slug do (dang attach: %s)" % (_exp, ", ".join(_adapters)))

'''

s = io.open(P, encoding="utf-8", newline="").read()
if "G11" in s:
    print("da co G11 -> khong sua")
    sys.exit(0)
if ANCHOR not in s:
    print("FAIL: khong tim thay anchor G9")
    sys.exit(1)
s = s.replace(ANCHOR, G11 + ANCHOR, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da them G11 vao:", P)
