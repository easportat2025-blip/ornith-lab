# -*- coding: utf-8 -*-
"""patch_think_and_vllm.py - theo chi danh user:
   "cho models nghi. nhieu k sao, tang max-new va co the dung vllm tang toc"

1) REASON_MAX 256 -> 512 (env ENV_REASON_MAX) trong cac kernel bench/rollout
2) harness.py: them duong VLLM (OpenAI-compatible server) - khi ENV_VLLM_URL
   duoc set thi dung HTTP thay vi load model local (RTX 96GB: model fit, vLLM nhanh)
3) sync ban inline cua harness.py vao 4 kernel desktop-bench + bump max-new.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------- 1) bump REASON_MAX trong kernel bench/rollout ----------
KERNELS = [
    "phase13-gui/kernel_bench_v21/bench_v15_kernel.py",
    "phase13-gui/kernel_bench_v22/bench_v15_kernel.py",
    "phase13-gui/kernel_bench_v155_v21/bench_v15_kernel.py",
    "phase13-gui/kernel_bench_v16_v21/bench_v15_kernel.py",
    "phase13-gui/kernel_rollout_v21/rollout_kernel.py",
    "phase13-gui/kernel_bench_3d_v21/bench3d_kernel.py",
    "phase13-gui/kernel_bench_3d_hard_v21/bench3d_kernel.py",
]
for p in KERNELS:
    fp = os.path.join(ROOT, p)
    if not os.path.exists(fp):
        continue
    s = io.open(fp, encoding="utf-8").read()
    o = s
    s = s.replace("REASON_MAX = 256",
                  "REASON_MAX = int(os.environ.get('ENV_REASON_MAX', '512'))")
    if s != o:
        io.open(fp, "w", encoding="utf-8", newline="\n").write(s)
        print("REASON_MAX->512:", p)

# ---------- 2) harness: duong vLLM ----------
HP = os.path.join(ROOT, "phase14-desktop", "harness.py")
s = io.open(HP, encoding="utf-8").read()

VLLM_CLASS = '''

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
            {"type": "text", "text": f"Task: {task}\\n"
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

'''
if "class VLLMPolicy" not in s:
    s = s.replace("def parse_action_v2(text):",
                  VLLM_CLASS.strip() + "\n\ndef parse_action_v2(text):", 1)
    print("them class VLLMPolicy vao harness.py")

# load_policy_model: uu tien VLLM khi co ENV_VLLM_URL
OLD_LOAD = '''def load_policy_model(adapter=None, base_dir=None):
    """Load base + optional LoRA exactly like bench v15 (lazy: only for --policy model).'''
NEW_LOAD = '''def load_policy_model(adapter=None, base_dir=None):
    """Load base + optional LoRA exactly like bench v15 (lazy: only for --policy model).

    Uu tien: neu ENV_VLLM_URL duoc set -> dung VLLM server (nhanh, phu hop RTX).
    """
    if os.environ.get("ENV_VLLM_URL"):
        log("dung VLLM server: %s" % os.environ["ENV_VLLM_URL"])
        return VLLMPolicy()'''
if OLD_LOAD in s and "class VLLMPolicy" in s:
    s = s.replace(OLD_LOAD, NEW_LOAD, 1)
    print("load_policy_model: uu tien VLLM")

io.open(HP, "w", encoding="utf-8", newline="\n").write(s)
try:
    compile(s, "x", "exec")
    print("harness compile OK")
except SyntaxError as e:
    print("harness LOI:", e.lineno, e.msg)

# ---------- 3) sync harness inline vao kernel desktop-bench ----------
sys_path = os.path.join(ROOT, "scripts", "sync_harness_into_kernel.py")
if os.path.exists(sys_path):
    import subprocess
    p = subprocess.run([sys.executable, sys_path], capture_output=True, text=True,
                       cwd=ROOT)
    print((p.stdout or p.stderr).strip()[:400])
