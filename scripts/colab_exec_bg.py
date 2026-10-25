# -*- coding: utf-8 -*-
r"""
colab_exec_bg.py - chay script tren Colab VM o che do NEN + bat log day du.

Ly do (22/10): 'colab exec' co timeout phia CLIENT (~25-30p) => job dai bi
mat output (script van chay tren VM nhung log khong ve). Giai phap:
  - gui launcher (base64) => VM ghi file + nohup chay > /content/out.log
  - poll bang 1 exec nho doc /content/out.log + trang thai pid
  - in log khi xong

Dung:
    python scripts\colab_exec_bg.py <session> <local_script.py> [--wait 600]
ASCII-only source.
"""
import base64
import io
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLAB = os.path.join(os.path.dirname(sys.executable), "colab.exe")
if not os.path.exists(COLAB):
    COLAB = "colab"
TMP = os.environ.get("TEMP", ".")
REMOTE_LOG = "/content/out.log"
REMOTE_PID = "/content/job.pid"

# script doc trang thai tren VM (dung cho poll)
CHECK = r'''
import os, sys
log = "/content/out.log"
pidf = "/content/job.pid"
alive = False
try:
    pid = int(open(pidf).read().strip())
    os.kill(pid, 0)
    alive = True
except Exception:
    alive = False
size = os.path.getsize(log) if os.path.exists(log) else 0
print("ALIVE=%s SIZE=%d" % ("1" if alive else "0", size))
'''


def cli(*args, timeout=600, capture=True, acc=None):
    """acc: so acc (dung config + token cua acc do)."""
    base = [COLAB]
    if acc:
        d = os.path.join(ROOT, "scripts", "colab_accounts", "acc%d" % acc)
        base += ["--config", os.path.join(d, "sessions.json")]
        # '-c' (client OAuth rieng) chi khi file ton tai - acc moi chi co
        # token.json => them '-c' se lam CLI bao loi
        _oauth = os.path.join(d, "oauth.json")
        if os.path.exists(_oauth):
            base += ["-c", _oauth]
    p = subprocess.run(base + list(args), capture_output=capture, text=True,
                       timeout=timeout)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    sess = sys.argv[1]
    script = sys.argv[2]
    wait = 600
    if "--wait" in sys.argv:
        wait = int(sys.argv[sys.argv.index("--wait") + 1])
    acc = None
    if "--acc" in sys.argv:
        acc = int(sys.argv[sys.argv.index("--acc") + 1])

    src = io.open(script, encoding="utf-8").read()
    b64 = base64.b64encode(src.encode("utf-8")).decode("ascii")
    launcher = (
        "import base64, subprocess, sys\n"
        "open('/content/job.py','wb').write(base64.b64decode(%r))\n"
        "f = open('/content/out.log','w')\n"
        "p = subprocess.Popen([sys.executable, '-u', '/content/job.py'],\n"
        "                   stdout=f, stderr=subprocess.STDOUT)\n"
        "open('/content/job.pid','w').write(str(p.pid))\n"
        "print('started pid', p.pid)\n" % b64)
    lpath = os.path.join(TMP, "colab_launcher.py")
    io.open(lpath, "w", encoding="utf-8", newline="\n").write(launcher)

    # FIX (MiMo 22/10): free tier thu hoi session idle ~15-30' => neu session
    # chua co thi TAO NGAY TRONG LENH NAY roi chay lien tuc (khong tao roi
    # de o, se bi thu hoi).
    rc0, out0 = cli("status", "-s", sess, timeout=300, acc=acc)
    if rc0 != 0 or "not found" in (out0 or "").lower():
        print("  session %s chua co -> TAO (CPU)" % sess)
        rc1, out1 = cli("new", "-s", sess, timeout=900, acc=acc)
        print("  new rc=%s %s" % (rc1, (out1 or "")[:160]))
        if rc1 != 0:
            print("  !! tao session that bai")
            return 1
    rc, out = cli("exec", "-s", sess, "-f", lpath, timeout=600, acc=acc)
    print("  launch rc=%s %s" % (rc, out[:160]))
    if rc != 0:
        return 1

    cpath = os.path.join(TMP, "colab_check.py")
    io.open(cpath, "w", encoding="utf-8", newline="\n").write(CHECK)

    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(40)
        rc2, out2 = cli("exec", "-s", sess, "-f", cpath, timeout=300, acc=acc)
        alive = "ALIVE=1" in out2
        print("  ... %s (%ds)" % (out2.strip().replace("\n", " ")[:80],
                                 int(time.time() - t0)))
        if not alive and "SIZE=" in out2:
            break
    # in log
    rc3, out3 = cli("exec", "-s", sess, "-f", cpath, timeout=300, acc=acc)
    print("\n=== noi dung log tren VM ===")
    print(out3[:4000])
    # thu tai ve (endpoint download co the hoat dong)
    dst = os.path.join(ROOT, "phase13-gui", "colab_out")
    os.makedirs(dst, exist_ok=True)
    d = os.path.join(dst, "%s.log" % sess)
    rc4, out4 = cli("download", "-s", sess, REMOTE_LOG, d, timeout=900, acc=acc)
    print("\n  download rc=%s %s" % (rc4, out4[:120]))
    if os.path.exists(d):
        print("  -> %s (%d KB)" % (d, os.path.getsize(d) // 1024))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
