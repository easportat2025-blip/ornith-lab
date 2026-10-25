"""bus.py - BUS TIN NHAN nhanh giua cac agent (localhost).

Muc dich: thay the "doc agent.md moi 2 phut" bang "nhan tin ngay lap tuc".
  POST /post            {from, text, tag}  -> ghi bus.jsonl + broadcast SSE
  GET  /events          -> SSE stream (subscriber nhan ngay)
  GET  /since?ts=...    -> tin nhung sau moc thoi gian (fallback polling)
  GET  /messages        -> N tin gan nhat
  GET  /health          -> ok

Chay:  python scripts/bus.py            (port 8777, bind 127.0.0.1)
Client: python scripts/bus_post.py <from> "<text>" [--tag T]
"""
import io
import json
import os
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "bus.jsonl")
PORT = int(os.environ.get("BUS_PORT", "8777"))
CLIENTS = []
LOCK = threading.Lock()


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


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path.split("?")[0]
        q = dict()
        if "?" in self.path:
            for kv in self.path.split("?")[1].split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    q[k] = v
        if p == "/health":
            return self._json(200, {"ok": True, "n": len(read_since(0, 100000))})
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
            q = queue.Queue()
            with LOCK:
                CLIENTS.append(q)
            try:
                # gui tin moi (co san) truoc
                for m in read_since(0, 5):
                    self.wfile.write(("data: %s\n\n" %
                                      json.dumps(m, ensure_ascii=False)).encode())
                self.wfile.flush()
                while True:
                    try:
                        m = q.get(timeout=15)
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
                    if q in CLIENTS:
                        CLIENTS.remove(q)
            return
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/post":
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
        # 23/10: giu them dinh tuyen 1-1 (to) + co skip_relay / kind / priority
        for k in ("to", "kind", "priority"):
            if body.get(k):
                msg[k] = str(body[k]).strip()[:80]
        if body.get("skip_relay"):
            msg["skip_relay"] = True
        if not msg["text"]:
            return self._json(400, {"error": "thieu text"})
        append(msg)
        return self._json(200, {"ok": True, "ts": msg["ts"]})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print("[bus] BUS chay tai http://127.0.0.1:%d (port %d)" % (PORT, PORT),
          flush=True)
    print("[bus] POST /post | GET /events (SSE) | GET /since | GET /messages",
          flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
