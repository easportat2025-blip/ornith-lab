# -*- coding: utf-8 -*-
"""clean_disk.py - don dia de pipeline khong bi day (can cho viec tai dataset/base).
Xoa AN TOAN: file tam, cache pip, zip tai tam, output cu.
"""
import os
import shutil
import sys

TARGETS = [
    (os.path.expandvars(r"%LOCALAPPDATA%\Temp\opencode"), "logs shell"),
    (os.path.expandvars(r"%USERPROFILE%\.cache\pip"), "cache pip"),
    (os.path.expandvars(r"%USERPROFILE%\Desktop\New folder\phase13-gui\verify_ds"), "zip verify"),
    (os.path.expandvars(r"%USERPROFILE%\Desktop\New folder\phase13-gui\verify_ds_b"), "zip verify B"),
    (os.path.expandvars(r"%LOCALAPPDATA%\Temp\dsmatch"), "zip dsmatch"),
    (os.path.expandvars(r"%USERPROFILE%\Desktop\New folder\phase13-gui\out_traj_test"), "out cu"),
    (os.path.expandvars(r"%USERPROFILE%\Desktop\New folder\phase13-gui\tmp_pull"), "tmp pull"),
    (os.path.expandvars(r"%USERPROFILE%\Desktop\New folder\phase13-gui\tmp_pull8"), "tmp pull8"),
]


def du(p):
    t = 0
    for root, _d, files in os.walk(p):
        for f in files:
            try:
                t += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return t


def free():
    import ctypes
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p("C:\\"), ctypes.byref(free_bytes), None, None)
    return free_bytes.value / 1e9


print("truoc: C: con %.2f GB" % free())
for p, why in TARGETS:
    if os.path.isdir(p):
        s = du(p)
        try:
            shutil.rmtree(p, ignore_errors=True)
            print("  xoa %-46s %7.1f MB (%s)" % (p[-46:], s / 1e6, why))
        except Exception as e:
            print("  loi", p, e)
print("sau:   C: con %.2f GB" % free())
