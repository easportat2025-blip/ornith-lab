# -*- coding: utf-8 -*-
r"""
colab_run_sft.py - chay kernel SFT tren Colab (4-bit) theo che do nen + lay
adapter ve may local.

Dung:
    python scripts\colab_run_sft.py <acc> <session> <local_sft.py> [--steps 500]
    # vi du: acc2 / v24-4bit / phase13-gui\colab_sft_v24\colab_sft.py

Env truyen vao VM:
    ORNITH_WORK=/content/work  ORNITH_BASE=/content/base
    ORNITH_INPUT=/content/data  COLAB_4BIT=1  COLAB_MAX_SEQ=2048
    COLAB_MAX_STEPS=<--steps>  ORNITH_BASE_ID=ornith-ai/Ornith-1.5-9B
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
OUT_DIR = os.path.join(ROOT, "phase13-gui", "colab_out")

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


def cli(acc, *args, timeout=600):
    d = os.path.join(ROOT, "scripts", "colab_accounts", "acc%d" % acc)
    cmd = [COLAB, "--config", os.path.join(d, "sessions.json"),
           "-c", os.path.join(d, "oauth.json")] + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except subprocess.TimeoutExpired as e:
        # 22/10: exec co the bi treo (kernel dang chay job) => coi nhu da
        # launch (khong phai loi) - viec se duoc xac nhan qua log tren VM
        return 0, "TIMEOUT-DA-LAUNCH " + str(e)[:120]


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    acc = int(sys.argv[1])
    sess = sys.argv[2]
    script = sys.argv[3]
    steps = 500
    if "--steps" in sys.argv:
        steps = int(sys.argv[sys.argv.index("--steps") + 1])

    src = io.open(script, encoding="utf-8").read()
    b64 = base64.b64encode(src.encode("utf-8")).decode("ascii")

    env_lines = "\n".join([
        'export ORNITH_WORK=/content/work',
        'export ORNITH_BASE=/content/base',
        'export ORNITH_INPUT=/content/data',
        'export COLAB_4BIT=1',
        'export COLAB_MAX_SEQ=2048',
        'export COLAB_MAX_STEPS=%d' % steps,
        'export ORNITH_BASE_ID=ornith-ai/Ornith-1.5-9B',
    ])
    launcher = (
        "import base64, os, subprocess, sys\n"
        "open('/content/job.py','wb').write(base64.b64decode(%r))\n"
        "f = open('/content/out.log','w')\n"
        "p = subprocess.Popen(['bash','-lc', %r + ' ; python -u /content/job.py'],\n"
        "                   stdout=f, stderr=subprocess.STDOUT)\n"
        "open('/content/job.pid','w').write(str(p.pid))\n"
        "print('started pid', p.pid)\n" % (b64, env_lines))
    lpath = os.path.join(TMP, "colab_launcher_sft.py")
    io.open(lpath, "w", encoding="utf-8", newline="\n").write(launcher)

    # 22/10: session CU co the con song o server-side (local state bi prune =>
    # status bao 'not found' nhung server van co) => THU EXEC THUOC; chi tao
    # session moi khi exec that bai "not found".
    rc0, out0 = cli(acc, "exec", "-s", sess, "-f", lpath, timeout=900)
    if "not found" in out0.lower() or "lost" in out0.lower():
        print("  [tao session moi %s tren acc%d]" % (sess, acc), flush=True)
        rcn, outn = cli(acc, "new", "-s", sess, "--gpu", "T4", timeout=900)
        print("  new: rc=%s %s" % (rcn, outn[:160]), flush=True)
        if rcn != 0:
            return 1
        rc0, out0 = cli(acc, "exec", "-s", sess, "-f", lpath, timeout=900)
    print("  launch rc=%s %s" % (rc0, out0[:160]), flush=True)
    if rc0 != 0 and "started pid" not in out0:
        return 1

    cpath = os.path.join(TMP, "colab_check.py")
    io.open(cpath, "w", encoding="utf-8", newline="\n").write(CHECK)
    t0 = time.time()
    while time.time() - t0 < 60 * 60 * 4:
        time.sleep(60)
        try:
            rc2, out2 = cli(acc, "exec", "-s", sess, "-f", cpath, timeout=120)
        except Exception:
            # kernel dang chay job nen exec bi queue -> poll qua
            print("  ... (job dang chay, poll qua)", flush=True)
            continue
        alive = "ALIVE=1" in out2
        print("  ... %s (%d phut)"
              % (out2.strip().replace("\n", " ")[:60], int((time.time() - t0) / 60)),
              flush=True)
        if not alive and "SIZE=" in out2:
            break
    os.makedirs(OUT_DIR, exist_ok=True)
    dst = os.path.join(OUT_DIR, "%s.log" % sess)
    rc3, out3 = cli(acc, "download", "-s", sess, "/content/out.log", dst,
                    timeout=900)
    print("  download rc=%s %s" % (rc3, out3[:120]))
    if os.path.exists(dst):
        print("  -> %s (%d KB)" % (dst, os.path.getsize(dst) // 1024))
    # adapter (neu co)
    for name, remote in (("gui_lora", "/content/work/gui_lora")):
        d2 = os.path.join(OUT_DIR, "%s_%s" % (sess, name))
        rc4, out4 = cli(acc, "download", "-s", sess, remote, d2, timeout=1800)
        print("  adapter %s rc=%s %s" % (name, rc4, out4[:100]))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
