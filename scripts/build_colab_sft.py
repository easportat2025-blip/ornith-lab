# -*- coding: utf-8 -*-
r"""
build_colab_sft.py - sinh kernel SFT cho GOOGLE COLAB (4-bit) tu kernel Kaggle.

Muc tieu: PHEP THU CAP DONG NHAT tren Colab T4:
    v24-4bit  vs  v25-4bit   (cung harness, cung seed, chi khac data moi)
=> tra loi "data moi co giup khong?" ma KHONG can doi 24/10 (Kaggle het quota).

Vi sao 4-bit: T4 16GB, model 10B bf16 can ~20GB -> 4-bit (QLoRA) la bat buoc.
=> so 4bit-vs-4bit van CONG BANG (cung che do) ✓.

Khac biet voi kernel Kaggle (patch):
  - duong dan: WORK=/content/work, ORN=/content/base, INPUT_ROOT=/content/data
    (kernel SFT da dung env ORNITH_WORK/ORNITH_BASE/ORNITH_INPUT ✓ -> chi can
     dat env khi chay)
  - install_unsloth(): pip tu PyPI (VM co internet) thay dataset wheels
  - base model: snapshot_download tu HF (public, khong can token)
  - load_in_4bit=True + max_seq_length 2048
  - data: tai 1 file .zip tu HF dataset PUBLIC bang wget
    https://huggingface.co/datasets/kkouadn/ornith-colab-data/resolve/main/<f>.zip
    roi giai nen vao /content/data/<ten-dataset>/ (ten phai trung de loader khop)

Dung:
    python scripts/build_colab_sft.py v24
    python scripts/build_colab_sft.py v25
ASCII-only source.
"""
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
HF_DATA = "https://huggingface.co/datasets/kkouadn/ornith-colab-data/resolve/main"

# (ten ban, thu muc nguon, co them dataset desktop-replay khong)
VARIANTS = {
    "v24": ("kernel_v24b", False),
    "v25": ("kernel_v25b", True),
}

# dataset can cho train (ten thu muc sau khi giai nen) + file .zip tren HF
DATASETS = {
    "ornith-gui-traj": "ornith-gui-traj.zip",
    "ornith-policy-replay-data": "ornith-policy-replay-data.zip",
    "ornith-gui-synth-recipe": "ornith-gui-synth-recipe.zip",
    "ornith-gui-train3d": "ornith-gui-train3d.zip",
    "ornith-gui-train3d-hard": "ornith-gui-train3d-hard.zip",
    "ornith-gui-real-ui": "ornith-gui-real-ui.zip",
    "ornith-gui-real-fixtures": "ornith-gui-real-fixtures.zip",
    "gui-selfplay": "gui-selfplay.zip",
    # 22/10: data moi do agent giao (ten file tren HF khac ten thu muc)
    "ornith-desktop-replay-v1": "desktop_replay.zip",
    "ornith-gui-synth-s11": "synth_s11.zip",
}


