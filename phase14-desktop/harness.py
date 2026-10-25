"""harness.py - DESKTOP-ENV harness (TASK-27, GLM).

Loop:  obs (screenshot of the real X11 screen)
     -> model (PolicyV2, copied from phase13-gui/kernel_bench_v15/bench_v15_kernel.py)
     -> action (real mouse/keyboard via xdotool, env.do_action)
     -> env (app state) -> reward (checker reads app state over CDP)

Artifacts (per run):
  obs/<task>_<ep>_<step>.png   screenshots (what the model sees)
  actions.jsonl                one row per step: action, desc, reward, raw model text
  reward.json                  per task: best reward, success, steps
  summary.json                 all tasks

Policy interface is EXACTLY the B15 one, so the current model + code run unchanged:
  "CLICK 322 440" (x,y normalized 0..1000) | "TYPE text" | "KEY up" | "KEY ctrl+a"
  plus desktop extras: "MOVE x y" | "DRAG x1 y1 x2 y2" | "SCROLL 3"

No GPU / no key needed: a scripted dummy policy proves the loop end-to-end.
ASCII-only source on purpose (Windows cp1252 lesson).

Usage:
  python harness.py --selftest                      # probe env only
  python harness.py --policy dummy --tasks T20_2048  # scripted policy
  python harness.py --policy model --adapter <lora>  # real model (needs torch+unsloth)
  python harness.py --novnc                          # best-effort noVNC for Space
"""
import argparse
import base64
import json
import os
import re
import shutil
import socket
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# env.py reads ENV_WORK at import time -> set it BEFORE import (Space has no /kaggle)
if not os.environ.get("ENV_WORK"):
    if os.path.isdir("/kaggle"):
        os.environ["ENV_WORK"] = "/kaggle/working/desktop"
    else:
        os.environ["ENV_WORK"] = os.path.join(HERE, "desktop_run")

import env  # noqa: E402  (local, same dir)

# ----------------------------------------------------------------- constants
CDP_PORT = int(os.environ.get("ENV_CDP_PORT", "9222"))
W, H = env.W, env.H
# HEADLESS: khong can X11/xdotool - dung cho test local + pipeline smoke.
# Action + anh chup chay qua Playwright/CDP (xem cdp_action/cdp_screenshot).
HEADLESS = os.environ.get("DB_HEADLESS", "0") == "1"

# FIX 22/10 (MiMo): loi HA TANG phai tach khoi loi model.
# App file bi thieu (hoac browser khong mo duoc) => KHONG co cua so nao tren
# X11 => anh chup ra MANH HINH DEN => model thay "black screen" => DONE
# reward=-1 => 20 ep/20 ep bi tinh nham la "model that" (o run B2:
# T21_form_desktop + T23_table_sort = 40/120 ep). => gio:
#   - BO QUA episode (khong goi model, khong ton GPU)
#   - ghi vao INFRA_ERRORS + file infra_errors.json
#   - bench result gan nhan "valid=False" cho task bi lo (khong tinh vao
#     diem) => so lieu khong bi nhieu.
INFRA_ERRORS = []

SYS = ("You are a GUI agent. Look at the screenshot and the task, then "
       "decide the next action.\n"
       "You MAY reason briefly first. Reply format:\n"
       "THINK: <one or two short sentences about what you see and what "
       "to do>\n"
       "ACTION: <CLICK x y | TYPE text | KEY name | SCROLL n | MOVE x y | "
       "DRAG x1 y1 x2 y2 | DONE>\n"
       "Rules: the LAST line MUST start with 'ACTION:'; x,y are integers "
       "0..1000 normalized to image width/height; never write anything "
       "after the ACTION line; if the task is already complete, "
       "output ACTION: DONE.\n"
       "SCROLL n scrolls the page or the focused panel down by n steps "
       "(use it when the content you need is below the visible area); "
       "DRAG x1 y1 x2 y2 drags from one point to another; MOVE x y moves the "
       "pointer without clicking.")

REASON_MAX = int(__import__('os').environ.get('ENV_REASON_MAX', '512'))
ENABLE_THINKING = os.environ.get("ORNI_THINK", "1") != "0"

# Builtin task table. TASK-26 apps can be added here, or via --tasks-json
# (JSON file with the same schema) so nobody has to edit this file.
BUILTIN_TASKS = {
    "T20_2048": {
        "app": "game_2048.html",
        "instruction": ("You are playing 2048 on the desktop. Use the arrow keys "
                        "to move the tiles and try to reach a score of 40. "
                        "Stop when the score is high enough."),
        "reward_js": "(window.__score || 0)",
        "threshold": 40,
        "max_steps": 60,
        "dummy": "2048",
    },
}


def log(m):
    print("[harness] %s" % m, flush=True)


# ------------------------------------------------------------- model policy
# PolicyV2 + parse_action_v2 + SYS: COPIED from
# phase13-gui/kernel_bench_v15/bench_v15_kernel.py (file cu KHONG bi sua).
def _bare_from(verb, arg):
    """(verb, arg) -> action hop le hoac None."""
    verb = (verb or "").upper()
    arg = (arg or "").strip()
    if verb in ("CLICK", "MOVE"):
        p = arg.split()
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            return ("click" if verb == "CLICK" else "move",
                    [int(p[0]), int(p[1])])
        return None
    if verb == "TYPE":
        return ("type", arg) if arg else None
    if verb == "KEY":
        return ("key", arg.lower()) if arg else None
    return None


def _scan_bare_action(text):
    """Fallback: quet text tim action bare (CLICK x y / TYPE .. / KEY ..) - dung
    khi model viet pro se nhung quen dong 'ACTION:'.

    FIX 22/10 (GLM): ban dau regex khop TU DUNG 'click' trong PROSE
    ("I will click the login button") => tra None du model da viet
    'CLICK 300 450' o dong sau => fallback that bai. Nay quet theo THU TU:
    (1) dong bat dau bang verb (format legacy) - lay dong dau tien HOP LE
    (2) neu chua co: verb kem args cu (keo trong prose) - chi lay khi args
        hop le (CLICK/MOVE co 2 so, TYPE/KEY co 1 chuoi).
    """
    if not text:
        return None
    t = text.strip()
    # (1) verb dau dong
    for m in re.finditer(r"(?:^|\n)\s*(CLICK|TYPE|KEY|MOVE|DRAG|SCROLL)\b([^\n]{0,60})",
                        t, re.I):
        act = _bare_from(m.group(1), m.group(2))
        if act:
            return act
    # (2) verb + args hop le, nam trong prose
    m = re.search(r"\b(CLICK|MOVE)\s+(\d+)\s+(\d+)", t, re.I)
    if m:
        return ("click" if m.group(1).upper() == "CLICK" else "move",
                [int(m.group(2)), int(m.group(3))])
    m = re.search(r"\bTYPE\s+(\S[^\n]{0,40})", t, re.I)
    if m:
        return ("type", m.group(1).strip())
    m = re.search(r"\bKEY\s+([A-Za-z+][^\n]{0,30})", t, re.I)
    if m:
        return ("key", m.group(1).strip().lower())
    return None

class VLLMPolicy:
    """Dung vLLM server (OpenAI-compatible) thay vi load model local.

    - ENV_VLLM_URL  : vd http://127.0.0.1:8000/v1
    - ENV_VLLM_MODEL: ten model (default 'ornith')
    - ENV_VLLM_KEY  : api key (default 'EMPTY')
    Uu diem: RTX 96GB - model fit, vLLM sinh nhanh ~10-30x so voi HF generate.
    """

    def __init__(self, url=None, model=None, key=None):
        import urllib.request
        self.url = (url or os.environ.get("ENV_VLLM_URL", "")).rstrip("/")
        self.model = model or os.environ.get("ENV_VLLM_MODEL", "ornith")
        self.key = key or os.environ.get("ENV_VLLM_KEY", "EMPTY")
        self.last = {}
        if not self.url:
            raise SystemExit("VLLMPolicy: thieu ENV_VLLM_URL")
        import json as _json
        import base64 as _b64
        self._json = _json
        self._b64 = _b64
        import urllib.request as _u
        self._u = _u

    def act(self, shot, task, t=0):
        from PIL import Image
        import base64
        import io as _io
        import json
        import urllib.request
        buf = _io.BytesIO()
        Image.open(shot).convert("RGB").save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        content = [
            {"type": "text", "text": f"Task: {task}\n"
                    f"(You MUST end your reply with a line 'ACTION: <verb> <args>')"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]
        body = {"model": self.model, "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": content}],
            "max_tokens": REASON_MAX, "temperature": 0.0}
        req = urllib.request.Request(
            self.url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.key})
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ans = (d.get("choices") or [{}])[0].get("message", {}).get("content", "")
        act = parse_action_v2(ans) or _scan_bare_action(ans)
        self.last = {"n_new": None, "fallback": None, "vllm": 1}
        return (ans or "").strip(), act

