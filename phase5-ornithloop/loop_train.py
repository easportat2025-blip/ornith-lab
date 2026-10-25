"""Loop SFT Ornith tren Kaggle (T4/RTX): GEN bang vLLM (6.6x HF) + TRAIN bang
Unsloth. 5 game/wave, 2 waves. Cu 20 turns = 1 phase (adapter MOI = ma tran
moi, on-policy: gen tiep bang adapter moi nhat). Luu flywheel buffer+static
moi phase cho run sau (kernel_sources).
"""
import gc
import glob
import json
import os
import random
import shutil
import signal
import site
import subprocess
import sys
import time
import traceback

WORK = "/kaggle/working"
GAMES = os.path.join(WORK, "games")
RANK, ALPHA, DROPOUT, LR = 128, 128, 0.1, 1e-4
SEQ_LEN = 2048
TURNS_TOTAL = 500
TRAIN_EVERY = 20
TIME_BUDGET = 8 * 3600
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj",
           "gate_proj", "up_proj", "down_proj"]
TASKS = [
    ("py", "Maze thoat me cung random gioi han gio"),
    ("gd", "Pong Godot 2 nguoi, den 5 thang"),
    ("cs", "Unity enemy AI duoi theo player danh can chien"),
    ("bpy", "Oto lowpoly: than + 4 banh tru + cua so"),
    ("py", "Asteroids xoay 360 ban da vo manh nho"),
]
SYS_OF = {}
PY_SYS = ("You are a game code generator. Output ONE complete single-file "
          "python pygame program only, no explanation. Headless-safe "
          "(SDL_VIDEODRIVER=dummy). BAT BUOC: get_state() tra dict JSON "
          "gom score (so), alive (bool), actions (list string); "
          "do_action(action: str) tra dict. KHONG game-loop o top-level. "
          "GAME THAT CANG DAI CANG TOT (multi-file, system day du). "
          "Neu game lon, duoc tach nhieu file: moi file bat dau bang dong "
          "'# === FILE: ten_file ===' (file chinh la main.py, chua "
          "get_state/do_action; main import cac file khac).")
GD_SYS = ("You are a Godot 4 GDScript generator. Output ONE complete .gd "
          "script only, no explanation. BAT BUOC: extends Node, "
          "func get_state() -> Dictionary (gom score, alive, actions), "
          "func do_action(action: String) -> Dictionary. "
          "KHONG dung autoload, KHONG tai scene ngoai.")
CS_SYS = ("You are a Unity C# generator. Output ONE complete C# "
          "MonoBehaviour script only, no explanation. BAT BUOC: class ke "
          "thua MonoBehaviour, co void Start() va void Update().")
BPY_SYS = ("You are a Blender bpy generator. Output ONE complete python "
           "script using bpy only, no explanation. Assume default scene.")
ALPACA = ("Below is an instruction. Write a response.\n\n"
          "### Instruction:\n{}\n\n### Input:\n{}\n\n### Response:\n{}")

GEN_TOK = {"py": 768, "gd": 512, "cs": 512, "bpy": 512}

# 3 file preprocessor (s1 dataset thieu) - fallback viet tay khi mount thieu
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


def log(m):
    print("[loop] " + m, flush=True)


def sh(cmd, timeout=600):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        log(f"CMD loi {r.returncode}: {(r.stderr or '')[-300:]}")
        return None
    return r


def save_flywheel(buf, static_rows, tag):
    try:
        with open(os.path.join(WORK, f"fly_buf_{tag}.json"), "w") as f:
            json.dump(buf, f)
        with open(os.path.join(WORK, f"fly_static_{tag}.json"), "w") as f:
            json.dump(static_rows, f)
        log(f"flywheel saved {tag}")
    except Exception as e:
        log(f"flywheel loi: {e}")


