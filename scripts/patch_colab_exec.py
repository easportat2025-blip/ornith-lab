# -*- coding: utf-8 -*-
"""
patch_colab_exec.py - colab_exec_bg.py:
  (1) chi them '-c <oauth.json>' khi file do TON tai (acc moi co token.json
      nhung thieu oauth.json => CLI bao loi du khong can client OAuth rieng)
  (2) TU TAO session neu chua co (free tier thu hoi session idle ~15-30'
      => phai 'tao + chay' lien tuc trong 1 lenh)
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "colab_exec_bg.py")

OLD_CLI = '''    base = [COLAB]
    if acc:
        d = os.path.join(ROOT, "scripts", "colab_accounts", "acc%d" % acc)
        base += ["--config", os.path.join(d, "sessions.json"),
                 "-c", os.path.join(d, "oauth.json")]'''

NEW_CLI = '''    base = [COLAB]
    if acc:
        d = os.path.join(ROOT, "scripts", "colab_accounts", "acc%d" % acc)
        base += ["--config", os.path.join(d, "sessions.json")]
        # '-c' (client OAuth rieng) chi khi file ton tai - acc moi chi co
        # token.json => them '-c' se lam CLI bao loi
        _oauth = os.path.join(d, "oauth.json")
        if os.path.exists(_oauth):
            base += ["-c", _oauth]'''

OLD_LAUNCH = '''    rc, out = cli("exec", "-s", sess, "-f", lpath, timeout=600, acc=acc)'''

NEW_LAUNCH = '''    # FIX (MiMo 22/10): free tier thu hoi session idle ~15-30' => neu session
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
    rc, out = cli("exec", "-s", sess, "-f", lpath, timeout=600, acc=acc)'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD_CLI not in s:
    print("FAIL: khong tim thay khoi cli()")
    sys.exit(1)
if OLD_LAUNCH not in s:
    print("FAIL: khong tim thay khoi launch")
    sys.exit(1)
s = s.replace(OLD_CLI, NEW_CLI, 1).replace(OLD_LAUNCH, NEW_LAUNCH, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da sua colab_exec_bg.py")