def parse_action_v2(text):
    """Parse a model answer -> (verb, arg) or None. Same rules as bench v15."""
    t = (text or "").strip()
    lines = [l.rstrip() for l in t.splitlines() if l.strip()]
    act = None
    for l in reversed(lines):
        m = re.match(r"^\s*ACTION\s*:\s*(.*)$", l, re.I)
        if m:
            rest = m.group(1).strip()
            mm = re.match(r"^(CLICK|TYPE|KEY|DONE|MOVE|DRAG|SCROLL)\b(.*)$",
                          rest, re.I)
            if mm:
                verb = mm.group(1).upper()
                arg = mm.group(2).strip()
                if verb == "CLICK":
                    p = arg.split()
                    if len(p) >= 2:
                        act = ("click", [int(p[0]), int(p[1])])
                elif verb == "TYPE":
                    act = ("type", arg)
                elif verb == "KEY":
                    act = ("key", arg.lower())
                elif verb == "DONE":
                    act = ("done", None)
                elif verb == "MOVE":
                    p = arg.split()
                    if len(p) >= 2:
                        act = ("move", [int(p[0]), int(p[1])])
                elif verb == "DRAG":
                    p = arg.split()
                    if len(p) >= 4:
                        act = ("drag", [int(p[0]), int(p[1]),
                                        int(p[2]), int(p[3])])
                elif verb == "SCROLL":
                    act = ("scroll", arg or "3")
            if act:
                break
    if act is None:
        m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                      t, re.I)
        if m:
            act = ("click", [int(m.group(1)), int(m.group(2))])
        else:
            m = re.search(r"TYPE\s+(.+)", t, re.I)
            if m:
                act = ("type", m.group(1).strip())
            else:
                m = re.search(r"\bKEY\s+([A-Za-z0-9+_-]+)", t, re.I)
                if m:
                    act = ("key", m.group(1).lower())
                elif re.search(r"\bDONE\b", t, re.I):
                    act = ("done", None)
    return act


KEY_ALIASES = {
    "pagedown": "Page_Down", "page_down": "Page_Down", "pgdn": "Page_Down",
    "pageup": "Page_Up", "page_up": "Page_Up", "end": "End", "home": "Home",
    "shift+tab": "shift+Tab", "esc": "Escape", "escape": "Escape",
    "del": "Delete", "page down": "Page_Down",
}

# Playwright yeu cau modifier dung case (Control/Shift/Alt/Meta) - dung
# 'control+c' se loi "Unknown key: control" => phim tat KHONG ban.
MOD_KEYS = {"control": "Control", "ctrl": "Control", "shift": "Shift",
            "alt": "Alt", "meta": "Meta", "cmd": "Meta",
            "command": "Meta", "super": "Meta"}

# Ten phim theo X11 (env.py / xdotool) -> ten phim Playwright.
# Sai ten se ra loi 'Unknown key: down' => phim khong duoc ban (2048 khong
# di chuyen duoc => task vo dung).
PLAYWRIGHT_KEYS = {
    "down": "ArrowDown", "up": "ArrowUp", "left": "ArrowLeft",
    "right": "ArrowRight", "pagedown": "PageDown", "pageup": "PageUp",
    "pgdn": "PageDown", "pgup": "PageUp", "end": "End", "home": "Home",
    "escape": "Escape", "esc": "Escape", "enter": "Enter",
    "return": "Enter", "tab": "Tab", "backspace": "Backspace",
    "delete": "Delete", "insert": "Insert", "space": "Space",
    "page_down": "PageDown", "page_up": "PageUp",
}


def act_to_str(act):
    """(verb, arg) -> action string in env.do_action format (or None)."""
    if not act:
        return None
    verb, arg = act
    if verb == "click":
        return "CLICK %d %d" % (arg[0], arg[1])
    if verb == "move":
        return "MOVE %d %d" % (arg[0], arg[1])
    if verb == "drag":
        return "DRAG %d %d %d %d" % (arg[0], arg[1], arg[2], arg[3])
    if verb == "scroll":
        return "SCROLL %s" % (arg if arg else "3")
    if verb == "type":
        return "TYPE %s" % arg
    if verb == "key":
        # env.py chi biet mot so ten phim -> dich ten lai (xdotool dung
        # ten keysym cua X, vi du Page_Down chu khong phai "pagedown")
        return "KEY %s" % KEY_ALIASES.get(str(arg).lower(), arg)
    if verb == "done":
        return "DONE"
    return None


