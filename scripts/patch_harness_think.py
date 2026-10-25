# -*- coding: utf-8 -*-
"""patch_harness_think.py - theo chi danh user: "cho models nghi, tang max-new,
dung vLLM tang toc".

1) REASON_MAX 256 -> 512 (model duoc nghi lau hon)
2) Policy.act: khi model KET THUC lời nghi mà KHONG co dong "ACTION:" ->
   a) quet toan bo text lay action bare (CLICK x y / TYPE .. / KEY ..)   [fallback 1]
   b) SINH LAI 1 lan voi prompt nang + temperature 0.7                   [fallback 2]
   -> het: tra None (harness bao 'stuck' nhu truoc)
   Muc dich: model hay ket thieu "THINK: ..." roi dung y tren man hinh ->
   vong lap vo han; fallback 2 (sampling) pha vong lap do.
3) Ghi lai raw + fallback info de phan tich.
"""
import io

P = "phase14-desktop/harness.py"
s = io.open(P, encoding="utf-8").read()

# 1) max-new 256 -> 512
if "REASON_MAX = 256" in s:
    s = s.replace("REASON_MAX = 256", "REASON_MAX = int(__import__('os').environ.get('ENV_REASON_MAX', '512'))")
    print("REASON_MAX -> 512 (env ENV_REASON_MAX)")

OLD = '''        with torch.no_grad():
            gen = self.model.generate(**inputs, max_new_tokens=REASON_MAX,
                                      do_sample=False)
        n_new = int(gen.shape[1] - inputs["input_ids"].shape[1])
        ans = self.processor.batch_decode(
            gen[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True)[0]
        self.last = {"n_new": n_new}
        return ans.strip(), parse_action_v2(ans)'''

NEW = '''        with torch.no_grad():
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
                                  "text": f"Task: {task}\\n"
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
                    ans = ans + "\\n[regen] " + ans2
                except Exception as e:
                    fb = "regen_loi:%s" % str(e)[:60]
        self.last = {"n_new": n_new, "fallback": fb}
        return ans.strip(), act'''

if OLD in s:
    s = s.replace(OLD, NEW)
    print("Policy.act: them fallback (bare + regen)")
else:
    print("!! khong khop Policy.act")

# them ham quet action bare
HELPER = '''

def _scan_bare_action(text):
    """Fallback: quet text tim action bare (CLICK x y / TYPE .. / KEY ..) - dung
    khi model viet pro se nhung quen dong 'ACTION:'."""
    if not text:
        return None
    t = text.strip()
    m = re.search(r"(CLICK|TYPE|KEY|MOVE|DRAG|SCROLL)\\b[^\\n]{0,60}", t, re.I)
    if not m:
        return None
    s = m.group(0).strip()
    verb = m.group(1).upper()
    arg = s[len(m.group(1)):].strip()
    if verb == "CLICK":
        p = arg.split()
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            return ("click", [int(p[0]), int(p[1])])
        return None
    if verb == "TYPE":
        return ("type", arg) if arg else None
    if verb == "KEY":
        return ("key", arg.lower()) if arg else None
    if verb == "MOVE":
        p = arg.split()
        if len(p) >= 2 and p[0].isdigit() and p[1].isdigit():
            return ("move", [int(p[0]), int(p[1])])
        return None
    return None

'''
if "_scan_bare_action" in s and "def _scan_bare_action" not in s:
    s = s.replace("def parse_action_v2(text):", HELPER.strip() + "\n\ndef parse_action_v2(text):", 1)
    print("them _scan_bare_action")
elif "def _scan_bare_action" in s:
    print("_scan_bare_action da co")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
try:
    compile(s, "x", "exec")
    print("compile OK")
except SyntaxError as e:
    print("LOI:", e.lineno, e.msg)
