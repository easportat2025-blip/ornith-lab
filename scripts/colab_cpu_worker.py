# -*- coding: utf-8 -*-
r"""
colab_cpu_worker.py - WORKER CPU tren Colab cho agent phu (GLM/MiMo/GPT...).

Vi sao (22/10): may local chi co 2 core / 3.9 GB RAM va DANG chay 5 agent
OpenCode + bus + watchdog => viec nang (sinh dataset, render anh, self-test
checker) lam nghen may va thieu RAM. Colab CPU VM: 2 vCPU / 13 GB RAM (hoac
--high-mem ~26 GB) => chuyen viec nang sang do, giu may local cho agent.

Dung:
    # 1) cap session CPU cho acc N
    python scripts\colab_cpu_worker.py provision 2 --name glm
    # 2) chay 1 task (script local) tren session do, che do nen + lay log
    python scripts\colab_cpu_worker.py run 2 --session glm --script scripts\x.py --wait 3600
    # 3) xem trang thai / tai ket qua
    python scripts\colab_cpu_worker.py status 2
    python scripts\colab_cpu_worker.py fetch 2 --session glm
    # 4) dung session
    python scripts\colab_cpu_worker.py stop 2 --session glm

Token: moi acc = 1 bo token rieng (scripts/colab_accounts/accN/token.json) =>
swap vao global khi goi CLI (xem login_colab_acc.py).
ASCII-only source.
"""
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC_ROOT = os.path.join(ROOT, "scripts", "colab_accounts")
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


def acc_dir(i):
    return os.path.join(ACC_ROOT, "acc%d" % i)


def acc_token(i):
    return os.path.join(acc_dir(i), "token.json")


def has_token(i):
    p = acc_token(i)
    if not os.path.exists(p):
        return False
    try:
        return bool(json.load(io.open(p, encoding="utf-8")))
    except Exception:
        return os.path.getsize(p) > 50


def proxy_env(i):
    """Proxy RIENG cho acc i (neu co: scripts/colab_accounts/accN/proxy.json
    {https_proxy, http_proxy, socks5_proxy}) - de moi acc ra IP khac nhau."""
    p = os.path.join(acc_dir(i), "proxy.json")
    env = dict(os.environ)
    if os.path.exists(p):
        try:
            d = json.load(io.open(p, encoding="utf-8"))
            for k, v in d.items():
                if v:
                    env[str(k).upper()] = str(v)
                    env[str(k).lower()] = str(v)
        except Exception:
            pass
    return env


def cli(i, args, timeout=600, env=None):
    d = acc_dir(i)
    cmd = [COLAB, "--config", os.path.join(d, "sessions.json"),
           "-c", os.path.join(d, "oauth.json")] + list(args)
    backup = None
    if os.path.exists(GLOBAL_TOKEN):
        backup = GLOBAL_TOKEN + ".bak_worker"
        shutil.copy2(GLOBAL_TOKEN, backup)
    try:
        if has_token(i):
            shutil.copy2(acc_token(i), GLOBAL_TOKEN)
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=env or os.environ)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    finally:
        if backup and os.path.exists(backup):
            shutil.copy2(backup, GLOBAL_TOKEN)
            try:
                os.remove(backup)
            except Exception:
                pass


def provision(i, name="cpu", high_mem=False, gpu=None):
    args = ["new", "-s", name]
    if gpu:
        args += ["--gpu", gpu]
    if high_mem:
        args += ["--high-mem"]
    rc, out = cli(i, args, timeout=900)
    print("  acc%d provision %s: rc=%s %s" % (i, name, rc, out[:200]))
    return rc == 0


def run_task(i, sess, script, wait=3600):
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
    rc, out = cli(i, ["exec", "-s", sess, "-f", lpath], timeout=600)
    print("  launch rc=%s %s" % (rc, out[:160]))
    if rc != 0:
        return False
    cpath = os.path.join(TMP, "colab_check.py")
    io.open(cpath, "w", encoding="utf-8", newline="\n").write(CHECK)
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(40)
        rc2, out2 = cli(i, ["exec", "-s", sess, "-f", cpath], timeout=300)
        alive = "ALIVE=1" in out2
        print("  ... %s (%ds)" % (out2.strip().replace("\n", " ")[:70],
                                 int(time.time() - t0)), flush=True)
        if not alive and "SIZE=" in out2:
            break
    fetch(i, sess)
    return True


def fetch(i, sess):
    os.makedirs(OUT_DIR, exist_ok=True)
    dst = os.path.join(OUT_DIR, "%s.log" % sess)
    rc, out = cli(i, ["download", "-s", sess, "/content/out.log", dst],
                  timeout=900)
    print("  fetch rc=%s %s" % (rc, out[:120]))
    if os.path.exists(dst):
        print("  -> %s (%d KB)" % (dst, os.path.getsize(dst) // 1024))
    return dst


def status(i):
    rc, out = cli(i, ["sessions"], timeout=300)
    print("  acc%d sessions: %s" % (i, out.replace("\n", " | ")[:200]))
    rc2, out2 = cli(i, ["usage"], timeout=300)
    print("  acc%d usage: %s" % (i, out2.replace("\n", " | ")[:200]))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    acc = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    env = proxy_env(acc)
    if cmd == "provision":
        name = "cpu"
        if "--name" in sys.argv:
            name = sys.argv[sys.argv.index("--name") + 1]
        hm = "--high-mem" in sys.argv
        gpu = None
        if "--gpu" in sys.argv:
            gpu = sys.argv[sys.argv.index("--gpu") + 1]
        provision(acc, name, hm, gpu)
    elif cmd == "run":
        sess = "cpu"
        if "--session" in sys.argv:
            sess = sys.argv[sys.argv.index("--session") + 1]
        script = sys.argv[sys.argv.index("--script") + 1]
        wait = 3600
        if "--wait" in sys.argv:
            wait = int(sys.argv[sys.argv.index("--wait") + 1])
        run_task(acc, sess, script, wait)
    elif cmd == "fetch":
        sess = "cpu"
        if "--session" in sys.argv:
            sess = sys.argv[sys.argv.index("--session") + 1]
        fetch(acc, sess)
    elif cmd == "status":
        status(acc)
    elif cmd == "stop":
        sess = "cpu"
        if "--session" in sys.argv:
            sess = sys.argv[sys.argv.index("--session") + 1]
        rc, out = cli(acc, ["stop", "-s", sess], timeout=600)
        print("  stop rc=%s %s" % (rc, out[:120]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
