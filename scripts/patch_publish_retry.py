# -*- coding: utf-8 -*-
"""
patch_publish_retry.py - them retry/backoff cho 429 (Kaggle rate limit) vao
publish_lora.py.

LY DO (22/10, @MiMo): chay nhieu lenh Kaggle song song (watchdog + kaggle
kernels list + tai output) => API tra 429 Too Many Requests => tai that bai
va mat ca 465MB adapter v24. => can retry co backoff.
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "publish_lora.py")

OLD = '''def run(cmd, timeout=3600):
    p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=timeout)
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \\
        (p.stderr or b"").decode("utf-8", "replace")
'''

NEW = '''def run(cmd, timeout=3600, retry=4):
    """Chay lenh, retry khi Kaggle tra 429 (rate limit) voi backoff."""
    wait = 20
    for i in range(retry + 1):
        p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=timeout)
        out = (p.stdout or b"").decode("utf-8", "replace")
        err = (p.stderr or b"").decode("utf-8", "replace")
        blob = out + err
        if "429" in blob and "Too Many Requests" in blob and i < retry:
            print("   [429] rate limit -> cho %ds roi thu lai (%d/%d)"
                  % (wait, i + 1, retry))
            time.sleep(wait)
            wait = min(wait * 2, 180)
            continue
        return p.returncode, out, err
    return p.returncode, out, err
'''


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    if "rate limit -> cho" in s:
        print("da co retry -> bo qua")
        return 0
    if OLD not in s:
        print("FAIL: khong tim thay ham run()")
        return 1
    s = s.replace(OLD, NEW, 1)
    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print("da them retry 429 vao:", P)
    return 0


if __name__ == "__main__":
    sys.exit(main())
