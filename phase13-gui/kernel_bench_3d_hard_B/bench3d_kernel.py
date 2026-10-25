"""Bench v15 kernel: REASONING 256 + offline browsers + B15 suite.

Nen tren bench_gui_kaggle.py (v14 bench da chay THANH CONG online). Khac biet:
  + SYS/format v20: duoc THINK ngan, dong CUOI bat buoc `ACTION: ...`.
  + decode `max_new_tokens=REASON_MAX=256` (24 token = tran cat thinking).
  + parser v2 (dong ACTION: CUOI -> fallback bare legacy) + do prose_leak,
    mean_new; ghi per-step vao b15_result.json.
  + playwright OFFLINE tu dataset hhjiji/ornith-offline-browsers qua
    setup_playwright_offline.py (gate V1-V6, fail LOUD) — internet OFF.
  + suite B15 tu dataset hhjiji/ornith-gui-bench-v15 (mount bench_v15/tasks/):
    goi module `bench_v15`/`checker` (render_instruction + check); khong thay
    suite -> fallback 3 task v14 (click_green/counter5/login_done) de khong
    mat run.
  + adapter: find_lora() (attach DUNG 1 adapter dataset moi kernel version:
    v18 baseline = hhjiji/ornith-gui-lora; v20 = hhjiji/ornith-gui-lora-v20).
"""
import glob
import json
import os

# --- ENABLE_THINKING: prompt co render think rong (enable_thinking=False) thi
# model (train action-only) emit thang action, het prose leak (failure C1).
# Mac dinh True de so sanh duoc voi baseline B15 27.8% (do voi thinking ON).
ENABLE_THINKING = os.environ.get("ORNI_THINK", "1") != "0"

import re
import subprocess
import sys
import time

WORK = "/kaggle/working"
ORN = "/tmp/ornbase"
FIX = "/tmp/fixtures"
OUT = os.path.join(WORK, "bench_out")

SYS = ("You are a GUI agent. Look at the screenshot and the task, then "
       "decide the next action.\n"
       "You MAY reason briefly first. Reply format:\n"
       "THINK: <one or two short sentences about what you see and what "
       "to do>\n"
       "ACTION: <CLICK x y | TYPE text | KEY name | DONE>\n"
       "Rules: the LAST line MUST start with 'ACTION:'; x,y are integers "
       "0..1000 normalized to image width/height; never write anything "
       "after the ACTION line; if the task is already complete, "
       "output ACTION: DONE.")

PREPROC = {
    "preprocessor_config.json": {
        "size": {"longest_edge": 16777216, "shortest_edge": 65536},
        "patch_size": 16, "temporal_patch_size": 2, "merge_size": 2,
        "image_mean": [0.5, 0.5, 0.5], "image_std": [0.5, 0.5, 0.5],
        "processor_class": "Qwen3VLProcessor",
        "image_processor_type": "Qwen2VLImageProcessorFast"},
    "processor_config.json": {
        "image_processor": {
            "do_convert_rgb": True, "do_normalize": True,
            "do_rescale": True, "do_resize": True,
            "image_mean": [0.5, 0.5, 0.5],
            "image_processor_type": "Qwen2VLImageProcessor",
            "image_std": [0.5, 0.5, 0.5], "merge_size": 2,
            "patch_size": 16, "resample": 3,
            "rescale_factor": 0.00392156862745098,
            "size": {"longest_edge": 16777216, "shortest_edge": 65536},
            "temporal_patch_size": 2},
        "processor_class": "Qwen3VLProcessor",
        "video_processor": {
            "do_convert_rgb": True, "do_normalize": True,
            "do_rescale": True, "do_resize": True,
            "do_sample_frames": True, "fps": 2,
            "image_mean": [0.5, 0.5, 0.5],
            "image_std": [0.5, 0.5, 0.5], "max_frames": 768,
            "merge_size": 2, "min_frames": 4, "patch_size": 16,
            "resample": 3, "rescale_factor": 0.00392156862745098,
            "return_metadata": False,
            "size": {"longest_edge": 25165824, "shortest_edge": 4096},
            "temporal_patch_size": 2,
            "video_processor_type": "Qwen3VLVideoProcessor"}},
    "video_preprocessor_config.json": {
        "size": {"longest_edge": 25165824, "shortest_edge": 4096},
        "patch_size": 16, "temporal_patch_size": 2, "merge_size": 2,
        "image_mean": [0.5, 0.5, 0.5], "image_std": [0.5, 0.5, 0.5],
        "processor_class": "Qwen3VLProcessor",
        "video_processor_type": "Qwen3VLVideoProcessor"},
}

