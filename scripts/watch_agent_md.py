"""watch_agent_md.py - watcher ONE-SHOT cho agent.md.

Protocol (agent.md LUCAT 4): moi thay doi agent.md -> bao DUNG 1 LAN roi tat;
agent doc tin moi roi TU GAI LAI watcher nay.

Dung:  python scripts/watch_agent_md.py
Exit 0 ngay khi agent.md doi -> harness bao cho agent chay tiep.
"""
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AGENT_MD = os.path.join(ROOT, "agent.md")
OUT_TXT = os.path.join(HERE, "agent_md_new.txt")
LOG_TXT = os.path.join(HERE, "agent_md_changes.log")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def bus_post(text, tag="agentmd"):
    """Day tin moi (agent.md) len BUS -> agent nhan NGAY (ke ca push vao
    session OpenCode qua watch_bus.py)."""
    try:
        import json as _json
        import urllib.request as _u
        body = _json.dumps({"from": "agent.md", "text": str(text)[:1200],
                            "tag": tag}).encode("utf-8")
        req = _u.Request(os.environ.get("BUS_URL",
                                         "http://127.0.0.1:8777") + "/post",
                         data=body,
                         headers={"Content-Type": "application/json"},
                         method="POST")
        _u.urlopen(req, timeout=6).read()
        return True
    except Exception:
        return False


def make_digest():
    """Sinh LOBBY_DIGEST.md (ban tom tat de nguoi doc de - agent.md co ky tu ky thuat)."""
    import subprocess
    import sys
    try:
        p = subprocess.run([sys.executable,
                            os.path.join(os.path.dirname(
                                os.path.abspath(__file__)), "make_digest.py")],
                           capture_output=True, text=True, timeout=120)
        print("[digest]", (p.stdout or p.stderr).strip()[:80], flush=True)
    except Exception as e:
        print("[digest] loi:", str(e)[:80], flush=True)


def snap():
    try:
        st = os.stat(AGENT_MD)
        return st.st_mtime, st.st_size
    except OSError:
        return 0, 0


def main():
    loop = os.environ.get("WATCH_LOOP", "0") == "1"
    base_m, base_s = snap()
    with io.open(AGENT_MD, encoding="utf-8") as fh:
        base_txt = fh.read()
    base_lines = base_txt.count("\n")
    print("watch agent.md: size=%d lines=%d loop=%s" % (base_s, base_lines, loop),
          flush=True)
    t0 = time.time()
    while True:
        time.sleep(8)
        m, s = snap()
        if (m, s) == (base_m, base_s):
            # het thay doi, dung 12h de chan doi chua xong
            if time.time() - t0 > 43200:
                print("watch agent.md: timeout 12h, khong co thay doi", flush=True)
                if loop:
                    t0 = time.time()
                    continue
                return 0
            continue
        # doi -> cho file on dinh 2s
        time.sleep(2)
        m2, s2 = snap()
        if (m2, s2) != (m, s):
            base_m, base_s = m2, s2
            continue
        with io.open(AGENT_MD, encoding="utf-8") as fh:
            txt = fh.read()
        lines = txt.splitlines()
        new = lines[base_lines:]
        body = "=== AGENT.MD MOI (%d dong moi) ===\n" % len(new) + \
            "\n".join(new) + "\n=== HET ===\n"
        with io.open(OUT_TXT, "w", encoding="utf-8") as fh:
            fh.write(body)
        with io.open(LOG_TXT, "a", encoding="utf-8") as fh:
            fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + body + "\n")
        print(body, flush=True)
        make_digest()
        try:
            heads = [l for l in new if l.startswith("### [")][:3]
            bus_post(" | ".join(h.strip() for h in heads) or
                    ("%d dong moi trong agent.md" % len(new)),
                    tag="agentmd")
        except Exception:
            pass
        base_m, base_s = m2, s2
        base_lines = len(lines)
        t0 = time.time()
        if not loop:
            return 0


if __name__ == "__main__":
    sys.exit(main())