def sub(s, old, new, tag):
    if old not in s:
        raise SystemExit("KHONG khop: %s\n---\n%s" % (tag, old[:200]))
    if s.count(old) != 1:
        raise SystemExit("KHONG duy nhat (%d): %s" % (s.count(old), tag))
    print("  ok: " + tag)
    return s.replace(old, new, 1)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in VARIANTS:
        print("dung: build_colab_sft.py %s" % "|".join(VARIANTS))
        return 2
    variant = sys.argv[1]
    src_rel, has_dr = VARIANTS[variant]
    src = os.path.join(P13, src_rel, "gui_sft_v23.py")
    if not os.path.exists(src):
        raise SystemExit("thieu nguon: %s" % src)
    dst_dir = os.path.join(P13, "colab_sft_" + variant)
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, "colab_sft.py")
    s = io.open(src, encoding="utf-8").read()

    # 1) pip tu PyPI (regex: thay ca khoi install_unsloth)
    import re as _re
    _new_pip = (
        'def install_unsloth():\n'
        '    # Colab: pip tu PyPI. KHONG cai "pillow" (ban preinstalled cua\n'
        '    # Colab khop torchvision; nang len Pillow 13 => loi\n'
        '    # "Pillow version is incompatible with torchvision")\n'
        '    sh("pip install -q -U unsloth unsloth_zoo trl peft datasets "\n'
        '       "accelerate bitsandbytes")\n'
        '    sh("pip install -q --no-deps qwen-vl-utils")\n'
    )
    _s2, _n = _re.subn(r"def install_unsloth\(\):.*?(?=\ndef )", _new_pip, s,
                        count=1, flags=_re.S)
    if _n != 1:
        raise SystemExit("KHONG khop khoi install_unsloth (%d)" % _n)
    s = _s2
    print("  ok: pip tu PyPI")

    # 2) base model tu HF (regex: thay ca khoi assemble_base)
    _new_base = (
        'def assemble_base():\n'
        '    """Colab: tai model base tu HF public (khong can token)."""\n'
        '    # Colab VM CO internet -> TAT offline mode (kernel SFT dat\n'
        '    # HF_HUB_OFFLINE=1 cho Kaggle; giu lai => "OfflineModeIsEnabled")\n'
        '    os.environ.pop("HF_HUB_OFFLINE", None)\n'
        '    os.environ.pop("TRANSFORMERS_OFFLINE", None)\n'
        '    if not os.path.isdir(ORN) or not any(\n'
        '            f.endswith(".safetensors") for f in os.listdir(ORN)):\n'
        '        os.makedirs(ORN, exist_ok=True)\n'
        '        from huggingface_hub import snapshot_download\n'
        '        bid = os.environ.get("ORNITH_BASE_ID", "ornith-ai/Ornith-1.5-9B")\n'
        '        log("tai base %s -> %s (10-25 phut lan dau)" % (bid, ORN))\n'
        '        snapshot_download(repo_id=bid, local_dir=ORN, max_workers=4,\n'
        '                          ignore_patterns=["*.pth", "original/*", "*.gguf"])\n'
        '    log("base files: %d" % len(os.listdir(ORN)))\n'
    )
    _s3, _n3 = _re.subn(r"def assemble_base\(\):.*?(?=\ndef )", _new_base, s,
                         count=1, flags=_re.S)
    if _n3 != 1:
        raise SystemExit("KHONG khop assemble_base (%d)" % _n3)
    s = _s3
    print("  ok: base tu HF")

    # 3) 4-bit + max_seq
    s = sub(s, '''        ORN, load_in_4bit=False, max_seq_length=4096,''',
            '''        ORN, load_in_4bit=os.environ.get("COLAB_4BIT", "1") == "1",
        max_seq_length=int(os.environ.get("COLAB_MAX_SEQ", "2048")),''',
            "4-bit + max_seq env")

    # 4) tai dataset .zip tu HF public (wget) + giai nen
    dl_lines = "\n".join(
        '    _fetch("%s", "%s")' % (z, n) for n, z in sorted(DATASETS.items())
        if has_dr or n != "ornith-desktop-replay-v1")
    s = sub(s, '''    log("gen data...")''',
            '''    # --- Colab: tai dataset tu HF dataset PUBLIC (khong can token) ---
    import subprocess as _sp
    import urllib.request as _ur

    def _fetch(zipname, dirname):
        _zp = os.path.join("/content", zipname)
        _dst = os.path.join(INPUT_ROOT, dirname)
        if os.path.isdir(_dst):
            log("dataset da co: %s" % dirname)
            return
        if not os.path.exists(_zp):
            _url = "%s/%s" % ("''' + HF_DATA + '''", zipname)
            log("tai %s ..." % zipname)
            try:
                _ur.urlretrieve(_url, _zp)
            except Exception as _e:
                log("!! tai that bai %s: %s" % (zipname, _e))
                return
        import zipfile as _zf
        os.makedirs(_dst, exist_ok=True)
        with _zf.ZipFile(_zp) as _zz:
            _zz.extractall(_dst)
        log("giai nen %s -> %s" % (zipname, _dst))

''' + dl_lines + '''
    log("gen data...")''', "tai dataset tu HF public")

    # 5) max_steps theo env (de chay ngan tren T4)
    s = sub(s, '''        max_steps=STEPS_V22,''',
            '''        max_steps=int(os.environ.get("COLAB_MAX_STEPS", str(STEPS_V22))),''',
            "max_steps env")

    # 6) collator max_seq
    s = s.replace("max_seq_length=4096,", "max_seq_length=int("
                  "os.environ.get(\"COLAB_MAX_SEQ\", \"2048\")),", 1)

    io.open(dst, "w", encoding="utf-8", newline="\n").write(s)
    import py_compile
    py_compile.compile(dst, doraise=True)
    print("  ok: py_compile")
    checks = [
        ("pip tu PyPI", "pip install -q -U unsloth" in s),
        ("base tu HF", "snapshot_download" in s),
        ("4-bit", "COLAB_4BIT" in s),
        ("tai dataset HF public", "_fetch(" in s),
        ("max_steps env", "COLAB_MAX_STEPS" in s),
        ("guard fail-loud giu nguyen", "FAIL: traj is still the OLD version" in s),
        ("loader quet base giu nguyen", "os.walk(base)" in s),
        ("N_3D giu nguyen", "N_3D = 600" in s),
    ]
    bad = 0
    for n, ok in checks:
        print("   %-30s %s" % (n, "PASS" if ok else "FAIL"))
        if not ok:
            bad += 1
    if bad:
        raise SystemExit("CO %d FAIL" % bad)
    print("\nSAN SANG: %s" % dst)
    print("Chay tren Colab:")
    print("  export ORNITH_WORK=/content/work ORNITH_BASE=/content/base "
          "ORNITH_INPUT=/content/data")
    print("  python colab_sft.py")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
