"""space_revive.py - thu 'mo lai' Space Docker khi HF bao PAUSED / bi flag.

Ly do can script nay: Space Docker tren HF free tier bi PAUSED khi het quota
CPU 16h/ngay, va co Space bi gan nhan "Flagged as abusive" -> API restart tra
503 ma khong co cach resume truc tiep. Khi HF bat flag / het cooldown, can
mot len thu restart de Space build lai.

Script nay:
  - moi SPACE_REVIVE_INTERVAL giay (mac dinh 600) thu HfApi.restart_space()
  - theo doi runtime.stage; khi len RUNNING -> bao "DA LEN" va dung vong lap
  - ghi log ra file (khong ghi key vao file)

Token theo namespace: kkouadn/* -> HF_TOKEN, himAgayem/* -> HF_TOKEN_2
(neu env khong co token dung thi fallback sang token con lai).

Chay nen:
    python scripts/space_revive.py
"""
import os
import sys
import time

from huggingface_hub import HfApi

DEFAULT_REPOS = ["kkouadn/dual_orchtractor", "himAgayem/ornith-space"]
INTERVAL = int(os.environ.get("SPACE_REVIVE_INTERVAL", "600"))
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs",
                   "space_revive.log")


def token_for(repo):
    """Token theo namespace (Space private -> phai dung token dung acc)."""
    ns = repo.split("/")[0]
    t = os.environ.get("HF_TOKEN", "")
    t2 = os.environ.get("HF_TOKEN_2", "")
    if ns == "himAgayem" and t2:
        return t2
    if ns != "himAgayem" and t:
        return t
    return t or t2


def log(msg):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def main():
    repos = sys.argv[1:] or DEFAULT_REPOS
    if not (os.environ.get("HF_TOKEN") or os.environ.get("HF_TOKEN_2")):
        print("THIEU env HF_TOKEN")
        return 1
    log("bat dau revive: %s (moi %ds)" % (", ".join(repos), INTERVAL))
    while True:
        for r in repos:
            tok = token_for(r)
            if not tok:
                log("%s -> thieu token" % r)
                continue
            api = HfApi(token=tok)
            try:
                rt = api.get_space_runtime(r)
                st = getattr(rt, "stage", None)
                err = getattr(rt, "error_message", None)
                if st == "RUNNING":
                    log("%s -> RUNNING (da song) - dung vong lap" % r)
                    return 0
                log("%s -> stage=%s err=%s" % (r, st, err))
            except Exception as e:
                log("%s -> loi khi doc runtime: %s" % (r, str(e)[:120]))
            try:
                rt = api.restart_space(r)
                log("%s -> restart OK, stage=%s" % (r, getattr(rt, "stage", "?")))
                if getattr(rt, "stage", None) == "RUNNING":
                    log("%s -> DA LEN RUNNING" % r)
                    return 0
            except Exception as e:
                log("%s -> restart FAIL: %s" % (r, str(e)[:160]))
        time.sleep(INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
