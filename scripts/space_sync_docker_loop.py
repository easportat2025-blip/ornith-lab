"""space_sync_docker_loop.py - day state len Space DOCKER (opencode + API).

Khac voi space_sync_loop.py (day state.json len Space STATIC), loop nay POST
vao /ingest cua app FastAPI tren Space Docker de /status tren do tra state
moi nhat.

Chay nen (token tu env HF_TOKEN - KHONG ghi key vao file):
    python scripts/space_sync_docker_loop.py

Bien:
    SPACE_DOCKER_URL   mac dinh https://kkouadn-dual-orchtractor.hf.space
    SPACE_DOCKER_URL2  Space Docker thu hai (mac dinh himAgayem-ornith-space)
    SPACE_SYNC_INTERVAL  mac dinh 180 (giay)

Token theo URL: khau `himagayem` -> HF_TOKEN_2, con lai -> HF_TOKEN.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import space_sync  # noqa: E402

DEFAULT_URL = "https://kkouadn-dual-orchtractor.hf.space"
DEFAULT_URL2 = "https://himagayem-ornith-space.hf.space"
INTERVAL = int(os.environ.get("SPACE_SYNC_INTERVAL", "180"))


def token_for(url):
    t = os.environ.get("HF_TOKEN", "")
    t2 = os.environ.get("HF_TOKEN_2", "")
    if "himagayem" in url.lower():
        return t2 or t
    return t or t2


def main():
    urls = [u for u in (os.environ.get("SPACE_DOCKER_URL", DEFAULT_URL),
                        os.environ.get("SPACE_DOCKER_URL2", DEFAULT_URL2))
            if u]
    if not (os.environ.get("HF_TOKEN") or os.environ.get("HF_TOKEN_2")):
        print("THIEU env HF_TOKEN -> khong sync")
        return 1
    print("[space-sync-docker] %s moi %ds" % (", ".join(urls), INTERVAL),
          flush=True)
    while True:
        try:
            st = space_sync.collect()
            # giu Space STATIC (dashboard) cung cap state moi nhat
            space_sync.push_to_space(st, "", os.environ.get("HF_TOKEN", ""))
            for u in urls:
                ok = space_sync.push_to_docker_space(st, u, token_for(u))
                if not ok:
                    print("[space-sync-docker] %s khong phan hoi (co the dang "
                          "PAUSED) - thu lai lan sau" % u, flush=True)
        except Exception as e:
            print("[space-sync-docker] loi:", str(e)[:200], flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
