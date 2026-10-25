# -*- coding: utf-8 -*-
# fix_harness_docstring.py
# Dong docstring cua load_policy_model bi cat mat '"""' khi chen khoi VLLM
# -> phan sau thanh code (ky tu la -> loi SyntaxError).
import io

P = "phase14-desktop/harness.py"
s = io.open(P, encoding="utf-8").read()
MARK = "        return VLLMPolicy()\n\n    FIX (21/10):"
FIX = "        return VLLMPolicy()\n\n    \"\"\"\n\n    FIX (21/10):"
if MARK in s:
    s = s.replace(MARK, FIX, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da them dong dong docstring")
else:
    print("khong tim thay mau (co the da sua)")
try:
    compile(s, "x", "exec")
    print("compile OK")
except SyntaxError as e:
    print("van loi:", e.lineno, e.msg)
