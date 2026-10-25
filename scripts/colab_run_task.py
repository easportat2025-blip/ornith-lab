# -*- coding: utf-8 -*-
"""
colab_run_task.py - chay 1 task tren Colab CPU cua ACC N, an toan khi nhieu
agent dung cung may.

LY DO: CLI colab dung 1 token OAuth GLOBAL (~/.config/colab-cli/token.json) =>
de chay bang acc khac phai SWAP token => neu giu nguyen trong suot job (20-60
phut) thi agent khac se tao session NHO SAI ACC => lo chan.
=> CUA SỔ NHỎ: (1) tao session + launch (vai giay) (2) restore (3) poll:
moi 60s swap -> check -> restore (1s) (4) cuoi: swap -> download log + ket qua
-> restore.

Dung:
    python scripts/colab_run_task.py 5 mimo-cpu2 scripts/colab_desktop_replay.py \
        --wait 3600 --download /content/desktop_replay.zip
ASCII-only source.
"""
import argparse
import base64
import io
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLAB = os.path.join(os.path.dirname(sys.executable), "colab.exe")
if not os.path.exists(COLAB):
    COLAB = "colab"
GLOBAL_TOKEN = os.path.join(os.path.expanduser("~"), ".config", "colab-cli",
                            "token.json")
OUT_DIR = os.path.join(ROOT, "phase13-gui", "colab_out")
TMP = os.environ.get("TEMP", ".")

CHECK = r'''
import os
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


class Swap(object):
    """Swap token global sang acc N trong thoi gian nho."""

    def __init__(self, acc):
        self.src = os.path.join(ROOT, "scripts", "colab_accounts",
                                "acc%d" % acc, "token.json")
        self.bak = None

    def __enter__(self):
        if os.path.exists(GLOBAL_TOKEN):
            self.bak = GLOBAL_TOKEN + ".bak.swaptask"
            subprocess.run(["copy", "/Y", GLOBAL_TOKEN, self.bak],
                           capture_output=True, shell=True)
        os.makedirs(os.path.dirname(GLOBAL_TOKEN), exist_ok=True)
        subprocess.run(["copy", "/Y", self.src, GLOBAL_TOKEN],
                       capture_output=True, shell=True)
        return self

    def __exit__(self, *a):
        if self.bak and os.path.exists(self.bak):
            subprocess.run(["copy", "/Y", self.bak, GLOBAL_TOKEN],
                           capture_output=True, shell=True)
            try:
                os.remove(self.bak)
            except Exception:
                pass
        return False


def cli(acc, *args, timeout=600):
    d = os.path.join(ROOT, "scripts", "colab_accounts", "acc%d" % acc)
    cmd = [COLAB, "--config", os.path.join(d, "sessions.json")] + list(args)
    # FIX 22/10 (MiMo): output VM co ky tu non-ASCII => cp1252 mac dinh cua
    # Windows nem decode duoc => mat context. Dung UTF-8 + replace.
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("acc", type=int)
    ap.add_argument("session")
    ap.add_argument("script")
    ap.add_argument("--wait", type=int, default=3600)
    ap.add_argument("--no-launch", action="store_true",
                    help="job da chay tren VM: chi poll + tai ket qua")
    ap.add_argument("--download", action="append", default=[],
                    help="file tren VM can tai ve (them nhieu lan duoc)")
    a = ap.parse_args()

    # 1) launcher (base64 -> /content/job.py, nohup > /content/out.log)
    src = io.open(a.script, encoding="utf-8").read()
    b64 = base64.b64encode(src.encode("utf-8")).decode("ascii")
    launcher = (
        "import base64, subprocess, sys\n"
        "open('/content/job.py','wb').write(base64.b64decode(%r))\n"
        "f = open('/content/out.log','w')\n"
        "p = subprocess.Popen([sys.executable, '-u', '/content/job.py'],\n"
        "                   stdout=f, stderr=subprocess.STDOUT)\n"
        "open('/content/job.pid','w').write(str(p.pid))\n"
        "print('started pid', p.pid)\n" % b64)
    lpath = os.path.join(TMP, "colab_launcher_task.py")
    io.open(lpath, "w", encoding="utf-8", newline="\n").write(launcher)
    cpath = os.path.join(TMP, "colab_check_task.py")
    io.open(cpath, "w", encoding="utf-8", newline="\n").write(CHECK)

    # 2) tao session (neu chua co) + launch - trong 1 cua so token nho
    if a.no_launch:
        print("[runner] --no-launch: bo qua tao/launch (job da chay tren VM)")
        return _poll_and_fetch(a, cpath)
    with Swap(a.acc):
        rc0, out0 = cli(a.acc, "status", "-s", a.session, timeout=300)
        if rc0 != 0 or "not found" in (out0 or "").lower():
            print("[runner] session %s chua co -> tao (CPU)" % a.session)
            rc1, out1 = cli(a.acc, "new", "-s", a.session, timeout=900)
            print("[runner] new rc=%s %s" % (rc1, (out1 or "")[:150]))
            if rc1 != 0:
                print("[runner] !! tao session that bai")
                return 1
        rc, out = cli(a.acc, "exec", "-s", a.session, "-f", lpath, timeout=600)
        print("[runner] launch rc=%s %s" % (rc, out[:160]))
        if rc != 0:
            return 1
    print("[runner] token da khoi phuc; job chay tren VM")

    return _poll_and_fetch(a, cpath)


def _poll_and_fetch(a, cpath):
    """Poll (swap nho moi 60s) roi tai log + ket qua (swap nho)."""
    # 3) poll (swap nho moi 60s)
    t0 = time.time()
    last = ""
    while time.time() - t0 < a.wait:
        time.sleep(60)
        with Swap(a.acc):
            rc2, out2 = cli(a.acc, "exec", "-s", a.session, "-f", cpath,
                            timeout=300)
        st = (out2 or "").strip().replace("\n", " ")
        print("[runner] %ds %s" % (int(time.time() - t0), st[:100]))
        last = st
        if "ALIVE=0" in st and "SIZE=" in st:
            print("[runner] job ket thuc")
            break

    # 4) tai log + ket qua
    os.makedirs(OUT_DIR, exist_ok=True)
    with Swap(a.acc):
        rc3, out3 = cli(a.acc, "exec", "-s", a.session, "-f", cpath,
                        timeout=300)
        print("[runner] trang thai cuoi: %s" % (out3 or "")[:120])
        d = os.path.join(OUT_DIR, "%s.log" % a.session)
        rc4, out4 = cli(a.acc, "download", "-s", a.session, "/content/out.log",
                        d, timeout=900)
        print("[runner] download log rc=%s %s" % (rc4, (out4 or "")[:100]))
        if os.path.exists(d):
            print("[runner] log: %s (%d KB)" % (d, os.path.getsize(d) // 1024))
        for remote in a.download:
            local = os.path.join(OUT_DIR, os.path.basename(remote))
            rc5, out5 = cli(a.acc, "download", "-s", a.session, remote, local,
                            timeout=1800)
            ok = os.path.exists(local)
            print("[runner] download %s rc=%s -> %s (%s)"
                  % (remote, rc5, local,
                     ("%d KB" % (os.path.getsize(local) // 1024)) if ok
                     else "LOI"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
