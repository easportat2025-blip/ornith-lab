# -*- coding: utf-8 -*-
"""client.py - tiny headless client for OpenChat.

Examples:
  python scripts/oc_chat/client.py health
  python scripts/oc_chat/client.py ping --agent heartbeat --status idle --detail "no active job"
  python scripts/oc_chat/client.py status
  python scripts/oc_chat/client.py jobs --limit 10
  python scripts/oc_chat/client.py logs --name logs/watchdog_B.log --tail 80
  python scripts/oc_chat/client.py notify --from GLM --text "B17 queued"
  python scripts/oc_chat/client.py send --to GLM,MiMo --text "check status"

No third-party dependencies. Base URL: OC_CHAT_URL or http://127.0.0.1:8788.
ASCII-only source on purpose.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("OC_CHAT_URL", "http://127.0.0.1:8788").rstrip("/")


def call(method, path, body=None, timeout=8):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:500]}
    except Exception as e:
        return 0, {"error": str(e)[:300]}


def show(obj, as_json=False):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="pretty JSON output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")

    p = sub.add_parser("ping")
    p.add_argument("--agent", default="agent")
    p.add_argument("--status", default="online")
    p.add_argument("--job", default="")
    p.add_argument("--detail", default="")
    p.add_argument("--host", default=os.environ.get("COMPUTERNAME", ""))
    p.add_argument("--pid", type=int, default=os.getpid())

    p = sub.add_parser("status")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("jobs")
    p.add_argument("--limit", type=int, default=40)

    p = sub.add_parser("logs")
    p.add_argument("--name", required=True)
    p.add_argument("--tail", type=int, default=100)

    p = sub.add_parser("notify")
    p.add_argument("--from", dest="frm", default="agent")
    p.add_argument("--text", required=True)
    p.add_argument("--tag", default="")
    p.add_argument("--kind", default="notify")
    p.add_argument("--to", default="")

    p = sub.add_parser("send")
    p.add_argument("--to", required=True, help="comma-separated agent names")
    p.add_argument("--text", required=True)
    p.add_argument("--from", dest="frm", default="user")

    args = ap.parse_args(argv)

    if args.cmd == "health":
        code, obj = call("GET", "/api/health")
    elif args.cmd == "ping":
        code, obj = call("POST", "/api/ping", {
            "agent": args.agent, "status": args.status, "job": args.job,
            "detail": args.detail, "host": args.host, "pid": args.pid})
    elif args.cmd == "status":
        code, obj = call("GET", "/api/ping")
    elif args.cmd == "jobs":
        code, obj = call("GET", "/api/jobs?limit=%d" % args.limit)
    elif args.cmd == "logs":
        qs = urllib.parse.urlencode({"name": args.name, "tail": args.tail})
        code, obj = call("GET", "/api/logs?" + qs)
        if code == 200 and not args.json:
            for line in obj.get("lines", []):
                print(line)
            return 0
    elif args.cmd == "notify":
        code, obj = call("POST", "/api/notify", {
            "from": args.frm, "text": args.text, "tag": args.tag,
            "kind": args.kind, "to": args.to})
    elif args.cmd == "send":
        targets = [x.strip() for x in args.to.split(",") if x.strip()]
        code, obj = call("POST", "/api/send", {
            "from": args.frm, "targets": targets, "text": args.text})
    else:
        return 2

    show(obj, args.json)
    return 0 if code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
