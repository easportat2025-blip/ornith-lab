# -*- coding: utf-8 -*-
"""patch_watcher_digest.py - watcher agent.md sinh them LOBBY_DIGEST.md (ban tom
tat de DOC DUOC) moi khi co tin moi + ghi 1 dong vao bus (nhan ngay).
"""
import io

P = "scripts/watch_agent_md.py"
s = io.open(P, encoding="utf-8").read()

if "make_digest" not in s:
    s = s.replace("import space_sync  # noqa: E402", "import space_sync  # noqa: E402") \
        if "import space_sync" in s else s
    # them ham sinh digest + goi trong vong lap
    helper = '''

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

'''
    if "def make_digest" not in s:
        s = s.replace("def snap():", helper.strip() + "\n\n\ndef snap():", 1)
    if "        make_digest()\n" not in s:
        s = s.replace("        print(body, flush=True)\n",
                      "        print(body, flush=True)\n        make_digest()\n", 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da them make_digest vao watcher agent.md")
else:
    print("da co san")
