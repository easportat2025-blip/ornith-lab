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
RANK, ALPHA, DROPOUT, LR = 128, 128, 0.0, 1e-4
SEQ_LEN = 2048
INJECT_HELP = True  # luoi cuu cuoi cua harness; False = model tu lo 100%
TURNS_TOTAL = 500
TRAIN_EVERY = 20
TIME_BUDGET = 8 * 3600
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj",
           "gate_proj", "up_proj", "down_proj"]
FALLBACK = [
    ("py", "Game thu thap xu me cung 10x10, quai ruot duoi, 3 mang, "
     "cang sau cang nhanh"),
    ("py", "Game ban may bay: ne dan, ha 20 dich, 3 loai dan, boss cuoi"),
    ("py", "Game dua xe top-down 3 vong, 4 cua kho, tinh gio, va cham "
     "tru toc"),
    ("gd", "Pong Godot 2 nguoi, den 5 thang, toc do bong tang dan"),
    ("cs", "Unity enemy AI duoi theo player danh can chien, 3 loai dich"),
    ("bpy", "Oto lowpoly: than + 4 banh tru + cua so, xoay banh xe"),
    ("bpy", "Nhan vat Anime don gian: dau + than + tay chan, armature, "
     "animation vung tay 12 frames"),
    ("py", "Game xep hinh roi 7 khoi, xoay/lat, combo x4, tang toc"),
]
PROPOSE_SYS = ("Ban la tho xay game/3D tu do. De xuat 5 nhiem vu KHO, "
               "moi dong 1 nhiem vu theo dung format:\n"
               "ENGINE: py|gd|cs|bpy | REQ: <nhiem vu cu the, kho that su>\n"
               "GAME = pygame choi duoc (get_state/do_action). "
               "bpy = Blender mesh+armature+animation. "
               "Chi output 5 dong, khong giai thich.")
SYS_OF = {}
PY_SYS = ("You are a game code generator. Output ONE complete single-file "
          "python pygame program only, no explanation. Headless-safe "
          "(SDL_VIDEODRIVER=dummy). BAT BUOC: get_state() tra dict JSON "
          "gom score (so), alive (bool), actions (list string); "
          "do_action(action: str) tra dict. KHONG game-loop o top-level. "
          "GAME THAT CANG DAI CANG TOT (multi-file, system day du). "
          "Neu game lon, tach nhieu file: moi file bat dau bang dong "
          "'# === FILE: ten_file ===' (file chinh la main.py, chua "
          "get_state/do_action; main import cac file khac). "
          "KHUNG XUONG BAT BUOC (giu nguyen ten ham, dien logic game vao):\n"
          "import pygame\n"
          "player = [5, 5]\ncoins = [[2, 2], [7, 7]]\n"
          "score = [0]\nalive = [True]\n"
          "def get_state():\n"
          "    return {'score': score[0], 'alive': alive[0], "
          "'actions': ['up', 'down', 'left', 'right']}\n"
          "def do_action(action):\n"
          "    d = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), "
          "'right': (1, 0)}.get(action, (0, 0))\n"
          "    player[0] += d[0]; player[1] += d[1]\n"
          "    if tuple(player) in [tuple(c) for c in coins]:\n"
          "        coins.remove(list(player)); score[0] += 10\n"
          "    if not (0 <= player[0] < 10 and 0 <= player[1] < 10):\n"
          "        alive[0] = False\n"
          "    return {'score': score[0], 'alive': alive[0], 'info': 'ok'}\n")
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
              use_bf16, prev=None):
    """Train 1 adapter MOI (seed moi = ma tran moi) roi nap lai vLLM.
    prev: adapter warm-start (khoi tao LoRA tu day thay vi random)."""
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
    if prev and os.path.isfile(os.path.join(prev,
                                            "adapter_model.safetensors")):
        try:
            from safetensors.torch import load_file
            pfile = os.path.join(prev, "adapter_model.safetensors")
            sd = load_file(pfile, device="cpu")
            sd2 = {}
            for k, v in sd.items():
                k2 = (k.replace(".lora_A.weight", ".lora_A.default.weight")
                      .replace(".lora_B.weight", ".lora_B.default.weight"))
                sd2[k2] = v
            best = 0
            for name, cand in (("default", sd2), ("raw", sd)):
                _, un = m.load_state_dict(cand, strict=False)
                ok = len(cand) - len(un)
                log(f"warm-start {name}: khop {ok}/{len(cand)}")
                best = max(best, ok)
                if ok == len(cand):
                    break
            if best == 0:
                try:
                    log("warm-key own=" + list(m.state_dict())[0] +
                        " | file=" + list(sd)[0])
                except Exception:
                    pass
            log(f"warm-start file {os.path.getsize(pfile)} bytes")
            del sd
        except Exception as e5:
            log(f"warm-start loi: {e5}")
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
    if _SOUP["acc"] is not None and _SOUP["n"] % 5 == 0:
        try:
            from safetensors.torch import save_file
            sdir = os.path.join(WORK, "loop_soup")
            os.makedirs(sdir, exist_ok=True)
            save_file({k: v.to(torch.float16)
                       for k, v in _SOUP["acc"].items()},
                      os.path.join(sdir, "adapter_model.safetensors"))
            cfg = os.path.join(latest, "adapter_config.json")
            if os.path.isfile(cfg):
                shutil.copy(cfg, os.path.join(sdir, "adapter_config.json"))
            log(f"soup checkpoint -> disk (n={_SOUP['n']})")
        except Exception as e4:
            log(f"soup save loi: {e4}")
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
    util = min(0.9, max(0.20, (free - 8 * 2**30) / total))
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
        log(f"vllm_init loi: {e} -> do lai voi util thap hon")
        gc.collect()
        try:
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
        except Exception:
            pass
        free2, total2 = torch.cuda.mem_get_info()
        kw["gpu_memory_utilization"] = min(
            0.9, max(0.15, (free2 - 8 * 2**30) / total2))
        log(f"retry util={kw['gpu_memory_utilization']:.2f}")
        try:
            VLLM["llm"] = LLM(**kw)
        except Exception as e2:
            log(f"vllm_init loi 2: {e2} -> bo LoRA")
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
    drop = re.compile(
        r"^\s*(Task\s*:|Code cu|Sua lai|VERDICT|SCORE|REQUEST|TRACK\s*:|"
        r"CRITIQUE|Here|Sure|Note\s*:|Explanation|Actually|Let me|"
        r"I'll|The user|This code|We need|Done|da xong|hoan thanh|"
        r"xong roi|All done)\b", re.I)
    lines = [ln for ln in code.split("\n")
             if not drop.match(ln)
             and not ln.strip().startswith("```")
             and "=== END OF FILE ===" not in ln]
    keep = ("import ", "from ", "def ", "class ", "@", "extends ",
            "func ", "using ", "namespace ", "[", "public ", "private ",
            "var ", "const ", '"""', "'''")
    for k, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith(keep) or s.startswith("# === FILE:"):
            return "\n".join(lines[k:])
    return "\n".join(lines)


