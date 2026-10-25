"""Pilot A/B self-play (20 rounds, RTX): 1 model, 2 prompt.
A-director: tu chon track (GAME/CHAR), ra yeu cau, che kho tinh (cam khen),
toi da 5 luot/round, verdict PASS/FAIL + SCORE 1-5.
B-builder: viet code (multi-file), harness verify ho (budget 5 luot/round:
import/probe/render/playtest), sua theo che.
Trajectory -> SFT (B: req+che->code sua; A: code+report->che) moi 5 rounds.
Cuoi: soup incremental.
"""
import gc
import glob
import json
import os
import random
import shutil
import subprocess
import sys
import time
import traceback

WORK = "/kaggle/working"
GAMES = os.path.join(WORK, "ab_games")
ROUNDS = 100
MAX_TURNS = 5
TOOL_BUDGET = 5
TRAIN_EVERY = 10
TIME_BUDGET = 10 * 3600
RANK, ALPHA, DROPOUT, LR = 128, 128, 0.1, 1e-4
LR_AB = 2e-5
SEQ_LEN = 4096
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj",
           "gate_proj", "up_proj", "down_proj"]

A_PICK = ("Ban la dao dien game/3D kho tinh. Nhiem vu DUY NHAT: chon "
          "track + RA DE + CHAM. Ban KHONG tu chay code (da co tho xay B "
          "va may kiem lo) nen KHONG BAO GIO tu choi ra de. Chon 1 track: "
          "GAME (game pygame choi duoc, co get_state/do_action) hoac CHAR "
          "(nhan vat Anime Blender bang bpy, co mesh+armature+animation "
          "don gian). "
          "GAME phai KHO THAT SU (doi hoi chien thuat/phan xa/giai do; "
          "de qua, thang ngay thi coi nhu hong). VI DU:\n"
          "TRACK: GAME\nREQUEST: Game thu thap xu me cung 10x10, quai "
          "ruot duoi, 3 mang, cang sau cang nhanh. Chi output 2 dong:\n"
          "TRACK: GAME|CHAR\nREQUEST: <yeu cau cu the>")
A_REVIEW = ("Ban la giam khao cuc ky kho tinh, CAM KHEN SUONG, va la "
            "game thu gioi (da TU CHOI game qua PLAYTEST). Doc CODE, bao "
            "cao VERIFY va PLAYTEST. NGUYEN TAC CUNG: neu VERIFY bao "
            "loi/hong (verify=False) -> VERDICT phai la FAIL, SCORE <= 2. "
            "Game DE QUA (thang ngay, khong can nghi, PLAYTEST diem cao "
            "ngay) cung FAIL (SCORE<=2, ghi ro 'de qua'). Chi PASS "
            "(SCORE>=3) khi VERIFY OK + game KHO that su. Chi output:\n"
            "VERDICT: PASS|FAIL\nSCORE: 1-5\nCRITIQUE: <che cu the, ngan>")
B_SYS = ("You are a builder. Output code only, no explanation. "
         "GAME pygame: headless-safe (SDL_VIDEODRIVER=dummy), BAT BUOC "
         "get_state()->dict(score,alive,actions) va do_action(action)->dict, "
         "KHONG game-loop top-level. CHAR bpy: script dung bpy, tao mesh + "
         "armature + animation co keyframes. Game lon: tach file bang dong "
         "'# === FILE: ten ===' (main.py chua API, main import file khac).")
ALPACA = ("Below is an instruction. Write a response.\n\n"
          "### Instruction:\n{}\n\n### Input:\n{}\n\n### Response:\n{}")

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


def no_think(txt):
    import re
    txt = re.sub(r"<think>.*?</think>", "", txt, flags=re.S | re.I)
    txt = re.sub(r"<think>.*$", "", txt, flags=re.S | re.I)
    return txt.strip()


def strip_code(code):
    import re
    code = no_think(code)
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

VLLM = {}
_SOUP = {"A": {"acc": None, "n": 0}, "B": {"acc": None, "n": 0}}

