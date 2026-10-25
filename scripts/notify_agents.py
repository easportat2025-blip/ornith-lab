# -*- coding: utf-8 -*-
"""notify_agents.py - gui tin cho CAC AGENT PHU (dung khi can tra loi nhanh).

- Post len BUS (agent nao poll bus deu thay) ✓
- Day thang vao SESSION OpenCode cua tung agent (theo tieu de session) ✓
  => agent duoc 'thuc' ngay ma khong can poll ✓

Dung:  python scripts/notify_agents.py "GLM" "noi dung tin"
       python scripts/notify_agents.py "MiMo,GLM,GPT" "noi dung"
"""
import io
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "oc_chat"))
import watch_bus as wb  # noqa: E402
import engine  # noqa: E402

# tu khoa -> tieu de session (dung de tim session cua tung agent)
KEYS = {
    "GLM": ["agent phu ornith", "lobby & task board"],
    "MiMo": ["doc agent.md", "nhiem vu lobby"],
    "GPT": ["gpt"],
    "SPACE": ["deploy opencode"],
    "DeepSeek": ["chao hoi lam quen"],
}


def _norm(s):
    """Bo dau de so khop (tieu de session co dau tieng Viet)."""
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def sessions():
    d = engine.sessions()
    d.sort(key=lambda s: (s.get("time") or {}).get("updated", 0), reverse=True)
    out = []
    seen = set()
    for s in d:
        title = _norm(s.get("title"))
        for name, kws in KEYS.items():
            if any(_norm(k) in title for k in kws):
                if name not in seen:
                    seen.add(name)
                    out.append((name, s.get("id"), s.get("title")))
                break
    return out


def main():
    who = sys.argv[1] if len(sys.argv) > 1 else "GLM,MiMo,GPT"
    text = sys.argv[2] if len(sys.argv) > 2 else ""
    if not text:
        raise SystemExit("dung: notify_agents.py <GLM,MiMo,GPT> \"<tin>\"")
    # 1) bus
    p = subprocess.run([sys.executable, os.path.join(HERE, "bus_post.py"),
                        "DeepSeek", text, "--tag", "assign"],
                       capture_output=True, text=True)
    print("bus:", (p.stdout or p.stderr).strip()[:80])
    # 2) day vao session tung agent
    sids = {}
    for name, sid, title in sessions():
        sids.setdefault(name, []).append((sid, title))
    for name in [x.strip() for x in who.split(",") if x.strip()]:
        for sid, title in sids.get(name, []):
            ok = wb.oc_send(sid, "[DeepSeek -> %s] %s" % (name, text))
            print("  -> %-8s %s  %s" % (name, "OK" if ok else "FAIL",
                                         str(title)[:40]))


if __name__ == "__main__":
    main()
