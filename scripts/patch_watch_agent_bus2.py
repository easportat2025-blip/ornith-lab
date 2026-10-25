# -*- coding: utf-8 -*-
"""patch_watch_agent_bus2.py - them LENH GOI bus_post trong watcher agent.md
(ban dau bi bo sot vi dieu kien kiem tra trung marker)."""
import io

P = "scripts/watch_agent_md.py"
s = io.open(P, encoding="utf-8").read()

MARK = "bus_post(\"[agent.md] tin moi"
OLD = "        print(body, flush=True)\n"
NEW = ('        print(body, flush=True)\n'
       '        try:\n'
       '            heads = [l for l in new if l.startswith("### [")][:3]\n'
       '            bus_post(" | ".join(h.strip() for h in heads) or\n'
       '                    ("%d dong moi trong agent.md" % len(new)),\n'
       '                    tag="agentmd")\n'
       '        except Exception:\n'
       '            pass\n')

if MARK not in s:
    assert OLD in s, "khong tim thay print(body)"
    s = s.replace(OLD, NEW, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da them lenh goi bus_post")
else:
    print("da co san lenh goi")
for i, l in enumerate(s.splitlines(), start=1):
    if "bus_post(" in l:
        print("  %3d: %s" % (i, l.strip()[:95]))
