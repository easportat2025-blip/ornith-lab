# -*- coding: utf-8 -*-
"""
patch_watchdog_ds_cache.py - CACHE 30' cho dataset_exists trong watchdog.py.

LY DO (22/10, @MiMo): watchdog kiem tra dataset cho MOI muc queue (9 dataset x
13 muc = ~117 lenh Kaggle moi vong 60s) => chay het quota API => Kaggle tra
429 "Too Many Requests" => lam CHAY luon ca luc tai adapter 465MB (publish
v24) => ton mat 10 phut moi lan.
=> cache theo slug, TTL 30 phut (dataset ton tai dai, khong can check lai moi
vong).
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "watchdog.py")

OLD = '''def dataset_exists(owner, slug, acc):
    """(state, n_file) voi state = exists | missing | unknown.'''

NEW = '''_DS_CACHE = {}
_DS_TTL = 1800   # 30 phut - xem ghi chu duoi


def dataset_exists(owner, slug, acc):
    """CACHE 30' (rat quan trong: 9 dataset x 13 muc queue x moi 60s = 117
    lenh Kaggle/phut => 429 'Too Many Requests' => lam chay download adapter
    465MB). Dataset ton tai dai => khong can check lai moi vong."""
    key = "%s/%s" % (owner, slug)
    hit = _DS_CACHE.get(key)
    if hit and (time.time() - hit[0]) < _DS_TTL:
        return hit[1], hit[2]
    state, n = _dataset_exists_raw(owner, slug, acc)
    _DS_CACHE[key] = (time.time(), state, n)
    return state, n


def _dataset_exists_raw(owner, slug, acc):
    """(state, n_file) voi state = exists | missing | unknown.'''

s = io.open(P, encoding="utf-8", newline="").read()
if "_DS_CACHE" in s:
    print("da co cache -> bo qua")
    sys.exit(0)
if OLD not in s:
    print("FAIL: khong tim thay dataset_exists")
    sys.exit(1)
s = s.replace(OLD, NEW, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da them cache 30' cho dataset_exists")