def salvage_py(txt):
    """Bo dan dong lam loi cu phap (van xuoi lot vao) cho den khi compile duoc."""
    for _ in range(15):
        try:
            compile(txt, "<s>", "exec")
            return txt
        except SyntaxError as e:
            ls = txt.split("\n")
            i = (e.lineno or 1) - 1
            if not (0 <= i < len(ls)):
                return txt
            ls.pop(i)
            txt = "\n".join(ls)
    return txt


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
    # --- warm-start: adapter v10 (soup) lam diem xuat phat ---
    prev_adapter, prev_src = None, None
    cands = []
    for root, _, files in os.walk("/kaggle/input"):
        if "adapter_model.safetensors" in files:
            cands.append(root)
    pref = ([c for c in cands if "loop_soup" in c.lower()]
            or [c for c in cands if "b5" in c.lower()]
            or [c for c in cands if "b10" in c.lower()] or cands)
    if pref:
        prev_adapter = os.path.join(WORK, "prev")
        prev_src = pref[0]
        os.makedirs(prev_adapter, exist_ok=True)
        for f in os.listdir(prev_src):
            if os.path.isfile(os.path.join(prev_src, f)):
                shutil.copy(os.path.join(prev_src, f), prev_adapter)
    log(f"warm-start adapter={prev_adapter} nguon={prev_src}")

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
                bd = "/tmp/blender"
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
    vllm_init(prev_adapter)
    SYS = {"py": PY_SYS, "gd": GD_SYS, "cs": CS_SYS, "bpy": BPY_SYS}

    def gen_wave(temp, items):
        prompts = [ALPACA.format(SYS[e], s, "") for e, s in items]
        texts = vllm_gen(prompts, 2048, temp)
        return [strip_code(t) for t in texts]

    def propose_tasks(temp):
        """B tu ra de (5 nhiem vu). Hong -> dung FALLBACK."""
        import re
        try:
            raw = vllm_gen([ALPACA.format(PROPOSE_SYS, "", "")], 512,
                           temp)[0]
            items = []
            for ln in raw.strip().split("\n"):
                m = re.search(r"ENGINE:\s*(py|gd|cs|bpy)\s*\|\s*REQ:\s*(.+)",
                              ln, re.I)
                if m and len(m.group(2).strip()) >= 10:
                    items.append((m.group(1).lower(), m.group(2).strip()
                                  [:300]))
            if len(items) >= 3:
                return (items + FALLBACK)[:5]
        except Exception as e:
            log(f"propose loi: {e}")
        return list(FALLBACK[:5])

    B_TOOL_SYS = (
        "Ban la tho xay game/3D. Nem code bang TOOL CALL, moi luot 1 tool:\n"
        "<tool_call>\nwrite_file main.py\n(noi dung code)\n</tool_call>\n"
        "hoac <tool_call>\nrun python -m py_compile main.py\n</tool_call>\n"
        "hoac <tool_call>\ndone da xong\n</tool_call>\n"
        "write_file(path + code) mien phi. run(cmd python) toi da 5 lan, "
        "chay trong thu muc game, tra output thuc. Ket thuc bang done.\n"
        "Game pygame PHAI giu khung xuong: get_state() tra dict score/alive/"
        "actions, do_action(str) tra dict. Khong game-loop o top. "
        "Moi lan CHI 1 tool_call, khong giai thich ngoai tool call.\n"
        "Goi y vong lap: write_file -> run py_compile -> sua -> run import "
        "thu get_state -> done.")

    PRE_TOOL = ("Khung xuong main.py bat buoc (giu nguyen ten ham):\n"
                "player = [5, 5]\nscore = [0]\nalive = [True]\n"
                "def get_state():\n"
                "    return {'score': score[0], 'alive': alive[0], "
                "'actions': ['up', 'down', 'left', 'right']}\n"
                "def do_action(action):\n"
                "    # ...logic game cua ban...\n"
                "    return {'score': score[0], 'alive': alive[0]}\n")

    def agent_build(eng, spec, i, temp):
        """B tu xay bang tool call that: write_file (free) + run (<=5)
        + done. Tra ve main.py cuoi cung."""
        import re
        gdir = os.path.join(GAMES, f"g{i}")
        os.makedirs(gdir, exist_ok=True)
        hist = ALPACA.format(
            B_TOOL_SYS, f"ENGINE: {eng}\nTask: {spec}\n\n{PRE_TOOL}", "")
        runs, last_code, last_run_out = 0, None, None
        for step in range(8):
            out = vllm_gen([hist], 1536, temp)[0]
            calls = re.findall(r"<tool_call>\s*(.*?)</tool_call>", out, re.S)
            resp = []
            if not calls:
                if "def get_state" in out:
                    txt = strip_code(out)
                    open(os.path.join(gdir, "main.py"), "w",
                         encoding="utf-8").write(txt)
                    last_code = txt
                    resp.append("(thieu the tool_call) da luu main.py")
                else:
                    resp.append("KHONG thay tool_call. Dung cu phap "
                                "<tool_call> ... </tool_call>")
            for c in (calls or [])[:2]:
                head, _, body = c.strip().partition("\n")
                p = head.split(None, 1)
                name = p[0].lower() if p else ""
                arg = p[1].strip() if len(p) > 1 else ""
                if name == "write_file" and arg:
                    txt = strip_code(body) if body.strip() else ""
                    if txt:
                        open(os.path.join(gdir, os.path.basename(arg)), "w",
                             encoding="utf-8").write(txt)
                        last_code = txt
                        resp.append(f"da ghi {arg} ({len(txt)}b)")
                elif name in ("run", "bash") and arg:
                    if runs >= 5:
                        resp.append("het budget run 5")
                    elif not arg.startswith(("python", "py ")):
                        resp.append("chi duoc run python ...")
                    else:
                        runs += 1
                        r = sh(f"cd {gdir} && timeout 30 {arg}", timeout=60)
                        o = ((r.stdout or "") + (r.stderr or "")) \
                            if r else ""
                        if o.strip() and o == last_run_out:
                            resp.append("LOI Y NGUYEN (khong thay doi). "
                                        "Sua code bang write_file truoc "
                                        "khi run lai.\n" + o[-500:])
                        else:
                            last_run_out = o
                            import re as _rer
                            _mnm = _rer.search(
                                r"NameError: name '(\w+)' is not defined",
                                o)
                            _mam = _rer.search(
                                r"AttributeError: module '(\w+)' has no "
                                r"attribute '(\w+)'", o)
                            if _mnm:
                                _nm2 = _mnm.group(1)
                                resp.append(
                                    f"THIEU KHAI BAO '{_nm2}': KHONG duoc "
                                    f"de vay. Dung write_file viet lai "
                                    f"file, them dong `{_nm2} = ...` o "
                                    f"dau file (global), roi run lai de "
                                    f"kiem tra.\n" + o[-400:])
                            elif _mam:
                                resp.append(
                                    f"LOI MODULE: file {_mam.group(1)}.py "
                                    f"KHONG co ham {_mam.group(2)} o muc "
                                    f"module. Neu {_mam.group(2)} la "
                                    f"phuong thuc cua class trong file "
                                    f"do, them CUOI file: "
                                    f"`{_mam.group(2)} = "
                                    f"<TenClass>.{_mam.group(2)}` hoac "
                                    f"viet def {_mam.group(2)}(...) o "
                                    f"muc module.\n" + o[-400:])
                            else:
                                resp.append(o[-700:] if o.strip()
                                            else "(no output)")
                elif name == "done":
                    resp.append("xong")
                    hist += out + "\n<tool_response>xong</tool_response>"
                    log(f"game{i} (py) agent xong: {step + 1} buoc "
                        f"{runs} run")
                    fp2 = os.path.join(gdir, "main.py")
                    if os.path.isfile(fp2):
                        return open(fp2, encoding="utf-8").read()
                    return last_code or ""
                else:
                    resp.append("tool hop le: write_file/run/done")
            hist += out + "\n<tool_response>" + " | ".join(resp) \
                + "</tool_response>\n"
            if len(hist) > 4200:
                hist = hist[:1600] + "\n...(luoc)...\n" + hist[-2400:]
        log(f"game{i} (py) agent het buoc ({runs} run)")
        fp2 = os.path.join(gdir, "main.py")
        if os.path.isfile(fp2):
            return open(fp2, encoding="utf-8").read()
        return last_code or ""

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
                files = {k2: salvage_py(v) for k2, v in files.items()}
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
                if not str(main_name).endswith(".py"):
                    open(os.path.join(gdir, "main.py"), "w",
                         encoding="utf-8").write(files[main_name])
                    main_name = "main.py"
                fp = os.path.join(gdir, os.path.basename(main_name))
                if gdir not in sys.path:
                    sys.path.insert(0, gdir)
                PRE = ("import os as _o\n"
                       "_o.environ.setdefault('SDL_VIDEODRIVER', 'dummy')\n"
                       "_o.environ.setdefault('SDL_AUDIODRIVER', 'dummy')\n"
                       "import pygame as _pg\n"
                       "pygame = _pg\npg = _pg\n"
                       "try:\n    _pg.init()\n    _pg.font.init()\n"
                       "except Exception:\n    pass\n")
                t0 = open(fp, encoding="utf-8").read()
                if not t0.startswith(PRE):
                    open(fp, "w", encoding="utf-8").write(PRE + t0)
                inject = {"score": "score = [0]",
                          "alive": "alive = [True]",
                          "player": "player = [5, 5]",
                          "coins": "coins = [[2, 2], [7, 7]]",
                          "actions": "actions = ['up', 'down', 'left', "
                                     "'right']"}
                import re as _re0
                _tt = open(fp, encoding="utf-8").read()
                _add = ""
                if INJECT_HELP:
                    for _nm, _inj in inject.items():
                        if not _re0.search(r"^\s*" + _nm + r"\s*=", _tt,
                                           _re0.M):
                            if _re0.search(
                                    r"\b" + _nm + r"\s*\[\s*['\"]", _tt):
                                _add += (
                                    (_nm + " = {'score': 0, 'alive': "
                                     "True, 'actions': ['up', 'down', "
                                     "'left', 'right']}\n")
                                    if _nm == "score" else
                                    (_nm + " = {'alive': True, 'score': "
                                     "0}\n"))
                            elif _re0.search(r"\b" + _nm + r"\s*\[", _tt) \
                                    or (_nm == "actions"
                                        and _re0.search(r"\bactions\b",
                                                        _tt)):
                                _add += _inj + "\n"
                if _add:
                    open(fp, "w", encoding="utf-8").write(
                        _tt.replace(PRE, PRE + _add, 1))
                    log(f"game{i} (py) khai bao truoc: {_add.strip()}")
                injected, mod, st = set(), None, None
                for attempt in range(5):
                    s = importlib.util.spec_from_file_location(
                        f"g{i}_{attempt}", fp)
                    mod = importlib.util.module_from_spec(s)
                    signal.signal(signal.SIGALRM, _tmo)
                    signal.alarm(60)
                    try:
                        s.loader.exec_module(mod)
                        for _ in range(3):
                            st = mod.get_state()
                            assert isinstance(st, dict) and "score" in st \
                                and "alive" in st and "actions" in st
                        # Cua playability: nuoc di dau phai song + dict
                        acts0 = st.get("actions") or ["noop"]
                        res0 = mod.do_action(acts0[0])
                        assert isinstance(res0, dict), \
                            "do_action khong tra dict"
                        assert res0.get("alive", True) is not False, \
                            "chet ngay nuoc dau"
                    except NameError as ne:
                        import re as _re
                        mm = _re.search(r"name '(\w+)' is not defined",
                                        str(ne))
                        nm = mm.group(1) if mm else None
                        exp = None
                        if nm and nm not in injected and attempt < 4:
                            if INJECT_HELP and nm in inject:
                                exp = inject[nm]
                            elif INJECT_HELP and _re.fullmatch(
                                    r"[A-Z][A-Z0-9_]*", nm):
                                exp = nm + " = set()"
                        if exp:
                            injected.add(nm)
                            t = open(fp, encoding="utf-8").read()
                            open(fp, "w", encoding="utf-8").write(
                                t.replace(PRE, PRE + exp + "\n", 1))
                            log(f"game{i} (py) khai bao ho {nm}")
                            continue
                        raise
                    finally:
                        signal.alarm(0)
                    break
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
        items = propose_tasks(temp)
        log(f"wave {wave}: B tu ra {len(items)} de: "
            f"{[s[:40] for _, s in items]}")
        try:
            codes = []
            for j, (eng, spec) in enumerate(items):
                idx = wave * 10 + j
                if eng == "py":
                    codes.append(agent_build(eng, spec, idx, temp))
                else:
                    codes.append(strip_code(vllm_gen(
                        [ALPACA.format(SYS[eng], spec, "")], 2048,
                        temp)[0]))
        except Exception as e:
            log(f"wave {wave} gen loi: {e}")
            continue
        fails = []
        for j, (eng, spec) in enumerate(items):
            r = verify_game(eng, spec, wave * 10 + j, codes[j])
            if isinstance(r, tuple):
                fails.append((eng, spec, wave * 10 + j, r[1], codes[j]))
        for rnd in range(2):
            reps = [(e, s, ii, er, oc) for (e, s, ii, er, oc) in fails
                    if e in ("py", "bpy")][:4]
            if not reps:
                break
            log(f"wave {wave} repair vong {rnd}: sua {len(reps)} game")
            import re as _re2
            try:
                def _rh(e2):
                    _m2 = _re2.search(
                        r"module '(\w+)' has no attribute '(\w+)'", e2)
                    if not _m2:
                        return ""
                    return (f"\nLOI MODULE: {_m2.group(1)}.py thieu "
                            f"{_m2.group(2)} muc module. Them cuoi file: "
                            f"`{_m2.group(2)} = <TenClass>."
                            f"{_m2.group(2)}` (neu la phuong thuc class) "
                            f"hoac `def {_m2.group(2)}(...)` muc module.")
                rp = [ALPACA.format(
                    SYS[e] + " CHI OUTPUT CODE (khong van xuoi, khong dong "
                    "Task:), KHONG GIAI THICH. Neu la py: PHAI giu nguyen "
                    "def get_state/do_action nhu khung xuong.",
                    f"Nhiem vu: {s}\nCode cu (LOI: {er}):\n{oc[:2800]}\n"
                    f"Tra ve code MOI da sua.{_rh(er)}",
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
                      tokenizer, base_dir, PDB, ACC, use_bf16,
                      prev=prev_adapter)
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
        if pool < 6:
            log("it mau (pool<6), bo qua phase")
            return
        texts = [ALPACA.format(
            f"Choi game. State: {b['state']}\nActions: {b['actions']}",
            "", b["action"]) + tokenizer.eos_token for b in good]
        for si, so, rw in STATIC_ROWS:
            texts.append(ALPACA.format(si, "", so) + tokenizer.eos_token)
        log(f"phase {phase}: texts play={len(good)} "
            f"static={len(STATIC_ROWS)}")
        adir = sft_train(texts, f"p{phase}", max(50, len(texts) // 16),
                         tokenizer, base_dir, PDB, ACC, use_bf16,
                         prev=prev_adapter)
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
                    if res.get("alive", True):
                        rw += 0.1
                        g["score"] = sc
                    else:
                        rw += -5.0
                        buf.append({"turn": turn, "task": i, "state": st,
                                    "actions": acts, "action": act,
                                    "reward": rw})
                        log(f"turn {turn} game{i} CHET (loai khoi alive)")
                        del alive[i]
                        continue
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