def sft_train(texts, tag, max_steps, tokenizer, base_dir, pdb, acc,
              use_bf16):
    """Train 1 adapter MOI (seed moi = ma tran moi) roi nap lai vLLM."""
    from unsloth import FastLanguageModel
    from datasets import Dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments
    import inspect
    import torch
    new_seed = random.SystemRandom().randint(1, 10**9)
    vllm_free()
    gc.collect()
    torch.cuda.empty_cache()
    m, _ = FastLanguageModel.from_pretrained(
        model_name=base_dir, max_seq_length=SEQ_LEN,
        dtype=None, load_in_4bit=True)
    m = FastLanguageModel.get_peft_model(
        m, r=RANK, target_modules=TARGETS, lora_alpha=ALPHA,
        lora_dropout=DROPOUT, bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=new_seed, use_rslora=False)
    log(f"train {tag}: adapter MOI seed={new_seed} texts={len(texts)} "
        f"steps={max_steps}")
    ds = Dataset.from_dict({"text": texts})
    sft_kw = dict(
        model=m, train_dataset=ds,
        args=TrainingArguments(
            per_device_train_batch_size=pdb,
            gradient_accumulation_steps=acc,
            warmup_steps=10,
            max_steps=max_steps,
            learning_rate=LR,
            fp16=not use_bf16, bf16=use_bf16,
            logging_steps=10, optim="adamw_8bit",
            weight_decay=0.01, lr_scheduler_type="linear",
            seed=random.SystemRandom().randint(1, 10**9),
            output_dir=os.path.join(WORK, "out"),
            save_steps=200, save_total_limit=2))
    sig = inspect.signature(SFTTrainer.__init__).parameters
    if "processing_class" in sig:
        sft_kw["processing_class"] = tokenizer
    elif "tokenizer" in sig:
        sft_kw["tokenizer"] = tokenizer
    for k, v in [("dataset_text_field", "text"),
                 ("max_seq_length", SEQ_LEN),
                 ("packing", False), ("dataset_num_proc", 2)]:
        if k in sig:
            sft_kw[k] = v
    SFTTrainer(**sft_kw).train()
    adir = os.path.join(WORK, f"loop_adapt_{tag}")
    m.save_pretrained(adir)
    del m
    gc.collect()
    # Soup incremental tren CPU roi XOA dir phase (disk working 20GB)
    try:
        from safetensors.torch import load_file
        sd = load_file(os.path.join(adir, "adapter_model.safetensors"),
                       device="cpu")
        n = _SOUP["n"]
        if _SOUP["acc"] is None:
            _SOUP["acc"] = {k: v.float() for k, v in sd.items()}
        else:
            for k in _SOUP["acc"]:
                _SOUP["acc"][k] = (_SOUP["acc"][k] * n + sd[k].float()) \
                    / (n + 1)
        _SOUP["n"] = n + 1
        del sd
        gc.collect()
        log(f"soup incremental n={_SOUP['n']}")
    except Exception as e:
        log(f"soup-inc loi: {e}")
    latest = os.path.join(WORK, "loop_adapt_latest")
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(adir, latest)
    shutil.rmtree(adir, ignore_errors=True)
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    vllm_init(latest)  # on-policy: gen tiep bang adapter moi
    log(f"xong train {tag}, adapter -> latest (soup n={_SOUP['n']})")
    return latest


SEED0 = random.SystemRandom().randint(1, 10**9)
random.seed(SEED0)
T0 = time.time()
VLLM = {}
_SOUP = {"acc": None, "n": 0}


def vllm_free():
    if "llm" in VLLM:
        try:
            del VLLM["llm"]
        except Exception:
            pass
        VLLM.pop("llm", None)
    gc.collect()
    try:
        import torch
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        a = torch.cuda.memory_allocated() / 2**30
        r = torch.cuda.memory_reserved() / 2**30
        log(f"vram sau free: allocated={a:.1f}G reserved={r:.1f}G")
    except Exception as e:
        log(f"vram free loi: {e}")


def vllm_init(lora_path=None):
    vllm_free()
    # RTX Blackwell: sampler flashinfer chet -> dung sampler torch.
    # Tat inductor remote-cache (spam redis + cham init).
    os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    os.environ["TORCHINDUCTOR_FX_GRAPH_CACHE"] = "0"
    import torch
    vram = torch.cuda.get_device_properties(0).total_memory / 2**30
    from vllm import LLM
    big = vram >= 20
    free, total = torch.cuda.mem_get_info()
    util = min(0.9, max(0.4, (free - 6 * 2**30) / total))
    log(f"vram free={free / 2**30:.1f}/{total / 2**30:.0f}G -> "
        f"util={util:.2f}")
    kw = dict(model=VLLM["base"],
              dtype="bfloat16" if torch.cuda.is_bf16_supported()
              else "float16",
              gpu_memory_utilization=util,
              max_model_len=2048 if not big else 4096,
              max_num_seqs=8 if not big else 16,
              enforce_eager=True,  # cudagraph sap tren sm_100+cu128
              enable_lora=True, max_loras=2, max_lora_rank=128)
    if not big:
        # T4 16GB: can 4bit (da chung minh o smoke)
        kw["quantization"] = "bitsandbytes"
    else:
        # RTX 95GB: bf16 nguyen con (bnb kernel thieu sm_100 Blackwell)
        log("RTX: nap bf16 day du, khong quant")
    try:
        VLLM["llm"] = LLM(**kw)
    except Exception as e:
        log(f"vllm_init loi: {e} -> thu lai khong LoRA")
        kw.pop("enable_lora", None)
        kw.pop("max_loras", None)
        kw.pop("max_lora_rank", None)
        VLLM["llm"] = LLM(**kw)
    VLLM["lora"] = lora_path
    log(f"vllm san sang (lora={lora_path})")


