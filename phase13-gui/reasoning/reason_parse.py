"""reason_parse.py — parser CHUAN cho reasoning protocol (MAIN_QUEST §2).

Ban canonical cua DeepSeek (19/10) — GLM/MiMo co the nang cap; MOI thay doi
phai giu tuong thich: 2 kernel (gui_sft_v20, bench_v15_kernel) nhung ban copy
cua cung thuat toan, va test_reason_parse.py cross-check ban kernel voi ban nay.

Hop dong (MAIN_QUEST §2.1-2.3):
  - Output model: `THINK: <ly do>` (0-n dong) roi dong CUOI `ACTION: <lenh>`.
  - Parser lay dong ACTION CUOI cung; neu khong co -> fallback bare legacy
    (dong bat dau bang CLICK/TYPE/KEY/DONE — so sanh voi v18).
  - KHONG duoc lay toa do trong THINK lam action.
  - prose_leak: dong khong bat dau bang `THINK:` nam TRUOC action.
  - fail_reason: "no_action_truncated" (chi THINK/prose ma het token —
    MAIN_QUEST §2.3) | "invalid_action" (co verb nhung thieu/no arg) | None.

parse_output(text) -> dict:
  action      : ("CLICK", [x,y]) | ("TYPE", str) | ("KEY", str) | ("DONE", None) | None
  mode        : "action" | "legacy" | "none"
  act_str     : "CLICK x y" | "TYPE ..." | "KEY ..." | "DONE" | None
  think_text  : cac dong THINK (giu nguyen, join \n)
  think_lines : so dong THINK
  prose_lines : so dong prose khong nam trong THINK truoc action
  leak        : prose_lines > 0
  valid       : action is not None (da qua arity check)
  fail_reason : None | "no_action_truncated" | "invalid_action" | "empty"
"""
import re

THINK_RX = re.compile(r"^\s*THINK\s*:", re.I)
ACTION_LINE_RX = re.compile(r"^\s*ACTION\s*:\s*(.*)$", re.I)
VERB_RX = re.compile(r"^\s*(?:ACTION\s*:\s*)?(CLICK|TYPE|KEY|DONE)\b", re.I)


def split_verb(s):
    parts = (s or "").strip().split(None, 1)
    if not parts:
        return None, ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def norm_action(verb, rest):
    verb = (verb or "").upper()
    rest = (rest or "").strip()
    if verb == "CLICK":
        m = re.search(r"(\d{1,4})\s*[,;\s]\s*(\d{1,4})", rest)
        if not m:
            return None, None
        return "CLICK", [int(m.group(1)), int(m.group(2))]
    if verb == "TYPE":
        t = rest.strip().strip('"').split("\n")[0].strip()
        return ("TYPE", t) if t else (None, None)
    if verb == "KEY":
        m = re.search(r"[A-Za-z0-9_\-+]+", rest)
        return ("KEY", m.group(0).lower()) if m else (None, None)
    if verb == "DONE":
        return "DONE", None
    return None, None


def act_to_str(act):
    if not act:
        return None
    v, a = act
    if v == "CLICK":
        return f"CLICK {a[0]} {a[1]}"
    if v == "TYPE":
        return f"TYPE {a}"
    if v == "KEY":
        return f"KEY {a}"
    return "DONE"


def parse_output(text):
    lines = [l.rstrip() for l in (text or "").splitlines() if l.strip()]
    act = None
    mode = "none"
    act_i = None
    invalid_seen = False
    for i, l in enumerate(lines):
        m = ACTION_LINE_RX.match(l)
        if m:
            v, a = norm_action(*split_verb(m.group(1)))
            if v:
                act, mode, act_i = (v, a), "action", i
            elif VERB_RX.match(l):
                invalid_seen = True
    if act is None:
        for i, l in enumerate(lines):
            m = VERB_RX.match(l)
            if m and not ACTION_LINE_RX.match(l):
                verb, rest = split_verb(l.strip())
                v, a = norm_action(verb, rest)
                if v:
                    act, mode, act_i = (v, a), "legacy", i
                    break
                invalid_seen = True
    limit = act_i if act_i is not None else len(lines)
    extra_actions = sum(1 for l in lines[:limit] if ACTION_LINE_RX.match(l))
    prose = [l for l in lines[:limit]
             if not THINK_RX.match(l) and not ACTION_LINE_RX.match(l)]
    think = [l for l in lines[:limit] if THINK_RX.match(l)]
    fail_reason = None
    if act is None:
        if invalid_seen:
            fail_reason = "invalid_action"
        elif lines:
            fail_reason = "no_action_truncated"
        else:
            fail_reason = "empty"
    return {"action": act, "mode": mode, "act_str": act_to_str(act),
            "think_text": "\n".join(think), "think_lines": len(think),
            "extra_actions": extra_actions,
            "prose_lines": len(prose), "leak": len(prose) > 0,
            "valid": act is not None, "fail_reason": fail_reason}


def metrics(outs):
    """Aggregate n outputs -> dict (dung cho gate §3)."""
    n = max(len(outs), 1)
    parsed = sum(1 for o in outs if o["valid"])
    leak = sum(1 for o in outs if o["leak"])
    trunc = sum(1 for o in outs if o["fail_reason"] == "no_action_truncated")
    return {"n": len(outs), "parse_rate": parsed / n, "leak_rate": leak / n,
            "trunc_rate": trunc / n,
            "modes": {m: sum(1 for o in outs if o["mode"] == m)
                      for m in ("action", "legacy", "none")}}
