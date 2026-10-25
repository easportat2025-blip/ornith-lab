# -*- coding: utf-8 -*-
# them muc vLLM vao RTX_OFFLINE_GUIDE.md
import io

P = "RTX_OFFLINE_GUIDE.md"
s = io.open(P, encoding="utf-8").read()
BLOCK = """
## 10. vLLM tren may RTX (nhanh gap 10-30x so voi `model.generate`)
> User: *"cu cho models nghi, nhieu k sao, tang max-new va co the dung vllm tang toc"*
> -> da thuc hien: `REASON_MAX` 256 -> **512** (moi kernel bench/rollout + harness) va
> harness **tu chuyen sang vLLM** neu co `ENV_VLLM_URL` ✓

### 10.1 Chay vLLM server (1 lan, offline)
```bash
# RTX 96GB: model 9B bf16 (~20GB) fit thoai mai
export HF_HUB_OFFLINE=1
python -m vllm.entrypoints.openai.api_server \\
  --model /path/to/ornith-base-or-adapter \\
  --served-model-name ornith \\
  --port 8000 --max-model-len 8192 --gpu-memory-utilization 0.85
# neu dung adapter: them --enable-lora --lora-modules ornith=/path/to/adapter
```

### 10.2 Tro harness/bench vao vLLM
```powershell
$env:ENV_VLLM_URL   = "http://127.0.0.1:8000/v1"
$env:ENV_VLLM_MODEL = "ornith"
$env:ENV_VLLM_KEY   = "EMPTY"
$env:ENV_REASON_MAX = "512"      # cho model nghi lau hon
python phase14-desktop\\harness.py --policy model --tasks T20_2048
```
- Harness dung `VLLMPolicy` (OpenAI-compatible `/chat/completions` + anh base64) -> **khong can load model local** ✓
- `max_new_tokens` la **tran** chu khong phai chi phi co dinh (model dung o EOS) -> tang thoai mai ✓
- Voi vLLM: bat **prefix caching** + **batching** de 4 episode chay song song van nhanh ✓

### 10.3 Luu y khi van dung HF generate (Kaggle GPU)
- Kaggle T4 16GB: model 9B **khong vua** vLLM bf16 -> dung AWQ/4bit hoac giu `transformers` ✓
- Kaggle GPU kernel co **internet OFF** -> vLLM phai cai tu wheels san (dong goi `.whl` vao dataset nhu `gemma12b-wheels` ✓)
"""
if "## 10. vLLM" not in s:
    s = s.rstrip() + "\n" + BLOCK
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("da them muc 10 (vLLM)")
else:
    print("da co muc 10")
