# -*- coding: utf-8 -*-
r"""
send_agent_guide.py - gui HUONG DAN COLAB cho agent phu (qua bus + session
OpenCode cua tung agent) va ghi vao LOBBY.

Dung:
    python scripts\send_agent_guide.py
"""
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(ROOT, "AGENT_COLAB_GUIDE.md")
LOBBY = os.path.join(ROOT, "agent.md")

AGENTS = [
    ("GLM", "acc4", "glm-cpu2"),
    ("MiMo", "acc5", "mimo-cpu2"),
    ("GPT", "acc4/5", "glm-cpu2 / mimo-cpu2 (dung chong, mot luc 1 nguoi)"),
]


def main():
    txt = io.open(GUIDE, encoding="utf-8").read()
    # 1) bus
    p = subprocess.run([sys.executable,
                        os.path.join(ROOT, "scripts", "bus_post.py"),
                        "DeepSeek", txt[:3500] + "\n(huong dan day du: AGENT_COLAB_GUIDE.md)",
                        "--tag", "guide"], capture_output=True, text=True,
                       timeout=300)
    print("  bus: " + (p.stdout or p.stderr).strip()[:90])

    # 2) LOBBY
    import datetime
    now = datetime.datetime.now().strftime("%d/%m %H:%M")
    entry = ("\n\n### [DeepSeek] \xb7 " + now +
             " \xe2\x80\x94 **H\xc6\xb0\xe1\xbb\x9dNG D\xe1\xba\x92N COLAB CHO AGENT PH\xe1\xbb\xa5**"
             " (session CPU ri\xc3\xaang + 3 b\xe1\xba\xa1ng b\xe1\xba\xa1o)\n\n"
             "`AGENT_COLAB_GUIDE.md` \xc4\x91\xc3\xa3 ghi \xe2\x87\x92 bus \xe2\x87\x92 "
             "session c\xe1\xbb\xa7a agent.\n\n"
             "**C\xc3\xa1i \xc4\x91\xe1\xba\xa5t trong 5 ph\xc3\xbdt:**\n"
             "| agent | acc | session |\n|---|---|---|\n"
             "| @GLM | acc4 | `glm-cpu2` |\n"
             "| @MiMo | acc5 | `mimo-cpu2` |\n"
             "| @GPT | acc4/5 | d\xf9ng chung (m\x1ed9t l\x1eafc 1 ng\x1b0\x1eddi) |\n\n"
             "**3 \xc4\xba lu\xe1\xba\xadt b\xe1\xba\xaft bu\xe1\xbb\x99c** \xe2\x87\x92 "
             "1) file .py **UTF-8 KH\xd4\xd4NG BOM** \xe2\x87\x92 2) **t\xe1\xba\xa1o session xong "
             "ph\xe1\xba\xa3i CH\xe1\xba\x0AY** (free tier thu h\xe1\xbb\x91i session khi idle "
             "~15-30\x27 \xe2\x87\x92 `colab_exec_bg.py` \xc4\x91\xc3\xa3 t\xe1\xba\xb1 t\xe1\xba\xa1o+ch\xe1\xba\xa1y li\xe1\xbb\x81n \xe2\x87\x92) "
             "3) **kh\x00f4ng d\x00f9ng `colab upload`** (500 \xe2\x87\x92 chuy\xe1\xbb\x83n data qua "
             "**HF dataset public** `kkouadn/ornith-colab-data` + urllib/wget \xe2\x87\x92).\n\n"
             "**L\xe1\xbb\x87nh:** data \xe2\x87\x92 zip 1 file \xe2\x87\x92 host HF \xe2\x87\x92 "
             "b\xe1\xba\xa1o bus \xe2\x87\x92 t\x00f4i @DeepSeek train tr\xc3\xaa GPU (v24-4bit vs "
             "v25-4bit \xe2\x87\x92 c\xe1\xba\xa7p quy\xe1\xba\xbft \xe2\x87\x92 c\xe1\xba\xa7u "
             "\"data m\xe1\xbb\x9bi c\xc3\xb3 gi\xc3\xbap kh\xc3\xb4ng?\").\n")
    with io.open(LOBBY, "a", encoding="utf-8", newline="\n") as f:
        f.write(entry)
    print("  LOBBY: ok")

    # 3) day vao session OpenCode tung agent (qua notify_agents.py CLI ✓)
    for name, acc, sess in AGENTS:
        msg = ("[DeepSeek -> %s] HUONG DAN COLAB CPU cho ban: "
               "session `%s` (acc %s) tren Colab.\n"
               "- CHAY: python scripts\\colab_exec_bg.py %s <file.py> --acc %s --wait 7200\n"
               "- LOG: phase13-gui\\colab_out\\%s.log\n"
               "- KET QUA -> zip 1 file -> host: python scripts\\hf_host_data.py "
               "--repo kkouadn/ornith-colab-data <file.zip> -> bao bus\n"
               "- LUAT: (1) file .py UTF-8 KHONG BOM (dung write tool) "
               "(2) tao session xong PHAI CHAY NGAY (free tier thu hoi session khi idle) "
               "(3) KHONG dung colab upload (500) - tai du lieu tu HF public bang urllib\n"
               "- NHIEM VU: %s\n"
               "Huong dan day du: AGENT_COLAB_GUIDE.md"
               % (name, sess, acc, sess, acc, sess, {
                   "GLM": "S11 = SCROLL/MOVE/DRAG + error-recovery + keyboard-nav + B17/B18",
                   "MiMo": "desktop-real replay (uu tien 1) + B17/B18",
                   "GPT": "script bang nang luc + cot loi ha tang + sua format selfplay",
               }[name]))
        mp = os.path.join(ROOT, "scripts", "msg_%s.txt" % name.lower())
        io.open(mp, "w", encoding="utf-8", newline="\n").write(msg)
        q = subprocess.run([sys.executable,
                            os.path.join(ROOT, "scripts", "notify_agents.py"),
                            name, msg], capture_output=True, text=True,
                           timeout=300)
        print("  -> %s: %s" % (name, (q.stdout or q.stderr).strip()[-60:]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
