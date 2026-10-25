# -*- coding: utf-8 -*-
"""engine.py - client cho OpenCode local server + map session -> agent.

Khong dung thu vien ngoai. Tu tim port cua OpenCode (desktop app doi port
moi lan chay), doc session/message, gui prompt vao session.

API (OpenCode 2.x):
    GET  /api/info
    GET  /api/session                 -> {data: [...]}
    GET  /api/session/active          -> {data: {sid: {...}}}
    GET  /api/session/<sid>/message   -> {data: [...]}   (?limit=&order=)
    POST /api/session/<sid>/prompt    {text} -> {data: ...}
    GET  /api/event                   SSE
"""
import base64
import io
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SVC = os.path.join(os.environ.get("USERPROFILE", ""), ".config", "opencode",
                   "service.json")
CACHE = os.path.join(HERE, ".port.json")
AGENTS_FILE = os.path.join(HERE, "agents.json")

# mau co dinh cho tung agent (de UI on dinh giua cac lan chay)
COLORS = {
    "DeepSeek": "#8b5cf6",
    "GLM": "#3b82f6",
    "MiMo": "#10b981",
    "GPT": "#f59e0b",
    "SPACE": "#ec4899",
}

DEFAULT_AGENTS = [
    {"name": "DeepSeek", "sid": "ses_eef1a0093ffeIEslDt6u6Yy2kx",
     "keywords": ["chào hỏi làm quen"], "role": "orchestrator",
     "enabled": True},
    {"name": "GLM", "sid": "ses_ead9ad3bbffelGBjC7wcKDiEZH",
     "keywords": ["lobby & task board", "agent phụ ornith"],
     "role": "bench + harness", "enabled": True},
    {"name": "MiMo", "sid": "ses_ead8c9fcdffe5oLN2Bs6ywVrw3",
     "keywords": ["nhiệm vụ lobby", "đọc agent.md"],
     "role": "data + desktop", "enabled": True},
    {"name": "GPT", "sid": "ses_ea33a2cebffevRvrIg1zGB3l76",
     "keywords": ["gpt"], "role": "audit + tooling", "enabled": True},
    {"name": "SPACE", "sid": "ses_ea35f710fffe9ddA1QKzyggmcG",
     "keywords": ["deploy opencode"], "role": "space deploy",
     "enabled": False},
]


# --------------------------------------------------------------------- auth
def _password():
    try:
        with io.open(SVC, encoding="utf-8") as fh:
            return json.load(fh).get("password", "") or ""
    except Exception:
        return ""


def headers(extra=None):
    pw = _password()
    tok = base64.b64encode(("opencode:" + pw).encode()).decode()
    h = {"Authorization": "Basic " + tok,
         "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


# --------------------------------------------------------------------- port
def _listening_ports():
    """Port TCP dang LISTEN tren 127.0.0.1 (khong can psutil)."""
    ports = set()
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "tcp"],
                             capture_output=True, text=True, timeout=15).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4 or "LISTEN" not in parts[3]:
                continue
            addr = parts[1]
            if ":" not in addr:
                continue
            host, port = addr.rsplit(":", 1)
            if host in ("127.0.0.1", "0.0.0.0", "[::1]", "[::]"):
                try:
                    ports.add(int(port))
                except ValueError:
                    pass
    except Exception:
        pass
    return sorted(ports)


def _probe(port, timeout=0.7):
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:%d/api/info" % port, headers=headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(400).decode("utf-8", "replace")
            return r.status == 200 and ('"version"' in body or '"data"' in body)
    except Exception:
        return False


def discover(force=False):
    """Tra port cua OpenCode server (cache 60s)."""
    env = os.environ.get("OPENCODE_PORT")
    if env and not force:
        try:
            p = int(env)
            if _probe(p):
                return p
        except Exception:
            pass
    if not force:
        try:
            with io.open(CACHE, encoding="utf-8") as fh:
                c = json.load(fh)
            if time.time() - c.get("ts", 0) < 60 and _probe(c.get("port")):
                return int(c["port"])
        except Exception:
            pass
    found = None
    for p in _listening_ports():
        if _probe(p):
            found = p
            break
    if found:
        try:
            with io.open(CACHE, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"port": found, "ts": time.time()}))
        except Exception:
            pass
    return found


