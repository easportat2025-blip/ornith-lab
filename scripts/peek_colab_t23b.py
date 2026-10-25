# -*- coding: utf-8 -*-
"""
peek_colab_t23b.py - in khoi adapter policy trong colab_desktop_replay.py.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
p = os.path.join(ROOT, "scripts", "colab_desktop_replay.py")
s = io.open(p, encoding="utf-8", errors="replace").read()
i = s.find('pol_cls = POL.get')
print(s[i:i + 620])
