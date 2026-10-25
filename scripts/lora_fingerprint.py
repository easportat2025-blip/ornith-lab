# -*- coding: utf-8 -*-
"""
lora_fingerprint.py - "van tay" TRONG SO cua 1 adapter LoRA (canonical).

LY DO (22/10, @MiMo): byte hash cua adapter KHONG phai dinh danh ton tai
(safetensors serialize lai ra byte khac nhung weights giong het). => phai
bam vao TENSOR: sha256 tren (ten + dtype + shape + bytes) theo thu tu sort.
=> 2 adapter "khac byte" nhung cung weights se cho cung fingerprint.

Dung:
    python scripts/lora_fingerprint.py --file <adapter_model.safetensors>
    python scripts/lora_fingerprint.py --slug dieniw/ornith-gui-lora-v21
    python scripts/lora_fingerprint.py --slug <slug> --register
ASCII-only source.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "scripts", "lora_fingerprints.json")


def fingerprint(path):
    from safetensors.torch import safe_open
    h = hashlib.sha256()
    n = 0
    with safe_open(path, framework="pt", device="cpu") as f:
        for k in sorted(f.keys()):
            t = f.get_tensor(k)
            h.update(k.encode("utf-8"))
            h.update(str(t.dtype).encode("ascii"))
            h.update(str(tuple(t.shape)).encode("ascii"))
            h.update(t.contiguous().view(-1).numpy().tobytes())
            n += 1
    return h.hexdigest(), n


def fetch(slug, owner):
    tmp = os.path.join(tempfile.gettempdir(), "mimo_fp_" +
                       slug.replace("/", "_"))
    os.makedirs(tmp, exist_ok=True)
    env = dict(os.environ)
    env["KAGGLE_USERNAME"] = owner
    keyvar = "KAGGLE_KEY_B" if owner == "dieniw" else "KAGGLE_KEY_A"
    key = os.environ.get(keyvar)
    if not key:
        # key thuong chi nam trong HKCU\Environment, khong co trong process env
        try:
            sys.path.insert(0, os.path.join(ROOT, "scripts"))
            from upload_staging import key_for
            key = key_for(owner)
        except Exception:
            key = ""
    if key:
        env["KAGGLE_KEY"] = key
    cmd = ["kaggle", "datasets", "download", slug,
           "-f", "adapter_model.safetensors", "-p", tmp, "--unzip"]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0:
        print("tai that bai: %s" % (p.stderr or p.stdout)[-300:])
        return None
    for base, _d, files in os.walk(tmp):
        for f in files:
            if f == "adapter_model.safetensors":
                return os.path.join(base, f)
    return None


def load_reg():
    try:
        return json.load(io.open(REG, encoding="utf-8"))
    except Exception:
        return {}


def save_reg(reg):
    with io.open(REG, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=1, sort_keys=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    p = a.file
    slug = a.slug
    if slug and not p:
        owner, name = slug.split("/", 1)
        p = fetch(slug, owner)
        if not p:
            return 1
    if not p:
        print("dung: --file <path> hoac --slug <owner/slug>")
        return 2
    fp, n = fingerprint(p)
    print("%-46s %s  (%d tensor)" % (slug or p, fp[:32], n))
    if a.register and slug:
        reg = load_reg()
        reg[slug] = {"fp": fp, "n_tensor": n, "note": a.note}
        save_reg(reg)
        print("=> da dang ky vao scripts/lora_fingerprints.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