def vllm_gen(prompts, max_tok, temp):
    from vllm import SamplingParams
    sp = SamplingParams(max_tokens=max_tok, temperature=temp, top_p=0.9)
    lreq = None
    if VLLM.get("lora"):
        try:
            from vllm.lora.request import LoRARequest
            lreq = LoRARequest("cur", 1, VLLM["lora"])
        except Exception as e:
            log(f"LoRA req loi (gen base): {e}")
    outs = VLLM["llm"].generate(prompts, sp, lora_request=lreq)
    return [o.outputs[0].text for o in outs]


def strip_code(code):
    import re
    m = re.search(r"```(?:python|csharp|gdscript|py|cs|gd)?\s*\n(.*?)```",
                  code, re.S)
    code = (m.group(1).strip() if m else code.strip())
    lines = code.split("\n")
    keep = ("import ", "from ", "def ", "class ", "@", "#", "extends ",
            "func ", "using ", "namespace ", "[", "public ", "private ",
            "var ", "const ", "\"\"\"", "'''")
    for k, ln in enumerate(lines):
        if ln.strip().startswith(keep):
            return "\n".join(lines[k:])
    return code


def main():
    os.makedirs(GAMES, exist_ok=True)
    # --- 1. unsloth stack (train) tu wheels dataset ---
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("unsloth-") and f.endswith(".whl")
               for f in files):
            wheels = root
            break
    assert wheels, "thieu wheels unsloth"
    sh(f"pip install --no-index --no-deps --find-links {wheels} "
       f"unsloth unsloth_zoo trl bitsandbytes")
    import torch
    # --- 2. vllm stack (gen) tu cpu-fetch kernel_sources ---
    SRC = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("vllm-") and f.endswith(".whl") for f in files):
            SRC = root
            break
    if SRC is None:
        log("kernel_sources khong mount. Cay /kaggle/input:")
        try:
            for r, ds, fs in os.walk("/kaggle/input"):
                log(f"  {r} dirs={len(ds)} files={len(fs)}")
        except Exception as e:
            log(f"walk loi: {e}")
        # T4 online: tu tai closure (RTX offline thi chet ro o day)
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=8).close()
            online = True
        except Exception:
            online = False
        if not online:
            raise SystemExit("offline + khong thay wheels vllm")
        log("T4 online -> tu tai closure vllm (4-5 phut)")
        SRC = "/tmp/wheels_dl"
        os.makedirs(SRC, exist_ok=True)
        sh(f"pip download --dest {SRC} vllm==0.26.0", timeout=1800)
        sh(f"pip download --no-deps --dest {SRC} --index-url "
           f"https://wheels.astral.sh/simple/cu128/ flash-attn",
           timeout=1200)
        import urllib.request as _u
        _cu = ("https://github.com/vllm-project/vllm/releases/download/"
               "v0.26.0/vllm-0.26.0+cu129-cp38-abi3-manylinux_2_28_x86_64.whl")
        try:
            _u.urlretrieve(_cu, os.path.join(SRC, os.path.basename(_cu)))
        except Exception as e:
            log(f"tai cu129 loi: {e}")
        sh(f"rm -f {SRC}/torch*.whl {SRC}/torchaudio* {SRC}/torchvision*")
    assert SRC, "thieu wheels vllm (check kernel_sources cpu-fetch)"
    W = "/tmp/wmin"
    if os.path.isdir(W):
        shutil.rmtree(W)
    os.makedirs(W)
    KILL = ("torch-", "torchaudio", "torchvision", "triton-", "numpy",
            "numba", "scipy", "tokenspeed", "tilelang", "quack_kernels",
            "cuda_", "cuda_bindings", "cuda_core", "cuda_pathfinder",
            "cuda_tile", "cuda_toolkit", "cutlass", "pynvvideocodec",
            "opencv_python", "agent_detector", "humming_kernels",
            "transformers", "tokenizers", "safetensors", "huggingface_hub")
    try:
        from packaging.version import Version
    except Exception:
        Version = None

    def _wkey(b):
        p = b.split("-")
        nm = p[0].lower().replace("_", "-")
        vs = p[1] if len(p) > 1 else "0"
        try:
            return (nm, Version(vs) if Version else vs)
        except Exception:
            return (nm, vs)

    best = {}
    for f in glob.glob(os.path.join(SRC, "*.whl")):
        b = os.path.basename(f)
        if b.startswith("nvidia_") or b.startswith(KILL):
            continue
        if b.startswith("vllm-") and "cu129" not in b:
            continue
        nm, vv = _wkey(b)
        if nm not in best or vv > best[nm][1]:
            best[nm] = (f, vv)
    for f, _ in best.values():
        os.symlink(f, os.path.join(W, os.path.basename(f)))
    log(f"wheels: {len(best)} goi (da dedup)")
    req = os.path.join(W, "all.txt")
    with open(req, "w") as fh:
        fh.write("\n".join(sorted(glob.glob(os.path.join(W, "*.whl")))))
    sh(f"pip install --no-index --no-deps -r {req}", timeout=2400)
    fa = glob.glob(os.path.join(W, "flash_attn*.whl"))
    if fa:
        sh(f"pip install --no-index --no-deps '{fa[0]}'")
    nvd = glob.glob("/usr/local/lib/python3.13/dist-packages/nvidia/*/lib")
    if nvd:
        os.environ["LD_LIBRARY_PATH"] = (
            ":".join(sorted(set(nvd))) + ":" +
            os.environ.get("LD_LIBRARY_PATH", ""))
    import vllm  # noqa: F401
    log("vllm " + vllm.__version__ + " san sang")
    log("torch=" + torch.__version__)

    # --- 3. base: 1 dir day du, hoac rap tu 4 shard datasets (RTX) ---
    def find_shards():
        found = {}
        for r, _, fs in os.walk("/kaggle/input"):
            for f in fs:
                if f.startswith("model-0000") and f.endswith(".safetensors"):
                    found[f] = r
        return found

    orn = None
    for _ in range(6):
        basedirs = [os.path.dirname(p) for p in
                    sum([[os.path.join(r, f) for f in fs
                          if f == "model.safetensors"]
                         for r, _, fs in os.walk("/kaggle/input")], [])]
        orn = next((d for d in basedirs
                    if "ornith" in d or "ornbase" in d), None)
        if orn:
            break
        if len(find_shards()) >= 4:
            break
        log("doi mount base (20s)...")
        time.sleep(20)
    if orn is None:
        # Rap 4 shards -> /tmp/ornbase bang symlink (0 copy, 0 disk)
        shards = find_shards()
        if len(shards) >= 4:
            orn = "/tmp/ornbase"
            os.makedirs(orn, exist_ok=True)
            for f, d in sorted(shards.items()):
                dst = os.path.join(orn, f)
                if not os.path.exists(dst):
                    os.symlink(os.path.join(d, f), dst)
            # File nho: TU s1 (dir co index.json), liet ke ro rang
            NEED = ["model.safetensors.index.json", "config.json",
                    "tokenizer.json", "tokenizer_config.json", "vocab.json",
                    "chat_template.jinja", "preprocessor_config.json",
                    "processor_config.json", "video_preprocessor_config.json"]
            s1dir = None
            for r, _, fs in os.walk("/kaggle/input"):
                if "model.safetensors.index.json" in fs:
                    s1dir = r
                    log(f"s1 dir={r} files={len(fs)}")
                    break
            if s1dir:
                for f in NEED:
                    src = os.path.join(s1dir, f)
                    dst = os.path.join(orn, f)
                    if os.path.isfile(src):
                        if not os.path.exists(dst):
                            os.symlink(src, dst)
                    elif f in PREPROC:
                        with open(dst, "w") as fh:
                            json.dump(PREPROC[f], fh)
                        log(f"viet tay fallback: {f}")
                    else:
                        log(f"THIEU tren mount: {f}")
            log(f"rap base tu {len(shards)} shards -> {orn}")
            log(f"/tmp/ornbase co: {sorted(os.listdir(orn))}")
    if orn is None:
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=8).close()
            online = True
        except Exception:
            online = False
        log(f"khong thay base qua mount, online={online}")
        if not online:
            raise SystemExit("offline + khong thay base (check 4 shard "
                             "datasets ornbase-s1..s4)")
        sh("pip install -q huggingface_hub")
        from huggingface_hub import snapshot_download
        orn = "/tmp/ornbase"
        for attempt in range(4):
            try:
                snapshot_download(
                    "ornith-ai/Ornith-1.5-9B", local_dir=orn,
                    allow_patterns=["*.safetensors", "*.json",
                                    "*.jinja", "*.model", "LICENSE*"],
                    max_workers=4)
                break
            except Exception as e:
                log(f"tai base lan {attempt + 1} loi: {e} -> doi 120s")
                time.sleep(120)
        else:
            raise SystemExit("het mang + mount")
    log(f"base ornith={orn}")
    VLLM["base"] = orn

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(orn)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    base_dir = orn

    from unsloth import FastLanguageModel
    props = torch.cuda.get_device_properties(0)
    vram_gb = props.total_memory / 2**30
    use_bf16 = torch.cuda.is_bf16_supported()
    if vram_gb < 20:
        PDB, ACC = 4, 2
    else:
        PDB, ACC = 8, 2
    log(f"GPU={props.name} vram={vram_gb:.0f}G bf16={use_bf16} "
        f"batch {PDB}x{ACC}")

    # --- 4. godot/blender ---
    import importlib.util
    godot_bin, blender_bin = None, None
    try:
        gd = os.path.join(WORK, "godot")
        os.makedirs(gd, exist_ok=True)
        if not os.path.isfile(os.path.join(gd, "godot")):
            sh("wget -q https://github.com/godotengine/godot/releases/"
               "download/4.3-stable/Godot_v4.3-stable_linux.x86_64.zip "
               f"-O {gd}/godot.zip", timeout=1200)
            sh(f"unzip -o -j {gd}/godot.zip -d {gd}", timeout=300)
            for root, _, files in os.walk(gd):
                for f in files:
                    if "Godot" in f and "64" in f:
                        shutil.move(os.path.join(root, f),
                                    os.path.join(gd, "godot"))
                        break
        gb = os.path.join(gd, "godot")
        if os.path.isfile(gb):
            os.chmod(gb, 0o755)
            r = sh(f"{gb} --version", timeout=60)
            if r and "4.3" in (r.stdout or ""):
                godot_bin = gb
    except Exception as e:
        log(f"godot khong san sang (static-only): {e}")
    for root, _, files in os.walk("/kaggle/input"):
        for f in files:
            if f.endswith(".tar.xz") and "blender" in f:
                bd = os.path.join(WORK, "blender")
                os.makedirs(bd, exist_ok=True)
                sh(f"tar -xf {os.path.join(root, f)} -C {bd}", timeout=600)
                for r2, _, fs in os.walk(bd):
                    if "blender" in fs:
                        p = os.path.join(r2, "blender")
                        os.chmod(p, 0o755)
                        r = sh(f"{p} --background --python-expr "
                               f"\"import bpy; print('BL-OK')\"", timeout=180)
                        if r and "BL-OK" in (r.stdout or ""):
                            blender_bin = p
                            break
                break
    log(f"godot={godot_bin} blender={blender_bin}")
    UNITY_APIS = ["transform", "GetComponent", "Instantiate", "Rigidbody",
                  "Collider", "Input", "Time", "Debug", "GameObject",
                  "Vector3", "Camera", "AudioSource", "Animator"]

    # --- 5. vLLM engine (gen) ---
    vllm_init()
    SYS = {"py": PY_SYS, "gd": GD_SYS, "cs": CS_SYS, "bpy": BPY_SYS}

    def gen_wave(temp):
        items = [(eng, spec) for eng, spec in TASKS]
        prompts = [ALPACA.format(SYS[e], s, "") for e, s in items]
        texts = vllm_gen(prompts, 2048, temp)
        return [strip_code(t) for t in texts]

    alive, STATIC_ROWS, TOOL_USED = {}, [], {}

    def _tmo(signum, frame):
        raise TimeoutError("probe qua 60s")

    def split_files(code):
        """Tach code nhieu file theo marker '# === FILE: ten ==='.
        Khong marker -> {'main.py': code}."""
        import re
        parts = re.split(r"^# === FILE:\s*(\S+)\s*===\s*$", code, flags=re.M)
        if len(parts) < 3:
            return {"main.py": code}
        out = {}
        for k in range(1, len(parts), 2):
            out[parts[k]] = parts[k + 1]
        return out or {"main.py": code}

    def use_tool(i):
        """Moi lan CHAY code (probe/import/godot/blender) = 1 luot.
        Write/edit file FREE. Toi da 5 luot/game."""
        TOOL_USED[i] = TOOL_USED.get(i, 0) + 1
        ok = TOOL_USED[i] <= 5
        if not ok:
            log(f"game{i} het budget tool (5)")
        return ok

    def verify_game(eng, spec, i, code):
        """Tra 'alive' / 'static' / ('fail', err)."""
        try:
            if eng == "py":
                if not use_tool(i):
                    return ("fail", "het budget tool (5)")
                files = split_files(code)
                gdir = os.path.join(GAMES, f"g{i}")
                os.makedirs(gdir, exist_ok=True)
                for name, txt in files.items():
                    safe = os.path.basename(name) or "main.py"
                    open(os.path.join(gdir, safe), "w",
                         encoding="utf-8").write(txt)
                log(f"game{i} (py) gen {len(code)} chars "
                    f"{len(files)} files tool={TOOL_USED.get(i, 0)}/5")
                main_name = ("main.py" if "main.py" in files
                             else sorted(files)[0])
                fp = os.path.join(gdir, os.path.basename(main_name))
                if gdir not in sys.path:
                    sys.path.insert(0, gdir)
                s = importlib.util.spec_from_file_location(f"g{i}", fp)
                mod = importlib.util.module_from_spec(s)
                signal.signal(signal.SIGALRM, _tmo)
                signal.alarm(60)
                try:
                    s.loader.exec_module(mod)
                    for _ in range(3):
                        st = mod.get_state()
                        assert isinstance(st, dict) and "score" in st \
                            and "alive" in st and "actions" in st
                    # Cua playability: nuoc di dau phai song + tra dict
                    acts0 = st.get("actions") or ["noop"]
                    res0 = mod.do_action(acts0[0])
                    assert isinstance(res0, dict), "do_action khong tra dict"
                    assert res0.get("alive", True) is not False, \
                        "chet ngay nuoc dau"
                finally:
                    signal.alarm(0)
                alive[i] = {"mod": mod, "spec": spec, "score": 0}
                log(f"game{i} (py) OK actions={st['actions']}")
                return "alive"
            elif eng == "gd":
                log(f"game{i} (gd) gen {len(code)} chars")
                fp = os.path.join(GAMES, f"game{i}.gd")
                open(fp, "w", encoding="utf-8").write(code)
                score_gd, note = 0, "chua check"
                run_gd = bool(godot_bin) and use_tool(i)
                try:
                    if run_gd:
                        r = sh(f"timeout 60 {godot_bin} --headless "
                               f"--check-only --script {fp}", timeout=120)
                        out_all = ((r.stdout or "") + (r.stderr or "")) \
                            if r else ""
                        if (r and r.returncode == 0
                                and "ERROR" not in out_all[:2000]):
                            score_gd, note = 4, "godot parse OK"
                        else:
                            score_gd, note = 1, "godot bao loi"
                    if ("extends" in code and "func get_state" in code
                            and "func do_action" in code):
                        score_gd = max(score_gd, 3)
                        note += "+API du"
                except Exception as e2:
                    note = f"check crash: {e2}"
                STATIC_ROWS.append([f"{GD_SYS}\nTask: {spec}", code,
                                    round(score_gd / 5, 3)])
                log(f"game{i} (gd) diem={score_gd}/5 ({note})")
                return "static"
            elif eng == "cs":
                log(f"game{i} (cs) gen {len(code)} chars")
                fp = os.path.join(GAMES, f"Game{i}.cs")
                open(fp, "w", encoding="utf-8").write(code)
                s_cs = 0
                try:
                    s_cs += 1 if ("MonoBehaviour" in code
                                   and "class" in code) else 0
                    s_cs += 1 if ("void Start" in code
                                   and "void Update" in code) else 0
                    s_cs += 1 if (code.count("{") == code.count("}")
                                   and "{" in code) else 0
                    hit = sum(1 for a in UNITY_APIS if a in code)
                    s_cs += 2 if hit >= 5 else (1 if hit >= 3 else 0)
                except Exception as e2:
                    log(f"game{i} (cs) cham crash: {e2}")
                STATIC_ROWS.append([f"{CS_SYS}\nTask: {spec}", code,
                                    round(min(s_cs, 5) / 5, 3)])
                log(f"game{i} (cs) diem={min(s_cs, 5)}/5")
                return "static"
            elif eng == "bpy":
                log(f"game{i} (bpy) gen {len(code)} chars")
                fp = os.path.join(GAMES, f"scene{i}.py")
                open(fp, "w", encoding="utf-8").write(code)
                ok_b = False
                bb = blender_bin if use_tool(i) else None
                if bb:
                    png = os.path.join(WORK, f"_r{i}.png")
                    full = (code + f"\nimport bpy\nbpy.context.scene."
                            f"render.filepath = '{png}'\n"
                            f"bpy.ops.render.render(write_still=True)\n")
                    open(os.path.join(WORK, f"_b{i}.py"), "w").write(full)
                    r = sh(f"{blender_bin} --background --python "
                           f"{os.path.join(WORK, f'_b{i}.py')}",
                           timeout=240)
                    ok_b = (r is not None and r.returncode == 0
                            and os.path.exists(png))
                else:
                    import ast as _ast
                    _ast.parse(code)
                    ok_b = True
                if ok_b:
                    STATIC_ROWS.append([f"{BPY_SYS}\nTask: {spec}", code,
                                        1.0])
                log(f"game{i} (bpy) {'OK' if ok_b else 'HONG'}")
                return "static" if ok_b else ("fail", "bpy render hong")
            return ("fail", "engine la")
        except Exception as e:
            tb = traceback.format_exc().strip().split("\n")[-3:]
            log(f"game{i} ({eng}) HON (bo qua): {e} | {tb}")
            return ("fail", str(e)[:200])

    ntrained = 0
    for wave in range(3):
        temp = [0.3, 0.7, 1.0][wave]
        try:
            codes = gen_wave(temp)
        except Exception as e:
            log(f"wave {wave} gen loi: {e}")
            continue
        fails = []
        for j, (eng, spec) in enumerate(TASKS):
            r = verify_game(eng, spec, wave * 10 + j, codes[j])
            if isinstance(r, tuple):
                fails.append((eng, spec, wave * 10 + j, r[1], codes[j]))
        for rnd in range(2):
            reps = [(e, s, ii, er, oc) for (e, s, ii, er, oc) in fails
                    if e in ("py", "bpy")][:4]
            if not reps:
                break
            log(f"wave {wave} repair vong {rnd}: sua {len(reps)} game")
            try:
                rp = [ALPACA.format(
                    SYS[e] + " CHI OUTPUT CODE, KHONG GIAI THICH.",
                    f"Task: {s}\nCode cu (LOI {er}):\n{oc[:1500]}\n"
                    f"Sua lai cho chay duoc.",
                    "") for (e, s, ii, er, oc) in reps]
                rcodes = [strip_code(t) for t in vllm_gen(rp, 1536, 0.5)]
                fails = []
                for k, ((e, s, ii, er, oc), nc) in enumerate(
                        zip(reps, rcodes)):
                    rr = verify_game(e, s, 200 + wave * 20 + rnd * 5 + k, nc)
                    if isinstance(rr, tuple):
                        fails.append((e, s, ii, rr[1], nc))
            except Exception as e:
                log(f"repair loi: {e}")
                break
        if len(STATIC_ROWS) > ntrained + 1:
            stexts = [ALPACA.format(si, "", so) + tokenizer.eos_token
                      for si, so, rw in STATIC_ROWS]
            mrw = sum(r for _, _, r in STATIC_ROWS) / len(STATIC_ROWS)
            log(f"wave {wave}: HOC ngay {len(stexts)} static "
                f"mean_rw={mrw:.3f}")
            sft_train(stexts, f"w{wave}",
                      max(30, len(stexts) // 4),
                      tokenizer, base_dir, PDB, ACC, use_bf16)
            save_flywheel([], STATIC_ROWS, f"w{wave}")
            ntrained = len(STATIC_ROWS)
        if ((alive and len(STATIC_ROWS) >= 3) or len(alive) >= 2
                or len(STATIC_ROWS) >= 10):
            break
        log(f"wave {wave} yeu (alive={len(alive)} "
            f"static={len(STATIC_ROWS)}), gen them")
    if not alive and len(STATIC_ROWS) < 3:
        raise SystemExit("khong co game nao song (da thu 3 waves)")

    # --- 6. TURNS (play batch bang vLLM) + train phase (Unsloth) ---
    buf, phase = [], 0

    def train_phase():
        nonlocal phase
        good = [b for b in buf if b["reward"] > 0]
        pool = len(good) + len(STATIC_ROWS)
        mean_rw = (sum(b["reward"] for b in buf) / max(len(buf), 1))
        log(f"phase {phase}: buffer={len(buf)} good={len(good)} "
            f"static={len(STATIC_ROWS)} pool={pool} mean_rw={mean_rw:.3f}")
        if pool < 16:
            log("it mau (pool<16), bo qua phase")
            return
        texts = [ALPACA.format(
            f"Choi game. State: {b['state']}\nActions: {b['actions']}",
            "", b["action"]) + tokenizer.eos_token for b in good]
        for si, so, rw in STATIC_ROWS:
            texts.append(ALPACA.format(si, "", so) + tokenizer.eos_token)
        log(f"phase {phase}: texts play={len(good)} "
            f"static={len(STATIC_ROWS)}")
        adir = sft_train(texts, f"p{phase}", max(50, len(texts) // 16),
                         tokenizer, base_dir, PDB, ACC, use_bf16)
        json.dump({"phase": phase, "n_buf": len(buf), "n_good": len(good)},
                  open(os.path.join(adir, f"phase_info_p{phase}.json"),
                       "w"))
        save_flywheel(buf, STATIC_ROWS, f"p{phase}")
        phase += 1

    for turn in range(TURNS_TOTAL):
        if time.time() - T0 > TIME_BUDGET:
            log("het gio, dung turns")
            break
        ids_alive = sorted(alive)
        prompts, states = [], []
        for i in ids_alive:
            g = alive[i]
            try:
                st = g["mod"].get_state()
                acts = st.get("actions", ["noop"]) or ["noop"]
                prompts.append(ALPACA.format(
                    f"Choi game. State: {json.dumps(st)[:800]}",
                    f"Chon 1 action trong {acts}", ""))
                states.append((i, st, acts))
            except Exception as e:
                buf.append({"turn": turn, "task": i, "state": {},
                            "actions": [], "action": "ERR",
                            "reward": -5.0})
                log(f"turn {turn} game{i} loi state: {e}")
        if prompts:
            try:
                raw = vllm_gen(prompts, 32, 0.3)
            except Exception as e:
                log(f"turn {turn} vllm_gen loi: {e}")
                raw = [""] * len(prompts)
            for (i, st, acts), txt in zip(states, raw):
                g = alive[i]
                try:
                    act = txt.strip().split("\n")[0][:40]
                    if act not in acts:
                        act = acts[0]
                    res = g["mod"].do_action(act)
                    res = res if isinstance(res, dict) else {"info": str(res)}
                    sc = float(res.get("score", st.get("score", 0)))
                    rw = (sc - g["score"]) * 1.0
                    rw += 0.1 if res.get("alive", True) else -5.0
                    g["score"] = sc
                    buf.append({"turn": turn, "task": i, "state": st,
                                "actions": acts, "action": act,
                                "reward": rw})
                except Exception as e:
                    buf.append({"turn": turn, "task": i, "state": {},
                                "actions": [], "action": "ERR",
                                "reward": -5.0})
                    log(f"turn {turn} game{i} loi: {e}")
        if (turn + 1) % TRAIN_EVERY == 0:
            train_phase()
        if turn % 20 == 0:
            log(f"turn {turn}/{TURNS_TOTAL} buf={len(buf)} "
                f"elapsed={int(time.time() - T0)}s")
    json.dump({"turns_done": turn + 1, "buf": len(buf), "phases": phase},
              open(os.path.join(WORK, "loop_state.json"), "w"))
    try:
        from safetensors.torch import save_file
        if _SOUP["n"] >= 1 and _SOUP["acc"]:
            sdir = os.path.join(WORK, "loop_soup")
            os.makedirs(sdir, exist_ok=True)
            save_file({k: v.to(torch.float16)
                       for k, v in _SOUP["acc"].items()},
                      os.path.join(sdir, "adapter_model.safetensors"))
            cfg = os.path.join(WORK, "loop_adapt_latest",
                               "adapter_config.json")
            if os.path.isfile(cfg):
                shutil.copy(cfg, os.path.join(sdir, "adapter_config.json"))
            log(f"SOUP DONE {_SOUP['n']} adapters -> {sdir}")
        else:
            log("soup 0 adapters")
    except Exception as e:
        log(f"soup loi (bo qua): {e}")
    log(f"LOOP DONE turns={turn + 1} buf={len(buf)} phases={phase}")


if __name__ == "__main__":
    main()
