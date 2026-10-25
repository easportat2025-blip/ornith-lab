"""dashboard_sync.py - dong bo du lieu DESKTOP-ENV len dashboard cua Space.

Doc output cua harness (phase14-desktop/harness.py):
    out/actions.jsonl   moi dong = 1 buoc: {task_id, episode, step, obs, action,
                     act_desc, reward, raw}
    out/reward.json     {task_id: {best_reward, success, threshold, steps}}
    out/obs/*.png       anh chup man hinh THAT (model nhin cai nay)

Ghi vao thu muc static cua Space (nguon su cho push_space_static.py):
    static/desktop_state.json     metadata (task, step, action, reward, success)
    static/desktop/obs/*.png      anh cua episode moi nhat (resize <= width)

KHONG push gi (mac dinh --push TAT): can HF_TOKEN + --push de day len Space repo.
ASCII-only source (bai hoc cp1252).
"""
import argparse
import io
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(ROOT, "phase14-space", "static")


def log(m):
    print("[dbsync] %s" % m, flush=True)


def read_jsonl(p, limit=200000):
    rows = []
    if not os.path.exists(p):
        return rows
    try:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i > 200000:
                    break
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    except Exception as e:
        log("doc %s loi: %s" % (p, e))
    return rows


def find_harness_dir(explicit):
    if explicit:
        return explicit if os.path.isdir(explicit) else None
    cands = []
    base = HERE
    for d in os.listdir(base):
        full = os.path.join(base, d)
        if not os.path.isdir(full):
            continue
        if d.startswith("out_harness") or d.startswith("harness_out"):
            cands.append(full)
    if not cands:
        return None
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cands[0]


def resize_copy(src, dst, width):
    """Copy (resize <= width) -> dst. Return bytes written or 0."""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        from PIL import Image
        img = Image.open(src).convert("RGB")
        if img.width > width:
            h = int(img.height * width / float(img.width))
            img = img.resize((width, h), Image.LANCZOS)
        img.save(dst, "PNG", optimize=True)
        return os.path.getsize(dst)
    except Exception as e:
        log("resize loi (%s) -> copy thu: %s" % (type(e).__name__, e))
        try:
            shutil.copy(src, dst)
            return os.path.getsize(dst)
        except Exception as e2:
            log("copy fail: %s" % e2)
            return 0


def collect(harness_dir, out_dir, max_shots, width):
    rows = read_jsonl(os.path.join(harness_dir, "actions.jsonl"))
    summary = {}
    rp = os.path.join(harness_dir, "reward.json")
    if os.path.exists(rp):
        try:
            summary = json.load(io.open(rp, encoding="utf-8"))
        except Exception as e:
            log("reward.json loi: %s" % e)
    if not rows:
        log("khong co dong nao trong %s" % harness_dir)
        return {"ts": time.time(), "source": harness_dir, "tasks": {},
                "note": "chua co episode (chay harness truoc)"}

    # episode moi nhat cho moi task
    latest = {}
    for r in rows:
        key = (r.get("task_id"), r.get("episode"))
        cur = latest.get(key)
        if cur is None or (r.get("step") or 0) > (cur.get("step") or 0):
            latest[key] = r
    by_task = {}
    for (task_id, ep), last in latest.items():
        ep_rows = [r for r in rows
                   if r.get("task_id") == task_id and r.get("episode") == ep]
        ep_rows.sort(key=lambda r: r.get("step") or 0)
        by_task.setdefault(task_id, []).append((ep, ep_rows))

    state = {"ts": time.time(),
             "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
             "source": os.path.relpath(harness_dir, ROOT).replace("\\", "/"),
             "tasks": {}}
    obs_dir = os.path.join(out_dir, "desktop", "obs")
    total_bytes = 0
    for task_id, eps in by_task.items():
        ep, ep_rows = max(eps, key=lambda x: (x[0] or 0))
        steps = ep_rows[-max_shots:]
        details = []
        for r in steps:
            rel = (r.get("obs") or "").replace("\\", "/")
            src = os.path.join(harness_dir, rel)
            img = None
            if rel and os.path.exists(src):
                name = "%s_e%02d_s%02d.png" % (task_id, ep or 0,
                                               r.get("step") or 0)
                dst = os.path.join(obs_dir, name)
                n = resize_copy(src, dst, width)
                total_bytes += n
                img = "desktop/obs/" + name
            details.append({
                "step": r.get("step"),
                "action": r.get("action"),
                "act_desc": r.get("act_desc"),
                "reward": r.get("reward"),
                "raw": (r.get("raw") or "")[:300],
                "img": img,
            })
        summ = summary.get(task_id) or {}
        rewards = [d["reward"] for d in details
                   if isinstance(d.get("reward"), (int, float))]
        state["tasks"][task_id] = {
            "episode": ep,
            "n_steps": len(ep_rows),
            "shown_steps": len(details),
            "success": bool(summ.get("success")),
            "threshold": summ.get("threshold"),
            "best_reward": summ.get("best_reward",
                                    max(rewards) if rewards else None),
            "last_reward": rewards[-1] if rewards else None,
            "step_detail": details,
        }
        log("task %s: ep=%s steps=%s best=%s success=%s" %
            (task_id, ep, len(ep_rows),
             state["tasks"][task_id]["best_reward"],
             state["tasks"][task_id]["success"]))
    # clean anh cu (giua cho repo nhe)
    try:
        keep = set()
        for t in state["tasks"].values():
            for d in t["step_detail"]:
                if d.get("img"):
                    keep.add(os.path.basename(d["img"]))
        if os.path.isdir(obs_dir):
            for f in os.listdir(obs_dir):
                if f not in keep:
                    try:
                        os.remove(os.path.join(obs_dir, f))
                    except Exception:
                        pass
    except Exception as e:
        log("cleanup loi: %s" % e)
    log("tong anh moi: %.1f MB" % (total_bytes / 1e6))
    return state


def push(out_dir, repo, token):
    if not token:
        log("thieu HF_TOKEN -> skip push")
        return False
    try:
        from huggingface_hub import HfApi, upload_folder
        api = HfApi(token=token)
        upload_folder(repo_id=repo, folder_path=out_dir, repo_type="space",
                      commit_message="desktop dashboard %s" %
                      time.strftime("%H:%M:%S"), token=token)
        log("uploaded -> %s" % repo)
        return True
    except Exception as e:
        log("push FAIL: %s" % str(e)[:200])
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--harness-dir", default=None)
    ap.add_argument("--out-dir", default=DEFAULT_OUT)
    ap.add_argument("--max-shots", type=int, default=12)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--push", action="store_true",
                    help="day len Space repo (can HF_TOKEN) - mac dinh TAT")
    ap.add_argument("--repo", default=os.environ.get("SPACE_REPO",
                                                      "himAgayem/ornith-agent"))
    a = ap.parse_args()

    hd = find_harness_dir(a.harness_dir)
    if not hd:
        log("khong tim thay thu muc output cua harness (phase14-desktop/out_harness*)")
        hd = a.harness_dir or os.path.join(HERE, "out_harness")
    log("harness dir: %s" % hd)
    state = collect(hd, a.out_dir, a.max_shots, a.width)
    os.makedirs(a.out_dir, exist_ok=True)
    p = os.path.join(a.out_dir, "desktop_state.json")
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=1)
    log("ghi %s (%d bytes)" % (p, os.path.getsize(p)))
    if a.push:
        push(a.out_dir, a.repo, os.environ.get("HF_TOKEN", ""))
    else:
        log("skip push (dung --push + HF_TOKEN neu can)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
