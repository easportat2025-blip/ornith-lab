# -*- coding: utf-8 -*-
"""
test_grpo_reward.py - test LOCAL (0 GPU) cho ham reward cua kernel GRPO.
Kiem tra: parse action dung format SFT, reward phan biet duoc dung/sai.
ASCII-only source.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.join(HERE, "..", "phase13-gui", "kernel_grpo_v1", "grpo_v1.py")


def load():
    spec = importlib.util.spec_from_file_location("grpo_v1", KP)
    m = importlib.util.module_from_spec(spec)
    sys.modules["grpo_v1"] = m
    spec.loader.exec_module(m)
    return m


def main():
    m = load()
    P = m.parse_action_v2
    N = m.norm_gt
    R = m.action_reward
    ok = True

    cases = [
        # (raw, expected_verb, expected_arg)
        ("THINK: I see a button\nACTION: CLICK 300 450", "click", (300, 450)),
        ("ACTION: TYPE hello world", "type", "hello world"),
        ("ACTION: KEY ctrl+a", "key", "CTRL+A"),
        ("ACTION: KEY Enter", "key", "ENTER"),
        ("ACTION: DONE", "done", None),
        # dong cuoi co ACTION (nhieu dong tho)
        ("I will click it.\nACTION: CLICK 12 34", "click", (12, 34)),
        # viet sai format: "CLICK x y" khong co ACTION:
        ("THINK: hmm\nCLICK 5 6", "click", (5, 6)),
        # prose thuot -> None
        ("The task is complete. No action needed.", None, None),
    ]
    print("== parse_action_v2 ==")
    for raw, ev, ea in cases:
        got = P(raw)
        good = (got is None and ev is None) or (
            got is not None and got[0] == ev and
            (ev != "click" or got[1] == ea))
        ok = ok and good
        print("  %-5s %-46r -> %s" % ("PASS" if good else "FAIL", raw[:44], got))

    print("== norm_gt ==")
    for g, ev in [("CLICK 300 450", ("click", (300, 450))),
                  ("TYPE abc", ("type", "abc")),
                  ("KEY ctrl+a", ("key", "CTRL+A")),
                  ("DONE", ("done", None))]:
        got = N(g)
        good = got == ev
        ok = ok and good
        print("  %-5s %-14r -> %s" % ("PASS" if good else "FAIL", g, got))

    print("== action_reward ==")
    gts = ["CLICK 300 450", "CLICK 300 450", "CLICK 300 450", "CLICK 300 450"]
    comps = ["ACTION: CLICK 300 450",     # exact -> 1.0
             "ACTION: CLICK 305 455",     # gan -> 1.0 (<=20)
             "ACTION: CLICK 500 500",     # xa -> 0.0
             "ACTION: DONE"]              # sai verb -> 0.0
    rs = R(["p"] * 4, comps, gt=gts)
    exp = [1.0, 1.0, 0.0, 0.0]
    for i, (r, e) in enumerate(zip(rs, exp)):
        good = abs(r - e) < 1e-6
        ok = ok and good
        print("  %-5s comp=%-26r r=%.2f (mong doi %.2f)"
              % ("PASS" if good else "FAIL", comps[i][:24], r, e))

    # khong parse -> -0.1
    rs2 = R(["p"], ["I am not sure what to do"], gt=["CLICK 1 1"])
    good = abs(rs2[0] - (-0.1)) < 1e-6
    ok = ok and good
    print("  %-5s prose -> r=%.2f (mong doi -0.10)"
          % ("PASS" if good else "FAIL", rs2[0]))

    # chat-format completion (list of content blocks)
    rs3 = R(["p"], [[{"type": "text", "text": "ACTION: CLICK 300 450"}]],
            gt=["CLICK 300 450"])
    good = abs(rs3[0] - 1.0) < 1e-6
    ok = ok and good
    print("  %-5s completion dang list -> r=%.2f (mong doi 1.00)"
          % ("PASS" if good else "FAIL", rs3[0]))

    print("\n=> %s" % ("ALL PASS" if ok else "CO LOI - KHONG PUSH"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
