import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V26 = ROOT / "phase13-gui" / "kernel_v26" / "gui_sft_v23.py"


def _load_v26():
    spec = importlib.util.spec_from_file_location("ornith_v26_recipe", V26)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_v26_train_target_has_clean_think_action_format():
    v = _load_v26()
    assert v._train_target("CLICK 12 34") == (
        "THINK: I will click the target element.\nACTION: CLICK 12 34")
    assert v._train_target("SCROLL 5").endswith("\nACTION: SCROLL 5")
    assert v._train_target("DRAG 1 2 3 4").endswith("\nACTION: DRAG 1 2 3 4")


def test_v26_parse_action_prefers_action_line():
    v = _load_v26()
    assert v.parse_action("THINK: scroll first\nACTION: SCROLL 5") == "SCROLL 5"
    assert v.parse_action("THINK: hover\nACTION: MOVE 10 20") == "MOVE 10 20"
    assert v.parse_action("THINK: drag\nACTION: DRAG 1 2 3 4") == "DRAG 1 2 3 4"


def test_v26_hard_pack_is_b15_b16_only():
    v = _load_v26()
    assert "T07_scroll" in v.V26_HARD_TASKS
    assert "T13_wizard" in v.V26_HARD_TASKS
    assert not any(t.startswith(("T30", "T31", "T32", "T34", "T36"))
                   for t in v.V26_HARD_TASKS)
    assert v.V26_HARD_MULT >= 2
