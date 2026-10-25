"""Phase 3 bench — 60 task, cham base vs r1 vs r2 theo SCORING.md.
GPU T4, OFFLINE. Eval seed co dinh 123."""
import ast
import json
import os
import random
import subprocess
import sys
import time

WORK = "/kaggle/working"
EVAL_SEED = 123
MAX_NEW = 256


def log(m):
    print(f"[bench] {m}", flush=True)


def sh(cmd, timeout=300):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    return r


def find_dirs_with(fname):
    hits = []
    for root, _, files in os.walk("/kaggle/input"):
        if fname in files:
            hits.append(root)
    return hits


PYGAME = [
    "Snake an moi dai ra, thua khi dam tuong hoac tu can, co diem",
    "Pong 2 nguoi choi phim W/S va len/xuong, co diem den 5 la thang",
    "Breakout pha gach, 3 mang, thanh do dieu khien bang chuot",
    "Flappy bird vuot ong, space de bay, co diem cao nhat",
    "Ban may bay: tau di chuyen trai/phai, space ban dan, dich roi xuong",
    "Tetris don gian: 7 khoi, xoay, xoa hang day, tinh diem",
    "Maze random: tim duong ra khoi me cung trong thoi gian gioi han",
    "Clicker: bam chuot cang nhanh cang nhieu diem trong 30 giay",
    "Platformer: nhan vat chay/nhay qua cac be, cham gai la thua",
    "Asteroids: tau xoay 360 do, ban da, da vo thanh manh nho",
    "Memory match: lat 8 cap the giong nhau, dem so luot",
    "Simon: lap lai day mau am thanh ngay cang dai",
    "Dodge: ne cac vien dan roi tu tren trong 60 giay",
    "Catcher: hung do roi, trung bom tru mang",
    "Runner vo han: nhay/ electoral college truong, toc do tang dan",
    "Frogger: qua duong ne xe roi qua song nhay len go",
    "Invaders: hang dich di chuyen ngang va do xuong, ban het la thang",
    "Tennis don gian: 1 nguoi vs AI danh bong qua luoi",
    "Minesweeper 9x9 10 min: mo o, cam co, thang khi mo het o an toan",
    "2048: truot gop o giong nhau den 2048 la thang",
]
UNITY = [
    "Player controller di chuyen WASD + nhay, xoay camera theo chuot",
    "Camera follow nhan vat muot co do tre va gioi han bien",
    "Enemy duoi theo player khi vao tam nhin, danh can chien",
    "Nhat coin xoay tron, cong diem, phat am thanh",
    "Mau player: trung dan tru mau, het mau chet va respawn",
    "Spawner dich theo dot, moi dot tang so luong",
    "Ban dan tu player theo huong nhin, dan co thoi gian song",
    "Cua mo khi nhan cong tac, dong khi roi khoi",
    "UI diem + mang cap nhat realtime tren man hinh",
    "Pause menu: Esc dung game, co nut tiep tuc/choi lai/thoat",
    "NPC tuan tra giua cac diem, thay player thi duoi",
    "Dem nguoc thoi gian, het gio thua, qua man cong gio",
    "Be di chuyen cho player dung len di theo",
    "Checkpoint luu vi tri, chet hoi sinh o checkpoint gan nhat",
    "Hoi thoai NPC: lai gan hien bang chu, E de next",
    "Double jump + dash co hoi",
    "Chay nhanh ton stamina, dung lai hoi phuc",
    "Wave enemy tang dan, hien so wave tren UI",
    "Luu diem cao nhat bang PlayerPrefs",
    "Vat pham xoay collectible tu hut ve player khi lai gan",
]
BPY = [
    "Ban ghe go don gian: mat ngoi + 4 chan + lung tua",
    "Ban an tron + 1 den ngu tren ban",
    "Den ban co chup den va anh sang point",
    "Oto lowpoly: than + 4 banh tru + cua so",
    "Ngoi nha: tuong + mai tam giac + cua + 2 cua so",
    "Cay thap: than tru + 3 tang la non",
    "Thanh kiem: luoi dai + chuoi kiem + can",
    "Coc uong nuoc co quai cam",
    "Cau thang 10 bac di len",
    "Hang rao 8 coc + 2 thanh ngang",
    "Ten lua: than + mui nhon + 3 canh + cua so tron",
    "Robot do choi: dau hop + than + tay chan tru",
    "Cay cau cong qua song co lan can 2 ben",
    "Den long do treo co hoa van don gian",
    "Lau dai mini: 4 thap tru + tuong bao",
    "Giong nuoc co voi va tay cam",
    "May bay do choi: than + canh + duoi",
    "Dong ho treo tuong kim gio phut chay duoc",
    "Gia sach 3 tang co vai quyen sach",
    "Thuyen buom: than + cot + canh buom tam giac",
]
UNITY_APIS = ["transform", "GetComponent", "Instantiate", "Rigidbody",
              "Collider", "Input", "Time", "Debug", "GameObject",
              "Vector3", "Camera", "AudioSource", "Animator"]
