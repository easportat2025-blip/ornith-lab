# -*- coding: utf-8 -*-
"""
patch_watchdog_gate.py - them check GATE (prepush_gate.py G1-G12) vao
watchdog.py TRUOC khi push.

LY DO (22/10, @MiMo): 2 kernel chet ngay tren Kaggle ton GPU vi:
  (a) code doi adapter (v21) nhung metadata mount v22 -> "dataset thieu"
  (b) adapter bi "BAI" (slug giong, weights khac) -> do sai model, khong ai biet
=> watchdog phai chay GATE truoc khi push, chan o day (0 GPU ton).

Cache: theo (dir, mtime kernel-metadata.json) + 15 phut => khong goi Kaggle
qua nhieu lan.

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "watchdog.py")

s = io.open(P, encoding="utf-8", newline="").read()
if "GATE_CACHE" in s:
    print("da co gate check -> khong sua")
    sys.exit(0)

# 1) helper (dat ngay truoc ham fetch)
HELPER = '''_GATE_CACHE = {"key": None, "t": 0, "ok": True, "out": ""}


def gate_check(kdir):
    """Chay prepush_gate.py (G1-G12) truoc khi push. Tra (ok, blob).

    FIX 22/10 (MiMo): 2 kernel chet ngay ton GPU vi code khong khop metadata
    va adapter 'bai' (slug giong, weights khac) => chan o day, 0 GPU.
    Cache theo (dir, mtime metadata) trong 15' de khong goi Kaggle nhieu lan.
    """
    mp = os.path.join(kdir, "kernel-metadata.json")
    try:
        stamp = int(os.path.getmtime(mp))
    except Exception:
        stamp = 0
    key = (kdir, stamp)
    if (_GATE_CACHE.get("key") == key and
            time.time() - _GATE_CACHE.get("t", 0) < 900):
        return _GATE_CACHE["ok"], _GATE_CACHE["out"]
    rc, out, err = run([sys.executable,
                        os.path.join(HERE, "prepush_gate.py"), kdir],
                       timeout=900)
    blob = (out or "") + (err or "")
    ok = ("KET QUA: 0 FAIL" in blob)
    _GATE_CACHE.update({"key": key, "t": time.time(), "ok": ok,
                        "out": blob})
    return ok, blob


'''

ANCHOR = "def fetch(kernel, outdir, pattern):"
if ANCHOR not in s:
    print("FAIL: khong tim thay anchor fetch()")
    sys.exit(1)
s = s.replace(ANCHOR, HELPER + ANCHOR, 1)

# 2) check truoc khi push
OLD_PUSH = '''        log("queue: push %s (%s)" % (kid, item.get("note", "")))'''
NEW_PUSH = '''        # FIX 22/10 (MiMo): GATE G1-G12 truoc khi push (chan loi "code doi
        # adapter" + "adapter bai" + "dataset thieu" o 0 GPU ton).
        g_ok, g_blob = gate_check(item["dir"])
        if not g_ok:
            g_lines = [l.strip() for l in g_blob.splitlines()
                       if "FAIL" in l or "G1" in l or "G9" in l or "G11" in l
                       or "G12" in l]
            log("queue %s: BO QUA push - GATE FAIL: %s"
                % (kid, " | ".join(g_lines[-4:])[:400]))
            bus_post("[watchdog] KHONG PUSH %s - GATE FAIL (G1-G12): %s"
                     % (kid, " | ".join(g_lines[-4:])[:400]), tag="queue")
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 600
            continue
        log("queue: push %s (%s)" % (kid, item.get("note", "")))'''
if OLD_PUSH not in s:
    print("FAIL: khong tim thay cho push")
    sys.exit(1)
s = s.replace(OLD_PUSH, NEW_PUSH, 1)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da them gate check vao watchdog.py")
