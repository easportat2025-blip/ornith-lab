# -*- coding: utf-8 -*-
"""bus_post.py - gui tin nhanh len BUS (nhan duoc ngay lap tuc).

Dung:
    python scripts/bus_post.py <from> "<text>" [--tag TAG] [--to NAME]
                               [--priority auto|critical|normal|low] [--url U]

Giam tan suat GUI (23/10):
  - tin lap (cung nguoi gui + cung noi dung) trong 30 phut -> SKIP
  - > 5 tin / 10 phut -> tu ha xuong 'low' (khong push session)
  - muon chac chan day: --priority critical (nhung van bi gioi han o consumer)
"""
import argparse
import hashlib
import io
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("BUS_URL", "http://127.0.0.1:8777")
STATE = os.path.join(HERE, ".bus_send_state.json")
DUP_WINDOW = 30 * 60
BURST_WINDOW = 10 * 60
BURST_MAX = 5

sys.path.insert(0, HERE)
import bus_policy  # noqa: E402


def _load():
    try:
        with io.open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"sent": []}


def _save(st):
    try:
        with io.open(STATE, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(st, fh, ensure_ascii=False)
    except Exception:
        pass


def check_spam(sender, text):
    """-> (blocked_reason | None, forced_priority | None)."""
    st = _load()
    now = time.time()
    h = hashlib.sha1((bus_policy.norm(sender) + "|" +
                      bus_policy.norm(text)[:400]).encode("utf-8")).hexdigest()
    sent = [x for x in st.get("sent", []) if now - x[0] < DUP_WINDOW]
    for ts, hh in sent:
        if hh == h:
            return "tin lap trong 30 phut", None
    recent = [x for x in sent if now - x[0] < BURST_WINDOW]
    forced = "low" if len(recent) >= BURST_MAX else None
    sent.append([now, h])
    _save({"sent": sent[-300:]})
    return None, forced


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sender")
    ap.add_argument("text")
    ap.add_argument("--tag", default="")
    ap.add_argument("--to", default="", help="gui rieng cho agent nay")
    ap.add_argument("--priority", default="auto",
                    choices=["auto", "critical", "normal", "low"])
    ap.add_argument("--force", action="store_true",
                    help="bo qua chan tin lap/burst")
    ap.add_argument("--url", default=URL)
    a = ap.parse_args()

    pri = a.priority
    if not a.force:
        why, forced = check_spam(a.sender, a.text)
        if why:
            print("SKIP: %s (dung --force neu that su can)" % why)
            return 0
        if forced and pri in ("auto", "normal"):
            pri = forced
            print("WARN: burst >%d tin/%ds -> ha xuong low (khong push)"
                  % (BURST_MAX, BURST_WINDOW))
    if pri == "auto":
        pri = bus_policy.classify(a.text)
    if pri != "critical":
        print("priority=%s -> chi vao phong/LOBBY, KHONG push session" % pri)

    body = json.dumps({"from": a.sender, "text": a.text, "tag": a.tag,
                       "to": a.to, "priority": pri}).encode("utf-8")
    req = urllib.request.Request(a.url + "/post", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=10)
        out = r.read().decode("utf-8", "replace")
        print("bus OK:", out)
        return 0
    except Exception as e:
        # bus chua chay -> ghi xuong file de khong mat tin
        fallback = os.path.join(HERE, "bus_outbox.jsonl")
        with open(fallback, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"ts": time.time(), "from": a.sender,
                                 "text": a.text, "tag": a.tag, "to": a.to,
                                 "priority": pri, "queued": True},
                                ensure_ascii=False) + "\n")
        print("bus khong phan hoi (%s) -> da ghi vao %s" % (e, fallback))
        return 1


if __name__ == "__main__":
    sys.exit(main())
