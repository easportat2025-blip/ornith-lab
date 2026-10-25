"""test_action_fallback.py - kiem tra fallback khi model quen dong 'ACTION:'
(GLM, 22/10, theo yeu cau cua @DeepSeek).

Harness moi (do @DeepSeek sua):
  * REASON_MAX 256 -> 512 (ENV_REASON_MAX)
  * fallback (a): quet TOAN BO text lay action bare (_scan_bare_action)
  * fallback (b): sinh LAI 1 lan voi prompt nang + do_sample + temperature 0.7
  * VLLMPolicy: dung VLLM server (ENV_VLLM_URL) thay vi load model local

Test nay DUNG 0 GPU: model + processor deu la MOCK, chi kiem logic fallback.

Dung: python phase14-desktop/test_action_fallback.py
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILS = []


def ok(cond, msg):
    print("  %s %s" % ("ok  " if cond else "FAIL", msg))
    if not cond:
        FAILS.append(msg)


# ---------------------------------------------------------------- mock model
class FakeTensor:
    def __init__(self, n=10):
        self._n = n

    @property
    def shape(self):
        return (1, self._n)

    def __getitem__(self, k):
        return FakeTensor(self._n)

    def to(self, dev):
        return self


class FakeInputs(dict):
    def to(self, dev):
        return self


class FakeProcessor:
    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def apply_chat_template(self, msgs, **kw):
        txt = str(msgs)
        self.prompts.append(txt)
        return "PROMPT:%d" % len(self.prompts)

    def __call__(self, text=None, images=None, return_tensors=None):
        return FakeInputs(input_ids=FakeTensor(10))

    def batch_decode(self, ids, skip_special_tokens=True):
        return [self.answers.pop(0) if self.answers else ""]


class FakeModel:
    def __init__(self, processor):
        self.processor = processor
        self.device = "cpu"
        self.calls = []

    def generate(self, **kw):
        self.calls.append(kw)
        return FakeTensor(12)


def make_policy(answers):
    proc = FakeProcessor(answers)
    model = FakeModel(proc)
    pol = harness.PolicyV2(model, proc)
    return pol, proc, model


def _png(path):
    """Tao 1 PNG nho (PIL can file that de PolicyV2.act mo) - 0 GPU."""
    from PIL import Image
    Image.new("RGB", (64, 48), (30, 34, 44)).save(path)
    return path


import tempfile
SHOT = _png(os.path.join(tempfile.gettempdir(), "glm_fb.png"))
os.environ["ENV_REASON_MAX"] = "512"
import harness  # noqa: E402

print("== 1) REASON_MAX = 512 (ENV_REASON_MAX) ==")
ok(harness.REASON_MAX == 512, "REASON_MAX=%s (mong doi 512)" % harness.REASON_MAX)

print("== 2) parse_action_v2 (duong binh thuong) ==")
ok(harness.parse_action_v2("blah\nACTION: CLICK 123 456") == ("click", [123, 456]),
   "parse 'ACTION: CLICK 123 456'")
ok(harness.parse_action_v2("ACTION: DONE") == ("done", None) or
   harness.parse_action_v2("ACTION: DONE") is not None, "parse 'ACTION: DONE'")

print("== 3) _scan_bare_action (fallback a) ==")
ok(harness._scan_bare_action("I will click the login button.\nCLICK 300 450") ==
   ("click", [300, 450]), "bare CLICK 300 450")
ok(harness._scan_bare_action("now type the password\nTYPE hunter2") ==
   ("type", "hunter2"), "bare TYPE hunter2")
ok(harness._scan_bare_action("press ctrl+a\nKEY Control+a") is not None,
   "bare KEY Control+a")
ok(harness._scan_bare_action("I am thinking about what to do") is None,
   "prose khong co action -> None (khong bat action sai)")
ok(harness._scan_bare_action("") is None, "chuoi rong -> None")

print("== 4) model quen dong 'ACTION:' nhung co bare action -> parse_action_v2 xu ly ==")
pol, proc, model = make_policy([
    "The email field is empty, I should click it first.\nCLICK 400 250"])
raw, act = pol.act(SHOT, "Fill the form")
ok(act == ("click", [400, 250]), "action lay duoc: %s" % (act,))
ok(pol.last.get("fallback") is None,
   "last.fallback=%r (parse_action_v2 da quet bare -> khong can fallback)"
   % pol.last.get("fallback"))
ok(len(model.calls) == 1, "KHONG goi lai model (%d call)" % len(model.calls))

print("== 4b) NEU parse_action_v2 VA _scan_bare_action deu that -> fallback (b) ==")
pol, proc, model = make_policy([
    "I am not sure what to do here, let me think about it for a while...",
    "ACTION: CLICK 12 34"])
raw, act = pol.act(SHOT, "Fill the form")
ok(act == ("click", [12, 34]), "fallback (b) lay action: %s" % (act,))
ok(pol.last.get("fallback") == "regen",
   "last.fallback=%r (mong doi 'regen')" % pol.last.get("fallback"))
ok(len(model.calls) == 2, "model goi 2 lan (%d)" % len(model.calls))

print("== 5) fallback (b): khong co action nao -> sinh LAI voi prompt nang ==")
pol, proc, model = make_policy([
    "I am not sure what to do here, let me think about it for a while...",
    "ACTION: CLICK 12 34"])
raw, act = pol.act(SHOT, "Fill the form")
ok(act == ("click", [12, 34]), "fallback (b) lay action: %s" % (act,))
ok(pol.last.get("fallback") == "regen",
   "last.fallback=%r (mong doi 'regen')" % pol.last.get("fallback"))
ok(len(model.calls) == 2, "model goi 2 lan (%d)" % len(model.calls))
kw = model.calls[1]
ok(kw.get("do_sample") is True, "lan 2 do_sample=True")
ok(abs(float(kw.get("temperature", 0)) - 0.7) < 1e-6,
   "lan 2 temperature=%s (mong doi 0.7)" % kw.get("temperature"))
ok(kw.get("max_new_tokens") == 512,
   "lan 2 max_new_tokens=%s (mong doi 512)" % kw.get("max_new_tokens"))
ok(len(proc.prompts) == 2 and "ACTION" in proc.prompts[1],
   "prompt lan 2 co nho 'ACTION:' (prompt nang)")

print("== 6) khong co fallback khi model tra ACTION dung ==")
pol, proc, model = make_policy(["ACTION: CLICK 7 8"])
raw, act = pol.act(SHOT, "t")
ok(act == ("click", [7, 8]), "action binh thuong")
ok(pol.last.get("fallback") is None,
   "last.fallback=%r (mong doi None)" % pol.last.get("fallback"))
ok(len(model.calls) == 1, "chi goi model 1 lan (%d)" % len(model.calls))

print("== 7) KEYMAP X11 -> Playwright (phim 'down' se loi Unknown key) ==")
for src, want in [("down", "ArrowDown"), ("up", "ArrowUp"),
                  ("left", "ArrowLeft"), ("right", "ArrowRight"),
                  ("pagedown", "PageDown"), ("page_down", "PageDown"),
                  ("end", "End"), ("escape", "Escape"),
                  ("enter", "Enter"), ("tab", "Tab"),
                  ("control+a", "Control+a"), ("control+c", "Control+c")]:
    got = harness.PLAYWRIGHT_KEYS.get(src.lower(), src)
    if "+" in src:
        mods, base = src.split("+", 1)
        got = "%s+%s" % (harness.MOD_KEYS.get(mods.lower(), mods),
                         harness.PLAYWRIGHT_KEYS.get(base.lower(), base))
    ok(got == want, "KEY %-12s -> %-14s (mong doi %s)" % (src, got, want))

print("== 8) VLLMPolicy: thieu ENV_VLLM_URL -> SystemExit ro rang ==")
os.environ.pop("ENV_VLLM_URL", None)
try:
    harness.VLLMPolicy()
    ok(False, "VLLMPolicy khong raise khi thieu ENV_VLLM_URL")
except SystemExit as e:
    ok("ENV_VLLM_URL" in str(e), "SystemExit noi ro: %s" % str(e)[:60])

print()
if FAILS:
    print("FAILED: %d -> %s" % (len(FAILS), FAILS))
    sys.exit(1)
print("ALL ACTION-FALLBACK TESTS PASSED")
