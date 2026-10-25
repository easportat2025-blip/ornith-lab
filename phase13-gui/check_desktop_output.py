"""check_desktop_output.py - triage nhanh output DESKTOP-BENCH (GLM, 22/10).

Kiem tra 1 thu muc output (vi du phase13-gui/out_desktop_bench_a):
  1) co desktop_result.json / reward.json / actions.jsonl / obs/*.png khong
  2) so episode theo task (co dung so ep mong doi khong)
  3) anh quan sat: so file, file 0 byte (screenshot fail), kich thuoc
  4) parse_rate: raw co "ACTION:" khong, phan bo verb, episode stuck
  5) suc khoe env tu log: [preflight] OK / display OK / screenshot fail /
     "Missing X server" / "adapter ON" (model + adapter da load?)
  => in KET LUAN ngan: env OK / model OK / ket qua dung duoc khong.

Chi doc, khong GPU/key/mang.
Dung:
  python phase13-gui/check_desktop_output.py phase13-gui/out_desktop_bench_a
  python phase13-gui/check_desktop_output.py <dir> --expect-episodes 20
"""
import argparse
import collections
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(m):
    print("[chk] %s" % m, flush=True)


def find(d, *names):
    for n in names:
        p = os.path.join(d, n)
        if os.path.exists(p):
            return p
    return None


def load_json(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception as e:
        log("LOI doc %s: %s" % (p, e))
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--expect-episodes", type=int, default=20)
    ap.add_argument("--expect-tasks", default="")
    a = ap.parse_args()
    d = os.path.abspath(a.dir)
    log("dir: %s" % d)
    if not os.path.isdir(d):
        log("FAIL: khong ton tai")
        return 1
    problems = []
    warns = []

    # 1) file bat buoc
    res_p = find(d, "desktop_result.json", "desktop_bench/desktop_result.json")
    act_p = find(d, "actions.jsonl", "desktop_bench/actions.jsonl")
    rew_p = find(d, "reward.json", "desktop_bench/reward.json")
    log("result : %s" % (os.path.relpath(res_p, d) if res_p else "THIEU"))
    log("actions: %s" % (os.path.relpath(act_p, d) if act_p else "THIEU"))
    log("reward : %s" % (os.path.relpath(rew_p, d) if rew_p else "THIEU"))
    if not res_p:
        problems.append("khong co desktop_result.json => kernel chua xong hoac crash")
        for p in problems:
            log("PROBLEM: %s" % p)
        return 2
    res = load_json(res_p) or {}
    eps = res.get("episodes") or []
    by_task = collections.OrderedDict()
    for e in eps:
        by_task.setdefault(e.get("task_id"), []).append(e)
    log("episodes: %d | tasks: %s" % (len(eps), sorted(by_task)))
    for t, gg in sorted(by_task.items()):
        wins = sum(1 for e in gg if e.get("win"))
        log("  %-16s n=%-3d win=%-3d (%.0f%%)" %
            (t, len(gg), wins, 100.0 * wins / max(1, len(gg))))
        if a.expect_episodes and len(gg) != a.expect_episodes:
            warns.append("task %s co %d ep (mong doi %d)" %
                         (t, len(gg), a.expect_episodes))
    if a.expect_tasks:
        want = sorted(x.strip() for x in a.expect_tasks.split(",") if x.strip())
        got = sorted(by_task)
        if want != got:
            problems.append("task khong khop: mong doi %s, co %s" % (want, got))
    if a.expect_episodes and len(eps) != a.expect_episodes * len(by_task):
        warns.append("tong ep = %d, mong doi %d" %
                     (len(eps), a.expect_episodes * len(by_task)))

    # 2) anh quan sat
    obs_dirs = []
    for root, dirs, files in os.walk(d):
        if os.path.basename(root) == "obs" and files:
            obs_dirs.append(root)
    tot_png = 0
    zero = []
    small = []
    sizes = []
    for od in obs_dirs:
        for f in os.listdir(od):
            if not f.lower().endswith(".png"):
                continue
            p = os.path.join(od, f)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            tot_png += 1
            sizes.append(sz)
            if sz == 0:
                zero.append(p)
            elif sz < 3000:
                small.append((p, sz))
    log("anh quan sat: %d file PNG trong %d thu muc obs" % (tot_png, len(obs_dirs)))
    if tot_png == 0:
        problems.append("KHONG co anh quan sat (obs/*.png) => model khong the thay gi")
    if zero:
        problems.append("%d anh 0 byte (screenshot fail)" % len(zero))
    if small:
        warns.append("%d anh < 3KB (nen rong?)" % len(small))
    if sizes:
        log("kich thuoc anh: min=%d max=%d median=%d" %
            (min(sizes), max(sizes), sorted(sizes)[len(sizes) // 2]))

    # 3) actions + parse_rate
    rows = []
    if act_p:
        for line in io.open(act_p, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    log("actions.jsonl: %d dong" % len(rows))
    if rows:
        with_raw = [r for r in rows if (r.get("raw") or "").strip()]
        with_act = [r for r in with_raw
                    if re.search(r"ACTION\s*:", r.get("raw") or "", re.I)]
        log("parse_rate (raw co ACTION): %.3f (%d/%d)" %
            (len(with_act) / max(1, len(with_raw)), len(with_act), len(with_raw)))
        verbs = collections.Counter()
        for r in rows:
            v = (r.get("action") or r.get("desc") or "").strip().split()
            verbs[v[0].upper() if v else "?"] += 1
        log("verb: %s" % dict(verbs.most_common(8)))
        rew = [r.get("reward") for r in rows if isinstance(r.get("reward"), (int, float))]
        if rew:
            log("reward: n=%d max=%s mean=%.3f" %
                (len(rew), max(rew), sum(rew) / len(rew)))
        n_none = sum(1 for r in rows if r.get("reward") is None)
        if n_none:
            warns.append("%d dong reward=None (checker khong doc duoc app state)" % n_none)

    # 4) suc khoe env tu log
    logp = None
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith(".log"):
                logp = os.path.join(root, f)
    if logp:
        s = io.open(logp, encoding="utf-8", errors="replace").read()
        log("log: %s (%d KB)" % (os.path.relpath(logp, d), len(s) // 1024))
        checks = [
            ("[preflight] OK", "preflight X11 OK"),
            ("display :99", "co dong display"),
            ("adapter ON", "model + adapter da load"),
            ("screenshot fail", "CO LOI chup anh"),
            ("Missing X server", "THIEU X SERVER"),
            ("import: not found", "thieu imagemagick"),
            ("Traceback", "co traceback"),
            ("FAIL:", "co dong FAIL"),
        ]
        for pat, desc in checks:
            n = s.count(pat)
            if n:
                log("  %-22s %d lan  (%s)" % (pat, n, desc))
                if pat in ("screenshot fail", "Missing X server",
                           "import: not found", "Traceback"):
                    problems.append("%s x%d" % (desc, n))
        if "[preflight] OK" not in s and "Missing X server" in s:
            problems.append("preflight khong bao OK => X11 chua len")
        if "adapter ON" not in s:
            warns.append("khong thay 'adapter ON' => model co the chua load adapter")
    else:
        warns.append("khong tim thay file .log de kiem env")

    # 5) ket luan
    print()
    if problems:
        log("KET LUAN: CO VAN (fix truoc khi ket luan 'model yeu'):")
        for p in problems:
            log("   - %s" % p)
    else:
        log("KET LUAN: env OK + ket qua du dung de doc")
    if warns:
        log("CANH BAO:")
        for w in warns:
            log("   - %s" % w)
    return 3 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