# De du phong khi A chet (echo template): lay de co san, kho that
FALLBACK_REQS = [
    ("GAME", "Game thu thap xu me cung 10x10, quai ruot duoi, 3 mang, "
     "cang sau cang nhanh, co diem cao nhat"),
    ("GAME", "Game ban may bay: dieu khien phi thuyen ne dan, ban ha 20 "
     "dich, 3 loai dan dich, boss cuoi man hinh"),
    ("GAME", "Game dua xe top-down 3 vong, 4 cua kho, toc do tang dan, "
     "tinh gio, va cham tru toc do"),
    ("GAME", "Game xep hinh roi: 7 khoi co dien, xoay/lat, combo x4 diem, "
     "toc do tang theo cap"),
    ("GAME", "Game thu thanh: 3 loai thap, 5 dot quai, tien nang cap, "
     "giap/hoi mau"),
    ("GAME", "Game ran san moi 2D: an tao lon len, tranh tu can than, "
     "tang toc dan, 3 che do toc do"),
    ("CHAR", "Nhan vat Anime chien binh: giap vai, kiem dai, the dung tan "
     "cong, armature day du, animation chem kiem 24 frames"),
    ("CHAR", "Nhan vat Anime phu thuy: ao choang, mu nhon, gay phep, the "
     "bay, armature, animation bay luon 30 frames"),
    ("CHAR", "Robot mecha lowpoly: than, tay, chan rieng biet, khop xoay, "
     "animation buoc di 20 frames"),
    ("CHAR", "Nhan vat Anime ninja: khan mat, song dao, the ngoi, armature, "
     "animation nem phi tieu 16 frames"),
]


def log(m):
    print("[ab] " + m, flush=True)


def sh(cmd, timeout=600):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0:
        return None
    return r


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
    except Exception:
        pass


def vllm_init(loraA=None, loraB=None):
    vllm_free()
    os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    os.environ["TORCHINDUCTOR_FX_GRAPH_CACHE"] = "0"
    import torch
    free, total = torch.cuda.mem_get_info()
    util = min(0.9, max(0.4, (free - 6 * 2**30) / total))
    from vllm import LLM
    kw = dict(model=VLLM["base"], dtype="bfloat16",
              gpu_memory_utilization=util,
              max_model_len=4096, max_num_seqs=16, enforce_eager=True,
              enable_lora=True, max_loras=2, max_lora_rank=128)
    VLLM["llm"] = LLM(**kw)
    VLLM["loraA"] = loraA
    VLLM["loraB"] = loraB
    log(f"vllm san sang (A={loraA} B={loraB})")


def vllm_gen(prompts, max_tok, temp, rep=1.0, pres=0.0, which=None):
    from vllm import SamplingParams
    sp = SamplingParams(max_tokens=max_tok, temperature=temp, top_p=0.9,
                        repetition_penalty=rep, presence_penalty=pres)
    lreq = None
    try:
        from vllm.lora.request import LoRARequest
        if which == "A" and VLLM.get("loraA"):
            lreq = LoRARequest("a", 1, VLLM["loraA"])
        elif which == "B" and VLLM.get("loraB"):
            lreq = LoRARequest("b", 2, VLLM["loraB"])
    except Exception:
        pass
    outs = VLLM["llm"].generate(prompts, sp, lora_request=lreq)
    return [o.outputs[0].text for o in outs]


def split_files(code):
    import re
    parts = re.split(r"^# === FILE:\s*(\S+)\s*===\s*$", code, flags=re.M)
    if len(parts) < 3:
        return {"main.py": code}
    out = {}
    for k in range(1, len(parts), 2):
        out[parts[k]] = parts[k + 1]
    return out or {"main.py": code}


def parse_verdict(txt):
    v, s, c = "FAIL", 1, txt.strip()[:500]
    import re
    m = re.search(r"VERDICT:\s*(PASS|FAIL)", txt, re.I)
    if m:
        v = m.group(1).upper()
    m = re.search(r"SCORE:\s*([1-5])", txt)
    if m:
        s = int(m.group(1))
    m = re.search(r"CRITIQUE:\s*(.*)", txt, re.S)
    if m:
        c = m.group(1).strip()[:500]
    return v, s, c


