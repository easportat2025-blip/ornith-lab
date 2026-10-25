# -*- coding: utf-8 -*-
"""
patch_colab_dup3.py - xoa khoi trung policy_fn (lan 2) dung text chinh xac.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_desktop_replay.py")
s = io.open(P, encoding="utf-8", newline="").read()
old = ("                task = t\n\n"
       "                def policy_fn(spec, peek, _pol=pol, _t=task):\n"
       "                    def fn(obs):\n"
       "                        _d, act = _pol.act(\"\", _t, obs[\"step\"])\n"
       "                        return act_to_str(act) or \"DONE\"\n"
       "                    return fn\n"
       "                task = t\n\n"
       "                def policy_fn(spec, peek, _pol=pol, _t=task):\n"
       "                    def fn(obs):\n"
       "                        _d, act = _pol.act(\"\", _t, obs[\"step\"])\n"
       "                        return act_to_str(act) or \"DONE\"\n"
       "                    return fn\n")
new = ("                task = t\n\n"
       "                def policy_fn(spec, peek, _pol=pol, _t=task):\n"
       "                    def fn(obs):\n"
       "                        _d, act = _pol.act(\"\", _t, obs[\"step\"])\n"
       "                        return act_to_str(act) or \"DONE\"\n"
       "                    return fn\n")
if old not in s:
    print("FAIL: khong tim thay khoi trung 3")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
print("da xoa khoi trung 3")