# ---------------------------------------------------------------------- api
def base(port=None):
    p = port or discover()
    if not p:
        raise RuntimeError("khong tim thay OpenCode server (desktop app dang tat?)")
    return "http://127.0.0.1:%d" % p


def get(path, port=None, timeout=10):
    req = urllib.request.Request(base(port) + path, headers=headers())
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def post(path, obj, port=None, timeout=20):
    req = urllib.request.Request(
        base(port) + path, data=json.dumps(obj).encode("utf-8"),
        headers=headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
        return json.loads(raw) if raw.strip() else {}


def sessions():
    d = get("/api/session")
    return d.get("data") if isinstance(d, dict) else (d or [])


def active_map():
    try:
        d = get("/api/session/active")
        return d.get("data") or {}
    except Exception:
        return {}


def raw_messages(sid, limit=12):
    d = get("/api/session/%s/message?limit=%d&order=desc" % (sid, limit))
    ms = d.get("data") if isinstance(d, dict) else (d or [])
    return list(reversed(ms or []))


def send(sid, text, timeout=25):
    return post("/api/session/%s/prompt" % sid, {"text": text},
                timeout=timeout)


# ------------------------------------------------------------------ extract
def _text_parts(m):
    out, tools = [], []
    for p in (m.get("content") or []):
        t = p.get("type")
        if t == "text" and p.get("text"):
            out.append(p["text"])
        elif t == "tool":
            name = p.get("tool") or p.get("name")
            if name:
                tools.append(str(name))
    return "\n".join(out).strip(), tools


def norm_message(m, sid, agent):
    text, tools = _text_parts(m)
    if not text:
        return None
    ts = ((m.get("time") or {}).get("created") or 0)
    return {"id": m.get("id"), "sid": sid, "agent": agent,
            "role": m.get("type") or "assistant",
            "ts": ts / 1000.0 if ts > 1e11 else ts,
            "text": text, "tools": tools}


def replies(sid, agent, limit=12):
    out = []
    for m in raw_messages(sid, limit=limit):
        if (m.get("type") or "") != "assistant":
            continue
        n = norm_message(m, sid, agent)
        if n:
            out.append(n)
    return out


# ------------------------------------------------------------------ agents
def load_agents():
    try:
        with io.open(AGENTS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("agents"), list):
            return data
    except Exception:
        pass
    return {"agents": [dict(a) for a in DEFAULT_AGENTS]}


def save_agents(data):
    os.makedirs(HERE, exist_ok=True)
    with io.open(AGENTS_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def refresh_agents():
    """Neu session cua agent bi thay doi (session moi), tim lai theo keyword."""
    data = load_agents()
    ss = sessions()
    by_id = {s.get("id"): s for s in ss}
    changed = False
    for a in data["agents"]:
        if a.get("sid") in by_id:
            a["title"] = by_id[a["sid"]].get("title")
            a["model"] = (by_id[a["sid"]].get("model") or {}).get("id")
            a["updated"] = (by_id[a["sid"]].get("time") or {}).get("updated")
            continue
        best = None
        for s in ss:
            title = _norm(s.get("title"))
            if any(_norm(k) in title for k in a.get("keywords") or []):
                if best is None or ((s.get("time") or {}).get("updated", 0) >
                                    (best.get("time") or {}).get("updated", 0)):
                    best = s
        if best:
            a["sid"] = best.get("id")
            a["title"] = best.get("title")
            a["model"] = (best.get("model") or {}).get("id")
            a["updated"] = (best.get("time") or {}).get("updated")
            changed = True
    if changed:
        save_agents(data)
    return data


def agent_by_name(name):
    for a in refresh_agents()["agents"]:
        if _norm(a.get("name")) == _norm(name):
            return a
    return None


def name_for_sid(sid):
    for a in load_agents()["agents"]:
        if a.get("sid") == sid:
            return a.get("name")
    return None
