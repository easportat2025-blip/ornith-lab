# -*- coding: utf-8 -*-
"""Print a compact, secret-free ops snapshot for agents and humans."""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "configs", "kaggle_queue.json")
OPS_CONFIG = os.path.join(ROOT, "configs", "ops.json")
STATE = os.path.join(ROOT, "state", "current.json")
LOOP_HEALTH = os.path.join(ROOT, "state", "loop_health.json")
SECRETS = [
    "KAGGLE_USERNAME", "KAGGLE_KEY", "HF_TOKEN", "GH_TOKEN",
    "GEMINI_API_KEY", "MISTRAL_API_KEY", "DEEPSEEK_API_KEY",
    "GROQ_API_KEY", "OPENCODE_API_KEY",
]


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def git(*args):
    try:
        p = subprocess.run(["git"] + list(args), cwd=ROOT,
                           capture_output=True, text=True, timeout=15)
        return p.stdout.strip() if p.returncode == 0 else ""
    except Exception:
        return ""


def user_env(name):
    if os.name != "nt":
        return ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            value, _ = winreg.QueryValueEx(k, name)
            return str(value)
    except Exception:
        return ""


def has_secret(name):
    return bool(os.environ.get(name) or user_env(name))


def build_snapshot():
    queue = load_json(QUEUE, {"targets": []})
    state = load_json(STATE, None)
    ops_cfg = load_json(OPS_CONFIG, {})
    loop_health = load_json(LOOP_HEALTH, None)
    targets = []
    for t in queue.get("targets", []):
        targets.append({
            "ref": t.get("ref", ""),
            "kind": t.get("kind", ""),
            "state": t.get("state", ""),
            "path": t.get("path", ""),
            "note": t.get("note", ""),
        })
    snap = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repo": "easportat2025-blip/ornith-lab",
        "git": {
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "commit": git("rev-parse", "--short", "HEAD"),
            "dirty": bool(git("status", "--porcelain")),
        },
        "queue": {
            "account": queue.get("account", ""),
            "targets": targets,
        },
        "state": None,
        "ops": {
            "loop_enabled": bool((ops_cfg.get("loop") or {}).get("enabled", True)),
            "delay_seconds": (ops_cfg.get("loop") or {}).get("delay_seconds", 600),
            "upgrade_mode": bool((ops_cfg.get("upgrade") or {}).get("mode", False)),
            "features": ops_cfg.get("features") or {},
        },
        "loop_health": loop_health,
        "secrets": {name: has_secret(name) for name in SECRETS},
    }
    if isinstance(state, dict):
        snap["state"] = {
            "iso": state.get("iso", ""),
            "active": state.get("active", []),
            "results": state.get("results", []),
            "pushed": state.get("pushed"),
        }
    return snap


def render(snap):
    lines = []
    lines.append("Ornith Lab ops status")
    lines.append("UTC:    %s" % snap["utc"])
    lines.append("Git:    %s %s%s" % (
        snap["git"]["branch"], snap["git"]["commit"],
        " (dirty)" if snap["git"]["dirty"] else ""))
    lines.append("Queue:  %s" % (snap["queue"]["account"] or "n/a"))
    for t in snap["queue"]["targets"]:
        lines.append("  %-44s %-8s %-8s %s" % (
            t["ref"], t["kind"], t["state"], t["path"]))
    ops = snap.get("ops") or {}
    lines.append("Ops:    loop=%s delay=%ss upgrade=%s" % (
        "enabled" if ops.get("loop_enabled", True) else "disabled",
        ops.get("delay_seconds", 600), ops.get("upgrade_mode", False)))
    if snap["state"]:
        st = snap["state"]
        lines.append("State:  %s active=%s" % (
            st.get("iso") or "n/a",
            ",".join(st.get("active") or []) or "none"))
        for r in st.get("results", []):
            outs = len(r.get("outputs") or [])
            lines.append("  %-44s %-10s %-8s outputs=%d" % (
                r.get("ref", ""), r.get("status", ""),
                r.get("state", ""), outs))
        if st.get("pushed"):
            lines.append("Pushed: %s" % st["pushed"].get("ref", ""))
    else:
        lines.append("State:  state/current.json missing "
                     "(normal on main; see ops-state)")
    health = snap.get("loop_health")
    if health:
        lines.append("Health: %s enabled=%s actions=%d" % (
            health.get("ts", "n/a"), health.get("enabled"),
            len(health.get("actions") or [])))
    else:
        lines.append("Health: state/loop_health.json missing (normal on main)")
    missing = [k for k, v in snap["secrets"].items() if not v]
    lines.append("Secrets: %d/%d set; missing=%s" % (
        len(snap["secrets"]) - len(missing), len(snap["secrets"]),
        ",".join(missing) or "none"))
    lines.append("Issues: https://github.com/easportat2025-blip/ornith-lab/issues")
    lines.append("HF chat: https://huggingface.co/datasets/kkouadn/ornith-chat")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    snap = build_snapshot()
    if a.json:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
    else:
        print(render(snap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
