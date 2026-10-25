# -*- coding: utf-8 -*-
"""patch_result_md_script.py - them khoi HISTORY vao update_result_md.py + chay
1 lan/ngay tu space_sync_loop (de result.md luon moi).
"""
import io

P = "scripts/update_result_md.py"
s = io.open(P, encoding="utf-8").read()

if "HIST_START" not in s.split("def main")[0]:
    s = s.replace('DIARY_START = "<!-- DIARY:BEGIN -->"',
                  'DIARY_START = "<!-- DIARY:BEGIN -->"\n'
                  'HIST_START = "<!-- HISTORY:BEGIN -->"\n'
                  'HIST_END = "<!-- HISTORY:END -->"')
    if "import re" not in s:
        s = s.replace("import os\n", "import os\nimport re\n")
    # them phan HISTORY vao HEAD
    s = s.replace('"""\n\n\ndef _unused', '"""\n\n\ndef _unused')
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da them khoi HISTORY")
else:
    print("da co khoi HISTORY")

# --- them vao space_sync_loop: cap nhat result.md 1 lan/ngay ---
SP = "scripts/space_sync_loop.py"
t = io.open(SP, encoding="utf-8").read()
if "update_result_md" not in t:
    block = '''
def update_result_daily():
    """Cap nhat result.md 1 lan/ngay (nhat ky ket qua + hang doi GPU)."""
    import datetime
    import subprocess
    import sys
    stamp = os.path.join(HERE, ".result_md_date")
    today = datetime.date.today().isoformat()
    try:
        if os.path.exists(stamp):
            with open(stamp, encoding="utf-8") as fh:
                if fh.read().strip() == today:
                    return
    except Exception:
        pass
    try:
        p = subprocess.run([sys.executable,
                            os.path.join(HERE, "update_result_md.py")],
                           capture_output=True, text=True, timeout=600)
        print("[space-sync] result.md:", (p.stdout or p.stderr).strip()[:120])
        with open(stamp, "w", encoding="utf-8") as fh:
            fh.write(today)
    except Exception as e:
        print("[space-sync] result.md loi:", str(e)[:100])

'''
    t = t.replace("def main():", block + "\ndef main():", 1)
    t = t.replace("        space_sync.push_to_space(st, \"\", os.environ[\"HF_TOKEN\"])",
                  "        space_sync.push_to_space(st, \"\", os.environ[\"HF_TOKEN\"])\n"
                  "        update_result_daily()")
    io.open(SP, "w", encoding="utf-8", newline="\n").write(t)
    print("da them update_result_daily vao space_sync_loop")
else:
    print("space_sync_loop da co san")
