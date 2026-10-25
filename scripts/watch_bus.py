"""watch_bus.py - subscriber BUS: nhan tin NGAY va day thuc vao session
OpenCode hien tai (de agent khong phai cho/poll de biet co tin moi).

Nguon: SSE (uu tien) -> fallback polling /since moi 2s.
Khi co tin moi:
  1) in ra console + ghi scripts/bus.log
  2) 'beep' (winsound) de user nghe thay
  3) POST tin vao session OpenCode hien tai (api /api/session/<id>/message)
     -> agent duoc 'thuc' ngay, khong can cho vong poll
  4) ghi 1 dong ngan vao agent.md (durable) - chi khi nhac ro

Chay: python scripts/watch_bus.py
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "bus.log")
BUS = os.environ.get("BUS_URL", "http://127.0.0.1:8777")
SVC = os.path.join(os.environ.get("USERPROFILE", ""), ".config", "opencode",
                   "service.json")
sys.path.insert(0, os.path.join(HERE, "oc_chat"))
import engine  # noqa: E402  (tu tim port OpenCode + map agent)
import bus_policy  # noqa: E402

PORT = int(os.environ.get("OPENCODE_PORT", "0") or 0) or None
CHAT_URL = os.environ.get("OC_CHAT_URL", "http://127.0.0.1:8788")
SEND_SESSION = os.environ.get("BUS_PUSH_SESSION", "1") == "1"


def log(m):
    line = time.strftime("%H:%M:%S") + " " + m
    print(line, flush=True)
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def bus_get(path):
    try:
        with urllib.request.urlopen(BUS + path, timeout=6) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None


def oc_headers():
    return engine.headers()


def oc_session():
    """Session moi nhat (fallback khi khong map duoc agent)."""
    try:
        d = engine.sessions()
        d.sort(key=lambda s: (s.get("time") or {}).get("updated", 0)
               if isinstance(s.get("time"), dict) else 0, reverse=True)
        return d[0].get("id") if d else None
    except Exception as e:
        log("oc_session loi: %s" % str(e)[:80])
        return None


def oc_send(session_id, text):
    """Day tin vao session OpenCode (dung de 'thuc' agent ngay)."""
    if not session_id:
        return False
    try:
        engine.send(session_id, text)
        return True
    except urllib.error.HTTPError as e:
        log("oc_send HTTP %s" % e.code)
    except Exception as e:
        log("oc_send loi: %s" % str(e)[:80])
    return False


def chat_server_up():
    """Neu oc_chat server dang chay thi no lo relay (tranh day 2 lan)."""
    try:
        req = urllib.request.Request(CHAT_URL + "/api/health")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def beep():
    try:
        import winsound
        winsound.Beep(880, 120)
        winsound.Beep(1320, 160)
    except Exception:
        pass


SELF = os.environ.get("BUS_SELF", "DeepSeek")


def handle(m):
    if m.get("from") == SELF and os.environ.get("BUS_NO_ECHO", "1") == "1":
        # tin cua chinh ta: da gui truc tiep vao session agent khuc roi
        log("(bo echo tin cua ta: %s)" % str(m.get("text", ""))[:60])
        return
    ok, tgts, pri, why = bus_policy.should_push(m)
    if not ok:
        log("(khong push: %s | %s)" % (why, str(m.get("text", ""))[:60]))
        return
    txt = "[BUS %s%s] %s" % (m.get("from", "?"),
                            ("/" + m["tag"]) if m.get("tag") else "",
                            m.get("text", ""))
    log(txt)
    beep()
    if m.get("skip_relay"):
        log("(skip_relay)")
        return
    if chat_server_up():
        log("(oc_chat dang chay -> no relay, khong day lap)")
        return
    if SEND_SESSION:
        if tgts:
            for name in tgts:
                a = engine.agent_by_name(name)
                if not a:
                    log("khong tim thay agent '%s'" % name)
                    continue
                if oc_send(a.get("sid"), txt):
                    log("-> da day vao %s (%s)" % (a.get("name"), a.get("sid")))
            return
        n = 0
        for a in engine.refresh_agents().get("agents", []):
            if not a.get("enabled"):
                continue
            if engine._norm(a.get("name")) == engine._norm(m.get("from", "")):
                continue
            if oc_send(a.get("sid"), txt):
                n += 1
        log("-> da day vao %d session" % n)


def main():
    log("watch_bus: BUS=%s | push session=%s" % (BUS, SEND_SESSION))
    last = time.time() - 1
    seen = set()
    # lay tin chua xu ly (neu bus vua khoi dong)
    d = bus_get("/since?ts=%.3f" % max(0, last - 3600))
    if d:
        for m in d.get("messages", [])[-3:]:
            seen.add(m.get("ts"))
    while True:
        d = bus_get("/since?ts=%.3f" % last)
        if d:
            for m in d.get("messages", []):
                ts = m.get("ts", 0)
                if ts <= last or ts in seen:
                    continue
                seen.add(ts)
                last = max(last, ts)
                handle(m)
        time.sleep(1.5)


if __name__ == "__main__":
    main()
