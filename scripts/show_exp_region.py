# -*- coding: utf-8 -*-
"""show_exp_region.py - in khu vuc quanh mot chuoi trong EXP_SRC (string inline)."""
import io
import re
import sys

P = "phase13-gui/kernel_desktop_bench/desktop_bench_kernel.py"
s = io.open(P, encoding="utf-8").read()
i = s.find("EXP_SRC = ")
j = s.find("\n", i)
exp = s[i:j].replace("\\n", "\n").replace("\\'", "'").replace('\\\\', '\\')
needle = sys.argv[1] if len(sys.argv) > 1 else "for_inference(u_model)"
k = exp.find(needle)
print(exp[max(0, k - 1500):k + 700])
