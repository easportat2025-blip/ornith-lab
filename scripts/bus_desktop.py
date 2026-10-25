# -*- coding: utf-8 -*-
"""bus_desktop.py - BUS TIN NHAN (giong bus.py) + API cho DESKTOP APP:
   GET  /lobby         -> tail agent.md (LOBBY)
   GET  /tasks         -> queue B (gpu_queue_B.json) + trang thai push
   GET  /agents        -> danh sach agent + session Colab + tinh trang
   GET  /kernels       -> trang thai kernel Kaggle (acc B)
   GET  /kq?slug=...   -> doc file result json (nhanh, khong can Kaggle)
   POST /post          -> ghi bus + broadcast SSE (giong bus.py)
   GET  /events        -> SSE
   GET  /since?ts=     -> fallback polling
   GET  /messages      -> N tin gan nhat
   GET  /health        -> ok
   GET  /              -> giao dien desktop app (single-file HTML)

Chay:  python scripts/bus_desktop.py            (port 8777)
       python scripts/bus_desktop.py --port 9000
"""
import io
import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG = os.path.join(HERE, "bus.jsonl")
PORT = int(os.environ.get("BUS_PORT", "8777"))
CLIENTS = []
LOCK = threading.Lock()
AGENTS = ["DeepSeek", "GLM", "MiMo", "GPT", "SPACE"]


def now():
    return time.time()


def append(msg):
    with io.open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(msg, ensure_ascii=False) + "\n")
    with LOCK:
        for q in CLIENTS:
            try:
                q.put_nowait(msg)
            except Exception:
                pass


def read_since(ts=0.0, limit=100):
    out = []
    try:
        with io.open(LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if m.get("ts", 0) >= ts:
                    out.append(m)
    except Exception:
        pass
    return out[-limit:]


def read_file(path, limit=200000):
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except Exception:
        return ""


def read_tail(path, n=60):
    lines = read_file(path).splitlines()
    return "\n".join(lines[-n:])


def read_json(path):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return None


def lobby_tail(n=40):
    p = os.path.join(ROOT, "agent.md")
    return read_tail(p, n)


def task_board():
    p = os.path.join(HERE, "gpu_queue_B.json")
    q = read_json(p) or []
    out = []
    for it in q:
        if not isinstance(it, dict):
            continue
        out.append({"id": it.get("id"), "paused": bool(it.get("paused")),
                    "dir": it.get("dir"), "note": it.get("note")})
    return out


def agents_status():
    # danh sach agent + session Colab (tu AGENT_COLAB_GUIDE.md / lobby)
    return [
        {"name": "DeepSeek", "acc": "acc1", "session": "orn-gpu1",
         "role": "orchestrator", "color": "#7c3aed"},
        {"name": "GLM", "acc": "acc4", "session": "glm-cpu2",
         "role": "bench + harness", "color": "#2563eb"},
        {"name": "MiMo", "acc": "acc5", "session": "mimo-cpu2",
         "role": "data + desktop", "color": "#059669"},
        {"name": "GPT", "acc": "acc4/5", "session": "glm-cpu2 / mimo-cpu2",
         "role": "audit + tooling", "color": "#d97706"},
    ]


def kernel_status(slug):
    try:
        import subprocess
        p = subprocess.run(["kaggle", "kernels", "status", slug],
                           capture_output=True, text=True, timeout=90)
        out = (p.stdout or "") + (p.stderr or "")
        return out.strip()[-120:]
    except Exception as e:
        return "ERR " + str(e)[:80]


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _file(self, path, ctype):
        try:
            data = open(path, "rb").read()
        except Exception:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path.split("?")[0]
        q = {}
        if "?" in self.path:
            for kv in self.path.split("?")[1].split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    q[k] = v
        if p == "/health":
            return self._json(200, {"ok": True,
                                    "n": len(read_since(0, 100000))})
        if p == "/messages":
            msgs = read_since(float(q.get("since", 0) or 0),
                             int(q.get("limit", 50)))
            return self._json(200, {"messages": msgs})
        if p == "/since":
            return self._json(200, {"messages": read_since(
                float(q.get("ts", 0) or 0), int(q.get("limit", 50)))})
        if p == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            qq = queue.Queue()
            with LOCK:
                CLIENTS.append(qq)
            try:
                for m in read_since(0, 5):
                    self.wfile.write(("data: %s\n\n" %
                                      json.dumps(m, ensure_ascii=False)).encode())
                self.wfile.flush()
                while True:
                    try:
                        m = qq.get(timeout=15)
                        self.wfile.write(("data: %s\n\n" %
                                          json.dumps(m, ensure_ascii=False)).encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                with LOCK:
                    if qq in CLIENTS:
                        CLIENTS.remove(qq)
            return
        if p == "/lobby":
            return self._json(200, {"text": lobby_tail(60)})
        if p == "/tasks":
            return self._json(200, {"items": task_board()})
        if p == "/agents":
            return self._json(200, {"items": agents_status()})
        if p == "/kernels":
            slugs = [t["id"] for t in task_board()]
            res = {}
            for s in slugs[:8]:
                res[s] = kernel_status(s)
            return self._json(200, {"items": res})
        if p == "/":
            return self._file(os.path.join(HERE, "desktop_app.html"),
                              "text/html; charset=utf-8")
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ("/post", "/send"):
            return self._json(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            body = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            body = {}
        msg = {"ts": now(), "from": (body.get("from") or "?").strip()[:60],
               "tag": (body.get("tag") or "").strip()[:40],
               "text": (body.get("text") or "").strip()}
        if not msg["text"]:
            return self._json(400, {"error": "thieu text"})
        append(msg)
        return self._json(200, {"ok": True, "ts": msg["ts"]})


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
    print("[bus_desktop] http://127.0.0.1:%d  (frontend + bus + lobby + tasks)"
          % args.port, flush=True)
    print("[bus_desktop] endpoints: / /health /events /messages /since /post "
          "/lobby /tasks /agents /kernels", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
