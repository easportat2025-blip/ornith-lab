"""session_send.py - GUI TIN TRUC TIEP vao mot session OpenCode (khong qua bus).

Dung:
    python scripts/session_send.py --list
    python scripts/session_send.py <session_id> "noi dung tin"
    python scripts/session_send.py --title "Agent phu" "noi dung tin"   # tim theo tieu de
    python scripts/session_send.py --last "noi dung tin"                 # session moi nhat

Ghi them 1 ban vao bus (de co log + agent khac thay).
"""
import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "oc_chat"))
import watch_bus as wb  # noqa: E402
import engine  # noqa: E402


def sessions():
    d = engine.sessions()
    d.sort(key=lambda s: (s.get("time") or {}).get("updated", 0), reverse=True)
    return d


def bus_post(text, tag="session"):
    try:
        body = json.dumps({"from": "DeepSeek", "text": text,
                           "tag": tag}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8777/post", data=body,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        urllib.request.urlopen(req, timeout=6).read()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session_id", nargs="?")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--title", default="")
    ap.add_argument("--last", action="store_true")
    a = ap.parse_args()

    if a.list or not a.text:
        print("%-30s %-52s %s" % ("SESSION ID", "TITLE", "MODEL"))
        for s in sessions()[:20]:
            m = (s.get("model") or {}).get("id", "")
            print("%-30s %-52s %s" % (s.get("id", "")[:30],
                                      str(s.get("title", ""))[:52], m[:28]))
        return 0

    text = a.text
    sid = a.session_id
    ss = sessions()
    if a.last:
        sid = ss[0].get("id") if ss else None
    elif a.title:
        for s in ss:
            if a.title.lower() in str(s.get("title", "")).lower():
                sid = s.get("id")
                break
    if not sid:
        print("khong tim thay session (dung --list de xem id)")
        return 1
    ok = wb.oc_send(sid, text)
    bus_post("[gui truc tiep] -> %s : %s" % (sid[:14], text[:300]))
    print("session %s -> %s" % (sid, "OK" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
