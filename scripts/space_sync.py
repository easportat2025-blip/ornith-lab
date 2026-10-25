"""space_sync.py - may local day trang thai + LOBBY tail len Space (de Space
luon co snapshot moi, khong can copy kaggle key sang HF).

Chay (neu co HF Space URL + token):
    python scripts/space_sync.py --url https://<user>-<space>.hf.space --token $HF_TOKEN
Mac dinh: chi doc local + ghi ra file state.json (de kiem tra), khong gui gi.
"""
import argparse
import io
import json
import os
import subprocess
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_LOCAL = os.path.join(ROOT, "scripts", "space_state.json")


def read(p, limit=400000):
    try:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except Exception:
        return ""


def kaggle_cmd(args, timeout=120):
    try:
        p = subprocess.run(["kaggle"] + args, capture_output=True, timeout=timeout,
                           creationflags=(0x08000000 if os.name == "nt" else 0))
        return (p.stdout or b"").decode("utf-8", "replace")
    except Exception as e:
        return "ERR " + str(e)


QUOTA_CACHE = os.path.join(ROOT, "scripts", "quota_cache.json")
QUOTA_TTL = 6 * 3600          # dashboard: cache quota 6h (check thuc 1 lan/ngay)


def quota_cached():
    """Doc quota tu cache (TTL 6h) - khong goi Kaggle moi 3 phut mot lan."""
    try:
        d = json.load(io.open(QUOTA_CACHE, encoding="utf-8"))
        if time.time() - d.get("ts", 0) < QUOTA_TTL:
            return d.get("txt", "")
    except Exception:
        pass
    txt = kaggle_cmd(["quota"])[:600]
    try:
        with io.open(QUOTA_CACHE, "w", encoding="utf-8") as fh:
            json.dump({"ts": time.time(), "txt": txt}, fh)
    except Exception:
        pass
    return txt


def collect():
    st = {"ts": time.time()}
    st["quota"] = quota_cached()
    st["watchdog_state"] = read(os.path.join(ROOT, "scripts",
                                             "watchdog_state.json"), 20000)
    st["queue_state"] = read(os.path.join(ROOT, "scripts",
                                         "gpu_queue_state.json"), 20000)
    st["watchdog_log"] = read(os.path.join(ROOT, "scripts", "watchdog.log"),
                               20000)[-12000:]
    st["lobby_tail"] = read(os.path.join(ROOT, "agent.md"), 400000)[-20000:]
    for name, p in [("b15_v18", "phase13-gui/out_bench_v15/b15_result.json"),
                    ("b15_v20", "phase13-gui/out_bench_v15_v20/b15_result.json"),
                    ("bench3d", "phase13-gui/out_bench_3d/bench3d_result.json"),
                    ("gates", "phase13-gui/gate_results.jsonl")]:
        t = read(os.path.join(ROOT, p), 200000)
        if t:
            try:
                d = json.loads(t)
                st[name] = d.get("summary", d) if isinstance(d, dict) else {}
            except Exception:
                st[name] = {}
    return st


def token_for_repo(repo):
    """Token theo namespace cua Space (private Space -> phai dung token acc).

    himAgayem/* -> HF_TOKEN_2, cac acc khac -> HF_TOKEN.
    """
    t = os.environ.get("HF_TOKEN", "")
    t2 = os.environ.get("HF_TOKEN_2", "")
    if repo.split("/")[0].lower() == "himagayem":
        return t2 or t
    return t or t2


def push_to_space(state, url, token):
    """Day state.json vao Space repo (static dashboard doc file nay)."""
    if not token:
        print("chua co HF_TOKEN -> chi ghi local")
        return
    import io as _io
    from huggingface_hub import HfApi
    repo = os.environ.get("SPACE_REPO", "himAgayem/ornith-agent")
    tok = token_for_repo(repo) or token
    api = HfApi(token=tok)
    p = os.path.join(ROOT, "scripts", "space_state.json")
    with _io.open(p, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False)
    try:
        api.upload_file(
            path_or_fileobj=p, path_in_repo="state.json", repo_id=repo,
            repo_type="space", commit_message="state %s" %
            time.strftime("%H:%M:%S"), token=tok)
        print("state.json -> %s (da commit)" % repo)
    except Exception as e:
        print("push state FAIL:", str(e)[:200])


def push_to_docker_space(state, url, token):
    """Day state len Space DOCKER (app FastAPI) qua POST /ingest.

    Space private -> phai gui header Authorization: Bearer <token>.
    Neu Space chua chay (PAUSED/flag) -> in loi, van tiep tuc vong lap.
    """
    if not url:
        return False
    if not token:
        print("chua co HF_TOKEN -> khong gui /ingest")
        return False
    data = json.dumps(state, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + "/ingest", data=data,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            # HF tra trang "Preparing Space" (HTML) khi container chua len ->
            # phai kiem tra JSON "ok" moi coi la thanh cong
            try:
                j = json.loads(body.decode("utf-8", "replace"))
            except Exception:
                j = {}
            if not j.get("ok"):
                print("ingest Docker Space: HTTP %s nong phai app (container "
                      "chua chay?)" % r.status)
                return False
            print("ingest Docker Space:", r.status, body[:120])
            return True
    except Exception as e:
        print("ingest Docker Space FAIL:", str(e)[:160])
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("SPACE_URL", ""))
    ap.add_argument("--token", default=os.environ.get("HF_TOKEN", ""))
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    st = collect()
    with io.open(STATE_LOCAL, "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)
    print("state: %d bytes -> %s" % (len(json.dumps(st)), STATE_LOCAL))
    if not a.dry and not a.no_push:
        push_to_space(st, a.url, a.token)
    if a.dry or not a.url:
        print("dry-run: khong gui (can --url + --token de gui that)")
        return
    push_to_docker_space(st, a.url, a.token)


if __name__ == "__main__":
    main()
