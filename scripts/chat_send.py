# -*- coding: utf-8 -*-
"""chat_send.py - agent gui tin TRUC TIEP cho agent khac (1-1 hoac nhom).

Khac bus_post.py:
  - bus_post.py  : chi ghi len bus (broadcast), khong day vao session
  - chat_send.py : day thang vao session dich + ghi bus (skip_relay) =>
                   agent dich nhan duoc NGAY, va tra loi se duoc chuyen
                   nguoc ve session cua nguoi gui (server oc_chat lo).

Dung:
    python scripts/chat_send.py GLM "nội dung"
    python scripts/chat_send.py GLM,MiMo "nội dung" --from DeepSeek
    python scripts/chat_send.py --list
"""
import argparse
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "oc_chat"))
import engine  # noqa: E402

BUS = os.environ.get("BUS_URL", "http://127.0.0.1:8777")


def bus_post(msg):
    try:
        req = urllib.request.Request(
            BUS + "/post", data=json.dumps(msg).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=6).read()
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("to", nargs="?", default="")
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--from", dest="frm", default=os.environ.get("AGENT_NAME", "agent"))
    ap.add_argument("--tag", default="chat")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    data = engine.refresh_agents()
    if a.list or not a.to or not a.text:
        print("agents:")
        for x in data.get("agents", []):
            print("  %-9s %-5s  %s  %s" % (x.get("name"),
                                           "on" if x.get("enabled") else "off",
                                           x.get("sid"), x.get("title", "")[:50]))
        return 0

    names = [n.strip() for n in a.to.split(",") if n.strip()]
    ok_any = False
    for name in names:
        ag = engine.agent_by_name(name)
        if not ag or not ag.get("sid"):
            print("  %-9s KHONG TIM THAY" % name)
            continue
        body = "[%s → %s] %s" % (a.frm, name, a.text)
        try:
            engine.send(ag["sid"], body)
            ok_any = True
            print("  %-9s OK  -> %s" % (name, ag["sid"]))
        except Exception as e:
            print("  %-9s LOI %s" % (name, str(e)[:120]))
    if ok_any:
        bus_post({"from": a.frm, "to": a.to, "tag": a.tag, "text": a.text,
                  "skip_relay": True, "kind": "agent-chat",
                  "ts": time.time()})
    return 0 if ok_any else 1


if __name__ == "__main__":
    sys.exit(main())
