# -*- coding: utf-8 -*-
"""patch_watch_agent_bus.py - watcher agent.md day tin moi len BUS (nhan ngay)."""
import io

P = "scripts/watch_agent_md.py"
s = io.open(P, encoding="utf-8").read()

HELPER = '''

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

'''

if "def bus_post(" not in s:
    s = s.replace("def snap():", HELPER.strip() + "\n\n\ndef snap():", 1)

OLD = '        print(body, flush=True)\n'
NEW = ('        print(body, flush=True)\n'
       '        # gui phan tin moi len BUS (agent nhan ngay lap tuc)\n'
       '        try:\n'
       '            heads = [l for l in new if l.startswith("### [")][:3]\n'
       '            bus_post(" | ".join(h.strip() for h in heads) or\n'
       '                    ("%d dong moi trong agent.md" % len(new)),\n'
       '                    tag="agentmd")\n'
       '        except Exception:\n'
       '            pass\n')
if 'tag="agentmd"' not in s:
    assert OLD in s, "khong tim thay cho print(body)"
    s = s.replace(OLD, NEW, 1)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("watch_agent_md -> da noi BUS")
