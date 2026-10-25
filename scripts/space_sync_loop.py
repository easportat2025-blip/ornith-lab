"""space_sync_loop.py - vong lap day state.json len Space (moi ~3 phut).

Chay nen:  python scripts/space_sync_loop.py
Token lay tu env HF_TOKEN (KHONG ghi vao file). Dung khi may local bat.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import space_sync  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
INTERVAL = int(os.environ.get("SPACE_SYNC_INTERVAL", "180"))



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


def main():
    if not os.environ.get("HF_TOKEN"):
        print("THIEU env HF_TOKEN -> khong sync")
        return 1
    print("[space-sync] bat dau, moi %ds" % INTERVAL, flush=True)
    while True:
        try:
            st = space_sync.collect()
            space_sync.push_to_space(st, "", os.environ["HF_TOKEN"])
        except Exception as e:
            print("[space-sync] loi:", e, flush=True)
        try:
            update_result_daily()
        except Exception as e:
            print("[space-sync] result.md loi:", e, flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
