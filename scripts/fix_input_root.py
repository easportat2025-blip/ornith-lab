# -*- coding: utf-8 -*-
"""fix_input_root.py - sua default cua INPUT_ROOT (tu tham chieu) trong kernel train."""
import io

BAD = 'INPUT_ROOT = os.environ.get("ORNITH_INPUT", INPUT_ROOT)'
GOOD = 'INPUT_ROOT = os.environ.get("ORNITH_INPUT", "/kaggle/input")'
for p in ["phase13-gui/kernel_v22/gui_sft_v22.py",
          "phase13-gui/kernel_v23/gui_sft_v23.py"]:
    s = io.open(p, encoding="utf-8").read()
    if BAD in s:
        s = s.replace(BAD, GOOD)
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("fixed", p)
    else:
        print("ok (khong can sua)", p)
