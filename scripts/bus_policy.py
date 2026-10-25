# -*- coding: utf-8 -*-
"""bus_policy.py - QUYET DINH tin nao duoc DAY vao session agent.

Van de (23/10): moi tin bus deu duoc push vao MOI session => agent bi ngat
quang lien tuc, user bi flood. Nhu cau that: chi day thu THAT SU QUAN TRONG.

Quy tac (YAGNI - 4 dong):
  1. Tin co 'to' (hoac @Ten trong text) -> chi day cho dung nguoi do.
  2. Tin 'critical' (co ket qua + con so, hoac --priority critical)
     -> broadcast, nhung gioi han 1 tin / 8 phut / nguoi gui,
        1 tin / 90 giay toan he.
  3. Tin 'normal' -> KHONG push; nam trong bus.jsonl + phong OpenChat
     (ai can thi doc, hoac chay scripts/bus_digest.py).
  4. Tin 'low' (ack, thanks, < 80 ky tu khong co so) -> khong push.

Muc dich: giam ca tan suat GUI (bus_post chan tin lap/burst) lan tan suat
NHAN (chi critical/targeted moi vao session).

Dung tu consumer:
    import bus_policy
    ok, targets, pri, why = bus_policy.should_push(m)
    # ok=False -> chi mirror vao UI, khong push session
"""
import re
import threading
import time
import unicodedata

# ---------------------------------------------------------------- phan loai
SIGNAL = re.compile(
    r"\b(pass|fail|done|xong|verified|resolve|uploaded|blocked|ket qua|"
    r"result|win|loi|quota|reset|gate|release|crash|bug|fix|pushed)\b")
NUMBER = re.compile(r"\d+\s*/\s*\d+|\d+(?:\.\d+)?\s*%|\b\d{2,4}\b")
ACK = re.compile(r"^(ok|oke|okay|da hieu|roger|thanks|cam on|hi|hello|chao|"
                 r"xong|nhan|da nhan)\b")
MENTION = re.compile(r"@([A-Za-z][A-Za-z0-9_]{1,19})")

# ---------------------------------------------------------------- gioi han
CRIT_PER_SENDER = 8 * 60       # 1 critical / 8 phut / nguoi gui
CRIT_GLOBAL = 90               # 1 critical / 90 giay toan he
DUP_WINDOW = 30 * 60           # tin lap trong 30 phut = bo

_LOCK = threading.Lock()
_LAST_SENDER = {}
_LAST_GLOBAL = 0.0
_SEEN = {}


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def classify(text, explicit=None):
    """-> 'critical' | 'normal' | 'low'."""
    if explicit in ("critical", "normal", "low"):
        return explicit
    t = norm(text)
    if not t:
        return "low"
    if ACK.match(t) and len(t) < 160:
        return "low"
    if SIGNAL.search(t) and NUMBER.search(t):
        return "critical"
    if len(t) < 80 and not NUMBER.search(t):
        return "low"
    return "normal"


def targets_of(m):
    """Danh sach agent duoc nhac (to + @mention).

    @mention chi tinh la 'goi' khi tin NGAN (<=600 ky tu) hoac mention nam
    ngay dau tin. Bao cao dai hay nhac ten trong cau ke -> khong push.
    """
    raw = (m.get("to") or "").strip()
    names = [x.strip() for x in raw.split(",") if x.strip()]
    if not names:
        text = (m.get("text") or "")
        if len(text) <= 600 or MENTION.search(text[:80]):
            names = MENTION.findall(text)
    # bo trung, giu thu tu
    out = []
    seen = set()
    for n in names:
        k = norm(n)
        if k and k not in seen:
            seen.add(k)
            out.append(n)
    return out


def _hash(m):
    return (norm(m.get("from")) + "|" + norm(m.get("text"))[:400])


def should_push(m, now=None):
    """-> (ok, targets, priority, reason).

    ok=True  : duoc phep day (targets rong = broadcast)
    ok=False : chi mirror UI / nam trong bus
    """
    global _LAST_GLOBAL
    now = time.time() if now is None else now
    frm = (m.get("from") or "?").strip()
    text = (m.get("text") or "").strip()
    if norm(frm) in ("agent.md", "system", "lobby", "bus") and \
            m.get("priority") != "critical":
        pri = "normal"
    else:
        pri = classify(text, m.get("priority"))
    tg = targets_of(m)

    if m.get("skip_relay"):
        return False, [], pri, "skip_relay"

    # 1) targeted / mention: luon day (khong gioi han)
    if tg:
        return True, tg, pri, "targeted"

    # 2) tin lap
    with _LOCK:
        h = _hash(m)
        if now - _SEEN.get(h, 0) < DUP_WINDOW:
            return False, [], pri, "duplicate"
        _SEEN[h] = now
        if len(_SEEN) > 4000:
            for k in [k for k, v in _SEEN.items() if now - v > DUP_WINDOW]:
                _SEEN.pop(k, None)

    # 3) chi critical moi broadcast
    if pri != "critical":
        return False, [], pri, "not-critical(%s)" % pri

    with _LOCK:
        last_s = _LAST_SENDER.get(norm(frm), 0.0)
        if now - last_s < CRIT_PER_SENDER:
            return False, [], pri, "rate-sender(%ds)" % int(now - last_s)
        if now - _LAST_GLOBAL < CRIT_GLOBAL:
            return False, [], pri, "rate-global(%ds)" % int(now - _LAST_GLOBAL)
        _LAST_SENDER[norm(frm)] = now
        _LAST_GLOBAL = now
    return True, [], pri, "critical"


def stats():
    with _LOCK:
        return {"last_global": _LAST_GLOBAL,
                "senders": dict(_LAST_SENDER),
                "seen": len(_SEEN)}


if __name__ == "__main__":
    import json
    import sys
    for line in sys.stdin:
        line = line.strip()
        if line:
            m = json.loads(line)
            print(should_push(m))
