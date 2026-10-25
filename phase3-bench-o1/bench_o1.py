"""Bench O1: base Ornith vs O1-soup. 60 game tasks + 20 computer-control.
Greedy batch-8, T4 offline. Theo SCORING.md (game/unity/bpy + computer)."""
import ast
import gc
import json
import os
import random
import re
import shutil
import subprocess
import sys

WORK = "/kaggle/working"
SB = os.path.join(WORK, "sandbox")
EVAL_SEED = 123
MAX_NEW = 256
EVAL_BATCH = 8


def log(m):
    print(f"[o1bench] {m}", flush=True)


def sh(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    return r


PYGAME = [
    "Snake an moi dai ra, thua khi dam tuong hoac tu can, co diem",
    "Pong 2 nguoi W/S va len/xuong, den 5 thang",
    "Breakout pha gach, 3 mang, chuot",
    "Flappy vuot ong, space bay, diem cao nhat",
    "Ban may bay trai/phai space ban, dich roi xuong",
    "Tetris 7 khoi xoay xoa hang tinh diem",
    "Maze random ra khoi me cung gioi han gio",
    "Clicker bam nhanh 30 giay",
    "Platformer chay nhay qua be, gai la thua",
    "Asteroids xoay 360 ban da vo manh nho",
    "Memory match 8 cap dem luot",
    "Simon lap day mau am thanh dai dan",
    "Dodge ne dan 60 giay",
    "Catcher hung do trung bom tru mang",
    "Runner nhay truong toc do tang",
    "Frogger qua duong ne xe qua song",
    "Invaders ban het hang dich",
    "Tennis 1 nguoi vs AI",
    "Minesweeper 9x9 10 min",
    "2048 truot gop den 2048",
]
UNITY = [
    "Player WASD+nhay camera chuot",
    "Camera follow muot gioi han bien",
    "Enemy duoi gan danh can chien",
    "Coin xoay nhat cong diem am thanh",
    "Mau trung dan tru het chet respawn",
    "Spawner dot tang so luong",
    "Ban dan huong nhin co tuoi tho",
    "Cua mo khi nhan cong tac",
    "UI diem+mang realtime",
    "Pause Esc tiep tuc/choi lai/thoat",
    "NPC tuan tra thay duoi",
    "Dem nguoc het gio thua",
    "Be di chuyen cho dung",
    "Checkpoint hoi sinh gan nhat",
    "Hoi thoai E next",
    "Double jump+dash hoi",
    "Sprint ton stamina",
    "Wave tang hien UI",
    "Luu diem PlayerPrefs",
    "Vat xoay hut ve player",
]
BPY = [
    "Ban ghe go: mat+4 chan+lung tua",
    "Ban tron + den ngu",
    "Den ban chup + point light",
    "Oto lowpoly than+4 banh+cua",
    "Ngoi nha tuong+mai+cua+2 so",
    "Cay than+3 tang la",
    "Kiem luoi+chuoi+can",
    "Coc co quai",
    "Thang 10 bac",
    "Rao 8 coc+2 ngang",
    "Ten lua than+mui+3 canh",
    "Robot dau hop+than+tay chan",
    "Cau cong lan can",
    "Long do treo",
    "Lau dai 4 thap+tuong",
    "Giong voi+tay cam",
    "May bay than+canh+duoi",
    "Dong ho kim chay",
    "Gia sach 3 tang+sach",
    "Thuyen than+cot+buom",
]
GAME_SYS = "You are a game code generator. Output ONE complete single-file python pygame program only, no explanation. It must run with `SDL_VIDEODRIVER=dummy` (no real display needed)."
UNITY_SYS = "You are a Unity C# generator. Output ONE complete C# MonoBehaviour script only, no explanation."
BPY_SYS = "You are a Blender bpy generator. Output ONE complete python script using bpy only, no explanation. Assume default scene."
PC_SYS = ("You are a computer operator. Output ONLY bash commands, one per "
          "line, no explanation, no markdown fences. Working dir is the "
          "sandbox. No internet, no installs, no sudo.")
UNITY_APIS = ["transform", "GetComponent", "Instantiate", "Rigidbody",
              "Collider", "Input", "Time", "Debug", "GameObject",
              "Vector3", "Camera", "AudioSource", "Animator"]
DENY = ["rm -rf /", "mkfs", ":(){", "dd if=", "> /dev/", "shutdown",
        "reboot", "curl ", "wget ", "pip install", "apt ", "sudo ",
        "chmod -R", "mkfifo"]


def strip_fences(code):
    m = re.search(r"```(?:python|csharp|py|cs|bash|sh)?\s*\n(.*?)```",
                  code, re.S)
    if m:
        return m.group(1).strip()
    return "\n".join(l for l in code.splitlines()
                      if not l.strip().startswith("```")).strip()


def score_unity(code):
    s = 0
    s += 1 if ("MonoBehaviour" in code and "class" in code) else 0
    s += 1 if ("void Start" in code and "void Update" in code) else 0
    s += 1 if (code.count("{") == code.count("}") and "{" in code) else 0
    hit = sum(1 for a in UNITY_APIS if a in code)
    s += 2 if hit >= 5 else (1 if hit >= 3 else 0)
    return min(s, 5)


def score_pygame(code, run_ok, survived):
    s = 0
    if run_ok:
        s += 2
    if survived:
        s += 1
    hit = sum(1 for k in ["pygame.init", "display.set_mode", "event.get",
                          "Clock", "flip"] if k in code)
    hit += 1 if ("tick" in code or ".update(" in code) else 0
    if hit >= 4:
        s += 1
    if any(w in code for w in ["score", "lives", "level", "health"]):
        s += 1
    return min(s, 5)


def run_pygame(code, have_pygame):
    fp = os.path.join(WORK, "_g.py")
    open(fp, "w", encoding="utf-8").write(code)
    if not have_pygame:
        try:
            ast.parse(code)
            return True, True
        except SyntaxError:
            return False, False
    env = dict(os.environ, SDL_VIDEODRIVER="dummy",
               SDL_AUDIODRIVER="dummy")
    try:
        p = subprocess.Popen([sys.executable, fp],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=env)
        try:
            _, err = p.communicate(timeout=15)
            err = err.decode(errors="ignore")
            if p.returncode == 0:
                return True, True
            return (False, False) if "Traceback" in err else (True, True)
        except subprocess.TimeoutExpired:
            p.kill()
            _, err = p.communicate()
            err = err.decode(errors="ignore")
            return (False, False) if "Traceback" in err else (True, True)
    except Exception:
        return False, False


def run_bpy(code, blender_bin):
    fp = os.path.join(WORK, "_b.py")
    png = os.path.join(WORK, "_r.png")
    if os.path.exists(png):
        os.remove(png)
    if blender_bin is None:
        try:
            ast.parse(code)
        except SyntaxError:
            return 0
        n = sum(1 for l in code.splitlines() if "bpy.ops.mesh" in l)
        return 2 + (1 if n >= 2 else 0) + 2
    full = code + (f"\nimport bpy\nscene = bpy.context.scene\n"
                   f"scene.render.filepath = '{png}'\n"
                   f"scene.render.resolution_x = 256\n"
                   f"scene.render.resolution_y = 256\n"
                   f"bpy.ops.render.render(write_still=True)\n")
    open(fp, "w", encoding="utf-8").write(full)
    r = sh(f"{blender_bin} --background --python {fp}", timeout=240)
    if r.returncode != 0 or not os.path.exists(png):
        return 0
    try:
        from PIL import Image
        import numpy as np
        a = np.asarray(Image.open(png).convert("L"), dtype=float)
        if a.std() <= 5:
            return 2
    except Exception:
        if os.path.getsize(png) < 10240:
            return 2
    n = sum(1 for l in code.splitlines() if "bpy.ops.mesh" in l)
    return 4 + (1 if n >= 2 else 0)


def reset_sandbox():
    if os.path.isdir(SB):
        shutil.rmtree(SB, ignore_errors=True)
    os.makedirs(SB, exist_ok=True)
    os.makedirs(os.path.join(SB, "docs"), exist_ok=True)
    os.makedirs(os.path.join(SB, "src"), exist_ok=True)
    open(os.path.join(SB, "docs", "notes.txt"), "w").write(
        "alpha\nbeta\ngamma\n")
    open(os.path.join(SB, "src", "main.py"), "w").write(
        "print('hello')\n# TODO fix bug\n")
    open(os.path.join(SB, "src", "util.py"), "w").write(
        "VALUE = 41\n")
    open(os.path.join(SB, "data.csv"), "w").write(
        "name,score\na,10\nb,20\nc,30\n")


PC_TASKS = [
    ("Tao file hello.txt voi noi dung 'xin chao'",
     lambda: open(os.path.join(SB, "hello.txt")).read().strip()
     == "xin chao"),
    ("Tao thu muc logs va file logs/a.log ghi 'start'",
     lambda: open(os.path.join(SB, "logs", "a.log")).read().strip()
     == "start"),
    ("Doi ten docs/notes.txt thanh docs/memo.txt",
     lambda: os.path.isfile(os.path.join(SB, "docs", "memo.txt")) and
     not os.path.exists(os.path.join(SB, "docs", "notes.txt"))),
    ("Copy src/main.py thanh src/main_bak.py",
     lambda: open(os.path.join(SB, "src", "main_bak.py")).read() ==
     open(os.path.join(SB, "src", "main.py")).read()),
    ("Xoa file src/util.py",
     lambda: not os.path.exists(os.path.join(SB, "src", "util.py"))),
    ("Them dong 'delta' vao cuoi docs/notes.txt",
     lambda: open(os.path.join(SB, "docs", "notes.txt")).read().
     strip().splitlines()[-1] == "delta"),
    ("Dem so dong cua docs/notes.txt, ghi ket qua vao count.txt",
     lambda: open(os.path.join(SB, "count.txt")).read().strip() == "3"),
    ("Tim file .py chua chu TODO, ghi ten file vao found.txt",
     lambda: "main.py" in open(os.path.join(SB, "found.txt")).read()),
    ("Sua VALUE=41 thanh VALUE=42 trong src/util.py",
     lambda: "VALUE = 42" in open(os.path.join(SB, "src",
                                               "util.py")).read()),
    ("Tao file list.txt liet ke ten file trong src (moi dong 1 ten)",
     lambda: set(open(os.path.join(SB, "list.txt")).read().split()) >=
     {"main.py", "util.py"}),
    ("Tinh tong cot score trong data.csv, ghi vao total.txt",
     lambda: open(os.path.join(SB, "total.txt")).read().strip() == "60"),
    ("Tao 3 file f1.txt f2.txt f3.txt voi noi dung lan luot 1 2 3",
     lambda: all(open(os.path.join(SB, f"f{i}.txt")).read().strip() ==
                 str(i) for i in (1, 2, 3))),
    ("Gop noi dung 3 file f1 f2 f3 vao merged.txt (can co 1 2 3)",
     lambda: all(x in open(os.path.join(SB, "merged.txt")).read()
                 for x in "123")),
    ("Di chuyen data.csv vao thu muc docs/",
     lambda: os.path.isfile(os.path.join(SB, "docs", "data.csv")) and
     not os.path.exists(os.path.join(SB, "data.csv"))),
    ("Thay 'beta' thanh 'BETA' trong docs/notes.txt",
     lambda: "BETA" in open(os.path.join(SB, "docs",
                                         "notes.txt")).read()),
    ("Tao file empty.txt rong + file nonempty.txt co chu x",
     lambda: os.path.getsize(os.path.join(SB, "empty.txt")) == 0 and
     open(os.path.join(SB, "nonempty.txt")).read().strip() == "x"),
    ("Ghi so file .py trong src vao py.txt (la so 2)",
     lambda: open(os.path.join(SB, "py.txt")).read().strip() == "2"),
    ("Ghi dong dau tien cua docs/notes.txt vao first.txt",
     lambda: open(os.path.join(SB, "first.txt")).read().strip() == "alpha"),
    ("Tao thu muc nested/a/b va file nested/a/b/deep.txt ghi 'deep'",
     lambda: open(os.path.join(SB, "nested", "a", "b",
                               "deep.txt")).read().strip() == "deep"),
    ("Xoa thu muc docs va tao lai docs/ voi file new.txt ghi 'new'",
     lambda: open(os.path.join(SB, "docs", "new.txt")).read().strip() ==
     "new" and not os.path.exists(os.path.join(SB, "docs",
                                                "notes.txt"))),
]


def run_pc(cmds):
    reset_sandbox()
    for line in cmds:
        s = line.strip().lstrip("$ ").strip()
        if not s or s.startswith("#"):
            continue
        if any(d in s for d in DENY):
            return False, "lenh cam"
        try:
            r = subprocess.run(s, shell=True, capture_output=True, text=True,
                               timeout=15, cwd=SB)
            if r.returncode != 0:
                return False, f"exit {r.returncode}: {(r.stderr or '')[-200:]}"
        except subprocess.TimeoutExpired:
            return False, "timeout"
        except Exception as e:
            return False, str(e)[:200]
    return True, "chay xong"


def main():
    log("probe moi truong")
    try:
        import pygame  # noqa
        have_pygame = True
    except Exception:
        have_pygame = False
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
                        r = sh(f"{p} --background --python-expr "
                               f"\"import bpy; print('BL-OK')\"", timeout=180)
                        if "BL-OK" in (r.stdout or ""):
                            blender_bin = p
                            break
                break
    log(f"pygame={have_pygame} blender={blender_bin}")

    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    basedirs = [os.path.dirname(p) for p in
                sum([[os.path.join(r, f) for f in fs
                      if f == "model.safetensors"]
                     for r, _, fs in os.walk("/kaggle/input")], [])]
    orn = next((d for d in basedirs
                if "ornith" in d or "ornbase" in d), None)
    if orn is None:
        # Rap 4 shards -> /tmp/ornbase (RTX offline)
        shards = {}
        for r, _, fs in os.walk("/kaggle/input"):
            for f in fs:
                if f.startswith("model-0000") and f.endswith(".safetensors"):
                    shards[f] = r
        if len(shards) >= 4:
            orn = "/tmp/ornbase"
            os.makedirs(orn, exist_ok=True)
            for f, d in sorted(shards.items()):
                dst = os.path.join(orn, f)
                if not os.path.exists(dst):
                    os.symlink(os.path.join(d, f), dst)
            NEED = ["model.safetensors.index.json", "config.json",
                    "tokenizer.json", "tokenizer_config.json", "vocab.json",
                    "chat_template.jinja"]
            for r, _, fs in os.walk("/kaggle/input"):
                if "model.safetensors.index.json" in fs:
                    for f in NEED:
                        src, dst = os.path.join(r, f), os.path.join(orn, f)
                        if os.path.isfile(src) and not os.path.exists(dst):
                            os.symlink(src, dst)
                    break
            log(f"rap base tu {len(shards)} shards -> {orn}")
    if orn is None:
        # Tu tai base ve /tmp (khong phu thuoc attach, can mang)
        sh("pip install -q huggingface_hub")
        from huggingface_hub import snapshot_download
        orn = "/tmp/ornbase"
        snapshot_download("ornith-ai/Ornith-1.5-9B", local_dir=orn,
                          allow_patterns=["*.safetensors", "*.json",
                                          "*.jinja", "*.model", "LICENSE*"],
                          max_workers=4)
    log(f"base ornith={orn}")
    assert orn, "thieu base Ornith"
    adirs = [os.path.dirname(p) for p in
             sum([[os.path.join(r, f) for f in fs
                   if f == "adapter_model.safetensors"]
                  for r, _, fs in os.walk("/kaggle/input")], [])]
    o1 = next((d for d in adirs if "adapter-o1" in d), None)
    log(f"adapter o1={o1}")
    loop1 = next((d for d in adirs if "adapter-loop1" in d), None)
    log(f"adapter loop1={loop1}")
    ab1 = next((d for d in adirs if "adapter-ab1" in d), None)
    log(f"adapter ab1={ab1}")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 2**30
    use_bnb = vram_gb < 20
    log(f"vram={vram_gb:.0f}G -> {'bnb-4bit' if use_bnb else 'bf16 full'}")
    wheels = None
    for root, _, files in os.walk("/kaggle/input"):
        if any("bitsandbytes" in f and f.endswith(".whl")
               for f in files):
            wheels = root
            break
    if wheels:
        sh(f"pip install --no-index --no-deps --find-links {wheels} "
           f"bitsandbytes")
    import gc
    # torchao image (0.10) bi peft 0.20 tu choi (>0.16 moi chiu); bench
    # khong dung torchao -> go luon cho peft bo qua check version
    sh("pip uninstall -y torchao")
    from peft import PeftModel

    def load_cfg(ad):
        if use_bnb:
            m = AutoModelForCausalLM.from_pretrained(
                orn, quantization_config=bnb, device_map="auto")
        else:
            m = AutoModelForCausalLM.from_pretrained(
                orn, torch_dtype=torch.bfloat16, device_map="auto")
        if ad is not None:
            m = PeftModel.from_pretrained(m, ad)
        m.eval()
        return m

    tok = AutoTokenizer.from_pretrained(orn)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    tok.padding_side = "left"
    EVAL_BATCH = 8 if use_bnb else 32
    cfgs = [("ornith-base", None, True), ("base-raw", None, False)]
    if o1:
        cfgs.append(("o1", o1, False))
    if loop1:
        cfgs.append(("loop1", loop1, False))
    if ab1:
        cfgs.append(("ab1", ab1, False))
    log(f"configs={[c for c, _, _ in cfgs]}")

    tasks = ([("game", GAME_SYS, t) for t in PYGAME] +
             [("unity", UNITY_SYS, t) for t in UNITY] +
             [("bpy", BPY_SYS, t) for t in BPY])
    totals, detail = {}, []
    for name, ad, use_chat in cfgs:
        model = load_cfg(ad)
        log(f"eval config={name} batch={EVAL_BATCH}")
        pstrs = []
        for kind, sysp, spec in tasks:
            if use_chat:
                pstrs.append(tok.apply_chat_template(
                    [{"role": "user",
                      "content": f"{sysp}\nTask: {spec}\nCode:\n"}],
                    tokenize=False, add_generation_prompt=True))
            else:
                pstrs.append(f"{sysp}\nTask: {spec}\nCode:\n")
        gens_all = []
        for i in range(0, len(pstrs), EVAL_BATCH):
            chunk = pstrs[i:i + EVAL_BATCH]
            try:
                enc = tok(chunk, return_tensors="pt", padding=True,
                          truncation=True,
                          max_length=2048).to(model.device)
                out = model.generate(
                    **enc, max_new_tokens=MAX_NEW,
                    do_sample=False, pad_token_id=tok.eos_token_id)
                gens_all.extend(tok.batch_decode(
                    out[:, enc["input_ids"].shape[1]:],
                    skip_special_tokens=True))
            except Exception as e:
                log(f"gen loi batch {name}/{i}: {e}")
                gens_all.extend([""] * len(chunk))
        ts = {"game": 0, "unity": 0, "bpy": 0, "pc": 0}
        for (kind, sysp, spec), gen in zip(tasks, gens_all):
            gen = strip_fences(gen)
            if kind == "game":
                ok, surv = run_pygame(gen, have_pygame)
                s = score_pygame(gen, ok, surv)
            elif kind == "unity":
                s = score_unity(gen)
            else:
                s = run_bpy(gen, blender_bin)
            ts[kind] += s
            detail.append({"cfg": name, "kind": kind, "spec": spec,
                           "score": s, "gen": gen[:1500]})
        # --- track dieu khien may tinh (single-shot commands) ---
        pc_ok = 0
        for spec, check in PC_TASKS:
            prompt = f"{PC_SYS}\nTask: {spec}\nCommands:\n"
            ids = tok(prompt, return_tensors="pt").to(model.device)
            try:
                out = model.generate(
                    **ids, max_new_tokens=128,
                    do_sample=False, pad_token_id=tok.eos_token_id)
                gen = tok.decode(out[0][ids["input_ids"].shape[1]:],
                                 skip_special_tokens=True)
                gen = strip_fences(gen)
                lines = [l for l in gen.splitlines() if l.strip()]
                ok_run, _ = run_pc(lines)
                good = False
                if ok_run:
                    try:
                        good = bool(check())
                    except Exception:
                        good = False
                if good:
                    pc_ok += 1
            except Exception as e:
                log(f"pc loi {name}/{spec[:25]}: {e}")
        ts["pc"] = pc_ok * 5
        detail.append({"cfg": name, "kind": "pc-summary",
                       "spec": f"{pc_ok}/{len(PC_TASKS)}", "score": ts["pc"],
                       "gen": ""})
        totals[name] = {**ts, "total": ts["game"] + ts["unity"] +
                        ts["bpy"] + ts["pc"]}
        log(f"SCORE {name}: game={ts['game']} unity={ts['unity']} "
            f"bpy={ts['bpy']} pc={ts['pc']} TOTAL={totals[name]['total']}/400")
        del model
        gc.collect()
        torch.cuda.empty_cache()
    with open(os.path.join(WORK, "bench_scores.json"), "w") as f:
        json.dump(totals, f, indent=2)
    with open(os.path.join(WORK, "bench_detail.jsonl"), "w",
              encoding="utf-8") as f:
        for row in detail:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log("BENCH DONE " + json.dumps({k: v["total"]
                                    for k, v in totals.items()}))


if __name__ == "__main__":
    main()
