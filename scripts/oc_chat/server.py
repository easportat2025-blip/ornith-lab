# -*- coding: utf-8 -*-
"""server.py - OpenChat relay/API for all OpenCode sessions.

Chay:
  python scripts/oc_chat/server.py --port 8788            # UI + API (legacy)
  python scripts/oc_chat/server.py --port 8788 --headless # API-only, nhe
  python scripts/oc_chat/server.py --port 8788 --headless --no-relay

Headless mode does not read/serve app.html. Agents use JSON endpoints:
  GET  /api/health       minimal liveness
  GET  /api/ping         presence + jobs + relay summary
  POST /api/ping         heartbeat: {agent,status,job,detail}
  GET  /api/jobs         read scripts/jobs/state.json
  GET  /api/logs?name=...&tail=200   tail a log under scripts/logs or phase13-gui
  POST /api/notify       append an event without pushing into a session
  GET  /api/events       event log
  POST /api/send         send a prompt to one or more agents (same as UI)

Luong du lieu:
  - UI gui tin  -> POST /api/send -> day prompt vao session dich + ghi event
  - Agent post bus (bus_post.py --to X) -> relay thread day vao session X
  - Agent tra loi -> relay thread poll message -> mirror vao phong + tra nguoc
    ve session cua agent da hoi (chat 2 chieu that su)
"""
import argparse
import io
import json
import os
import queue
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EVENTS = os.path.join(HERE, "events.jsonl")
BUS = os.path.join(ROOT, "scripts", "bus.jsonl")
APP = os.path.join(HERE, "app.html")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import engine  # noqa: E402
import bus_policy  # noqa: E402

PORT = int(os.environ.get("OC_CHAT_PORT", "8788"))
LOCK = threading.Lock()
CLIENTS = []
EVENT_SEQ = 0
SEEN_MSG = set()          # (sid, msgid) da mirror
PENDING = {}              # sid dich -> {origin, origin_sid, after}
BUS_POS = 0
RELAY_ON = True
BOOT = {"done": False}
RECENT = {}

# --- headless/API state ---------------------------------------------------
HEADLESS = os.environ.get("OC_CHAT_HEADLESS", "0").lower() in (
    "1", "true", "yes", "on")
START_TS = time.time()
JOBS_FILE = os.environ.get("OC_JOBS_FILE",
                           os.path.join(ROOT, "scripts", "jobs", "state.json"))
LOG_ROOTS = [
    os.path.join(ROOT, "scripts", "logs"),
    os.path.join(ROOT, "phase13-gui"),
    os.path.join(ROOT, "scripts", "jobs"),
]
PRESENCE = {}
PRESENCE_LOCK = threading.Lock()
ACTIVE_STATES = ("pending", "starting", "running", "fetching", "leased")


# ------------------------------------------------------------------ events
def _next_id():
    global EVENT_SEQ
    EVENT_SEQ += 1
    return "ev_%d_%d" % (int(time.time() * 1000), EVENT_SEQ)


