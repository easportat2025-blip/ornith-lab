"""test_reason_parse.py — unit tests parser reasoning (TASK-10 toi thieu).

Chay:  python phase13-gui/reasoning/test_reason_parse.py
Kiem tra:
  1) reason_parse.parse_output tren 22 case (MAIN_QUEST §2).
  2) CROSS-CHECK: ban copy trong kernel eval (`kernel_bench_v15`) phai cho
     cung (act_str, mode, prose_leak) tren cung bo case — chong troi thuat toan.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from reason_parse import parse_output  # noqa: E402

KERNEL = os.path.join(HERE, "..", "kernel_bench_v15", "bench_v15_kernel.py")

# (name, text, act_str, mode, prose_lines, fail_reason)
CASES = [
    ("basic", "THINK: The green button is on the left.\n"
              "ACTION: CLICK 100 200", "CLICK 100 200", "action", 0, None),
    ("last_action_wins", "THINK: x\nACTION: CLICK 1 2\nTHINK: fix\n"
                         "ACTION: CLICK 3 4", "CLICK 3 4", "action", 0, None),  # extra_actions=1
    ("legacy_bare", "I will click it now.\nCLICK 50 60",
     "CLICK 50 60", "legacy", 1, None),
    ("coords_in_think_ignored",
     "THINK: I need to click near (121, 668).\nACTION: CLICK 121 668",
     "CLICK 121 668", "action", 0, None),
    ("think_only_truncated",
     "THINK: Let me look at the screen and think about what to do next.",
     None, "none", 0, "no_action_truncated"),
    ("type_quoted", 'THINK: enter the email\n'
                    'ACTION: TYPE "user@example.com"',
     "TYPE user@example.com", "action", 0, None),
    ("prose_leak", "Thinking about the page...\n\nACTION: KEY ctrl+a",
     "KEY ctrl+a", "action", 1, None),
    ("done", "THINK: all done\nACTION: DONE", "DONE", "action", 0, None),
    ("click_bounds", "ACTION: CLICK 999 1000", "CLICK 999 1000",
     "action", 0, None),
    ("type_code", "THINK: read code\nACTION: TYPE ABC-123",
     "TYPE ABC-123", "action", 0, None),
    ("key_enter", "THINK: submit\nACTION: KEY enter", "KEY enter",
     "action", 0, None),
    ("prose_sandwich", "blah\nTHINK: hm\nmore prose\nACTION: CLICK 10 20",
     "CLICK 10 20", "action", 2, None),
    ("invalid_click", "ACTION: CLICK abc def", None, "none", 0,
     "invalid_action"),  # extra_actions=1 (dong ACTION khong dung duoc)
    ("action_first_line", "CLICK 123 456\nTHINK: after", "CLICK 123 456",
     "legacy", 0, None),
    ("login_pil_real",
     'Clicking the "Sign in" button should complete the login process. \n'
     '\u200b\nCLICK 500 672', "CLICK 500 672", "legacy", 2, None),
    ("multi_think_no_prose", "THINK: a\n\nTHINK: b\n\nACTION: KEY ctrl+c",
     "KEY ctrl+c", "action", 0, None),
    ("type_legacy", "THINK: ...\nTYPE hello", "TYPE hello", "legacy", 0, None),
    ("trailing_after_action", "ACTION: DONE\nsome trailing text",
     "DONE", "action", 0, None),
    ("think_no_colon_is_prose", "THINK x\nACTION: click 5 6",
     "CLICK 5 6", "action", 1, None),
    ("empty", "", None, "none", 0, "empty"),
    ("click_paren", "ACTION: CLICK (300, 400)", "CLICK 300 400",
     "action", 0, None),
    ("key_combo", "ACTION: KEY ctrl+shift+t", "KEY ctrl+shift+t",
     "action", 0, None),
]

# so dong ACTION: khong duoc dung lam action cuoi (thong tin, khong phai leak)
EXTRA_ACTIONS = {"last_action_wins": 1, "invalid_click": 1}


def load_kernel_parser():
    if not os.path.exists(KERNEL):
        return None
    spec = importlib.util.spec_from_file_location("bench_v15_kernel_t",
                                                  KERNEL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "parse_output", None)


def main():
    npass = 0
    nfail = 0
    for name, text, act_str, mode, prose, fail_reason in CASES:
        po = parse_output(text)
        problems = []
        if po["act_str"] != act_str:
            problems.append(f"act_str={po['act_str']!r} != {act_str!r}")
        if po["mode"] != mode:
            problems.append(f"mode={po['mode']} != {mode}")
        if po["prose_lines"] != prose:
            problems.append(f"prose={po['prose_lines']} != {prose}")
        if po["fail_reason"] != fail_reason:
            problems.append(f"fail={po['fail_reason']} != {fail_reason}")
        if po["extra_actions"] != EXTRA_ACTIONS.get(name, 0):
            problems.append(f"extra_actions={po['extra_actions']} != "
                            f"{EXTRA_ACTIONS.get(name, 0)}")
        if problems:
            nfail += 1
            print(f"FAIL {name}: {'; '.join(problems)}")
        else:
            npass += 1
            print(f"ok   {name}")

    kp = load_kernel_parser()
    if kp is None:
        print("WARN khong thay kernel parser -> bo qua cross-check")
    else:
        mism = 0
        for name, text, act_str, mode, prose, _fr in CASES:
            k = kp(text)
            if (k["act_str"], k["mode"], k["prose_lines"],
                    k["extra_actions"]) != (act_str, mode, prose,
                                            EXTRA_ACTIONS.get(name, 0)):
                mism += 1
                print(f"MISMATCH kernel {name}: "
                      f"{(k['act_str'], k['mode'], k['prose_lines'], k['extra_actions'])} != "
                      f"{(act_str, mode, prose, EXTRA_ACTIONS.get(name, 0))}")
        if mism == 0:
            print(f"ok   cross-check kernel ({len(CASES)} case dong nhat)")
        else:
            nfail += mism

    print(f"\n{'-' * 50}\nPASS {npass}/{npass + nfail}"
          + (" — TAT CA OK" if nfail == 0 else f" — {nfail} FAIL"))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
