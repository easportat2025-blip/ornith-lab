# -*- coding: utf-8 -*-
"""
patch_colab_t23b.py - thay khoi T23 (policy tay + class) bang policy factory
theo Playwright (toa do tinh bang peek).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_desktop_replay.py")

s = io.open(P, encoding="utf-8", newline="").read()
start = s.find('    # T23_table_sort:')
end = s.find('    POL["DummyTableSort"] = lambda: _T23Policy()', start)
if start < 0 or end < 0:
    print("FAIL: khong tim thay khoi T23")
    sys.exit(1)
end += len('    POL["DummyTableSort"] = lambda: _T23Policy()')
new_block = '''    # T23_table_sort: policy theo Playwright (toa do tinh bang peek).
    # run_task goi policy_fn({}, peek) -> fn(obs) => phai la HAM.
    def _t23_policy(spec, peek):
        def _rect(sel):
            return peek("(function(){const e=document.querySelector('%s');"
                        "if(!e) return null;const r=e.getBoundingClientRect();"
                        "return [Math.round((r.left+r.width/2)/innerWidth*1000),"
                        "Math.round((r.top+r.height/2)/innerHeight*1000)];})()"
                        % sel)
        def fn(obs):
            s = obs["step"]
            if s == 0:
                r = _rect("#hscore")
                return "CLICK %d %d" % (r[0], r[1])
            if s == 1:
                r = _rect("#hscore")
                return "CLICK %d %d" % (r[0], r[1])
            if s == 2:
                r = _rect("#tb tr")
                if r is None:
                    return "DONE"
                return "CLICK %d %d" % (r[0], r[1])
            if s == 3:
                r = _rect("#confirm")
                return "CLICK %d %d" % (r[0], r[1])
            return "DONE"
        return fn
    POL["DummyTableSort"] = _t23_policy'''
s = s[:start] + new_block + s[end:]
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da thay khoi T23 bang policy factory")
# kiem tra adapter call (pol = POL[...]()) -> voi factory pol la function, khong phai instance
# run_task goi policy_fn({}, peek) => voi _t23_policy (factory) -> fn(obs) => OK
# nhung code hien tai goi pol = POL[...]() => goi factory khong tham so => loi
# => sua: pol = POL[...] (khong goi) cho T23
old_adapter = '''                pol = POL[t["dummy"]]()'''
new_adapter = '''                if t["dummy"] == "DummyTableSort":
                    pol = POL[t["dummy"]]
                else:
                    pol = POL[t["dummy"]]()'''
if old_adapter in s:
    s = s.replace(old_adapter, new_adapter, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("da sua adapter call cho T23")
else:
    print("WARN: khong tim thay adapter call")
print("OK")
