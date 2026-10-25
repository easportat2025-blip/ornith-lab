# -*- coding: utf-8 -*-
"""fix_desktop_bench_model.py - sua kernel desktop-bench (GLM) cho chay duoc.

Loi: "Unsloth: I think you're passing a tokenizer, not the model to for_inference!"
=> EXP_SRC (serving-stack) goi FastVisionModel.for_inference() - API khac ban
unsloth trong wheels. Kernel bench V21 (dang chay duoc) KHONG dung for_inference:
transformers.from_pretrained + peft LoRA + Policy tu viet.

Sua: trong main(), thay phan "exp.* + unsloth" bang cach load MODEL + build
Policy giong het kernel_bench_v21 (copy nguyen doan load_model/Policy).
Giu nguyen harness (env that + app that) va phan ghi ket qua.
"""
import io
import re

P = "phase13-gui/kernel_desktop_bench/desktop_bench_kernel.py"
s = io.open(P, encoding="utf-8").read()

# --- 1) them Policy + load_model (theo kernel bench v21) vao file ---
BENCH = io.open("phase13-gui/kernel_bench_v21/bench_v15_kernel.py",
                encoding="utf-8").read()
i = BENCH.find("def load_model():")
j = BENCH.find("class Policy:")
lm = BENCH[i:j]
pl_end = BENCH.find("\ndef ", j)
pl = BENCH[j:pl_end if pl_end > 0 else j + 2000]

BLOCK = '''

# ==== FIX (DeepSeek): load model + Policy theo kernel bench V21 (da chay duoc)
# Khong dung unsloth for_inference (API khac ban wheels -> loi "passing a
# tokenizer, not the model"). Dung transformers + peft nhu bench V21.
def db_load_model():
    import torch
    import transformers
    dt = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    cls = None
    for name in ("Qwen3_5ForConditionalGeneration",
                 "AutoModelForImageTextToText", "AutoModelForCausalLM"):
        cls = getattr(transformers, name, None)
        if cls is not None:
            log("model class: %s" % name)
            break
    assert cls, "khong tim thay model class qwen3_5"
    model = cls.from_pretrained(ORN, dtype=dt, device_map="auto")
    model.eval()
    log("model load xong: %s" % type(model).__name__)
    return model


class DBPolicy:
    """Policy giong het bench V15.5 (action-only, khong prose)."""

    def __init__(self, model, processor, lora_dir):
        self.model = model
        self.processor = processor
        self.last = {"n_new": None, "parse": None}
        try:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(model, lora_dir)
            log("LoRA da attach: %s" % lora_dir)
        except Exception as e:
            log("attach LoRA that bai: %s" % str(e)[:120])

    def act(self, shot, task, t):
        import torch
        from PIL import Image
        img = Image.open(shot).convert("RGB")
        msgs = [{"role": "system", "content": [{"type": "text", "text": SYS}]},
                {"role": "user", "content": [{"type": "image"},
                                             {"type": "text",
                                              "text": "Task: %s" % task}]}]
        text = self.processor.apply_chat_template(
            msgs, tokenize=False, add_generation_prompt=True,
            enable_thinking=False)
        inputs = self.processor(text=[text], images=[img],
                                return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            gen = self.model.generate(**inputs, max_new_tokens=24,
                                      do_sample=False)
        ans = self.processor.batch_decode(
            gen[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True)[0]
        self.last["raw"] = ans
        m = re.search(r"CLICK\\s*(\\d{1,4})\\s*[,;\\s]\\s*(\\d{1,4})", ans, re.I)
        if m:
            self.last["n_new"] = 1
            return ans, "CLICK %s %s" % (m.group(1), m.group(2))
        m2 = re.search(r"TYPE\\s+(.+)", ans, re.I)
        if m2:
            self.last["n_new"] = 1
            return ans, "TYPE %s" % m2.group(1).strip()
        m3 = re.search(r"KEY\\s+([A-Za-z]+)", ans, re.I)
        if m3:
            self.last["n_new"] = 1
            return ans, "KEY %s" % m3.group(1)
        self.last["n_new"] = 0
        return ans, None

'''

if "class DBPolicy" not in s:
    # insert truoc def main()
    k = s.find("\ndef main():")
    assert k > 0, "khong tim thay def main()"
    s = s[:k] + BLOCK + s[k:]
    print("da them DBPolicy + db_load_model")

# --- 2) trong main(): bo phan exp/unsloth, dung db_load_model + DBPolicy ---
old_pat = re.compile(r"        # 4\) base \+ adapter \+ processor\n"
                     r"        exp\.ass[\s\S]{0,2500}?run_stack\(", re.M)
mm = old_pat.search(s)
if mm:
    print("tim thay khoi exp/unsloth (dung %d char)" % (mm.end() - mm.start()))
else:
    # fallback: in phan xung quanh exp.assemble_base
    k = s.find("exp.assemble_base")
    print("--- vung quanh exp.assemble_base ---")
    print(s[max(0, k - 400):k + 1200])
    raise SystemExit("can sua tay theo vung tren")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("OK")