FIXTURES = {}

FIXTURES["click_button.html"] = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Color Buttons</title>
<style>
  body { font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f4f4f4; }
  header { display: flex; justify-content: space-between; align-items: center; }
  h1 { font-size: 22px; margin: 0; }
  #clicked { font-size: 16px; color: #333; }
  .grid { display: grid; grid-template-columns: repeat(3, 180px); gap: 18px; margin-top: 36px; }
  button { height: 64px; border: 0; border-radius: 10px; font-size: 16px; color: #fff; cursor: pointer; }
  #btn-red { background: #d0342c; } #btn-green { background: #2e9e44; }
  #btn-blue { background: #1e6fd9; } #btn-yellow { background: #c9a10a; color: #222; }
  #btn-purple { background: #7a3bbd; } #btn-orange { background: #d97a1e; }
  #reset { background: #555; height: 36px; margin-top: 28px; width: 120px; }
</style></head>
<body>
<header><h1>Color Button Panel</h1><span id="clicked">Clicked: 0</span></header>
<div class="grid">
  <button id="btn-red" data-label="Red button">Red</button>
  <button id="btn-green" data-label="Green button">Green</button>
  <button id="btn-blue" data-label="Blue button">Blue</button>
  <button id="btn-yellow" data-label="Yellow button">Yellow</button>
  <button id="btn-purple" data-label="Purple button">Purple</button>
  <button id="btn-orange" data-label="Orange button">Orange</button>
</div>
<button id="reset" data-label="Reset button">Reset</button>
<script>
  window.__goal_reached = false;
  window.__task_ok = false;
  window.__clicks = 0;
  var Q = new URLSearchParams(location.search);
  var reqDone = Q.get('req') === 'done';
  window.__target = Q.get('target') || 'btn-green';
  document.querySelectorAll('.grid button').forEach(function (b) {
    b.addEventListener('click', function () {
      window.__clicks += 1;
      document.getElementById('clicked').textContent = 'Clicked: ' + window.__clicks;
      if (b.id === window.__target) {
        window.__task_ok = true;
        if (!reqDone) window.__goal_reached = true;
      }
    });
  });
  document.getElementById('reset').addEventListener('click', function () {
    window.__clicks = 0;
    document.getElementById('clicked').textContent = 'Clicked: 0';
  });
</script>
</body>
</html>
"""

FIXTURES["counter.html"] = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Counter</title>
<style>
  body { font-family: Arial, sans-serif; margin: 0; padding: 80px 0; background: #faf7f0; text-align: center; }
  #count { font-size: 72px; font-weight: bold; color: #333; margin: 24px 0; }
  button { width: 90px; height: 90px; font-size: 40px; border: 0; border-radius: 50%; cursor: pointer; margin: 0 16px; color: #fff; }
  #plus { background: #2e9e44; }
  #minus { background: #d0342c; }
  #goal { margin-top: 36px; font-size: 16px; color: #666; }
</style></head>
<body>
<div id="count" data-label="Counter display">0</div>
<button id="minus" data-label="Minus button">&minus;</button>
<button id="plus" data-label="Plus button">+</button>
<div id="goal">Goal: reach 5 and press Done</div>
<script>
  window.__goal_reached = false;
  window.__task_ok = false;
  var Q = new URLSearchParams(location.search);
  var target = parseInt(Q.get('goal') || '5', 10);
  var reqDone = Q.get('req') === 'done';
  var n = parseInt(Q.get('start') || '0', 10);
  function render() { document.getElementById('count').textContent = String(n); }
  document.getElementById('goal').textContent =
    'Goal: reach ' + target + (reqDone ? ', then say DONE' : '');
  document.getElementById('plus').addEventListener('click', function () {
    n += 1; render();
    if (n >= target) { window.__task_ok = true; if (!reqDone) window.__goal_reached = true; }
  });
  document.getElementById('minus').addEventListener('click', function () { n -= 1; render(); });
  render();
</script>
</body>
</html>
"""

FIXTURES["login_form.html"] = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Login Form</title>
<style>
  body { font-family: Arial, sans-serif; margin: 0; padding: 60px; background: #eef1f5; }
  .card { width: 380px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 12px rgba(0,0,0,.12); }
  h1 { font-size: 20px; margin: 0 0 24px; }
  label { display: block; font-size: 13px; color: #444; margin-bottom: 6px; }
  input[type=text], input[type=password] { width: 100%; box-sizing: border-box; height: 40px; margin-bottom: 18px; border: 1px solid #bbb; border-radius: 6px; padding: 0 10px; font-size: 15px; }
  .row { display: flex; align-items: center; gap: 8px; margin-bottom: 22px; font-size: 14px; }
  #submit { width: 100%; height: 42px; border: 0; border-radius: 6px; background: #1e6fd9; color: #fff; font-size: 16px; cursor: pointer; }
  #msg { text-align: center; margin-top: 16px; font-size: 14px; color: #2e9e44; }
  input:focus, button:focus { outline: 3px solid #1e6fd9; outline-offset: 1px; }
</style></head>
<body>
<div class="card">
  <h1>Sign in</h1>
  <label for="username">Username</label>
  <input id="username" type="text" data-label="Username field" autocomplete="off">
  <label for="password">Password</label>
  <input id="password" type="password" data-label="Password field">
  <div class="row"><input id="remember" type="checkbox" data-label="Remember me checkbox"><span>Remember me</span></div>
  <button id="submit" data-label="Sign in button">Sign in</button>
  <div id="msg"></div>
</div>
<script>
  window.__goal_reached = false;
  window.__task_ok = false;
  var Q = new URLSearchParams(location.search);
  var EU = Q.get('eu') || 'admin';
  var EP = Q.get('ep') || '1234';
  var reqDone = Q.get('req') === 'done';
  function try_login() {
    var u = document.getElementById('username').value;
    var p = document.getElementById('password').value;
    if (u === EU && p === EP) {
      document.getElementById('msg').textContent = 'Welcome, ' + u + '!';
      document.getElementById('msg').style.color = '#2e9e44';
      window.__task_ok = true;
      if (!reqDone) window.__goal_reached = true;
    } else {
      document.getElementById('msg').textContent = 'Sai tai khoan hoac mat khau';
      document.getElementById('msg').style.color = '#d0342c';
    }
  }
  document.getElementById('submit').addEventListener('click', try_login);
  document.getElementById('password').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') try_login();
  });
</script>
</body>
</html>
"""


TASKS = [
    ("click_green", "click_button.html?target=btn-green",
     "Click the green button."),
    ("counter5", "counter.html?goal=5",
     "Increment the counter to 5."),
    ("login_done", "login_form.html?eu=admin&ep=1234&req=done",
     "Log in with username admin and password 1234. "
     "When you are done, say DONE."),
]


def log(m):
    print("[bench] " + str(m), flush=True)


def sh(cmd, timeout=1800):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
        return None
    return r


def check_internet(tries=6, wait=10):
    import socket
    for i in range(tries):
        try:
            s = socket.create_connection(("pypi.org", 443), timeout=6)
            s.close()
            log(f"INTERNET OK (lan thu {i + 1})")
            return True
        except Exception as e:
            log(f"INTERNET chua duoc (lan {i + 1}/{tries}): "
                f"{str(e)[:120]}")
            time.sleep(wait)
    log("INTERNET OFF sau nhieu lan thu")
    return False


def assemble_base():
    cand = []
    for root, dirs, _ in os.walk("/kaggle/input"):
        for d in dirs:
            if d.startswith("ornbase-s"):
                cand.append(os.path.join(root, d))
    if not cand:
        for root, _, files in os.walk("/kaggle/input"):
            if any(f.startswith("model-") and f.endswith(".safetensors")
                   for f in files) and "adapter_config.json" not in files:
                cand.append(root)
    cand = sorted(set(cand))
    assert cand, "khong thay ornbase-s*"
    log(f"base dirs: {cand}")
    os.makedirs(ORN, exist_ok=True)
    got = set()
    for base in cand:
        for root, _, files in os.walk(base):
            for f in files:
                if f.endswith((".safetensors", ".json", ".jinja", ".model")):
                    src = os.path.join(root, f)
                    dst = os.path.join(ORN, f)
                    if f in got or os.path.exists(dst):
                        got.add(f)
                        continue
                    try:
                        os.link(src, dst)
                    except Exception:
                        import shutil
                        shutil.copy(src, dst)
                    got.add(f)
    for f in ("adapter_config.json", "adapter_model.safetensors"):
        p = os.path.join(ORN, f)
        if os.path.exists(p):
            os.remove(p)
            log(f"xoa {f} khoi ORN")
    cfg = json.load(open(os.path.join(ORN, "config.json")))
    assert cfg.get("model_type") == "qwen3_5", "ORN config khong phai qwen3_5"
    idx = os.path.join(ORN, "model.safetensors.index.json")
    miss = []
    if os.path.exists(idx):
        wm = json.load(open(idx)).get("weight_map", {})
        miss = sorted({v for v in wm.values()
                       if not os.path.exists(os.path.join(ORN, v))})
    if miss:
        log(f"THIEU SHARDS: {miss}")
    assert not miss, "thieu model shards (dataset ornbase thieu?)"
    log(f"base: {len(os.listdir(ORN))} files -> {ORN}")


def find_lora():
    for root, _, files in os.walk("/kaggle/input"):
        if "adapter_config.json" in files:
            return root
    return None


def fix_processor():
    import transformers
    from transformers import AutoProcessor
    cands = [n for n in dir(transformers)
             if re.match(r"Qwen3.*(VL)?Processor$", n)]
    log(f"processor classes: {cands}")
    order = ["Qwen3VLProcessor", "Qwen3_5Processor", "Qwen3_5VLProcessor"]
    for n in cands:
        if n not in order:
            order.append(n)
    try:
        proc = AutoProcessor.from_pretrained(ORN)
        if hasattr(proc, "image_processor"):
            log(f"processor truc tiep OK: {type(proc).__name__}")
            return proc
    except Exception as e:
        log(f"AutoProcessor loi: {str(e)[:160]}")
    for pclass in order:
        for fname, blob in PREPROC.items():
            b = json.loads(json.dumps(blob))
            if b.get("processor_class"):
                b["processor_class"] = pclass
            with open(os.path.join(ORN, fname), "w") as fh:
                json.dump(b, fh)
        try:
            proc = AutoProcessor.from_pretrained(ORN)
            if hasattr(proc, "image_processor"):
                log(f"processor fallback OK: {pclass}")
                return proc
        except Exception as e:
            log(f"{pclass} loi: {str(e)[:120]}")
    raise SystemExit("khong tao duoc processor")


def setup_playwright():
    os.makedirs(FIX, exist_ok=True)
    for name, html in FIXTURES.items():
        with open(os.path.join(FIX, name), "w", encoding="utf-8") as fh:
            fh.write(html)
    try:
        import playwright  # noqa
    except ImportError:
        for i in range(3):
            if sh("pip install playwright"):
                break
            log(f"pip playwright that bai lan {i + 1}/3")
            time.sleep(10)
    try:
        import playwright  # noqa
    except ImportError:
        return False
    r = sh("python -m playwright install chromium --with-deps", timeout=900)
    if r is None:
        r = sh("python -m playwright install chromium", timeout=900)
    if r is None:
        log("playwright install chromium THAT BAI")
        return False
    log("playwright setup xong")
    return True


def parse_click(text):
    t = (text or "").strip()
    m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                  t, re.I)
    if not m:
        m = re.search(r"(\d{1,4})\s*[,;\s]\s*(\d{1,4})", t)
    if not m:
        return None
    return [int(m.group(1)), int(m.group(2))]


def parse_action(text):
    t = (text or "").strip()
    m = re.search(r"CLICK\s*[\(\[]?\s*(\d{1,4})\s*[,;\s]\s*(\d{1,4})",
                  t, re.I)
    if m:
        return ("click", [int(m.group(1)), int(m.group(2))])
    m = re.search(r"TYPE\s+(.+)", t, re.I)
    if m:
        return ("type", m.group(1).strip())
    m = re.search(r"\bKEY\s+([A-Za-z]+)", t, re.I)
    if m:
        return ("key", m.group(1).lower())
    if re.search(r"\bDONE\b", t, re.I):
        return ("done", None)
    return None


def make_probe_image():
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (768, 512), (240, 240, 242))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 768, 48], fill=(52, 58, 70))
    d.rectangle([284, 196, 484, 316], fill=(30, 111, 217))
    p = os.path.join(WORK, "probe.png")
    img.save(p)
    return p


def load_model():
    import torch
    import transformers
    dt = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    cls = None
    for name in ("Qwen3_5ForConditionalGeneration",
                 "AutoModelForImageTextToText", "AutoModelForCausalLM"):
        cls = getattr(transformers, name, None)
        if cls is not None:
            log(f"model class: {name}")
            break
    assert cls, "khong tim thay model class qwen3_5"
    model = cls.from_pretrained(ORN, dtype=dt, device_map="auto")
    model.eval()
    log(f"model load xong: {type(model).__name__} "
        f"peft_auto={hasattr(model, 'peft_config')}")
    return model


class Policy:
    def __init__(self, model, processor):
        self.model = model
        self.processor = processor

    def act(self, shot, task, t):
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
            gen = self.model.generate(**inputs, max_new_tokens=16,
                                      do_sample=False)
        ans = self.processor.batch_decode(
            gen[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True)[0]
        return ans.strip(), parse_action(ans)


def unwrap(model):
    try:
        if hasattr(model, "peft_config"):
            base = getattr(model, "base_model", None)
            inner = getattr(base, "model", None)
            if inner is not None:
                return inner
    except Exception:
        pass
    return model


def concretize_lora(lora):
    import shutil
    from safetensors import safe_open
    from peft import PeftConfig
    cfg = PeftConfig.from_pretrained(lora)
    tm = cfg.target_modules
    if isinstance(tm, (list, set, tuple)):
        return lora, tm
    f = os.path.join(lora, "adapter_model.safetensors")
    keys = []
    with safe_open(f, framework="pt", device="cpu") as sf:
        for k in sf.keys():
            if ".lora_A" in k or ".lora_B" in k:
                keys.append(k)
    mods = sorted({k.split(".lora_")[0].replace("base_model.model.", "", 1)
                   for k in keys})
    if not mods:
        return lora, None
    fixed = os.path.join(WORK or "/tmp", "lora_fixed")
    if os.path.isdir(fixed):
        shutil.rmtree(fixed)
    shutil.copytree(lora, fixed)
    pc = json.load(open(os.path.join(fixed, "adapter_config.json")))
    pc["target_modules"] = mods
    with open(os.path.join(fixed, "adapter_config.json"), "w") as fh:
        json.dump(pc, fh)
    log(f"concretize target_modules: {len(mods)} modules "
        f"(vd {mods[0]})")
    return fixed, mods


def probe_generate(model, proc, probe):
    shot, task = probe
    p = Policy(model, proc)
    with_txt = p.act(shot, task, 0)
    txt, act = with_txt
    return txt, act, (act is not None and act[0] == "click")


def load_adapter_robust(model, lora, proc,
                        probe=("probe.png", "Click the blue square.")):
    from peft import PeftModel
    base_txt, base_act, base_ok = probe_generate(model, proc, probe)
    log(f"probe BASE: ok={base_ok} out={base_txt[:60]!r}")

    def s1():
        return PeftModel.from_pretrained(model, lora)

    def s2():
        m = model
        m.load_adapter(lora)
        return m

    fixed, mods = concretize_lora(lora)

    def s3():
        return PeftModel.from_pretrained(model, fixed)

    strategies = [("PeftModel", s1), ("transformers.load_adapter", s2),
                  ("PeftModel+concrete target_modules", s3)]
    cur = model
    used = None
    for name, fn in strategies:
        try:
            cand = fn()
        except Exception as e:
            log(f"strategy {name} LOI: {str(e)[:180]}")
            continue
        txt, pt, ok = probe_generate(cand, proc, probe)
        if ok:
            log(f"strategy {name}: PARSE OK out={txt[:60]!r}")
            used = name + " (parse)"
            cur = cand
            break
        if txt != base_txt:
            log(f"strategy {name}: khac base -> NHAN (probe con prose) "
                f"out={txt[:60]!r}")
            used = name + " (changed)"
            cur = cand
            break
        log(f"strategy {name}: giong base (LoRA vo hieu) -> go")
        cur = unwrap(cand)
    return cur, used


REASON_MAX = 256
B15_RESULT = os.path.join(WORK, "b15_result.json")

THINK_RX = re.compile(r"^\s*THINK\s*:", re.I)
ACTION_LINE_RX = re.compile(r"^\s*ACTION\s*:\s*(.*)$", re.I)
ACTION_RX = re.compile(r"^\s*(?:CLICK|TYPE|KEY|DONE)\b", re.I)


def _split_verb(s):
    parts = (s or "").strip().split(None, 1)
    if not parts:
        return None, ""
    return parts[0], parts[1] if len(parts) > 1 else ""


def _norm_action(verb, rest):
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
    for i, l in enumerate(lines):
        m = ACTION_LINE_RX.match(l)
        if m:
            v, a = _norm_action(*_split_verb(m.group(1)))
            if v:
                act, mode, act_i = (v, a), "action", i
    if act is None:
        for i, l in enumerate(lines):
            m = ACTION_RX.match(l)
            if m:
                verb, rest = _split_verb(l.strip())
                v, a = _norm_action(verb, rest)
                if v:
                    act, mode, act_i = (v, a), "legacy", i
                    break
    limit = act_i if act_i is not None else len(lines)
    extra_actions = sum(1 for l in lines[:limit] if ACTION_LINE_RX.match(l))
    prose = [l for l in lines[:limit]
             if not THINK_RX.match(l) and not ACTION_LINE_RX.match(l)]
    think = [l for l in lines[:limit] if THINK_RX.match(l)]
    return {"action": act, "mode": mode, "act_str": act_to_str(act),
            "prose_lines": len(prose), "think_lines": len(think),
            "think_chars": sum(len(x) for x in think),
            "extra_actions": extra_actions}


def parse_action_v2(text):
    po = parse_output(text)
    a = po["action"]
    if not a:
        return None
    v, arg = a
    if v == "CLICK":
        return ("click", arg)
    if v == "TYPE":
        return ("type", arg)
    if v == "KEY":
        return ("key", arg)
    return ("done", None)


class PolicyV2:
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
        self.last = {"n_new": n_new}
        return ans.strip(), parse_action_v2(ans)




# ================= BENCH 3D GROUNDING =================
def load_eps():
    """Doc episodes tu dataset: <ds>/bench3d.jsonl + <ds>/shots/*.png"""
    base = None
    for root, _dirs, files in os.walk("/kaggle/input"):
        if "bench3d.jsonl" in files:
            base = root
            break
    assert base, "khong thay bench3d.jsonl trong /kaggle/input"
    rows = [json.loads(l) for l in
            open(os.path.join(base, "bench3d.jsonl"), encoding="utf-8")
            if l.strip()]
    # anh: thu muc shots/ can dat dataset, dung lai thu muc dataset
    imgdir = os.path.join(base, "shots")
    if not os.path.isdir(imgdir):
        for root, _dirs, files in os.walk(base):
            if "e00000.png" in files:
                imgdir = root
                break
    eps = []
    for r in rows:
        p = os.path.join(imgdir, os.path.basename(r["image"]))
        if not os.path.exists(p):
            continue
        eps.append({"image": p, "instruction": r["instruction"],
                    "bbox": r["bbox"], "color": r.get("color"),
                    "shape": r.get("shape")})
    log("episodes: %d (image dir %s)" % (len(eps), imgdir))
    return eps


def hit(point, bbox):
    x, y = point
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def main_3d():
    t0 = time.time()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log("BENCH 3D grounding: click tren render Blender, bbox-hit checker")
    sh("pip uninstall -y torchao")
    import torch
    log("gpu: " + (torch.cuda.get_device_name(0)
                   if torch.cuda.is_available() else "NONE"))
    assemble_base()
    import transformers
    proc = fix_processor()
    model = load_model()
    lora = find_lora()
    assert lora, "khong thay adapter"
    log("lora: " + lora)
    probe = make_probe_image()
    model, used = load_adapter_robust(model, lora, proc,
                                      probe=(probe, "Click the blue square."))
    log("ADAPTER STRATEGY: " + used)
    policy = PolicyV2(model, proc)

    eps = load_eps()
    results = []
    n_parse = 0
    n_prose = 0
    for i, ep in enumerate(eps):
        try:
            ans, act = policy.act(ep["image"], ep["instruction"])
        except Exception as e:
            log("ep %d loi: %s" % (i, e))
            continue
        po = parse_output(ans)
        pt = parse_click(ans)
        ok = bool(pt) and hit(pt, ep["bbox"])
        if pt:
            n_parse += 1
        if po["prose_lines"] > 0:
            n_prose += 1
        results.append({"i": i, "instruction": ep["instruction"],
                        "color": ep["color"], "shape": ep["shape"],
                        "click": pt, "bbox": ep["bbox"], "hit": ok,
                        "mode": po["mode"], "prose_lines": po["prose_lines"],
                        "raw": ans[:200]})
        log("[3d %d] %-28s click=%s hit=%s" %
            (i, ep["instruction"][:28], pt, ok))
    n = max(len(results), 1)
    n_hit = sum(1 for r in results if r["hit"])
    by_color = {}
    for r in results:
        d = by_color.setdefault(r["color"] or "?", [0, 0])
        d[0] += 1
        d[1] += 1 if r["hit"] else 0
    summary = {"n": len(results), "n_hit": n_hit, "hit_rate": n_hit / n,
               "parse_rate": n_parse / n, "prose_leak_rate": n_prose / n,
               "by_color": {k: "%d/%d" % (v[1], v[0])
                            for k, v in by_color.items()},
               "adapter": lora, "adapter_strategy": used,
               "t_sec": round(time.time() - t0, 1)}
    with open(os.path.join(WORK, "bench3d_result.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"summary": summary, "episodes": results}, fh,
                  ensure_ascii=False, indent=1)
    log("BENCH3D XONG: hit %d/%d = %.3f parse=%.3f t=%.0fs" %
        (n_hit, len(results), summary["hit_rate"], summary["parse_rate"],
         summary["t_sec"]))


main = main_3d

# FIX: thieu lenh goi main() -> script chay nhung khong lam gi
main()
