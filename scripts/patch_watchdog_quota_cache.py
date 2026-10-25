"""patch_watchdog_quota_cache.py - cache quota 6h (user: check quota 1 lan/ngay)
va tach khoi logic push hang doi (push phai chay MOI 2 phut, khong bi chan)."""
import io

P = 'scripts/watchdog.py'
s = io.open(P, encoding='utf-8').read()

OLD = '''def gpu_remaining_hours():
    """Cot 'remaining' trong bang quota (cot 3), KHONG phai 'used' (cot 2)."""
    rc, out, err = run(["kaggle", "quota"], timeout=120)
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "GPU" and len(parts) >= 3:
            for cand in (parts[2], parts[1]):   # remaining, fallback used
                if cand.endswith("h"):
                    try:
                        return float(cand[:-1])
                    except ValueError:
                        pass
    return 0.0'''

NEW = '''QUOTA_CACHE = {"h": None, "ts": 0.0}


def gpu_remaining_hours():
    """Quota GPU con lai (h). CACHE 6h (user: check quota 1 lan/ngay) ->
    khong spam API, nhung van push duoc hang doi ngay."""
    now = time.time()
    if QUOTA_CACHE["h"] is not None and now - QUOTA_CACHE["ts"] < 21600:
        return QUOTA_CACHE["h"]
    rc, out, err = run(["kaggle", "quota"], timeout=120)
    val = 0.0
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "GPU" and len(parts) >= 3:
            for cand in (parts[2], parts[1]):
                if cand.endswith("h"):
                    try:
                        val = float(cand[:-1])
                        break
                    except ValueError:
                        pass
    QUOTA_CACHE["h"] = val
    QUOTA_CACHE["ts"] = now
    return val'''

assert OLD in s, 'khong khop gpu_remaining_hours'
s = s.replace(OLD, NEW, 1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('patched watchdog: quota cache 6h')
