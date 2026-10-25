"""Soup 2 adapters (main ckpt8000 + aux ckpt7000) bang trung binh mmap,
nhe RAM. Output: data\\soup\\soup50/."""
import json
import os

A = r"C:\Users\Admin\Desktop\New folder\data\soup\mainCkpt\out\checkpoint-8000\adapter_model.safetensors"
B = r"C:\Users\Admin\Desktop\New folder\data\soup\branchB\out\checkpoint-7000\adapter_model.safetensors"
OUT = r"C:\Users\Admin\Desktop\New folder\data\soup\soup50"
RATIO_A = 0.5


def main():
    os.makedirs(OUT, exist_ok=True)
    from safetensors import safe_open
    from safetensors.numpy import save_file
    import numpy as np
    fa = safe_open(A, framework="np")
    fb = safe_open(B, framework="np")
    ka, kb = set(fa.keys()), set(fb.keys())
    print("keys A:", len(ka), "keys B:", len(kb), "chung:", len(ka & kb))
    assert ka == kb, "keys khac nhau, khong soup duoc"
    out = {}
    for i, k in enumerate(sorted(ka)):
        ta = fa.get_tensor(k).astype("float32")
        tb = fb.get_tensor(k).astype("float32")
        out[k] = (ta * RATIO_A + tb * (1 - RATIO_A)).astype(
            str(fa.get_tensor(k).dtype))
        if i % 100 == 0:
            print(f"  {i}/{len(ka)}", flush=True)
    save_file(out, os.path.join(OUT, "adapter_model.safetensors"))
    del out
    import shutil
    shutil.copy(os.path.join(os.path.dirname(A), "adapter_config.json"),
                os.path.join(OUT, "adapter_config.json"))
    info = {"a": "main-ckpt8000", "b": "aux-ckpt7000", "ratio_a": RATIO_A,
            "n_tensors": len(ka)}
    json.dump(info, open(os.path.join(OUT, "soup_info.json"), "w"),
              indent=2)
    print("SOUP DONE:", OUT)


if __name__ == "__main__":
    main()