ALPACA = ("Below is an instruction. Write a response.\n\n"
          "### Instruction:\n{}\n\n### Input:\n{}\n\n### Response:\n{}")


def strip_fences(code):
    # Lot bo markdown fence de cham code that (cong bang cho moi config).
    import re
    m = re.search(r"```(?:python|csharp|py|cs)?\s*\n(.*?)```",
                  code, re.S)
    if m:
        return m.group(1).strip()
    lines = [l for l in code.splitlines()
             if not l.strip().startswith("```")]
    return "\n".join(lines).strip()

GAME_SYS = ("You are a game code generator. Output ONE complete single-file "
            "python pygame program only, no explanation. It must run with "
            "`SDL_VIDEODRIVER=dummy` (no real display needed).")
UNITY_SYS = ("You are a Unity C# generator. Output ONE complete C# "
             "MonoBehaviour script only, no explanation.")
BPY_SYS = ("You are a Blender bpy generator. Output ONE complete python "
           "script using bpy only, no explanation. Assume default scene.")


def score_pygame(code, run_ok, survived):
    s, why = 0, []
    if run_ok:
        s += 2
    else:
        why.append("crash")
    if survived:
        s += 1
    else:
        why.append("chet som")
    keys = ["pygame.init", "display.set_mode", "event.get",
            "Clock", "flip"]
    alt = ["tick", "update"]
    hit = sum(1 for k in keys if k in code)
    hit += 1 if any(a in code for a in alt) else 0
    if hit >= 4:
        s += 1
    else:
        why.append("thieu loop")
    if any(w in code for w in ["score", "lives", "level", "health"]):
        s += 1
    else:
        why.append("thieu state")
    return min(s, 5), ",".join(why) if why else "ok"


def score_unity(code):
    s, why = 0, []
    if "MonoBehaviour" in code and "class" in code:
        s += 1
    else:
        why.append("no-mono")
    if "void Start" in code and "void Update" in code:
        s += 1
    else:
        why.append("no-start/update")
    if code.count("{") == code.count("}") and "{" in code:
        s += 1
    else:
        why.append("brace")
    hit = sum(1 for a in UNITY_APIS if a in code)
    if hit >= 5:
        s += 2
    elif hit >= 3:
        s += 1
    else:
        why.append("it-api")
    return min(s, 5), ",".join(why) if why else "ok"


def run_pygame(code, have_pygame):
    fp = os.path.join(WORK, "_g.py")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(code)
    if not have_pygame:
        try:
            ast.parse(code)
            return True, True, "no-pygame-fallback"
        except SyntaxError:
            return False, False, "syntax"
    env = dict(os.environ, SDL_VIDEODRIVER="dummy",
               SDL_AUDIODRIVER="dummy")
    try:
        p = subprocess.Popen([sys.executable, fp], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, env=env)
        try:
            _, err = p.communicate(timeout=15)
            err = err.decode(errors="ignore")[-500:]
            if p.returncode == 0:
                return True, True, "exit0"
            if "Traceback" in err or "Error" in err:
                return False, False, err[-100:]
            return True, True, "exit-non0-no-trace"
        except subprocess.TimeoutExpired:
            p.kill()
            _, err = p.communicate()
            err = err.decode(errors="ignore")[-500:]
            if "Traceback" in err:
                return False, False, err[-100:]
            return True, True, "song-15s"
    except Exception as e:
        return False, False, str(e)[:100]


def run_bpy(code, blender_bin):
    fp = os.path.join(WORK, "_b.py")
    png = os.path.join(WORK, "_r.png")
    if os.path.exists(png):
        os.remove(png)
    if blender_bin is None:
        try:
            ast.parse(code)
        except SyntaxError:
            return 0, "syntax"
        n = sum(1 for l in code.splitlines()
                if "bpy.ops.mesh" in l)
        return 2 + (1 if n >= 2 else 0) + 2, "no-blender-fallback"
    full = code + (f"\nimport bpy\nscene = bpy.context.scene\n"
                   f"scene.render.filepath = '{png}'\n"
                   f"scene.render.resolution_x = 256\n"
                   f"scene.render.resolution_y = 256\n"
                   f"bpy.ops.render.render(write_still=True)\n")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(full)
    r = sh(f"{blender_bin} --background --python {fp}", timeout=240)
    if r.returncode != 0 or not os.path.exists(png):
        return 0, "blender-fail"
    try:
        from PIL import Image
        import numpy as np
        a = np.asarray(Image.open(png).convert("L"), dtype=float)
        if a.std() <= 5:
            return 2, "anh-rong"
    except Exception:
        if os.path.getsize(png) < 10240:
            return 2, "anh-nghi-rong"
    n = sum(1 for l in code.splitlines() if "bpy.ops.mesh" in l)
    return 4 + (1 if n >= 2 else 0), "ok"


