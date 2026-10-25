"""Bench end-to-end v2: transformers THUAN (khong Unsloth) + adapter robust load.

v1 (kernel version 1) that bai: PeftModel tren model Unsloth -> forward patch
bo qua LoRA (prose output). v2: khong import unsloth ty nao; PeftModel chuan;
sau moi chien luoc load adapter -> probe (gen thu) phai ra CLICK x y moi nhan.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

WORK = "/kaggle/working"
ORN = "/tmp/ornbase"
FIX = "/tmp/fixtures"
OUT = os.path.join(WORK, "bench_out")

SYS = ("You are a GUI agent. Look at the screenshot and the task, then "
       "output ONE action line only.\n"
       "Actions: CLICK x y (x,y integers 0..1000 normalized to image "
       "width/height) | TYPE text (type into the focused field) | "
       "KEY name (press a key, e.g. enter) | DONE (task is complete). "
       "No explanation.")

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
            msgs, tokenize=False, add_generation_prompt=True)
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


def run_task(name, html, task, policy, max_steps=10):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto("file:///" + os.path.join(FIX, html).replace("\\", "/"))
    page.wait_for_timeout(250)
    trace = []
    win = False
    for t in range(max_steps):
        shot = os.path.join(OUT, f"{name}_s{t:02d}.png")
        page.screenshot(path=shot)
        t0 = time.time()
        ans, act = policy.act(shot, task, t)
        dt = time.time() - t0
        kind = act[0] if act else None
        arg = act[1] if act else None
        if kind == "click":
            x = max(1, min(1278, int(round(arg[0] / 1000.0 * 1280))))
            y = max(1, min(718, int(round(arg[1] / 1000.0 * 720))))
            page.mouse.click(x, y)
            res = f"clicked ({x},{y})"
        elif kind == "type":
            page.keyboard.type(str(arg)[:40])
            res = "typed %r" % str(arg)[:30]
        elif kind == "key":
            keys = {"enter": "Enter", "tab": "Tab", "space": "Space",
                    "backspace": "Backspace", "escape": "Escape"}
            k = keys.get(str(arg).lower(), str(arg))
            page.keyboard.press(k)
            res = f"key {k}"
        elif kind == "done":
            page.evaluate("window.__goal_reached = "
                          "(window.__task_ok === true)")
            res = "DONE"
        else:
            res = "WAIT (khong parse duoc)"
        page.wait_for_timeout(120)
        goal = bool(page.evaluate("window.__goal_reached === true"))
        tok = bool(page.evaluate("window.__task_ok === true"))
        trace.append({"t": t, "raw": ans, "act": act, "res": res,
                      "goal": goal, "task_ok": tok, "dt": round(dt, 2)})
        log(f"[{name}] t{t} out={ans.strip()[:40]!r} -> {res} "
            f"goal={goal} task_ok={tok} ({dt:.1f}s)")
        if goal:
            win = True
            page.screenshot(path=os.path.join(OUT, f"{name}_win.png"))
            break
    tok = bool(page.evaluate("window.__task_ok === true"))
    if not win:
        log(f"[{name}] het buoc: task_ok={tok}")
    browser.close()
    pw.stop()
    log(f"[{name}] KET QUA: {'WIN' if win else 'FAIL'} "
        f"sau {len(trace)} buoc")
    return win, trace


def main():
    t0 = time.time()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log("bench v14 (internet-check + probe-changed)")
    sh("pip uninstall -y torchao")
    import torch
    log(f"gpu: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'} "
        f"x{torch.cuda.device_count()}")
    if not check_internet():
        log("=> DUNG SOM: khong co internet -> khong the cai playwright. "
            "Bat Internet cho kernel nay (UI) roi push lai.")
        return
    assemble_base()
    if not setup_playwright():
        log("=> DUNG SOM: playwright setup that bai (internet/apt?).")
        return
    import transformers
    log(f"transformers {transformers.__version__}")
    try:
        import peft
        log(f"peft {peft.__version__}")
    except ImportError:
        sh("pip install peft")
    proc = fix_processor()
    model = load_model()
    lora = find_lora()
    assert lora, "khong thay adapter (dataset ornith-gui-lora)"
    log(f"lora: {lora}")
    probe_img = make_probe_image()
    model, used = load_adapter_robust(
        model, lora, proc, probe=(probe_img, "Click the blue square."))
    log(f"ADAPTER STRATEGY DUNG: {used}")
    log(f"model load xong t={time.time() - t0:.0f}s")

    policy = Policy(model, proc)
    results = {}
    traces = {}
    for name, html, task in TASKS:
        win, tr = run_task(name, html, task, policy)
        results[name] = win
        traces[name] = tr
    with open(os.path.join(WORK, "bench_result.json"), "w") as f:
        json.dump({"results": results, "adapter_strategy": used,
                   "traces": traces, "t_sec": time.time() - t0}, f)
    log(f"BENCH XONG: {results} strategy={used} t={time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
