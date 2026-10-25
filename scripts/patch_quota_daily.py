"""patch_quota_daily.py - theo yeu cau user: KHIEM TRA QUOTA 1 LAN/NGAY
(thay vì 5 phút/lần) + len lich đúng lúc Kaggle refreshAt + cache quota cho
space_sync (dashboard) để khong ton API call.

1) scripts/watchdog.py:
   - QUOTA_EVERY 300 -> 86400
   - next_check = refreshAt + 5 phut (neu chua toi) else +24h
2) scripts/space_sync.py: cache quota 6 gio (ghi vao state.json)
"""
import io
import re

# ---------------- watchdog ----------------
p = 'scripts/watchdog.py'
s = io.open(p, encoding='utf-8').read()
s = s.replace("QUOTA_EVERY = 300          # 5 phong kiem tra 1 lan (tránh tốn API)",
              "QUOTA_EVERY = 86400        # theo yeu cau user: check quota 1 LAN/NGAY")
s = s.replace("QUOTA_EVERY = 300          # 5 phong kiem tra 1 lan (tránh tồn API)",
              "QUOTA_EVERY = 86400        # theo yeu cau user: check quota 1 LAN/NGAY")

# them ham next_quota_check + dung trong main loop
helper = '''

def quota_refresh_at():
    """Doc refreshAt tu bang quota (Kaggle tra) -> timestamp epoch (neu co)."""
    rc, out, err = run(["kaggle", "quota"], timeout=180)
    for line in (out + err).splitlines():
        parts = line.split()
        if parts and parts[0] == "GPU" and len(parts) >= 5:
            m = re.match(r"(\\d{4}-\\d{2}-\\d{2})T(\\d{2}:\\d{2}:\\d{2})", parts[4])
            if m:
                try:
                    import datetime
                    dt = datetime.datetime.strptime(
                        m.group(1) + " " + m.group(2),
                        "%Y-%m-%d %H:%M:%S")
                    return dt.timestamp()
                except Exception:
                    return None
    return None
'''
if 'def quota_refresh_at' not in s:
    s = s.replace('\ndef gpu_remaining_hours():', helper + '\ndef gpu_remaining_hours():', 1)

# main loop: len lich theo refreshAt
old = """        now = time.time()
        if now - last_quota_check > QUOTA_EVERY:
            last_quota_check = now"""
new = """        now = time.time()
        if now >= next_quota_check:
            last_quota_check = now
            _ra = quota_refresh_at()
            if _ra and _ra > now + 60:
                next_quota_check = _ra + 300      # dung luc quota về (+5 phut)
                log("next quota check: %s" %
                    time.strftime("%m-%d %H:%M", time.localtime(next_quota_check)))
            else:
                next_quota_check = now + QUOTA_EVERY"""
if old in s:
    s = s.replace(old, new, 1)
else:
    print('CANH: khong tim thay khoi ' + repr(old[:40]))

if 'next_quota_check = 0' not in s:
    s = s.replace("    last_quota_check = 0",
                  "    last_quota_check = 0\n    next_quota_check = 0", 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('patched', p)

# ---------------- space_sync: cache quota 6h ----------------
p2 = 'scripts/space_sync.py'
s2 = io.open(p2, encoding='utf-8').read()
old2 = '''def collect():
    st = {"ts": time.time()}
    st["quota"] = kaggle_cmd(["quota"])[:600]'''
new2 = '''QUOTA_CACHE = os.path.join(ROOT, "scripts", "quota_cache.json")
QUOTA_TTL = 6 * 3600          # dashboard: cache quota 6h (check thuc 1 lan/ngay)


def quota_cached():
    """Doc quota tu cache (TTL 6h) - khong goi Kaggle moi 3 phut mot lan."""
    try:
        d = json.load(io.open(QUOTA_CACHE, encoding="utf-8"))
        if time.time() - d.get("ts", 0) < QUOTA_TTL:
            return d.get("txt", "")
    except Exception:
        pass
    txt = kaggle_cmd(["quota"])[:600]
    try:
        with io.open(QUOTA_CACHE, "w", encoding="utf-8") as fh:
            json.dump({"ts": time.time(), "txt": txt}, fh)
    except Exception:
        pass
    return txt


def collect():
    st = {"ts": time.time()}
    st["quota"] = quota_cached()'''
if old2 in s2:
    s2 = s2.replace(old2, new2, 1)
    io.open(p2, 'w', encoding='utf-8', newline='').write(s2)
    print('patched', p2)
else:
    print('CANH: space_sync khong doi')