def verify_py(gdir, main_fp, modname, tools):
    """1 luot tool: import + probe + playtest ngan.
    Tra (ok, report, mod, acts)."""
    tools[0] += 1
    if tools[0] > TOOL_BUDGET:
        return False, "het budget tool", None, []
    try:
        import importlib.util
        import signal

        def _tmo(sn, fr):
            raise TimeoutError("probe 60s")
        if gdir not in sys.path:
            sys.path.insert(0, gdir)
        s = importlib.util.spec_from_file_location(modname, main_fp)
        mod = importlib.util.module_from_spec(s)
        signal.signal(signal.SIGALRM, _tmo)
        signal.alarm(60)
        try:
            s.loader.exec_module(mod)
            st = mod.get_state()
            assert isinstance(st, dict) and "score" in st \
                and "alive" in st and "actions" in st
            acts = st.get("actions") or ["noop"]
            res = mod.do_action(acts[0])
            assert isinstance(res, dict) and res.get("alive", True)
            # playtest 5 nuoc random
            sc0 = float(st.get("score", 0))
            for _ in range(5):
                st = mod.get_state()
                a2 = st.get("actions") or ["noop"]
                r2 = mod.do_action(random.choice(a2))
                if not isinstance(r2, dict) or not r2.get("alive", True):
                    break
            sc1 = float(st.get("score", sc0))
        finally:
            signal.alarm(0)
        return True, (f"import+probe+playtest OK actions={acts} "
                     f"score {sc0}->{sc1}"), mod, acts
    except Exception as e:
        return False, f"loi: {e}"[:300], None, []


def playtest_game(mod, tools):
    """A TU CHOI (model chon action, toi da 12 nuoc). Chung 1 luot tool
    voi verify (khong +budget). Tra (report, dscore, survived, steps)."""
    try:
        st = mod.get_state()
        s0 = float(st.get("score", 0))
        n, last = 0, ""
        for _ in range(12):
            st = mod.get_state()
            a2 = st.get("actions") or ["noop"]
            p = ALPACA.format(
                f"Choi game de THANG DIEM CAO. State: "
                f"{json.dumps(st)[:600]}",
                f"Chon 1 action trong {a2}", "")
            act = vllm_gen([p], 32, 0.3, which="A")[0].strip().split(
                "\n")[0][:40]
            if act not in a2:
                act = a2[0]
            r = mod.do_action(act)
            last = act
            if not isinstance(r, dict) or not r.get("alive", True):
                break
            n += 1
        st = mod.get_state()
        s1 = float(st.get("score", s0))
        surv = bool(st.get("alive", True))
        rep = (f"A choi {n} nuoc (cuoi: {last}): diem {s0}->{s1}, "
               f"{'SONG' if surv else 'CHET'}")
        return rep, s1 - s0, surv, n
    except Exception as e:
        return f"playtest loi: {e}"[:200], 0.0, False, 0


def verify_bpy(code, idx, blender_bin, tools):
    tools[0] += 1
    if tools[0] > TOOL_BUDGET:
        return False, "het budget tool"
    try:
        fp = os.path.join(WORK, f"_ab{idx}.py")
        png = os.path.join(WORK, f"_abr{idx}.png")
        if blender_bin:
            full = (code + f"\nimport bpy\nbpy.context.scene.render."
                    f"filepath = '{png}'\n"
                    f"bpy.ops.render.render(write_still=True)\n")
            open(fp, "w").write(full)
            r = sh(f"{blender_bin} --background --python {fp}", timeout=300)
            if r and os.path.exists(png):
                # check rig: armature + keyframes trong code
                has_rig = ("armature" in code.lower()
                           and "keyframe" in code.lower())
                return True, ("render OK"
                              + (" +rig/anim" if has_rig else " (thieu rig)"))
            return False, "blender render hong"
        import ast
        ast.parse(code)
        return True, "ast OK (khong blender)"
    except Exception as e:
        return False, f"loi: {e}"[:300]


