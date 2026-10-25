# -*- coding: utf-8 -*-
r"""
colab_wait_run.py - CHO den khi co acc Colab trong (free tier: 1 session/acc,
session zombie bi thu hoi sau ~15-30 phut) roi chay 1 job SFT.

Dung:
    python scripts\colab_wait_run.py <acc> <session> <script.py> [--steps 400] [--wait 7200]
    python scripts\colab_wait_run.py auto <script.py> --steps 400
      # 'auto' = thu cac acc theo thu tu, acc nao trong truoc thi chay
ASCII-only source.
"""
import io
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "scripts", "colab_run_sft.py")


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        print(__doc__)
        return 2
    # script = tham so dau tien ket thuc bang .py
    script = next((x for x in a if x.endswith(".py")), "")
    if not script:
        print("thieu duong dan script .py")
        return 2
    accs = []
    if a[0] == "auto":
        accs = [1, 2, 3, 4, 5]
    else:
        accs = [int(x) for x in a[0].split(",")]
    sess = a[1] if a[0] != "auto" else "sft-4bit"
    steps = "400"
    if "--steps" in a:
        steps = a[a.index("--steps") + 1]
    wait = 7200
    if "--wait" in a:
        wait = a[a.index("--wait") + 1]

    for rnd in range(1, 20):
        for acc in accs:
            cmd = [sys.executable, RUNNER, str(acc), sess, script,
                   "--steps", steps]
            print("[wait] vong %d: thu acc%d ..." % (rnd, acc), flush=True)
            try:
                p = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=1800)
                out = (p.stdout or "") + (p.stderr or "")
            except subprocess.TimeoutExpired:
                print("[wait] acc%d: timeout (co the dang chay job) - xem log tren VM"
                      % acc, flush=True)
                return 0
            if "started pid" in out or "Allocation refused" not in out:
                print("[wait] acc%d: DA CHAY" % acc, flush=True)
                print(out[-1500:], flush=True)
                return 0
            print("[wait] acc%d: chua duoc (busy/zombie) - thu acc tiep"
                  % acc, flush=True)
        time.sleep(180)
    print("[wait] het gio - chua chay duoc acc nao")
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