class PolicyV2:
    """Copied from phase13-gui/kernel_bench_v15/bench_v15_kernel.py (lines ~776-804)."""

    def __init__(self, model, processor):
        self.model = model
        self.processor = processor
        self.last = {}

    def act(self, shot, task, t=0):
        import torch
        from PIL import Image
        img = Image.open(shot).convert("RGB")
        msgs = [{"role": "system", "content": [{"type": "text",
                                                "text": SYS}]},
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text", "text": f"Task: {task}"}]}]
        text = self.processor.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True,
            enable_thinking=ENABLE_THINKING)
        inputs = self.processor(text=[text], images=[img],
                                return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            gen = self.model.generate(**inputs, max_new_tokens=REASON_MAX,
                                      do_sample=False)
        n_new = int(gen.shape[1] - inputs["input_ids"].shape[1])
        ans = self.processor.batch_decode(
            gen[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True)[0]
        act = parse_action_v2(ans)
        fb = None
        if act is None:
            # (a) fallback 1: quet TOAN BO text lay action bare (legacy format)
            act = _scan_bare_action(ans)
            fb = "bare" if act is not None else None
            if act is None:
                # (b) fallback 2: sinh LAI voi prompt nang + sampling (pha vong lap
                # deterministic do model "ket thieu" o giua lời nghi)
                try:
                    msgs2 = [{"role": "system", "content": [{"type": "text",
                                                             "text": SYS}]},
                             {"role": "user", "content": [
                                 {"type": "image"},
                                 {"type": "text",
                                  "text": f"Task: {task}\n"
                                          f"(You MUST end your reply with a line "
                                          f"'ACTION: <verb> <args>')"}]}]
                    text2 = self.processor.apply_chat_template(
                        msgs2, tokenize=False, add_generation_prompt=True,
                        enable_thinking=ENABLE_THINKING)
                    inputs2 = self.processor(text=[text2], images=[img],
                                            return_tensors="pt").to(self.model.device)
                    with torch.no_grad():
                        gen2 = self.model.generate(
                            **inputs2, max_new_tokens=REASON_MAX,
                            do_sample=True, temperature=0.7, top_p=0.9)
                    ans2 = self.processor.batch_decode(
                        gen2[:, inputs2["input_ids"].shape[1]:],
                        skip_special_tokens=True)[0]
                    act = parse_action_v2(ans2) or _scan_bare_action(ans2)
                    fb = "regen" if act is not None else "none"
                    ans = ans + "\n[regen] " + ans2
                except Exception as e:
                    fb = "regen_loi:%s" % str(e)[:60]
        self.last = {"n_new": n_new, "fallback": fb}
        return ans.strip(), act


def load_policy_model(adapter=None, base_dir=None):
    """Load base + optional LoRA exactly like bench v15 (lazy: only for --policy model).

    Uu tien: neu ENV_VLLM_URL duoc set -> dung VLLM server (nhanh, phu hop RTX).
    """
    if os.environ.get("ENV_VLLM_URL"):
        log("dung VLLM server: %s" % os.environ["ENV_VLLM_URL"])
        return VLLMPolicy()

    """

    FIX (21/10): bo `FastVisionModel.for_inference(model)` — API cua ban unsloth
    trong wheels tra ve loi "I think you're passing a tokenizer, not the model".
    Dung cach load CUNG kieu voi kernel bench V21 (dang chay duoc):
    transformers cls.from_pretrained(dtype=bf16/fp16) + peft LoRA.
    """
    import torch
    import transformers
    from transformers import AutoProcessor
    from peft import PeftModel
    base = base_dir or os.environ.get("ENV_BASE", "/tmp/ornbase")
    log(f"loading model from {base} (adapter={adapter})")
    proc = None
    # 1) AutoProcessor TRUOC (giong kernel bench v15 dang chay duoc) - an toan
    #    khi ten class trong transformers tren Kaggle khac
    try:
        proc = AutoProcessor.from_pretrained(base)
        log("processor: AutoProcessor OK")
    except Exception as e:
        log(f"AutoProcessor loi: {type(e).__name__}: {str(e)[:120]}")
    # 2) fallback: thu tung class
    if proc is None:
        for cls_name in ("Qwen3VLProcessor", "Qwen3_5Processor"):
            cls = getattr(transformers, cls_name, None)
            if cls is None:
                continue
            try:
                proc = cls.from_pretrained(base)
                log(f"processor: {cls_name} OK")
                break
            except Exception as e:
                log(f"  {cls_name} loi: {type(e).__name__}: {str(e)[:120]}")
    if proc is None:
        raise SystemExit("khong load duoc processor - can AutoProcessor tu base")
    dt = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    cls = None
    for name in ("Qwen3_5ForConditionalGeneration",
                 "AutoModelForImageTextToText", "AutoModelForCausalLM"):
        cls = getattr(transformers, name, None)
        if cls is not None:
            log("model class: %s" % name)
            break
    assert cls, "khong tim thay model class qwen3_5"
    model = cls.from_pretrained(base, dtype=dt, device_map="auto")
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
        log(f"  adapter ON: {adapter}")
    model.eval()
    return PolicyV2(model, proc)


# ----------------------------------------------------------- dummy policies
class Dummy2048:
    """Scripted policy for T20_2048: read the grid over CDP, pick a good move.

    Proves the harness (obs -> action -> real keys -> reward) with NO model.
    """

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        grid = None
        try:
            grid = cdp_eval("JSON.stringify(window.__grid || null)")
        except Exception:
            grid = None
        best = None
        if grid:
            try:
                g = json.loads(grid)
                best = self._pick(g)
            except Exception:
                best = None
        if best is None:
            best = ["left", "down", "right", "up"][self.i % 4]
        self.i += 1
        key = {"left": "KEY left", "down": "KEY down",
               "right": "KEY right", "up": "KEY up"}[best]
        return "(scripted) 2048 move %s" % best, ("key", best)

    @staticmethod
    def _pick(g):
        """Greedy: prefer keeping the largest tile in a corner."""
        empty = sum(1 for row in g for v in row if not v)
        best_move, best_score = None, -1
        for m in ("left", "down", "right", "up"):
            ng = _slide(g, m)
            if ng is None:
                continue
            score = sum(v for row in ng for v in row)
            score += empty * 2
            corner = max(ng[0][0], ng[-1][-1], ng[0][-1], ng[-1][0])
            score += corner * 3
            if score > best_score:
                best_score, best_move = score, m
        return best_move


def _slide(g, m):
    """Simulate one 2048 move (left/down/right/up) -> new grid or None if no change."""
    n = len(g)

    def slide(row):
        a = [v for v in row if v]
        for i in range(len(a) - 1, 0, -1):
            if a[i] == a[i - 1]:
                a[i] *= 2
                a[i - 1] = 0
        while len(a) < n:
            a.append(0)
        return a

    ng = [row[:] for row in g]
    if m == "left":
        ng = [slide(r) for r in g]
    elif m == "right":
        ng = [slide(r[::-1])[::-1] for r in g]
    elif m == "up":
        for c in range(n):
            col = slide([g[r][c] for r in range(n)])
            for r in range(n):
                ng[r][c] = col[r]
    elif m == "down":
        for c in range(n):
            col = slide([g[r][c] for r in range(n)][::-1])[::-1]
            for r in range(n):
                ng[r][c] = col[r]
    if ng == g:
        return None
    return ng


# Demo policy cho cac app co BIEN NGAU NHIEN (TASK-28 v2): doc gia tri + toa do
# truc tiep tu trang (qua CDP) roi thao tac THAT -> sinh ra data co y nghia.
def _page_state(js):
    """Doc state app qua CDP -> dict (None neu khong doc duoc)."""
    txt = cdp_eval(js)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        return None


def _click_at(tg, key, fallback=(300, 500)):
    v = (tg or {}).get(key)
    if v and len(v) >= 2:
        return "CLICK %d %d" % (int(v[0]), int(v[1]))
    return "CLICK %d %d" % fallback


class DummyForm:
    """T21_form: doc user/email/password ngau nhien tu trang -> go vao 4 o -> Register."""

    def __init__(self):
        self.i = 0
        self.spec = None
        self.tg = None

    def _load(self):
        if self.spec is None:
            self.spec = _page_state("JSON.stringify(window.__spec||null)") or {}
            self.tg = _page_state("JSON.stringify(window.__targets||null)") or {}

    def act(self, shot, task, t=0):
        self._load()
        spec, tg = self.spec or {}, self.tg or {}
        u = spec.get("user", "")
        e = spec.get("email", "")
        p = spec.get("pass", "")
        seq = [_click_at(tg, "user"), "TYPE %s" % u,
               _click_at(tg, "email"), "TYPE %s" % e,
               _click_at(tg, "pass"), "TYPE %s" % p,
               _click_at(tg, "confirm"), "TYPE %s" % p,
               _click_at(tg, "register")]
        # bo "TYPE " rong (khi doc chua duoc spec tu trang)
        seq = [a for a in seq if a.strip() != "TYPE"]
        a = seq[min(self.i, len(seq) - 1)]
        self.i += 1
        return "(scripted) form %s" % a, parse_action_v2(a)


class DummyOrder:
    """T22_order: 4 buoc co thu tu -> doc gia tri + plan tu trang."""

    def __init__(self):
        self.i = 0
        self.spec = None
        self.tg = None

    def _load(self):
        if self.spec is None:
            self.spec = _page_state("JSON.stringify(window.__spec||null)") or {}
            self.tg = _page_state("JSON.stringify(window.__targets||null)") or {}

    def act(self, shot, task, t=0):
        self._load()
        spec, tg = self.spec or {}, self.tg or {}
        plan = "plan_%s" % spec.get("plan", "Basic")
        seq = [_click_at(tg, "name"), "TYPE %s" % spec.get("name", ""),
               _click_at(tg, plan, (150, 380)),
               _click_at(tg, "code"), "TYPE %s" % spec.get("code", ""),
               _click_at(tg, "submit")]
        seq = [a for a in seq if a.strip() != "TYPE"]
        a = seq[min(self.i, len(seq) - 1)]
        self.i += 1
        return "(scripted) order %s" % a, parse_action_v2(a)


class DummyKeys:
    """T23_keys: ESC de dong banner -> cuon bang CHUOT XE (SCROLL 5) -> click muc."""

    def __init__(self):
        self.i = 0
        self.n_scroll = 0

    def act(self, shot, task, t=0):
        st = _page_state(
            "JSON.stringify({keys:window.__keys||[],"
            "scrolled:!!window.__scrolled,targets:window.__targets||null})") or {}
        keys = st.get("keys") or []
        tg = st.get("targets") or {}
        if "Escape" not in keys:
            a = "KEY Escape"
        elif not st.get("scrolled"):
            # env DESKTOP khong co key end/pagedown -> cuon bang CHUOT XE (SCROLL 5)
            # (xem TASKS.md cua @MiMo). Neu van khong cuon duoc -> thu key (trinh duyet).
            a = "SCROLL 5" if self.n_scroll == 0 else "KEY Page_Down"
            self.n_scroll += 1
        else:
            v = tg.get("target")
            a = ("CLICK %d %d" % (int(v[0]), int(v[1]))) if v and len(v) >= 2 \
                else "SCROLL 5"
        self.i += 1
        return "(scripted) keys %s" % a, parse_action_v2(a)


class DummyRecovery:
    """T25_recovery: click 1 DECOY (khong an) -> DOI CHIEN LUWA -> click dong DUNG.

    Dummy nao 'lap lai cung 1 control' se FAIL (repeated=true) => dummy nay la
    mau DUNG cua hanh vi 'sau khi 1 click khong an thi thay control khac'.
    """

    def __init__(self):
        self.step = 0

    def act(self, shot, task, t=0):
        st = _page_state("JSON.stringify(window.__targets||{})") or {}
        tg = st.get("target")
        dec = st.get("decoys") or []
        if self.step == 0 and dec:
            p = dec[0]
            a = "CLICK %d %d" % (int(p[0]), int(p[1]))
        elif tg:
            a = "CLICK %d %d" % (int(tg[0]), int(tg[1]))
        else:
            a = "SCROLL 3"
        self.step += 1
        return "(scripted) recovery %s" % a, parse_action_v2(a)


class DummyClipboard:
    """T26_clipboard: click Source -> ctrl+a -> ctrl+c -> click Target -> ctrl+v.

    Day DUOI chuoi 5 buoc (chu ky B: model lap ctrl+c roi bo do).
    """

    def __init__(self):
        self.step = 0

    def act(self, shot, task, t=0):
        tg = (_page_state("JSON.stringify(window.__targets||{})") or {})
        src = tg.get("source")
        dst = tg.get("target")
        seq = []
        if src:
            seq.append("CLICK %d %d" % (int(src[0]), int(src[1])))
        seq += ["KEY Control+a", "KEY Control+c"]
        if dst:
            seq.append("CLICK %d %d" % (int(dst[0]), int(dst[1])))
        seq.append("KEY Control+v")
        a = seq[self.step] if self.step < len(seq) else "KEY Control+v"
        self.step += 1
        return "(scripted) clip %s" % a, parse_action_v2(a)


# ===== 4 dummy policy cua @MiMo (TASK-26) - COPY NGUYEN VAN tu
# phase14-desktop/tasks/dummy_mimo.py (de smoke app THAT su) =====
def _mimo_rect(sel):
    """Live rect cua 1 element -> (x, y) normalized 0..1000 (doc qua DOM)."""
    # FIX 22/10 (GLM): chuan hoa theo VIEWPORT THAT (innerWidth/innerHeight).
    # Dung 1280x720 cung => viewport that 1264x625 => click TRUOT ~16px/95px.
    js = ("(function(){const e=document.querySelector('%s'); if(!e) return null;"
          " const r=e.getBoundingClientRect();"
          " const W=window.innerWidth||1280,H=window.innerHeight||720;"
          " return [Math.round(((r.left+r.width/2)/W*1000)*10)/10,"
          "         Math.round(((r.top+r.height/2)/H*1000)*10)/10];})()"
          % sel)
    try:
        r = _page_state("JSON.stringify(%s)" % js)
    except Exception:
        r = None
    if not r:
        return None
    # FIX 22/10 (GLM): _page_state DA json.loads => r la list/str san.
    # Parse lai 2 lan gay TypeError (json.loads(list)) => _mimo_rect luon None
    # => dummy cua @MiMo (form_desktop/calc/table_sort/text_edit) tra 'DONE'
    # ngay buoc 0 => 4 task do khong bao giang do duoc.
    v = r
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            v = None
    if not v or len(v) < 2:
        return None
    return [int(v[0]), int(v[1])]


def _mimo_click(sel):
    p = _mimo_rect(sel)
    return ("click", [p[0], p[1]]) if p else None


def _mimo_text(sel):
    try:
        r = _page_state("JSON.stringify((document.querySelector('%s')||{}).textContent||'')"
                        % sel)
    except Exception:
        return ""
    if not r:
        return ""
    # FIX 22/10 (GLM): xem _mimo_rect - _page_state DA json.loads, r la gia tri
    # san (string text) => KHONG parse lai (json.loads(text) -> None).
    v = r
    return v.strip() if isinstance(v, str) else ""


def _mimo_top_row():
    """Toa do dong co score cao nhat (doc live, vi bang co the da cuon)."""
    js = ("(function(){const rows=Array.from(document.querySelectorAll('#tb tr'));"
          "let best=null,bv=-1;rows.forEach(tr=>{"
          "const sc=parseInt(tr.children[2].textContent.trim(),10)||0;"
          "if(sc>bv){bv=sc;best=tr;}});if(!best) return null;"
          "const r=best.getBoundingClientRect();"
          "const W=window.innerWidth||1280,H=window.innerHeight||720;"
          "return [Math.round(((r.left+r.width/2)/W*1000)*10)/10,"
          "       Math.round(((r.top+r.height/2)/H*1000)*10)/10];})()")
    try:
        r = _page_state("JSON.stringify(%s)" % js)
    except Exception:
        r = None
    # FIX 22/10 (GLM): _page_state DA json.loads => r la list/str san.
    # Parse lai 2 lan gay TypeError (json.loads(list)) => _mimo_top_row luon
    # None => dummy T23_table_sort khong chon duoc dong => task FAIL.
    v = r
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            v = None
    return [int(v[0]), int(v[1])] if v and len(v) >= 2 else None


class DummyFormDesktop:
    """T21_form_desktop: doc user/email/password tu o vang -> go vao 4 field
    -> tick terms -> Submit. MOI BUOC = 1 action (click field roi moi type)."""

    def __init__(self):
        self.i = 0

    def _plan(self):
        user = _mimo_text("#nu")
        email = _mimo_text("#ne")
        pwd = _mimo_text("#np")
        return [("click", "#u"), ("type", user), ("click", "#e"), ("type", email),
                ("click", "#p"), ("type", pwd), ("click", "#p2"), ("type", pwd),
                ("click", "#terms"), ("click", "#submit")]

    def act(self, shot, task, t=0):
        plan = self._plan()
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            a = _mimo_click(val)
            return ("(scripted) click %s" % val, a or ("done", None))
        if not val:
            return "(scripted) empty value", ("done", None)
        return ("(scripted) type %r" % val, ("type", val))


class DummyCalc:
    """T22_calc: doc 2 bieu thuc tu DOM, tinh lai, go dap an + bam Check."""

    def __init__(self):
        self.i = 0

    @staticmethod
    def _solve(expr):
        import re as _re
        m = _re.search(r"(\d+)\s*([+-])\s*(\d+)", expr or "")
        if not m:
            return None
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return str(a + b if op == "+" else a - b)

    def _plan(self):
        e1 = _mimo_text("#e1")
        e2 = _mimo_text("#e2")
        return [("click", "#a1"), ("type", self._solve(e1)), ("click", "#c1"),
                ("click", "#a2"), ("type", self._solve(e2)), ("click", "#c2"),
                ("click", "#submit")]

    def act(self, shot, task, t=0):
        plan = self._plan()
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            a = _mimo_click(val)
            return ("(scripted) click %s" % val, a or ("done", None))
        if not val:
            return "(scripted) cannot solve", ("done", None)
        return ("(scripted) type %r" % val, ("type", val))


class DummyTableSort:
    """T23_table_sort: SCROLL 5 (chuot xe) -> click header Score (2 lan) ->
    click dong co score cao nhat -> Confirm."""

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        # FIX 22/10 (GLM): phai click header TRUOC roi moi SCROLL - scroll truoc
        # lam header #hscore lot ra tren man hinh (rect y=-6) => click truot =>
        # app khong sort => reward 0.
        plan = [("click", "#hscore"), ("click", "#hscore"),
                ("scroll", "5"), ("row", None), ("click", "#confirm")]
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "scroll":
            return "(scripted) scroll down", ("scroll", "5")
        if kind == "row":
            p = _mimo_top_row()
            return ("(scripted) pick top row",
                    ("click", p) if p else ("done", None))
        a = _mimo_click(val)
        return ("(scripted) click %s" % val, a or ("done", None))


class DummyTextEdit:
    """T24_text_edit: click textarea -> ctrl+a -> go cau moi -> Save."""

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        want = _mimo_text("#want")
        plan = [("click", "#ta"), ("key", "ctrl+a"), ("type", want),
                ("click", "#save")]
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            a = _mimo_click(val)
            return ("(scripted) click %s" % val, a or ("done", None))
        if kind == "key":
            return "(scripted) key %s" % val, ("key", val)
        if not val:
            return "(scripted) no target text", ("done", None)
        return ("(scripted) type %r" % val, ("type", val))


class DummyErrorRecover:
    """T27_errorecover: doc code trong note -> go -> Activate (app bao loi) ->
    Activate LAN NUA (ket qua dung nhung app bao sai) -> app bat dau chay."""

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        code = _mimo_text("#code")
        tg = _page_state("JSON.stringify(window.__targets||{})") or {}
        cin = tg.get("code")
        act = tg.get("activate")
        plan = []
        if cin:
            plan.append(("click", cin))
        plan.append(("type", code))
        if act:
            plan.append(("click", act))
            plan.append(("click", act))   # lan 2: app moi bao loi
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            return ("(scripted) click", ("click", [int(val[0]), int(val[1])]))
        return ("(scripted) type %r" % val, ("type", val))


class DummyDistractor:
    """T28_distractor: doc badge trong note -> chon DUNG dong khop badge."""

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        tg = _page_state("JSON.stringify(window.__targets||{})") or {}
        ok = tg.get("ok")
        if self.i == 0 and ok and len(ok) >= 2:
            self.i = 1
            return ("(scripted) pick right row", ("click", [int(ok[0]), int(ok[1])]))
        self.i += 1
        return "(scripted) done", ("done", None)


class DummyScript:
    """Replay a fixed list of actions (from --script a;b;c)."""

    def __init__(self, actions):
        self.actions = actions
        self.i = 0

    def act(self, shot, task, t=0):
        a = self.actions[min(self.i, len(self.actions) - 1)]
        self.i += 1
        return "(scripted) %s" % a, parse_action_v2(a)


# Demo policy for the T21_form app (see phase14-desktop/tasks/t21_form.html
# built by phase13-gui/kernel_desktop_bench/apps/t21_form.html): fill the two
# fields with the values from the note box, then press Register.
FORM_DUMMY_SCRIPT = ["CLICK 297 489", "TYPE carol", "CLICK 297 656",
                     "TYPE carol@example.com", "CLICK 187 781"]


# ------------------------------------------------------- CDP (mini websocket)
def _http_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _ws_connect(ws_url, timeout=8):
    if not ws_url.startswith("ws://"):
        raise ValueError("chi ho tro ws:// (ws nho, khong TLS)")
    rest = ws_url[5:]
    hostport, _, path = rest.partition("/")
    path = "/" + path
    host, _, port = hostport.partition(":")
    port = int(port or 80)
    s = socket.create_connection((host, port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n" % (path, host, port, key))
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise IOError("ws handshake: peer closed")
        buf += chunk
    head, _, leftover = buf.partition(b"\r\n\r\n")
    if b" 101 " not in head.split(b"\r\n")[0] + b" ":
        raise IOError("ws handshake failed: %r" % head[:120])
    return s, leftover


def _ws_send(s, payload):
    data = payload.encode("utf-8")
    mask = os.urandom(4)
    n = len(data)
    hdr = bytearray([0x81])
    if n < 126:
        hdr.append(0x80 | n)
    elif n < 65536:
        hdr.append(0x80 | 126)
        hdr += n.to_bytes(2, "big")
    else:
        hdr.append(0x80 | 127)
        hdr += n.to_bytes(8, "big")
    hdr += mask
    s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def _ws_recv(s, leftover=b"", timeout=8):
    buf = bytearray(leftover)

    def need(n):
        while len(buf) < n:
            s.settimeout(timeout)
            chunk = s.recv(65536)
            if not chunk:
                raise IOError("ws closed")
            buf.extend(chunk)

    need(2)
    b0, b1 = buf[0], buf[1]
    opcode = b0 & 0x0F
    masked = b1 & 0x80
    ln = b1 & 0x7F
    off = 2
    if ln == 126:
        need(4)
        ln = int.from_bytes(buf[2:4], "big")
        off = 4
    elif ln == 127:
        need(10)
        ln = int.from_bytes(buf[2:10], "big")
        off = 10
    mask = b""
    if masked:
        need(off + 4)
        mask = bytes(buf[off:off + 4])
        off += 4
    need(off + ln)
    payload = bytes(buf[off:off + ln])
    del buf[:off + ln]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    if opcode == 0x9:  # ping -> pong
        s.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
        return _ws_recv(s, bytes(buf), timeout)
    if opcode == 0x8:
        raise IOError("ws closed by peer")
    return opcode, payload, bytes(buf)


_CDP_WARNED = False


def _cdp_alive(port, timeout=1.0):
    """Co process CDP dang listen o port khong (khong log nhieu)."""
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


_PW = None            # playwright instance
_PW_BROWSER = None    # chromium headful (cua so X11 THAT)
_PW_PAGE = None       # trang app
_VP = None            # (off_x, off_y, vw, vh) - viewport THAT cua trang trong
                      # man hinh X11 (dung de CAT ANH + DICH TOA DO click)


def cdp_eval(expr, port=None, timeout=8):
    """Evaluate JS trong app.

    Uu tien: PLAYWRIGHT (page.evaluate) — chromium bundle KHONG mo port
    remote-debugging (da thu 4 lan) nhung playwright launch(headless=False)
    van la CUA SO X11 THAT → xdotool van bam/key duoc ✓.
    Fallback: raw CDP websocket (phong cho truong hop khong co playwright).
    """
    global _CDP_WARNED
    if _PW_PAGE is not None:
        try:
            return _PW_PAGE.evaluate(expr)
        except Exception as e:
            if not _CDP_WARNED:
                _CDP_WARNED = True
                log("pw eval loi: %s" % str(e)[:100])
            return None
    port = port or CDP_PORT
    if not _cdp_alive(port):
        if not _CDP_WARNED:
            _CDP_WARNED = True
            log("cdp: port %d khong mo (chromium chua chay voi "
                "--remote-debugging-port?) -> reward = None" % port)
        return None
    try:
        tabs = env.dom_state(port)
    except Exception as e:
        if not _CDP_WARNED:
            _CDP_WARNED = True
            log(f"cdp: dom_state loi: {type(e).__name__}: {str(e)[:120]}")
        return None
    if not tabs:
        return None
    page = None
    for t in tabs:
        if str(t.get("url", "")).startswith("file://"):
            page = t
            break
    if page is None:
        page = tabs[0]
    s = None
    try:
        s, leftover = _ws_connect(page["ws"], timeout=timeout)
        _ws_send(s, json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": expr, "returnByValue": True}}))
        for _ in range(24):
            opcode, payload, leftover = _ws_recv(s, leftover, timeout)
            if opcode != 0x1:
                continue
            try:
                msg = json.loads(payload.decode("utf-8", "replace"))
            except Exception:
                continue
            if msg.get("id") == 1:
                res = msg.get("result") or {}
                if res.get("exceptionDetails"):
                    return None
                return (res.get("result") or {}).get("value")
    except Exception as e:
        log(f"cdp eval loi: {type(e).__name__}: {str(e)[:120]}")
        return None
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
    return None


# ----------------------------------------------------------------- app open
def find_browser():
    """Tim chromium dung duoc:
    1) binary tu bundle offline-browsers (/tmp/pw-browsers/.../chrome) - da biet
       chay tren Kaggle (co deps san sau setup_playwright_offline).
    2) 'chromium' trong PATH.
    3) 'chromium-browser' -> tren image Kaggle day la WRAPPER SNAP (khong chay
       duoc) -> bo qua.
    """
    import glob
    cands = []
    for pat in ("/tmp/pw-browsers/**/chrome-linux64/chrome",
                "/tmp/pw-browsers/**/chrome"):
        cands += glob.glob(pat, recursive=True)
    for c in cands:
        if os.path.exists(c):
            try:
                os.chmod(c, 0o755)
            except Exception:
                pass
            log("browser (bundle): %s" % c)
            return c
    for b in ("chromium", "google-chrome"):
        p = shutil.which(b)
        if p:
            log("browser (PATH): %s" % p)
            return p
    # 4) chromium do playwright cai san (LOCAL - de test integration khong
    #    can Kaggle): playwright.chromium.executable_path
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as _p:
            _exe = _p.chromium.executable_path
        if _exe and os.path.exists(_exe):
            log("browser (playwright local): %s" % _exe)
            return _exe
    except Exception as e:
        log("browser (playwright local) loi: %s" % str(e)[:80])
    log("browser: KHONG tim thay chromium -> can bundle offline-browsers")
    return None


def setup_browser_bundle():
    """Neu co dataset offline-browsers: chay setup_playwright_offline (copy
    browser + replay deps + ldconfig) de chromium chay duoc tren CPU kernel."""
    for root, _d, files in os.walk("/kaggle/input"):
        if "setup_playwright_offline.py" in files:
            if root not in sys.path:
                sys.path.insert(0, root)
            try:
                from setup_playwright_offline import setup_playwright_offline
                info = setup_playwright_offline()
                log("setup_playwright_offline: %s" % str(info)[:160])
                return True
            except Exception as e:
                log("setup_playwright_offline loi: %s" % e)
    return False


def open_app_cdp(url, port=None, extra_args=""):
    """Mo app trong chromium HEADFUL (playwright) tren X11 that.

    - env.py khong sua; phay nay harness-local.
    - Playwright tu lo flag nen van la cua so THAT (khac headless_shell) ->
      xdotool bam/key duoc vao app that ✓.
    """
    global _PW, _PW_BROWSER, _PW_PAGE
    port = port or CDP_PORT
    os.environ.setdefault("DISPLAY", ":99")
    close_app()          # dong browser cu (neu con) truoc khi mo moi
    setup_browser_bundle()
    chrome = find_browser()
    if not chrome:
        log("  WARNING: khong co chromium -> reward se = None")
        return False
    # 1) thu playwright headful
    try:
        from playwright.sync_api import sync_playwright
        _PW = sync_playwright().start()
        _PW_BROWSER = _PW.chromium.launch(
            headless=HEADLESS, executable_path=chrome,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                  "--window-size=%d,%d" % (W, H), "--window-position=0,0",
                  "--kiosk"])
        # no_viewport=True: dung viewport THAT cua cua so. Playwright MAC DINH
        # override 1280x720 -> trang bi cat 86px o cuoi (thanh cong cu browser)
        # va toa do CSS lech 86px so voi anh chup man hinh.
        ctx = _PW_BROWSER.new_context(no_viewport=True)
        _PW_PAGE = ctx.new_page()
        _PW_PAGE.goto(url)
        _PW_PAGE.wait_for_timeout(1200)
        _measure_viewport()
        log("app opened (playwright headful): %s" % url)
        # offset thanh cong cu browser: viewport thuc = innerHeight (playwright
        # override) -> do bang marker hoac suy tu vi tri cua #board
        try:
            off = _PW_PAGE.evaluate("""() => {
                const b = document.getElementById('board');
                if (!b) return 0;
                const r = b.getBoundingClientRect();
                return r.top;
            }""")
            log("playwright OK | board top=%s" % off)
        except Exception:
            pass
        return True
    except Exception as e:
        log("playwright that bai: %s: %s" % (type(e).__name__, str(e)[:120]))
        try:
            if _PW_BROWSER:
                _PW_BROWSER.close()
        except Exception:
            pass
        _PW = None
        _PW_BROWSER = None
        _PW_PAGE = None
    # 2) fallback: raw CDP (chromium --remote-debugging-port)
    if HEADLESS:
        log("  headless: bo qua fallback raw-CDP (khong ap dung)")
        return False
    cmd = ("%s --no-sandbox --disable-gpu --window-size=%d,%d "
           "--window-position=0,0 --kiosk --disable-dev-shm-usage "
           "--remote-debugging-port=%d --remote-allow-origins=* "
           "--user-data-dir=%s %s '%s' >%s 2>&1 &"
           % (chrome, W, H, port, os.path.join(env.WORK, "chrome_profile"),
              extra_args, url, os.path.join(env.WORK, "chrome.log")))
    env.sh(cmd, timeout=60)
    time.sleep(3)
    log("app opened (raw CDP, port %d): %s" % (port, url))
    # chromium khoi dong LAN DAU tren CPU kernel rat cham (~20-40s) -> cho lau
    for i in range(90):
        if _cdp_alive(port):
            log("  cdp ready sau %ds (port %d)" % (i + 1, port))
            return True
        time.sleep(1)
    log("  WARNING: CDP khong phan hoi sau 90s - reward se = None")
    try:
        with open(os.path.join(env.WORK, "chrome.log"), encoding="utf-8",
                  errors="replace") as fh:
            log("  chrome.log: %s" % fh.read()[-500:])
    except Exception:
        pass
    return False


def close_app():
    """Dong browser (neu dung playwright) de container ket thuc sach."""
    global _PW, _PW_BROWSER, _PW_PAGE, _VP
    try:
        if _PW_BROWSER:
            _PW_BROWSER.close()
    except Exception:
        pass
    try:
        if _PW:
            _PW.stop()
    except Exception:
        pass
    _PW = None
    _PW_BROWSER = None
    _PW_PAGE = None
    _VP = None


def maybe_novnc():
    """Best-effort noVNC for the Space (user can watch the agent in the browser)."""
    import shutil
    if not shutil.which("x11vnc"):
        log("noVNC: thieu x11vnc -> bo qua (cai 'x11vnc novnc websockify' neu can)")
        return None
    env.sh("x11vnc -display %s -forever -shared -nopw -rfbport 5900 "
           ">/dev/null 2>&1 &" % env.DISPLAY, timeout=30)
    if shutil.which("websockify"):
        env.sh("websockify --web=/usr/share/novnc 6080 localhost:5900 "
               ">/dev/null 2>&1 &", timeout=30)
        url = "http://<space-host>:6080/vnc.html"
    else:
        url = "vnc://<space-host>:5900"
    log("noVNC: x11vnc started -> %s" % url)
    return url


# --------------------------------------------------------------- task table
def load_tasks(tasks_dir, tasks_json=None):
    tasks = dict(BUILTIN_TASKS)
    pj = tasks_json or os.path.join(tasks_dir, "desktop_tasks.json")
    if os.path.exists(pj):
        try:
            with open(pj, encoding="utf-8") as fh:
                extra = json.load(fh)
            for k, v in (extra.get("tasks") or extra).items():
                tasks[k] = v
            log(f"loaded {len(extra.get('tasks') or extra)} task(s) tu {pj}")
        except Exception as e:
            log(f"tasks json loi: {type(e).__name__}: {str(e)[:120]}")
    return tasks


def task_app_path(task, tasks_dir):
    app = task.get("app")
    if not app:
        return None
    if os.path.isabs(app):
        return app
    for cand in (os.path.join(tasks_dir, app),
                 os.path.join(tasks_dir, os.path.basename(app))):
        if os.path.exists(cand):
            return cand
    return None


# ---------------------------------------------- viewport that (OFFSET 86px fix)
def _measure_viewport():
    """Do viewport THAT cua trang trong man hinh X11.

    Chromium headful co thanh cong cu (kiosk co the bi bo) -> viewport bat dau
    oi `screenY` (thuong 86px) va cao `innerHeight` (< 720). Anh cua model phai
    la ANH CUA VIEWPORT (cat), va click phai cong them offset.
    """
    global _VP
    if _PW_PAGE is None:
        _VP = None
        return None
    try:
        vw, vh, sx, sy = _PW_PAGE.evaluate(
            "() => [window.innerWidth, window.innerHeight, "
            "window.screenX, window.screenY]")
        _VP = (int(sx), int(sy), int(vw), int(vh))
        log("viewport that: off=(%d,%d) size=%dx%d | man hinh %dx%d" %
            (_VP[0], _VP[1], _VP[2], _VP[3], env.W, env.H))
    except Exception as e:
        _VP = None
        log("do viewport loi: %s: %s" % (type(e).__name__, str(e)[:120]))
    return _VP


def crop_to_viewport(src, dst):
    """Cat anh man hinh X11 ve dung viewport cua trang (bo thanh cong cu)."""
    if not os.path.exists(src):
        return False
    if _VP is None:
        try:
            shutil.copy(src, dst)
            return True
        except Exception:
            return False
    ox, oy, vw, vh = _VP
    try:
        from PIL import Image
        img = Image.open(src).convert("RGB")
        W0, H0 = img.size
        left = max(0, min(ox, W0 - 1))
        top = max(0, min(oy, H0 - 1))
        right = max(left + 1, min(ox + vw, W0))
        bottom = max(top + 1, min(oy + vh, H0))
        if (right - left, bottom - top) == (vw, vh) and (ox, oy) == (0, 0):
            img.save(dst, "PNG")
        else:
            img.crop((left, top, right, bottom)).save(dst, "PNG")
        return True
    except Exception as e:
        log("crop viewport loi: %s: %s" % (type(e).__name__, str(e)[:120]))
        try:
            shutil.copy(src, dst)
            return True
        except Exception:
            return False


_NUM2 = re.compile(r"^(\s*CLICK\s+)(\d+)(\s+)(\d+)(\s*)$", re.I)
_NUM1 = re.compile(r"^(\s*MOVE\s+)(\d+)(\s+)(\d+)(\s*)$", re.I)
_NUM4 = re.compile(r"^(\s*DRAG\s+)(\d+)(\s+)(\d+)(\s+)(\d+)(\s+)(\d+)(\s*)$",
                   re.I)


def to_screen_action(a_str):
    """Dich toa do theo VIEWPORT (model nhin anh viewport) sang toa do MAN HINH.

    model -> x_norm/1000 * vw + off_x  (px)  -> /env.W * 1000 (norm man hinh)
    """
    if not a_str or _VP is None:
        return a_str
    ox, oy, vw, vh = _VP
    sx, sy = float(env.W), float(env.H)

    def conv(x, y):
        px = ox + float(x) / 1000.0 * vw
        py = oy + float(y) / 1000.0 * vh
        return (int(round(px / sx * 1000.0)),
                int(round(py / sy * 1000.0)))

    m = _NUM2.match(a_str)
    if m:
        x, y = conv(m.group(2), m.group(4))
        return "%s%d %d" % (m.group(1), x, y)
    m = _NUM1.match(a_str)
    if m:
        x, y = conv(m.group(2), m.group(4))
        return "%s%d %d" % (m.group(1), x, y)
    m = _NUM4.match(a_str)
    if m:
        x1, y1 = conv(m.group(2), m.group(4))
        x2, y2 = conv(m.group(6), m.group(8))
        return "%s%d %d %d %d" % (m.group(1), x1, y1, x2, y2)
    return a_str


# --------------------------------------------------------------- main loop
def run_episode(task_id, task, policy, out_dir, ep, max_steps):
    obs_dir = os.path.join(out_dir, "obs")
    os.makedirs(obs_dir, exist_ok=True)
    threshold = float(task.get("threshold", 0) or 0)
    app_path = task_app_path(task, task.get("_tasks_dir", HERE))
    if app_path:
        # file:// yeu DUONG DAN TUYET DOI (Windows: 'C:/...' -> file:///C:/...)
        url = "file://" + os.path.abspath(app_path).replace("\\", "/")
        ok_open = open_app_cdp(url)
        if (not ok_open) and not HEADLESS:
            log("[INFRA] khong mo duoc app: %s -> BO QUA episode" % app_path)
            INFRA_ERRORS.append({"task_id": task_id, "episode": ep,
                                 "reason": "open_failed",
                                 "app": str(app_path)})
            return [], None, False
    else:
        # FIX 22/10 (MiMo): thieu app file => KHONG mo browser => anh X11 den
        # => model thay "black screen" => DONE reward=-1 => ep bi tinh nham
        # la model that (run B2: T21_form_desktop + T23_table_sort = 40/120).
        # => BO QUA episode (khong goi model) + ghi lai loi ha tang.
        # HEADLESS (test local, khong co X11) => giu hanh vi cu: dung env hien tai.
        if HEADLESS:
            log(f"task {task_id}: khong tim thay app -> dung env hien tai")
        else:
            log("[INFRA] task %s: khong tim thay app file (%s) -> BO QUA episode "
                "(khong goi model)" % (task_id, task.get("app")))
            INFRA_ERRORS.append({"task_id": task_id, "episode": ep,
                                 "reason": "app_missing",
                                 "app": str(task.get("app")),
                                 "tasks_dir": str(task.get("_tasks_dir", HERE))})
            return [], None, False
    rows = []
    best = None
    success = False
    for step in range(max_steps):
        shot = os.path.join(obs_dir, "%s_e%02d_s%02d.png" % (task_id, ep, step))
        raw_shot = os.path.join(obs_dir, "_full_%s_e%02d_s%02d.png" %
                                (task_id, ep, step))
        ok_full = env.screenshot(raw_shot) if not HEADLESS else False
        # CAT anh ve viewport (bo thanh cong cu browser) => toa do model khop CSS
        ok_shot = crop_to_viewport(raw_shot, shot) if ok_full else False
        if not ok_shot:
            # DU PHONG: khong co imagemagick/xwd => chup viewport qua CDP
            # (cung he toa do nen pipeline giong het)
            ok_shot = cdp_screenshot(shot)
        try:
            if os.path.exists(raw_shot):
                os.remove(raw_shot)
        except Exception:
            pass
        raw, act = policy.act(shot, task.get("instruction", ""), step)
        a_str = act_to_str(act)
        if a_str is None and raw:
            a_str = raw.strip().splitlines()[-1].strip() or None
        done_flag = False
        desc = "no-action"
        ok = False
        if a_str and a_str.upper() != "DONE":
            if HEADLESS:
                # khong co X11 -> thuc hien action qua Playwright/CDP.
                # He toa do: model nhin anh VIEWPORT => toa do chuan hoa theo
                # VIEWPORT (khong phai man hinh 1280x720) => bo qua
                # to_screen_action va dung kich thuoc viewport that.
                desc = cdp_action(a_str)
                ok = not desc.startswith("cdp loi") and not desc.startswith("cdp bo")
                time.sleep(0.15)
            else:
                ok, desc = env.do_action(to_screen_action(a_str))
                time.sleep(0.25)
        elif a_str and a_str.upper() == "DONE":
            done_flag = True
            desc = "done"
        reward = cdp_eval(task.get("reward_js", "0"))
        if reward is None:
            reward = -1
        try:
            reward = float(reward)
        except Exception:
            reward = -1
        if best is None or reward > best:
            best = reward
        rows.append({
            "step": step, "obs": os.path.relpath(shot, out_dir).replace("\\", "/"),
            "shot_ok": bool(ok_shot), "action": a_str, "act_desc": desc,
            "act_ok": bool(ok), "reward": reward, "raw": (raw or "")[:2000],
            "n_new": getattr(policy, "last", {}).get("n_new"),
        })
        log("  step %02d action=%-18s reward=%s raw=%r" %
            (step, str(a_str)[:18], reward, (raw or "")[:60]))
        if reward >= threshold:
            success = True
            break
        if done_flag:
            break
    close_app()   # dong browser cua episode nay (tranh ro browser moi moi
                  # episode -> het RAM)
    return rows, best, success


# ------------------------------------------------------------------ X11 deps
# env.py (cua @MiMo) start_display() co 2 loi lam desktop-env CHET trong
# Kaggle kernel (thay bang log that cua run out_desktop_bench):
#   (1) pgrep -f 'Xvfb :99' TU KHUPT CHINH NÓ (command line chua "Xvfb :99")
#       -> in "ok" nhung Xvfb CHUA BAO DUOC start -> chrome headful chet
#          "Missing X server or $DISPLAY".
#   (2) apt-get install ... >/dev/null 2>&1 -> loi bi che, va thieu
#       imagemagick (import/convert) + x11-apps (xwd) => KHONG chup duoc
#       man hinh ("import: not found | xwd: not found") => khong co anh quan sat.
# env.py khong sua (file cua nguoi khac) -> sua o day, harness-local.
X11_TOOLS = {"import": "imagemagick",   # ImageMagick: chup man hinh (du phong)
             "convert": "imagemagick",  # ImageMagick: xwd -> png (du phong)
             "xwd": "x11-apps",          # xwd: chup X11 raw (du phong)
             "xdotool": "xdotool",       # dieu kenh chuot/ban phim that
             "xdpyinfo": "x11-utils",   # kiem tra X server co that (du phong)
             "Xvfb": "xvfb",             # X server ao (co san trong image Kaggle)
             "fluxbox": "fluxbox"}       # WM: cua so map dung (du phong)

# HANH DONG CẦN THIẾT thật sự: xdotool (input OS that). Cai khac chi la
# DU PHONG - chup anh co the thay bang CDP (page.screenshot) => khong can
# imagemagick/x11-apps.
X11_REQUIRED = ["xdotool"]
X11_OPTIONAL = ["import", "convert", "xwd", "xdpyinfo", "fluxbox"]


def _apt_repair_sources():
    """Kaggle: DNS 'security.ubuntu.com' FAIL (archive.ubuntu.com OK) =>
    apt update/install treo 30' cho retry. Sua 1 dong: tro host hong sang
    host dang chay."""
    rc, out, err = env.sh(
        "grep -rl 'security.ubuntu.com' /etc/apt/sources.list "
        "/etc/apt/sources.list.d/ 2>/dev/null | while read f; do "
        "sed -i 's/security.ubuntu.com/archive.ubuntu.com/g' \"$f\"; "
        "echo patched:$f; done", timeout=120)
    if out.strip():
        log("[x11] apt sources patched: %s" % out.strip().replace("\n", " "))
    return out


def _install_xdotool_offline():
    """Cai xdotool tu DATASET OFFLINE (khong can apt/mang).

    Dataset: khoadangnguye/ornith-gui-xdotool (xdotool + libxdo3 .deb, 64KB)
    - image Kaggle CO Xvfb nhung THIEU xdotool; apt-get treo do DNS
      security.ubuntu.com fail => 30' GPU lang phi.
    - Ho tro CA 2 layout: (a) file .deb -> dpkg -i, (b) da giai nen (binary
      + libxdo.so*) -> copy vao /usr/local/bin + ldconfig.
    """
    import glob
    dirs = (glob.glob("/kaggle/input/*/ornith-gui-xdotool")
            + glob.glob("/kaggle/input/ornith-gui-xdotool")
            + glob.glob("/kaggle/input/datasets/*/ornith-gui-xdotool")
            + glob.glob("/kaggle/input/*/*/ornith-gui-xdotool"))
    for d in dirs:
        debs = sorted(glob.glob(os.path.join(d, "*.deb")))
        if debs:
            rc, out, err = env.sh("dpkg -i %s 2>&1 | tail -4" % " ".join(debs),
                                   timeout=300)
            log("[x11] dpkg -i (%d file) rc=%s | %s" %
                (len(debs), rc, (out or err or "")[-200:].replace("\n", " ")))
        else:
            rc, out, err = env.sh(
                "cp '%s'/xdotool /usr/local/bin/ 2>/dev/null; "
                "cp '%s'/libxdo.so* /usr/local/lib/ 2>/dev/null; ldconfig" %
                (d, d), timeout=180)
            log("[x11] copy binary tu offline bundle rc=%s | %s" %
                (rc, (out or err or "")[-160:].replace("\n", " ")))
        if shutil.which("xdotool"):
            rc, out, err = env.sh("xdotool --version 2>&1 | head -1",
                                   timeout=60)
            log("[x11] xdotool OFFLINE OK: %s" % (out or err).strip()[:80])
            return True
    return False


def ensure_x11(log=print):
    """Cai du cac tool X11 thieu (co LOG, khong che output).

    Thu tu: (1) dataset OFFLINE (nhanh, khong can mang) -> (2) apt (du phong)
    - 'xdotool' la BAT BUOC (input OS that)
    - 'import/convert/xwd' chi de chup man hinh X11: neu thieu thi dung
      DU PHONG chup qua CDP (page.screenshot) => van chay duoc.
    """
    need_req = [b for b in X11_REQUIRED if not shutil.which(b)]
    need_opt = [b for b in X11_OPTIONAL if not shutil.which(b)]
    if not need_req and not need_opt:
        log("[x11] tools OK (bat buoc + du phong)")
        return True
    if need_req:
        log("[x11] thieu BAT BUOC: %s -> thu cai OFFLINE truoc" % need_req)
        _install_xdotool_offline()
    need_req = [b for b in X11_REQUIRED if not shutil.which(b)]
    need_opt = [b for b in X11_OPTIONAL if not shutil.which(b)]
    if not need_req and not need_opt:
        log("[x11] tools OK (offline bundle)")
        return True
    pkgs = sorted({"xdotool": "xdotool", "import": "imagemagick",
                   "convert": "imagemagick", "xwd": "x11-apps",
                   "xdpyinfo": "x11-utils", "fluxbox": "fluxbox"}[b]
                  for b in (need_req + need_opt))
    log("[x11] con thieu: %s -> apt-get install %s (du phong)" %
        (need_req + need_opt, pkgs))
    _apt_repair_sources()
    rc, out, err = env.sh(
        "apt-get -o Acquire::Retries=0 -o Acquire::http::Timeout=20 "
        "-o Acquire::https::Timeout=20 update -qq 2>&1 | tail -3",
        timeout=300)
    log("[x11] apt-get update rc=%s | %s"
        % (rc, (out or err or "")[-260:].replace("\n", " ")))
    rc, out, err = env.sh(
        "DEBIAN_FRONTEND=noninteractive apt-get install -y "
        "--no-install-recommends %s 2>&1 | tail -6" % " ".join(pkgs),
        timeout=600)
    log("[x11] apt-get install rc=%s | %s"
        % (rc, (out or err or "")[-420:].replace("\n", " ")))
    still_req = [b for b in X11_REQUIRED if not shutil.which(b)]
    still_opt = [b for b in X11_OPTIONAL if not shutil.which(b)]
    if still_req:
        log("[x11] FAIL thieu BAT BUOC: %s" % still_req)
        return False
    if still_opt:
        log("[x11] thieu DU PHONG: %s (dung chup anh qua CDP)" % still_opt)
    log("[x11] tools OK sau khi cai")
    return True


def ensure_display(log=print):
    """Dam bao X server THAT dang chay (kiem bang xdpyinfo, khong pgrep)."""
    disp = env.DISPLAY

    def x_ok():
        # xdotool la BAT BUOC (input) => dung no de kiem X server that;
        # xdpyinfo chi la du phong.
        if shutil.which("xdotool"):
            rc, out, err = env.sh(
                "xdotool getdisplaygeometry >/dev/null 2>&1 && echo OK || echo NO",
                timeout=30)
            if "OK" in (out or ""):
                return True
        rc, out, err = env.sh(
            "xdpyinfo -display %s >/dev/null 2>&1 && echo OK || echo NO" % disp,
            timeout=30)
        return "OK" in (out or "")

    if x_ok():
        log("[x11] display %s da chay" % disp)
        return True
    if not shutil.which("Xvfb"):
        log("[x11] thieu binary Xvfb -> khong the bat X server")
        return False
    log("[x11] bat Xvfb tren %s ..." % disp)
    env.sh("rm -f /tmp/.X%s-lock" % disp.lstrip(":").split(".")[0]
           + "; (Xvfb %s -screen 0 %dx%dx24 -ac +extension GLX +render "
             "-noreset >/tmp/xvfb.log 2>&1 &) ; sleep 3"
           % (disp, env.W, env.H), timeout=90)
    for i in range(20):
        if x_ok():
            log("[x11] display %s OK (sau %ds)" % (disp, i + 1))
            return True
        time.sleep(1)
    log("[x11] FAIL: khong bat duoc X tren %s (xem /tmp/xvfb.log)" % disp)
    return False


def cdp_action(a_str):
    """Thuc hien action qua Playwright/CDP (KHONG can xdotool/X11).

    Dung cho che do HEADLESS (test local, pipeline smoke). Toa do: model
    (0..1000) -> viewport (1280x720) truc tiep (headless khong co thanh cong
    cu browser nen he toa do giong het voi desktop).
    """
    global _PW_PAGE
    if _PW_PAGE is None:
        return "cdp: no page"
    a = (a_str or "").strip()
    v = a.split()[0].upper() if a else ""
    # he toa do: viewport that (model nhin anh viewport)
    vw, vh = (_VP[2], _VP[3]) if _VP else (1280, 720)
    try:
        if v == "CLICK":
            m = _NUM2.match(a)
            if m:
                x = int(m.group(2)) / 1000.0 * vw
                y = int(m.group(4)) / 1000.0 * vh
                _PW_PAGE.mouse.click(x, y)
                return "cdp click(%d,%d)" % (x, y)
        elif v == "TYPE":
            txt = a[4:].strip() if len(a) > 4 else ""
            _PW_PAGE.keyboard.type(txt)
            return "cdp type(%r)" % txt[:40]
        elif v == "KEY":
            key = a[3:].strip() if len(a) > 3 else ""
            # ten phim X (Page_Down, down, ...) -> ten phim Playwright
            # (PageDown, ArrowDown, ...) - 'Unknown key: down' => phim khong ban
            pk = key.replace("_", "")
            if "+" in pk:
                mods, base = pk.split("+", 1)
                pk = "%s+%s" % (MOD_KEYS.get(mods.lower(), mods),
                                PLAYWRIGHT_KEYS.get(base.lower(), base))
            else:
                pk = PLAYWRIGHT_KEYS.get(pk.lower(), pk)
            _PW_PAGE.keyboard.press(pk)
            return "cdp key(%s)" % key
        elif v == "SCROLL":
            try:
                n = int(a.split()[1])
            except Exception:
                n = 3
            _PW_PAGE.mouse.wheel(0, n * 100)
            return "cdp scroll(%d)" % n
    except Exception as e:
        return "cdp loi: %s: %s" % (type(e).__name__, str(e)[:60])
    return "cdp bo qua: %r" % a[:40]


def cdp_screenshot(path):
    """Chup anh VIEWPORT qua Playwright/CDP - KHONG can imagemagick/xwd.

    Cung he toa do voi anh da cat viewport (model van click trong he viewport)
    => dung chung pipeline cua crop_to_viewport, chi khac nguon anh.
    """
    global _PW_PAGE
    if _PW_PAGE is None:
        return False
    try:
        _PW_PAGE.screenshot(path=path)
    except Exception as e:
        log("  cdp screenshot loi: %s: %s" % (type(e).__name__, str(e)[:80]))
        return False
    try:
        return os.path.exists(path) and os.path.getsize(path) > 0
    except OSError:
        return False


def preflight(log=print):
    """KIEM TRA ENV DESKTOP TRUOC KHI TON GPU (model load ~10' + browser ~4').

    Fail o day (<5') thay vi sau 15' moi biet 'import: not found'.
    """
    os.makedirs(env.WORK, exist_ok=True)
    if HEADLESS:
        log("[preflight] HEADLESS: bo qua kiem tra X11/xdotool (test local)")
        return True
    env.start_display()          # tao thu muc + cai Xvfb neu thieu
    ok_tools = ensure_x11(log=log)
    ok_disp = ensure_display(log=log)
    if not ok_disp:
        raise SystemExit("FAIL: khong co X server tren %s -> chrome headful se "
                         "chet 'Missing X server or $DISPLAY'. Xem log [x11]. "
                         "Nguyen nhan thuong gap: (a) kernel-metadata co "
                         "enable_internet=false => apt-get khong chay (phai "
                         "true), (b) bundle offline thieu X11 (Xvfb/import/xwd)."
                         % env.DISPLAY)
    if not ok_tools:
        raise SystemExit("FAIL: thieu xdotool (input OS that) - apt khong cai "
                         "duoc. Xem log [x11] (apt source/DNS).")
    probe = os.path.join(env.WORK, "preflight.png")
    ok = env.screenshot(probe)
    if ok:
        log("[preflight] OK: X %s + anh chup X11" % env.DISPLAY)
        return True
    # DU PHONG: khong co imagemagick/xwd => chup anh qua CDP (van dung)
    chrome = find_browser()
    try:
        import playwright  # noqa: F401
        has_pw = True
    except Exception:
        has_pw = False
    if has_pw and chrome:
        log("[preflight] anh X11 that (thieu imagemagick/xwd) -> se chup anh "
            "qua CDP (page.screenshot)")
        return True
    raise SystemExit("FAIL: khong chup duoc man hinh (thieu import/convert/xwd "
                     "VA khong dung duoc playwright) -> xem log [x11]. "
                     "Khong co anh = khong co quan sat.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default="T20_2048",
                    help="comma list of task ids")
    ap.add_argument("--tasks-dir", default=os.path.join(HERE, "tasks"))
    ap.add_argument("--tasks-json", default=None)
    ap.add_argument("--out", default=os.path.join(env.WORK, "harness"))
    ap.add_argument("--policy", default="dummy", choices=["dummy", "model"])
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--base-dir", default=None)
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=0,
                    help="0 = use task max_steps")
    ap.add_argument("--script", default=None,
                    help="dummy replay: 'KEY left;KEY up;...'")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--novnc", action="store_true")
    ap.add_argument("--no-display", action="store_true",
                    help="skip Xvfb start (Space may already have a display)")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    log(f"env: WORK={env.WORK} DISPLAY={env.DISPLAY} out={a.out}")

    if not a.no_display:
        preflight(log=log)
    if a.novnc:
        maybe_novnc()

    if a.selftest:
        probe = os.path.join(a.out, "selftest.png")
        ok = env.screenshot(probe)
        ok2, desc = env.do_action("CLICK 500 500")
        log(f"selftest: shot={ok} action={desc}")
        rep = {"shot": ok, "action": desc, "cdp_tabs": len(env.dom_state()),
               "reward_js": "window.__score || 0"}
        with open(os.path.join(a.out, "selftest.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=1)
        log("selftest DONE")
        return 0

    tasks = load_tasks(a.tasks_dir, a.tasks_json)
    wanted = [t.strip() for t in a.tasks.split(",") if t.strip()]
    for tid in wanted:
        if tid not in tasks:
            log(f"WARNING: khong biet task {tid} (co: {sorted(tasks)})")
    if a.policy == "model":
        policy = load_policy_model(a.adapter, a.base_dir)
    elif a.script:
        acts = [s.strip() for s in a.script.split(";") if s.strip()]
        policy = DummyScript(acts)
    else:
        policy = None  # per-task dummy below

    actions_path = os.path.join(a.out, "actions.jsonl")
    summary = {}
    with open(actions_path, "w", encoding="utf-8", newline="\n") as afh:
        for tid in wanted:
            task = tasks.get(tid)
            if not task:
                continue
            task["_tasks_dir"] = a.tasks_dir
            log(f"=== task {tid} (threshold={task.get('threshold')}) ===")
            ep_best, ep_success, ep_steps = None, False, 0
            for ep in range(max(1, a.episodes)):
                pol = policy
                if pol is None:
                    kind = task.get("dummy", "")
                    if kind == "2048":
                        pol = Dummy2048()
                    elif kind == "form":
                        pol = DummyForm()
                    elif kind == "order":
                        pol = DummyOrder()
                    elif kind == "keys":
                        pol = DummyKeys()
                    elif kind == "recovery":
                        pol = DummyRecovery()
                    elif kind == "clipboard":
                        pol = DummyClipboard()
                    elif kind == "errorecover":
                        pol = DummyErrorRecover()
                    elif kind == "distractor":
                        pol = DummyDistractor()
                    elif kind == "form_desktop":
                        pol = DummyFormDesktop()
                    elif kind == "calc":
                        pol = DummyCalc()
                    elif kind == "table_sort":
                        pol = DummyTableSort()
                    elif kind == "text_edit":
                        pol = DummyTextEdit()
                    else:
                        pol = DummyScript(["KEY tab", "KEY enter"])
                rows, best, success = run_episode(
                    tid, task, pol, a.out, ep,
                    a.max_steps or int(task.get("max_steps", 30)))
                for r in rows:
                    r["task_id"] = tid
                    r["episode"] = ep
                    afh.write(json.dumps(r, ensure_ascii=False) + "\n")
                afh.flush()
                ep_steps = len(rows)
                if best is not None and (ep_best is None or best > ep_best):
                    ep_best = best
                ep_success = ep_success or success
                log(f"  ep{ep}: steps={len(rows)} best_reward={best} "
                    f"success={success}")
            summary[tid] = {"best_reward": ep_best,
                            "success": bool(ep_success),
                            "threshold": task.get("threshold"),
                            "steps": ep_steps,
                            "episodes": max(1, a.episodes)}
            with open(os.path.join(a.out, "reward.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(summary, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    # FIX 22/10 (MiMo): ghi loi ha tang ra file + danh dau task bi lo.
    # (task bi lo KHONG co episode trong actions.jsonl => khong lam nhieu
    #  diem, nhung nguoi doc result phai BIET la no khong do duoc.)
    if INFRA_ERRORS:
        with open(os.path.join(a.out, "infra_errors.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(INFRA_ERRORS, fh, ensure_ascii=False, indent=1)
        bad = sorted(set(e.get("task_id") for e in INFRA_ERRORS))
        for tid in bad:
            summary.setdefault(tid, {})["infra_error"] = True
        with open(os.path.join(a.out, "summary.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=1)
        log("[INFRA] %d episode bi BO QUA do loi ha tang; task bi anh huong: %s"
            % (len(INFRA_ERRORS), bad))
    log("DONE: %s" % json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
