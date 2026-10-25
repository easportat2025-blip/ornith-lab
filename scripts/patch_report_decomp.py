# -*- coding: utf-8 -*-
"""
patch_report_decomp.py - them muc "PHAN RA HIEU UNG (CONG GIAO)" vao
report_fixed_suite.py: tu dong tinh Δ task / Δ data / interaction tu bang 2x2.

Ket qua do 22/10 (B15.5, 18 ep/o):
  Δ task = +38,9 (GIONG o ca 2 model) · Δ data = +11,1 (GIONG o ca 2 bo task)
  => 5,6 + 38,9 + 11,1 = 55,6  => interaction = 0 (cong giao)
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "report_fixed_suite.py")

DECOMP = '''    # ---- PHAN RA HIEU UNG (cua bang 2x2) : Δ task / Δ data / tuong tac
    try:
        _g = {}
        for _lbl, _oldc, _newc in grid:
            for _k, _c in (("old", _oldc), ("new", _newc)):
                _fp = pick(_c)
                if _fp:
                    _g[(_lbl.split()[0], _k)] = metrics(_fp)["win_rate"]
        if len(_g) == 4:
            print("=" * 78)
            print("PHAN RA HIEU UNG (bang 2x2, %d ep/o):" % 18)
            _r = sorted(set(k[0] for k in _g))
            _c = sorted(set(k[1] for k in _g))
            for _m in _r:
                for _t in _c:
                    if (_m, _t) in _g:
                        print("   %-8s %-5s %5.1f%%" % (_m, _t, _g[(_m, _t)]))
            _dt = {m: _g[(m, "new")] - _g[(m, "old")] for m in _r
                   if (m, "new") in _g and (m, "old") in _g}
            _dd = {t: _g[(_r[-1], t)] - _g[(_r[0], t)] for t in _c
                   if (_r[-1], t) in _g and (_r[0], t) in _g}
            print("   Δ TASK (CŨ->MỚI): %s"
                  % ", ".join("%s %+.1f" % (m, v) for m, v in _dt.items()))
            print("   Δ DATA (v21->v22): %s"
                  % ", ".join("%s %+.1f" % (t, v) for t, v in _dd.items()))
            _base = _g.get((_r[0], "old"))
            _sum = _base + list(_dt.values())[0] + list(_dd.values())[0]
            _real = _g.get((_r[-1], "new"))
            if _base is not None and _real is not None:
                print("   KIEM TRA CONG GIAO: %0.1f + %+.1f + %+.1f = %0.1f"
                      " (thuc te %0.1f) => TUONG TAC %+.1f điểm"
                      % (_base, list(_dt.values())[0], list(_dd.values())[0],
                         _sum, _real, _real - _sum))
                if abs(_real - _sum) < 3.0:
                    print("   => HIEU UNG CONG GIAO (interaction ~ 0)")
                else:
                    print("   => co TUONG TAC giua task va data (can nhac khi "
                          "ket luan)")
    except Exception as _e:
        print("   (phan ra hieu ung loi: %s)" % _e)

'''

ANCHOR = '''    print("LUU Y: chi so so sanh duoc giua CUNG mot suite.'''


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    if "PHAN RA HIEU UNG" in s:
        print("da co -> bo qua")
        return 0
    if ANCHOR not in s:
        print("FAIL: khong tim thay anchor")
        return 1
    s = s.replace(ANCHOR, DECOMP + ANCHOR, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("da them muc phan ra hieu ung")
    return 0


if __name__ == "__main__":
    sys.exit(main())