def main():
    T0 = time.time()
    os.makedirs(GAMES, exist_ok=True)
    # --- install unsloth stack ---
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
    # --- install vllm stack ---
    SRC = None
    for root, _, files in os.walk("/kaggle/input"):
        if any(f.startswith("vllm-") and f.endswith(".whl") for f in files):
            SRC = root
            break
    assert SRC, "thieu wheels vllm (stack-wheels dataset?)"
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
    log("vllm " + vllm.__version__ + " torch=" + torch.__version__)
    # --- base tu shards ---
    found = {}
    for r, _, fs in os.walk("/kaggle/input"):
        for f in fs:
            if f.startswith("model-0000") and f.endswith(".safetensors"):
                found[f] = r
    assert len(found) >= 4, f"thieu shards ({len(found)})"
    orn = "/tmp/ornbase"
    os.makedirs(orn, exist_ok=True)
    for f, d in sorted(found.items()):
        dst = os.path.join(orn, f)
        if not os.path.exists(dst):
            os.symlink(os.path.join(d, f), dst)
    NEED = ["model.safetensors.index.json", "config.json",
            "tokenizer.json", "tokenizer_config.json", "vocab.json",
            "chat_template.jinja", "preprocessor_config.json",
            "processor_config.json", "video_preprocessor_config.json"]
    for r, _, fs in os.walk("/kaggle/input"):
        if "model.safetensors.index.json" in fs:
            for f in NEED:
                src, dst = os.path.join(r, f), os.path.join(orn, f)
                if os.path.isfile(src) and not os.path.exists(dst):
                    os.symlink(src, dst)
                elif not os.path.exists(dst) and f in PREPROC:
                    with open(dst, "w") as fh:
                        json.dump(PREPROC[f], fh)
                    log(f"viet tay fallback: {f}")
            break
    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(orn)
    except Exception as e:
        log(f"tokenizer loi: {e}")
        raise SystemExit("thieu base")
    VLLM["base"] = orn
    from unsloth import FastLanguageModel
    props = torch.cuda.get_device_properties(0)
    log(f"GPU={props.name} vram={props.total_memory / 2**30:.0f}G")
    # --- blender ---
    blender_bin = None
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
                        blender_bin = p
                        break
                break
    log(f"blender={blender_bin}")
    # --- engine (chua adapter) ---
    vllm_init(None, None)
    trajs, ntrained = [], 0

    def sft_round(tag, texts, steps, kind):
        vllm_free()
        gc.collect()
        torch.cuda.empty_cache()
        m, _ = FastLanguageModel.from_pretrained(
            model_name=orn, max_seq_length=SEQ_LEN,
            dtype=None, load_in_4bit=True)
        m = FastLanguageModel.get_peft_model(
            m, r=RANK, target_modules=TARGETS, lora_alpha=ALPHA,
            lora_dropout=DROPOUT, bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=random.SystemRandom().randint(1, 10**9),
            use_rslora=False)
        from datasets import Dataset
        from trl import SFTTrainer
        from transformers import TrainingArguments
        import inspect
        sft_kw = dict(
            model=m, train_dataset=Dataset.from_dict({"text": texts}),
            args=TrainingArguments(
                per_device_train_batch_size=8,
                gradient_accumulation_steps=2, warmup_steps=5,
                max_steps=steps, learning_rate=LR_AB,
                fp16=False, bf16=True, logging_steps=5,
                optim="adamw_8bit", weight_decay=0.01,
                lr_scheduler_type="linear",
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
        adir = os.path.join(WORK, f"ab_adapt_{tag}")
        if os.path.isdir(adir):
            shutil.rmtree(adir)
        m.save_pretrained(adir)
        del m
        gc.collect()
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        # VALIDATE bang dung vai: gen thu, hong -> ROLLBACK
        curA, curB = VLLM.get("loraA"), VLLM.get("loraB")
        if kind == "A":
            vllm_init(adir, curB)
        else:
            vllm_init(curA, adir)
        try:
            t = vllm_gen([ALPACA.format(A_PICK, "", "")], 64, 0.5,
                         which=kind)[0]
            tu = t.upper()
            valid = (len(t.strip()) >= 50 and "TRACK" in tu
                     and "### INSTRUCTION" not in tu and "<" not in t
                     and "YOUR RESPONSE" not in tu)
        except Exception as e:
            log(f"validate loi: {e}")
            valid = False
        if not valid:
            log(f"adapter {tag}/{kind} HONG -> ROLLBACK")
            shutil.rmtree(adir, ignore_errors=True)
            vllm_init(curA, curB)
            return False
        try:
            from safetensors.torch import load_file
            sd = load_file(os.path.join(adir, "adapter_model.safetensors"),
                           device="cpu")
            SA = _SOUP[kind]
            n = SA["n"]
            if SA["acc"] is None:
                SA["acc"] = {k: v.float() for k, v in sd.items()}
            else:
                for k in SA["acc"]:
                    SA["acc"][k] = (SA["acc"][k] * n
                                    + sd[k].float()) / (n + 1)
            SA["n"] = n + 1
            del sd
            gc.collect()
        except Exception as e:
            log(f"soup-inc loi: {e}")
        latest = os.path.join(WORK, f"ab_adapt_latest_{kind}")
        prev = os.path.join(WORK, f"ab_adapt_prev_{kind}")
        shutil.rmtree(prev, ignore_errors=True)
        if os.path.isdir(latest):
            shutil.move(latest, prev)
        shutil.copytree(adir, latest)
        shutil.rmtree(adir, ignore_errors=True)
        torch.cuda.synchronize()
        torch.cuda.empty_cache()
        curA2 = latest if kind == "A" else VLLM.get("loraA")
        curB2 = latest if kind == "B" else VLLM.get("loraB")
        vllm_init(curA2, curB2)
        log(f"xong train {tag}/{kind} (soup {kind} n={_SOUP[kind]['n']})")
        return True

    for rnd in range(ROUNDS):
        if time.time() - T0 > TIME_BUDGET:
            log("het gio")
            break
        # A chon track + ra de (vai A)
        pick = no_think(vllm_gen([ALPACA.format(A_PICK, "", "")], 256, 0.7,
                                 rep=1.15, pres=0.3, which="A")[0])
        import re

        def parse_pick(p):
            tm = re.search(r"TRACK:\s*(GAME|CHAR)", p, re.I)
            track = tm.group(1).upper() if tm else ""
            rm = re.search(r"REQUEST:\s*(.*)", p, re.S)
            req = rm.group(1).strip()[:400] if rm else ""
            bad = (not track or len(req) < 10
                   or "YOUR RESPONSE" in p.upper()
                   or "CANNOT" in p.upper()[:200]
                   or "<" in req or "###" in req or "```" in p
                   or "TRACK:" in req or "REQUEST:" in req)
            return track, req, bad

        track, req, bad = parse_pick(pick)
        if bad:
            log(f"round {rnd}: de rac, regen 1 lan")
            pick = no_think(vllm_gen([ALPACA.format(A_PICK, "", "")],
                                     256, 0.5, which="A")[0])
            track, req, bad = parse_pick(pick)
        if bad or not track:
            track, req = FALLBACK_REQS[rnd % len(FALLBACK_REQS)]
            log(f"round {rnd}: de hong -> dung de du phong: {track}")
        log(f"round {rnd}: track={track} req={req[:80]}")
        traj = {"round": rnd, "track": track, "request": req, "turns": []}
        tools = [0]
        code, verdict, score, crit, report = "", "FAIL", 1, "", ""
        for t in range(MAX_TURNS):
            if t == 0:
                sysp = B_SYS + (f" Track: {track}. Nhiem vu: {req}")
                ctx_in = ""
            else:
                sysp = (B_SYS + f" Track: {track}. Sua code theo che, "
                        f"CHI OUTPUT CODE.")
                ctx_in = (f"Yeu cau: {req}\nCode cu:\n{code[:2000]}\n"
                          f"Che: {crit}")
            code = strip_code(vllm_gen(
                [ALPACA.format(sysp, ctx_in, "")], 2048, 0.4,
                which="B")[0])
            # harness: write (FREE) + verify (an budget)
            play_rep, pds, psurv, psteps = "khong choi (CHAR)", 0.0, False, 0
            if track == "CHAR":
                ok, report = verify_bpy(code, f"{rnd}_{t}", blender_bin,
                                        tools)
            else:
                files = split_files(code)
                gdir = os.path.join(GAMES, f"r{rnd}_{t}")
                os.makedirs(gdir, exist_ok=True)
                for name, txt in files.items():
                    safe = os.path.basename(name) or "main.py"
                    open(os.path.join(gdir, safe), "w",
                         encoding="utf-8").write(txt)
                main_n = ("main.py" if "main.py" in files
                          else sorted(files)[0])
                ok, report, mod, acts = verify_py(
                    gdir, os.path.join(gdir, os.path.basename(main_n)),
                    f"ab{rnd}_{t}", tools)
                if ok and mod is not None:
                    play_rep, pds, psurv, psteps = playtest_game(mod, tools)
                    report += f" | {play_rep}"
            # A cham (vai A)
            rev = no_think(vllm_gen([ALPACA.format(
                A_REVIEW,
                f"Yeu cau: {req}\nCODE:\n{code[:2500]}\nVERIFY: {report}\n"
                f"PLAYTEST: {play_rep}", "")], 512, 0.5,
                which="A")[0])
            verdict, score, crit = parse_verdict(rev)
            # Harness tu cham: PASS = verify OK + score>=3 (khong tin A)
            final = "PASS" if (ok and score >= 3) else "FAIL"
            log(f"round {rnd} turn {t}: verify={ok} A={verdict}/{score} "
                f"FINAL={final} tool={tools[0]}/5")
            traj["turns"].append({"code": code[:3000], "verify": ok,
                                  "report": report, "verdict": final,
                                  "score": score, "critique": crit,
                                  "play": play_rep, "play_dscore": pds,
                                  "play_survived": psurv})
            if final == "PASS":
                break
        traj["final_score"] = score
        trajs.append(traj)
        with open(os.path.join(WORK, f"ab_traj_r{rnd}.json"), "w") as f:
            json.dump(traj, f)
        # train moi 10 rounds: tach 2 adapter (nhe tay)
        if len(trajs) - ntrained >= TRAIN_EVERY:
            btexts, atexts = [], []
            for tr in trajs[ntrained:]:
                for tn in tr["turns"]:
                    btexts.append(ALPACA.format(
                        f"Nhiem vu: {tr['request']}\nChe: "
                        f"{tn.get('critique', '')}", "",
                        tn["code"][:2500]) + tokenizer.eos_token)
                    atexts.append(ALPACA.format(
                        "Nhan xet kho tinh code game/3D (VERDICT/SCORE/"
                        "CRITIQUE).",
                        f"CODE:\n{tn['code'][:2000]}\nVERIFY: "
                        f"{tn['report']}", "") + tokenizer.eos_token)
            log(f"train sau {len(trajs) - ntrained} rounds: "
                f"B {len(btexts)} + A {len(atexts)} texts")
            sft_round(f"r{len(trajs)}b", btexts, max(15, len(btexts) // 16),
                      "B")
            sft_round(f"r{len(trajs)}a", atexts, max(15, len(atexts) // 16),
                      "A")
            ntrained = len(trajs)
    # soup cuoi: ca 2 vai
    try:
        from safetensors.torch import save_file
        import torch as _t
        for kind in ("A", "B"):
            SA = _SOUP[kind]
            if SA["n"] >= 1 and SA["acc"]:
                sdir = os.path.join(WORK, f"ab_soup_{kind}")
                os.makedirs(sdir, exist_ok=True)
                save_file({k: v.to(_t.float16)
                           for k, v in SA["acc"].items()},
                          os.path.join(sdir, "adapter_model.safetensors"))
                cfg = os.path.join(WORK, f"ab_adapt_latest_{kind}",
                                   "adapter_config.json")
                if os.path.isfile(cfg):
                    shutil.copy(cfg, os.path.join(sdir,
                                                  "adapter_config.json"))
                log(f"AB SOUP DONE {kind} n={SA['n']} -> {sdir}")
    except Exception as e:
        log(f"soup loi: {e}")
    log(f"AB DONE rounds={len(trajs)}")


if __name__ == "__main__":
    main()