def main():
    log("probe moi truong")
    try:
        import pygame  # noqa
        have_pygame = True
    except Exception:
        have_pygame = False
    log(f"pygame={have_pygame}")
    blender_bin = None
    tars = []
    for root, _, files in os.walk("/kaggle/input"):
        for f in files:
            if f.endswith(".tar.xz") and "blender" in f:
                tars.append(os.path.join(root, f))
    if tars:
        bd = os.path.join(WORK, "blender")
        os.makedirs(bd, exist_ok=True)
        sh(f"tar -xf {tars[0]} -C {bd}")
        cands = []
        for root, _, files in os.walk(bd):
            if "blender" in files:
                cands.append(os.path.join(root, "blender"))
        if cands:
            os.chmod(cands[0], 0o755)
            r = sh(f"{cands[0]} --background --python-expr "
                   f"\"import bpy; print('BL-OK')\"", timeout=120)
            if "BL-OK" in (r.stdout or ""):
                blender_bin = cands[0]
    log(f"blender={blender_bin}")

    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig)
    bases = [os.path.dirname(p) for p in
             sum([[os.path.join(r, f) for f in fs
                   if f == "model.safetensors"]
                  for r, _, fs in os.walk("/kaggle/input")], [])]
    adirs = [os.path.dirname(p) for p in
             sum([[os.path.join(r, f) for f in fs
                   if f == "adapter_model.safetensors"]
                  for r, _, fs in os.walk("/kaggle/input")], [])]
    log(f"base={bases} adapters={adirs}")
    if not bases:
        raise SystemExit("thieu base")
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True)
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
    from peft import PeftModel

    def pick(adirs, key):
        cands = [d for d in adirs if key in d]
        return cands[0] if cands else None

    r2 = pick(adirs, "adapter-r2")
    r3 = pick(adirs, "adapter-r3")
    r4 = pick(adirs, "adapter-r4")
    r6 = pick(adirs, "adapter-r6")
    main8k, aux7k, soup = None, None, None
    for root, _, files in os.walk("/kaggle/input"):
        if "adapter_model.safetensors" in files:
            if "adapter-main8k" in root:
                main8k = root
            elif "adapter-aux7k" in root:
                aux7k = root
            elif "soup50" in root:
                soup = root
    cfgs = [("base-chat", None, True)]
    if r4:
        cfgs.append(("r4", r4, False))
    if r6:
        cfgs.append(("r6", r6, False))
    log(f"configs={[(c, a) for c, a, _ in cfgs]}")

    def load_cfg(ad):
        # Load rieng tung config voi ten adapter MAC DINH de keys khop
        # 100% (load sai ten -> weights MISSING -> chay random).
        m = AutoModelForCausalLM.from_pretrained(
            bases[0], quantization_config=bnb, device_map="auto")
        if ad is not None:
            m = PeftModel.from_pretrained(m, ad)
        m.eval()
        return m

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(bases[0])
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    tok.padding_side = "left"
    EVAL_BATCH = 8

    tasks = ([("game", GAME_SYS, t) for t in PYGAME] +
             [("unity", UNITY_SYS, t) for t in UNITY] +
             [("bpy", BPY_SYS, t) for t in BPY])
    rnd = random.Random(EVAL_SEED)
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
        ts, scores = {t: 0 for t in ["game", "unity", "bpy"]}, []
        for (kind, sysp, spec), gen in zip(tasks, gens_all):
            gen = strip_fences(gen)
            if kind == "game":
                ok, surv, _ = run_pygame(gen, have_pygame)
                s, why = score_pygame(gen, ok, surv)
            elif kind == "unity":
                s, why = score_unity(gen)
            else:
                s, why = run_bpy(gen, blender_bin)
            ts[kind] += s
            scores.append(s)
            detail.append({"cfg": name, "kind": kind,
                           "spec": spec, "score": s, "why": why,
                           "gen": gen[:2000]})
        totals[name] = {**ts, "total": sum(scores),
                        "n": len(scores)}
        log(f"SCORE {name}: game={ts['game']} unity={ts['unity']} "
            f"bpy={ts['bpy']} TOTAL={sum(scores)}/300")
        del model
        gc.collect()
        torch.cuda.empty_cache()
        log(f"xa model {name} de nap config tiep theo")
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
