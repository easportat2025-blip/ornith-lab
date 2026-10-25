# -*- coding: utf-8 -*-
"""
patch_colab_dup4.py - xoa cac dong 212-218 (0-indexed 211-217) trong
colab_desktop_replay.py (khoi trung policy_fn lan 2). Doc file, xoa, ghi.
ASCII-only source.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_desktop_replay.py")
lines = open(P, encoding="utf-8").read().split("\n")
# xoa dong 212..218 (1-indexed) => index 211..217
del lines[211:218]
with open(P, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines))
print("da xoa 7 dong (212-218). file bay gio co %d dong" % len(lines))
