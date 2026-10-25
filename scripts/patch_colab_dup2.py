# -*- coding: utf-8 -*-
"""
patch_colab_dup2.py - xoa khoi trung policy_fn (lan 2) trong colab_desktop_replay.py.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_desktop_replay.py")

s = io.open(P, encoding="utf-8", newline="").read()
dup = '''                task = t

                def policy_fn(spec, peek, _pol=pol, _t=task):
                    def fn(obs):
                        _d, act = _pol.act("", _t, obs["step"])
                        return act_to_str(act) or "DONE"
                    return fn
                task = t

                def policy_fn(spec, peek, _pol=pol, _t=task):
                    def fn(obs):
                        _d, act = _pol.act("", _t, obs["step"])
                        return act_to_str(act) or "DONE"
                    return fn
'''
single = '''                task = t

                def policy_fn(spec, peek, _pol=pol, _t=task):
                    def fn(obs):
                        _d, act = _pol.act("", _t, obs["step"])
                        return act_to_str(act) or "DONE"
                    return fn
'''
if dup not in s:
    print("FAIL: khong tim thay khoi trung 2")
    sys.exit(1)
io.open(P, "w", encoding="utf-8", newline="").write(s.replace(dup, single, 1))
print("da xoa khoi trung 2")
