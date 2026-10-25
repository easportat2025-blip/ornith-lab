# -*- coding: utf-8 -*-
"""
build_colab_grpo.py - sinh script GRPO cho GOOGLE COLAB tu kernel Kaggle.

Nguyen tac (bai hoc 22/10): PATCH tu kernel da viet (logic reward da test
15/15 PASS) - KHONG viet lai tu dau.

Khac biet tren Colab:
  - WORK          -> /content/work
  - INPUT_ROOT    -> /content/data (2 file .zip da upload, giai nen vao
                     /content/data/<ten-dataset>/ de loader khop ten)
  - base model    -> snapshot_download tu HF (public, khong can token)
  - pip           -> pip tu PyPI (VM co internet)
  - 4-bit         -> T4 16GB khong vua bf16
  - max_steps     -> 3 (SMOKE: kiem tra API/import, khong can train het)

Dung:
    python scripts/build_colab_grpo.py
    # roi upload 2 zip + colab_grpo.py len VM roi exec
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "kernel_grpo_v1", "grpo_v1.py")
DST = os.path.join(ROOT, "phase13-gui", "colab_grpo", "colab_grpo.py")


def sub(s, old, new, tag):
    if old not in s:
        raise SystemExit("KHONG khop: %s\n---\n%s" % (tag, old[:200]))
    if s.count(old) != 1:
        raise SystemExit("KHONG duy nhat (%d): %s" % (s.count(old), tag))
    print("  ok: " + tag)
    return s.replace(old, new, 1)


def main():
    s = io.open(SRC, encoding="utf-8").read()

    # 1) duong dan
    s = sub(s, 'WORK = "/kaggle/working"', 'WORK = "/content/work"',
            "WORK")
    s = sub(s, 'ORN = "/tmp/ornbase"', 'ORN = "/content/base"',
            "ORN")
    s = sub(s, 'INPUT_ROOT = "/kaggle/input"',
            'INPUT_ROOT = "/content/data"', "INPUT_ROOT")

    # 2) tham so mac dinh cho smoke
    s = sub(s, 'N_PROMPT = int(os.environ.get("GRPO_NPROMPT", "300"))',
            'N_PROMPT = int(os.environ.get("GRPO_NPROMPT", "16"))',
            "N_PROMPT default 16 (smoke)")
    s = sub(s, 'max_steps=int(os.environ.get("GRPO_MAX_STEPS", "30")),',
            'max_steps=int(os.environ.get("GRPO_MAX_STEPS", "3")),',
            "max_steps default 3 (smoke)")
    s = sub(s, 'use_4bit = os.environ.get("GRPO_4BIT", "0") == "1"',
            'use_4bit = os.environ.get("GRPO_4BIT", "1") == "1"',
            "4-bit mac dinh (T4)")

    # 3) base model: HF snapshot thay cho copy tu Kaggle
    s = sub(s,
            '''    # 1) base model
    if not os.path.isdir(ORN):
        import glob
        import shutil as _sh
        dst = ORN
        os.makedirs(dst, exist_ok=True)
        files = []
        for d in sorted(glob.glob("/kaggle/input/datasets/*/ornbase-s*")):
            for f in glob.glob(os.path.join(d, "*")):
                files.append(f)
        log("base: %d file -> %s" % (len(files), dst))
        for f in files:
            try:
                _sh.copy2(f, dst)
            except Exception:
                pass''',
            '''    # 1) base model: tai tu HF (public -> khong can token)
    if not os.path.isdir(ORN) or not any(
            f.endswith(".safetensors") for f in os.listdir(ORN)):
        os.makedirs(ORN, exist_ok=True)
        from huggingface_hub import snapshot_download
        bid = os.environ.get("ORNITH_BASE_ID", "ornith-ai/Ornith-1.5-9B")
        log("tai base %s -> %s (10-25 phut lan dau)" % (bid, ORN))
        snapshot_download(repo_id=bid, local_dir=ORN, max_workers=4,
                          ignore_patterns=["*.pth", "original/*", "*.gguf"])
    log("base files: %d" % len(os.listdir(ORN)))''',
            "base tu HF")

    # 4) pip: tu PyPI (VM co internet) thay vi dataset wheels
    s = sub(s,
            '''def install_unsloth():
    """22/10: THIEU buoc nay -> kernel v1 chet 'No module named unsloth'.
    Cai tu dataset wheels (KHONG internet) - giong het kernel SFT."""
    import subprocess
    wheels = None
    for root, _d, files in os.walk(INPUT_ROOT):
        if any(f.startswith("unsloth-") and f.endswith(".whl") for f in files):
            wheels = root
            break
    assert wheels, "FAIL: thieu wheels unsloth (dataset gemma12b-wheels)"

    def sh(cmd, timeout=1800):
        log("pip: %s" % cmd[:100])
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        out = ((p.stdout or "") + (p.stderr or ""))[-300:]
        log("  rc=%s %s" % (p.returncode, out.replace("\\n", " ")[:150]))
        return p.returncode

    sh("pip install --no-index --no-deps --find-links %s "
       "unsloth unsloth_zoo trl bitsandbytes" % wheels)
    # peft/transformers co san trong image; dam bao dung version
    sh("pip install --no-index --no-deps --find-links %s peft" % wheels)''',
            '''def install_unsloth():
    """Colab: pip tu PyPI (VM co internet). Tren Kaggle: tu dataset wheels.
    22/10: THIEU buoc nay -> kernel v1 chet 'No module named unsloth'."""
    import subprocess

    def sh(cmd, timeout=2400):
        log("pip: %s" % cmd[:100])
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        out = ((p.stdout or "") + (p.stderr or ""))[-300:]
        log("  rc=%s %s" % (p.returncode, out.replace("\\n", " ")[:150]))
        return p.returncode

    # KHONG cai 'pillow' (ban preinstalled cua Colab khop torchvision;
    # nang len Pillow 13 => loi "Pillow version is incompatible with torchvision")
    sh("pip install -q -U unsloth unsloth_zoo trl peft datasets accelerate "
       "bitsandbytes")
    sh("pip install -q --no-deps qwen-vl-utils")
    try:
        import unsloth  # noqa: F401
        log("unsloth OK")
    except Exception as e:
        raise SystemExit("FAIL: unsloth import loi: %s" % e)''',
            "pip tu PyPI")

    # 5) giai nen 2 zip du lieu vao /content/data/<ten>
    s = sub(s,
            '''    # 2) reward set (TACH tap eval!)''',
            '''    # 1b) giai nen dataset da upload (ten thu muc phai trung ten dataset
    #     de loader khop)
    import zipfile
    for _z, _name in (("ornith-gui-traj.zip", "ornith-gui-traj"),
                      ("ornith-policy-replay-data.zip",
                       "ornith-policy-replay-data")):
        _zp = os.path.join("/content", _z)
        _dst = os.path.join(INPUT_ROOT, _name)
        if os.path.exists(_zp) and not os.path.isdir(_dst):
            os.makedirs(_dst, exist_ok=True)
            with zipfile.ZipFile(_zp) as _zz:
                _zz.extractall(_dst)
            log("giai nen %s -> %s" % (_z, _dst))
        elif os.path.isdir(_dst):
            log("dataset da co: %s" % _dst)
        else:
            log("!! thieu %s" % _zp)

    # 2) reward set (TACH tap eval!)''',
            "giai nen data")

    # 6) tao thu muc work
    s = sub(s, 'def main():\n    log("SEED=%d',
            'def main():\n    os.makedirs(WORK, exist_ok=True)\n'
            '    log("SEED=%d', "tao WORK")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
    import py_compile
    py_compile.compile(DST, doraise=True)
    print("  ok: py_compile")
    checks = [("INPUT_ROOT /content/data", 'INPUT_ROOT = "/content/data"' in s),
              ("4-bit mac dinh", 'GRPO_4BIT", "1"' in s),
              ("base tu HF", "snapshot_download" in s),
              ("giai nen data", "extractall" in s),
              ("reward giu nguyen", "def action_reward" in s),
              ("checkpoint giu nguyen", "save_strategy=\"steps\"" in s)]
    bad = 0
    for n, ok in checks:
        print("   %-26s %s" % (n, "PASS" if ok else "FAIL"))
        if not ok:
            bad += 1
    if bad:
        raise SystemExit("CO %d FAIL" % bad)
    print("\nSAN SANG: %s" % DST)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