def append_event(ev):
    ev.setdefault("ts", time.time())
    ev.setdefault("id", _next_id())
    with LOCK:
        try:
            with io.open(EVENTS, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        except Exception:
            pass
    for q in list(CLIENTS):
        try:
            q.put_nowait(ev)
        except Exception:
            pass
    return ev


def read_events(since=0.0, limit=400):
    out = []
    try:
        with io.open(EVENTS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("ts", 0) > since:
                    out.append(e)
    except Exception:
        pass
    return out[-limit:]


# --------------------------------------------------------------- api state
def _ts_key(v):
    """Best-effort sortable key for int/float/ISO timestamps."""
    if isinstance(v, (int, float)):
        return float(v)
    return str(v or "")


def _load_jobs(limit=40):
    """Read the shared job registry. Never returns secrets; read-only."""
    try:
        limit = max(1, min(int(limit or 40), 200))
    except Exception:
        limit = 40
    try:
        with io.open(JOBS_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception as e:
        return {"ok": False, "error": str(e)[:160], "jobs": [],
                "counts": {}, "total": 0, "now": time.time(),
                "path": os.path.relpath(JOBS_FILE, ROOT)}
    jobs = raw.get("jobs") if isinstance(raw, dict) else raw
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    if not isinstance(jobs, list):
        jobs = []
    out = []
    for j in jobs:
        if not isinstance(j, dict):
            continue
        out.append({
            "id": j.get("id") or "",
            "backend": j.get("backend") or "",
            "account": j.get("account") or "",
            "session": j.get("session") or "",
            "script": j.get("script") or "",
            "status": j.get("status") or "unknown",
            "created": j.get("created") or "",
            "started": j.get("started") or "",
            "finished": j.get("finished") or "",
            "log_path": j.get("log_path") or "",
            "artifacts": j.get("artifacts") or [],
            "keepalive_until": j.get("keepalive_until") or "",
            "attempts": j.get("attempts") or 0,
            "error": (j.get("error") or "")[:300],
            "meta": j.get("meta") or {},
        })
    out.sort(key=lambda x: _ts_key(x.get("created")), reverse=True)
    counts = {}
    for j in out:
        s = str(j.get("status") or "unknown")
        counts[s] = counts.get(s, 0) + 1
    active = sum(counts.get(s, 0) for s in ACTIVE_STATES)
    return {"ok": True, "path": os.path.relpath(JOBS_FILE, ROOT),
            "jobs": out[:limit], "counts": counts, "total": len(out),
            "active": active, "idle": active == 0, "now": time.time()}


def _presence_snapshot(ttl=1800):
    now = time.time()
    with PRESENCE_LOCK:
        items = [dict(v) for v in PRESENCE.values()]
    items = [x for x in items if now - float(x.get("ts", 0)) <= ttl]
    items.sort(key=lambda x: float(x.get("ts", 0)), reverse=True)
    return items


def _record_presence(body):
    now = time.time()
    name = str(body.get("agent") or body.get("name") or "unknown")[:64]
    status = str(body.get("status") or "online")[:32]
    job = str(body.get("job") or "")[:120]
    detail = str(body.get("detail") or "")[:500]
    rec = {
        "agent": name, "status": status, "job": job, "detail": detail,
        "host": str(body.get("host") or os.environ.get("COMPUTERNAME", ""))[:80],
        "pid": body.get("pid") or 0, "ts": now, "event_ts": 0,
    }
    with PRESENCE_LOCK:
        old = PRESENCE.get(name) or {}
        PRESENCE[name] = rec
    changed = (not old or old.get("status") != status or
               old.get("job") != job or old.get("detail") != detail or
               now - float(old.get("event_ts", 0)) > 300)
    if changed:
        rec["event_ts"] = now
        text = "status=%s" % status
        if job:
            text += " job=%s" % job
        if detail:
            text += " | " + detail
        append_event({"kind": "presence", "from": name, "to": "",
                      "tag": "heartbeat", "text": text[:1000]})
    return rec


def _ping_payload():
    jobs = _load_jobs(limit=20)
    agents = []
    try:
        agents = [{"name": a.get("name"), "sid": a.get("sid"),
                   "enabled": bool(a.get("enabled", True))}
                  for a in engine.load_agents().get("agents", [])]
    except Exception:
        pass
    active = int(jobs.get("active", 0) or 0)
    return {
        "ok": True, "headless": HEADLESS, "pid": os.getpid(),
        "host": os.environ.get("COMPUTERNAME", ""),
        "uptime": round(time.time() - START_TS, 1), "now": time.time(),
        "relay": RELAY_ON, "agents": agents,
        "presence": _presence_snapshot(), "jobs": jobs,
        "active_jobs": active, "idle": active == 0,
    }


def _tail_log(name, tail=200):
    """Tail a log file under allowed roots. Rejects traversal/absolute escapes."""
    try:
        tail = max(1, min(int(tail or 200), 2000))
    except Exception:
        tail = 200
    raw = str(name or "").replace("\\", "/").strip()
    if not raw:
        return None, "missing name"
    if raw.startswith("/") or raw.startswith("~") or ":" in raw:
        return None, "absolute path not allowed"
    parts = [p for p in raw.split("/") if p]
    if not parts or any(p in (".", "..") for p in parts):
        return None, "invalid path"
    roots = [os.path.abspath(r) for r in LOG_ROOTS]
    for root in roots:
        p = os.path.abspath(os.path.join(root, *parts))
        if not (p == root or p.startswith(root + os.sep)):
            continue
        if not os.path.isfile(p):
            continue
        try:
            size = os.path.getsize(p)
            if size > 32 * 1024 * 1024:
                return None, "file too large (max 32MB)"
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()[-tail:]
            return {"ok": True, "name": raw, "path": os.path.relpath(p, ROOT),
                    "size": size, "lines": [ln.rstrip("\r\n") for ln in lines],
                    "tail": tail}, ""
        except Exception as e:
            return None, str(e)[:160]
    return None, "not found under scripts/logs, phase13-gui, scripts/jobs"


def _rotate_events():
    """Keep events.jsonl bounded without deleting recent history."""
    try:
        if os.path.getsize(EVENTS) > 64 * 1024 * 1024:
            os.replace(EVENTS, EVENTS + ".1")
    except Exception:
        pass


# ------------------------------------------------------------------- relay
def _agent_for_sid(sid):
    for a in engine.load_agents()["agents"]:
        if a.get("sid") == sid:
            return a
    return None


def push_to(name=None, sid=None, text="", origin=None, expect_reply=False):
    """Day text vao 1 session. Tra (ok, err)."""
    if not sid and name:
        a = engine.agent_by_name(name)
        sid = (a or {}).get("sid")
    if not sid:
        return False, "khong tim thay session"
    try:
        engine.send(sid, text)
    except Exception as e:
        return False, str(e)[:160]
    if expect_reply and origin:
        PENDING[sid] = {"origin": origin.get("name"),
                        "origin_sid": origin.get("sid"),
                        "after": time.time(),
                        "text": text[:200]}
    return True, ""


def bus_loop():
    """Doc bus.jsonl lien tuc, mirror vao phong + relay dung nguoi nhan."""
    global BUS_POS
    try:
        BUS_POS = os.path.getsize(BUS)
    except Exception:
        BUS_POS = 0
    # seed 25 tin gan nhat de phong co ngu canh
    try:
        with io.open(BUS, encoding="utf-8") as fh:
            lines = fh.read().splitlines()[-25:]
        for line in lines:
            try:
                m = json.loads(line)
            except Exception:
                continue
            if _dup("bus", m.get("from", "?"), m.get("text") or ""):
                continue
            append_event({"ts": m.get("ts", time.time()), "kind": "bus",
                          "from": m.get("from", "?"), "to": m.get("to", ""),
                          "tag": m.get("tag", ""),
                          "text": (m.get("text") or "")[:4000],
                          "seeded": True})
    except Exception:
        pass
    while True:
        try:
            size = os.path.getsize(BUS)
            if size < BUS_POS:
                BUS_POS = 0
            if size > BUS_POS:
                with io.open(BUS, encoding="utf-8") as fh:
                    fh.seek(BUS_POS)
                    chunk = fh.read()
                    BUS_POS = fh.tell()
                for line in chunk.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    _handle_bus(m)
        except Exception:
            pass
        time.sleep(1.2)


def _dup(kind, frm, text):
    """Chan tin lap (bus hay bi post 2 lan: notify + lobby sync)."""
    key = (kind, engine._norm(frm), (text or "")[:200])
    t = time.time()
    if t - RECENT.get(key, 0) < 120:
        return True
    RECENT[key] = t
    return False


def _handle_bus(m):
    frm = (m.get("from") or "?").strip()
    to = (m.get("to") or "").strip()
    text = (m.get("text") or "").strip()
    if not text:
        return
    # tin cua chinh UI/relay thi bo qua
    if m.get("kind") in ("ui", "relay"):
        return
    if _dup("bus", frm, text):
        return
    ok, tgts, pri, why = bus_policy.should_push(m)
    append_event({"ts": m.get("ts", time.time()), "kind": "bus", "from": frm,
                  "to": to, "tag": m.get("tag", ""), "text": text[:4000],
                  "priority": pri, "pushed": bool(ok), "why": why})
    if not RELAY_ON or m.get("skip_relay"):
        return
    if not ok:
        return
    if tgts:
        origin = engine.agent_by_name(frm)
        for name in tgts:
            target = engine.agent_by_name(name)
            if not target:
                continue
            if origin and origin.get("sid") == target.get("sid"):
                continue
            push_to(sid=target.get("sid"),
                    text="[%s -> %s] %s" % (frm, name, text),
                    origin=origin, expect_reply=bool(origin))
    else:
        # broadcast: chi tin critical (policy da loc) - moi agent tru nguoi gui
        for a in engine.load_agents()["agents"]:
            if not a.get("enabled"):
                continue
            if engine._norm(a.get("name")) == engine._norm(frm):
                continue
            push_to(sid=a.get("sid"), text="[BUS %s] %s" % (frm, text))


def reply_loop():
    """Poll message cua tung session -> mirror tra loi + tra nguoc nguoi hoi."""
    while True:
        try:
            if not RELAY_ON:
                time.sleep(3)
                continue
            data = engine.refresh_agents()
            boot = not BOOT["done"]
            for a in data.get("agents", []):
                if not a.get("enabled") or not a.get("sid"):
                    continue
                try:
                    reps = engine.replies(a["sid"], a.get("name"), limit=8)
                except Exception:
                    continue
                if boot:
                    # lan dau: lay tin tra loi cuoi cung cua moi agent lam ngu canh
                    reps = reps[-1:]
                for r in reps:
                    key = (r["sid"], r.get("id"))
                    if key in SEEN_MSG:
                        continue
                    SEEN_MSG.add(key)
                    # khong mirror tin cu (truoc khi app chay) qua 10 phut
                    if not boot and time.time() - r["ts"] > 600:
                        continue
                    append_event({"ts": r["ts"], "kind": "reply",
                                  "from": a.get("name"), "to": "",
                                  "text": r["text"][:6000],
                                  "sid": r["sid"], "msgid": r.get("id"),
                                  "tools": r.get("tools", [])})
                    p = PENDING.get(r["sid"])
                    if p and r["ts"] >= p.get("after", 0) - 2:
                        origin_sid = p.get("origin_sid")
                        if origin_sid and origin_sid != r["sid"]:
                            body = ("[%s -> %s] %s" %
                                    (a.get("name"), p.get("origin"),
                                     r["text"][:1800]))
                            ok, err = push_to(sid=origin_sid, text=body)
                            append_event({"ts": time.time(), "kind": "relay",
                                          "from": a.get("name"),
                                          "to": p.get("origin"),
                                          "text": ("da tra loi %s" %
                                                   p.get("origin")) if ok else
                                                  ("relay loi: " + err),
                                          "ok": ok})
                        PENDING.pop(r["sid"], None)
            BOOT["done"] = True
        except Exception:
            pass
        time.sleep(3)


# -------------------------------------------------------------------- state
def state():
    port = None
    err = ""
    try:
        port = engine.discover()
        ss = engine.sessions()
    except Exception as e:
        ss = []
        err = str(e)[:200]
    try:
        act = engine.active_map()
    except Exception:
        act = {}
    ag = engine.refresh_agents()
    by_id = {s.get("id"): s for s in ss}
    agents = []
    for a in ag.get("agents", []):
        s = by_id.get(a.get("sid")) or {}
        agents.append({
            "name": a.get("name"),
            "sid": a.get("sid"),
            "role": a.get("role", ""),
            "color": engine.COLORS.get(a.get("name"), "#64748b"),
            "enabled": bool(a.get("enabled", True)),
            "title": s.get("title") or a.get("title") or "(session cu)",
            "model": (s.get("model") or {}).get("id") or a.get("model") or "",
            "updated": (s.get("time") or {}).get("updated") or a.get("updated") or 0,
            "active": a.get("sid") in act,
        })
    recent = sorted(ss, key=lambda s: (s.get("time") or {}).get("updated", 0),
                    reverse=True)[:40]
    return {
        "port": port, "error": err, "agents": agents,
        "sessions": [{"id": s.get("id"), "title": s.get("title"),
                      "model": (s.get("model") or {}).get("id"),
                      "updated": (s.get("time") or {}).get("updated", 0),
                      "active": s.get("id") in act} for s in recent],
        "relay": RELAY_ON, "now": time.time(),
    }


def transcript(sid, limit=40):
    ss = engine.sessions()
    title = ""
    for s in ss:
        if s.get("id") == sid:
            title = s.get("title") or ""
            break
    out = []
    for m in engine.raw_messages(sid, limit=limit):
        n = engine.norm_message(m, sid, "")
        if n:
            out.append(n)
    return {"sid": sid, "title": title, "messages": out}


# --------------------------------------------------------------------- http
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _html(self, path):
        try:
            data = open(path, "rb").read()
        except Exception:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _query(self):
        q = {}
        if "?" in self.path:
            for kv in self.path.split("?", 1)[1].split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    q[k] = urllib.parse.unquote(v)
        return q

    def do_GET(self):
        p = self.path.split("?")[0]
        q = self._query()
        try:
            if p == "/":
                if HEADLESS:
                    return self._json(200, {
                        "ok": True, "headless": True,
                        "api": ["/api/health", "/api/ping", "/api/jobs",
                                "/api/logs", "/api/events", "/api/send",
                                "/api/notify"]})
                return self._html(APP)
            if p == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if p == "/api/health":
                return self._json(200, {
                    "ok": True, "headless": HEADLESS, "pid": os.getpid(),
                    "uptime": round(time.time() - START_TS, 1)})
            if p in ("/api/ping", "/api/status"):
                return self._json(200, _ping_payload())
            if p == "/api/jobs":
                return self._json(200, _load_jobs(
                    int(q.get("limit", 40) or 40)))
            if p == "/api/presence":
                return self._json(200, {"presence": _presence_snapshot(),
                                        "now": time.time()})
            if p == "/api/logs":
                data, err = _tail_log(q.get("name", ""),
                                      int(q.get("tail", 200) or 200))
                if data is None:
                    return self._json(404, {"ok": False, "error": err})
                return self._json(200, data)
            if p == "/api/state":
                return self._json(200, state())
            if p == "/api/events":
                return self._json(200, {"events": read_events(
                    float(q.get("since", 0) or 0),
                    int(q.get("limit", 400) or 400))})
            if p == "/api/transcript":
                return self._json(200, transcript(q.get("sid", ""),
                                                  int(q.get("limit", 40) or 40)))
            if p == "/api/stream":
                return self._stream()
        except Exception as e:
            return self._json(500, {"error": str(e)[:200]})
        return self._json(404, {"error": "not found"})

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = queue.Queue()
        with LOCK:
            CLIENTS.append(q)
        try:
            self.wfile.write(b": hello\n\n")
            self.wfile.flush()
            while True:
                try:
                    ev = q.get(timeout=15)
                    self.wfile.write(("data: %s\n\n" % json.dumps(
                        ev, ensure_ascii=False)).encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except Exception:
            pass
        finally:
            with LOCK:
                if q in CLIENTS:
                    CLIENTS.remove(q)

    def do_POST(self):
        global RELAY_ON
        p = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length", 0) or 0)
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8", "replace")) if n else {}
        except Exception:
            body = {}
        try:
            if p == "/api/ping":
                rec = _record_presence(body)
                return self._json(200, {"ok": True, "presence": rec,
                                        "jobs": _load_jobs(limit=5)})
            if p == "/api/notify":
                text = (body.get("text") or "").strip()
                if not text:
                    return self._json(400, {"error": "thieu text"})
                ev = append_event({
                    "kind": body.get("kind") or "notify",
                    "from": body.get("from") or "agent",
                    "to": body.get("to") or "",
                    "tag": body.get("tag") or "",
                    "text": text[:4000],
                    "skip_relay": True,
                })
                return self._json(200, {"ok": True, "event": ev})
            if p == "/api/send":
                return self._send(body)
            if p == "/api/pin":
                return self._pin(body)
            if p == "/api/relay":
                RELAY_ON = bool(body.get("on"))
                append_event({"kind": "system", "from": "system", "to": "",
                              "text": "relay " + ("ON" if RELAY_ON else "OFF")})
                return self._json(200, {"ok": True, "relay": RELAY_ON})
            if p == "/api/clear":
                open(EVENTS, "w", encoding="utf-8").close()
                return self._json(200, {"ok": True})
        except Exception as e:
            return self._json(500, {"error": str(e)[:200]})
        return self._json(404, {"error": "not found"})

    def _send(self, body):
        text = (body.get("text") or "").strip()
        if not text:
            return self._json(400, {"error": "thieu text"})
        targets = body.get("targets") or []
        frm = body.get("from") or "user"
        results = []
        append_event({"kind": "user", "from": "user" if frm == "user" else frm,
                      "to": ", ".join(targets), "text": text[:4000]})
        agents = {a["name"]: a for a in engine.load_agents()["agents"]}
        for name in targets:
            a = agents.get(name)
            if not a:
                results.append({"name": name, "ok": False,
                                "error": "khong co agent"})
                continue
            prefix = ("[chat tu %s] " % frm) if frm != "user" else ""
            ok, err = push_to(sid=a.get("sid"), text=prefix + text,
                              origin={"name": frm, "sid": a.get("sid")},
                              expect_reply=(frm != "user"))
            results.append({"name": name, "ok": ok, "error": err})
        return self._json(200, {"ok": any(r["ok"] for r in results),
                                "results": results})

    def _pin(self, body):
        name = body.get("name")
        sid = body.get("sid")
        data = engine.load_agents()
        for a in data["agents"]:
            if a.get("name") == name:
                a["sid"] = sid
                engine.save_agents(data)
                return self._json(200, {"ok": True})
        return self._json(404, {"error": "khong co agent"})


def main():
    global PORT, RELAY_ON, HEADLESS
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--no-relay", action="store_true")
    ap.add_argument("--headless", action="store_true",
                    help="API-only: do not serve app.html")
    args = ap.parse_args()
    PORT = args.port
    RELAY_ON = not args.no_relay
    HEADLESS = bool(args.headless or HEADLESS)
    _rotate_events()
    threading.Thread(target=bus_loop, daemon=True).start()
    threading.Thread(target=reply_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    if HEADLESS:
        print("[oc_chat] headless API http://127.0.0.1:%d/api/ping" % PORT,
              flush=True)
    else:
        print("[oc_chat] UI  http://127.0.0.1:%d/" % PORT, flush=True)
    try:
        print("[oc_chat] OpenCode port: %s" % engine.discover(), flush=True)
    except Exception as e:
        print("[oc_chat] OpenCode discover failed: %s" % str(e)[:160],
              flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
