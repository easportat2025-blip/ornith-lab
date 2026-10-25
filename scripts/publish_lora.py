# -*- coding: utf-8 -*-
"""
publish_lora.py - DONG VONG "train -> publish adapter -> verify" cho adapter
LoRA moi (v23/v24/...), thay the ban hardcode cua upload_lora_v22.py.

Lam gi:
  1) lay adapter:
       --src <dir>      : dung thu muc co san (VD out_sft_v24_B/gui_lora)
       --kernel <slug>  : tai 'gui_lora/*' tu output cua kernel da xong
  2) staging + dataset-metadata.json (id = <owner>/<slug>)
  3) 'kaggle datasets create' (hoac 'version' neu da co)
  4) doi READY bang 'kaggle datasets files' (KHONG dung 'status' - status
     tra 403/404 khi dataset dang processing => false positive)
  5) VERIFY: van tay TRONG SO cua adapter da upload == adapter local
     (sha256 tren tensor - on dinh qua moi cach serialize lai)

Dung:
    python scripts/publish_lora.py --kernel dieniw/ornith-gui-sft-v24 \
        --slug dieniw/ornith-gui-lora-v24 --acc B
    python scripts/publish_lora.py --src phase13-gui/out_sft_v24_B/gui_lora \
        --slug dieniw/ornith-gui-lora-v24 --acc B --check-only
ASCII-only source.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"
ENV["PYTHONIOENCODING"] = "utf-8"

FILES = ["adapter_config.json", "adapter_model.safetensors",
         "chat_template.jinja", "processor_config.json", "tokenizer.json",
         "tokenizer_config.json", "README.md"]


def run(cmd, timeout=3600, retry=4):
    """Chay lenh, retry khi Kaggle tra 429 (rate limit) voi backoff."""
    wait = 20
    for i in range(retry + 1):
        p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=timeout)
        out = (p.stdout or b"").decode("utf-8", "replace")
        err = (p.stderr or b"").decode("utf-8", "replace")
        blob = out + err
        if "429" in blob and "Too Many Requests" in blob and i < retry:
            print("   [429] rate limit -> cho %ds roi thu lai (%d/%d)"
                  % (wait, i + 1, retry))
            time.sleep(wait)
            wait = min(wait * 2, 180)
            continue
        return p.returncode, out, err
    return p.returncode, out, err


def fetch(kernel, dest):
    os.makedirs(dest, exist_ok=True)
    rc, out, err = run(["kaggle", "kernels", "output", kernel, "-p", dest,
                        "--force", "--file-pattern", "gui_lora/.*"], timeout=3600)
    print("   tai output: rc=%s %s" % (rc, (out or err)[-160:].replace("\n", " ")))
    for base, _d, files in os.walk(dest):
        if "adapter_model.safetensors" in files:
            return base
    return None


def fingerprint(path):
    from safetensors.torch import safe_open
    import hashlib
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="")
    ap.add_argument("--kernel", default="")
    ap.add_argument("--slug", required=True, help="owner/slug cua dataset moi")
    ap.add_argument("--acc", default="B", choices=["A", "B"])
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--title", default="")
    a = ap.parse_args()

    src = a.src
    if not src and a.kernel:
        tmp = os.path.join(tempfile.gettempdir(), "mimo_lora_pub_" +
                           a.kernel.replace("/", "_"))
        # da co adapter trong thu muc tam? DUNG LAI (khong tai lai 465MB)
        src = None
        if os.path.isdir(tmp):
            for base, _d, files in os.walk(tmp):
                if "adapter_model.safetensors" in files:
                    src = base
                    print("   dung lai adapter da tai:", src)
                    break
        if not src:
            src = fetch(a.kernel, tmp)
        if not src:
            print("FAIL: khong tai duoc adapter tu", a.kernel)
            return 1
        print("   adapter tai ve:", src)
    if not src:
        print("dung: --src <dir> hoac --kernel <slug>")
        return 2
    if not os.path.isdir(src):
        print("FAIL: khong co thu muc:", src)
        return 1
    ap_path = os.path.join(src, "adapter_model.safetensors")
    if not os.path.exists(ap_path):
        print("FAIL: thieu adapter_model.safetensors trong", src)
        return 1
    fp, n = fingerprint(ap_path)
    print("== van tay trong so: %s (%d tensor)" % (fp[:32], n))

    stage = os.path.join(ROOT, "phase13-gui",
                         "lora_pub_" + a.slug.replace("/", "_"))
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage, exist_ok=True)
    got = []
    for f in FILES:
        s = os.path.join(src, f)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(stage, f))
            got.append(f)
    if "adapter_model.safetensors" not in got:
        print("FAIL: staging thieu adapter_model.safetensors")
        return 1
    _t = (a.title or ("Ornith GUI LoRA %s" % a.slug.split("/")[-1])).strip()
    if not (6 <= len(_t) <= 50):   # Kaggle: title 6..50 ky tu
        _t = _t[:50].rstrip(" -_,")
        if len(_t) < 6:
            _t = "Ornith GUI LoRA"
        print("   [FIX] title cat con %d ky tu: %s" % (len(_t), _t))
    meta = {"title": _t, "id": a.slug, "licenses": [{"name": "other"}]}
    with io.open(os.path.join(stage, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("   staging: %s (%d file)" % (stage, len(got)))

    if a.check_only:
        print("== CHECK-ONLY (khong upload) ==")
        return 0

    keyvar = "KAGGLE_KEY_B" if a.acc == "B" else "KAGGLE_KEY_A"
    _owner = "dieniw" if a.acc == "B" else "khoadangnguye"
    ENV["KAGGLE_KEY"] = (os.environ.get(keyvar)
                         or os.environ.get("KAGGLE_KEY") or "")
    if not ENV["KAGGLE_KEY"]:
        # key thuong chi co trong HKCU\Environment, khong co trong env
        try:
            sys.path.insert(0, os.path.join(ROOT, "scripts"))
            from upload_staging import key_for
            ENV["KAGGLE_KEY"] = key_for(_owner)
        except Exception:
            ENV["KAGGLE_KEY"] = ""
    ENV["KAGGLE_USERNAME"] = _owner
    if not ENV["KAGGLE_KEY"]:
        print("FAIL: thieu %s trong HKCU" % keyvar)
        return 1

    rc, out, err = run(["kaggle", "datasets", "create", "-p", stage])
    blob = (out + err)
    if rc != 0 and "already exists" in blob.lower():
        rc, out, err = run(["kaggle", "datasets", "version", "-p", stage])
        blob = (out + err)
    print("   create/version rc=%s | %s" % (rc, blob[-200:].replace("\n", " ")))
    if rc != 0:
        return 1
    # doi READY bang 'datasets files' (status co the 403/404 khi processing)
    for i in range(40):
        rc2, out2, err2 = run(["kaggle", "datasets", "files", a.slug],
                               timeout=300)
        t = (out2 + err2)
        if "adapter_model.safetensors" in t:
            print("   [OK] dataset da co adapter_model.safetensors (vong %d)"
                  % (i + 1))
            break
        time.sleep(15)
    else:
        print("   [!] chua thay adapter trong dataset sau 10 phut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
