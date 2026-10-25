# -*- coding: utf-8 -*-
"""
build_colab_smoke.py - bien colab_grpo.py thanh ban SMOKE: khong can upload
dataset (endpoint upload cua Colab dang 500) - sinh prompt tong hop tren VM
bang PIL, dung de Kiem tra API/import/generation/reward (0 luong Kaggle).

Khac biet so voi ban day du:
  - khong giai nen zip, khong can du lieu
  - tao N prompt giong nhau: anh ve + instruction + GT 'CLICK 100 100'
  - max_steps 2, num_generations 4
ASCII-only.
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "phase13-gui", "colab_grpo", "colab_grpo.py")
DST = os.path.join(ROOT, "phase13-gui", "colab_grpo", "colab_grpo_smoke.py")

OLD = '''    # 2) reward set (TACH tap eval!)
    pr = load_ds_rows("ornith-policy-replay-data", "traj.jsonl", required=True)
    tr = load_ds_rows("ornith-gui-traj", "traj.jsonl", required=True)
    pool = pr + tr
    random.Random(SEED).shuffle(pool)
    log("reward pool: %d (policy-replay %d + traj %d) -> lay %d prompt"
        % (len(pool), len(pr), len(tr), N_PROMPT))
'''

NEW = '''    # 2) SMOKE: prompt tong hop (khong can dataset - upload endpoint 500)
    pr = []
    tr = []
    log("SMOKE: tao %d prompt tong hop tren VM" % N_PROMPT)
'''


def main():
    s = io.open(SRC, encoding="utf-8").read()
    if OLD not in s:
        raise SystemExit("KHONG khop khoi tao data")
    s = s.replace(OLD, NEW, 1)
    print("  ok: thay khoi tao pool")

    # thay phan loop lay row bang prompt tong hop
    OLD2 = '''    rows = []
    for r in pool:
        if len(rows) >= N_PROMPT:
            break
        x = to_row(r)
        if x is not None:
            rows.append(x)'''
    NEW2 = '''    from PIL import Image as _PIL, ImageDraw as _D
    rows = []
    for i in range(N_PROMPT):
        _im = _PIL.new("RGB", (768, 512), (250, 250, 250))
        _d = _D.Draw(_im)
        _d.rectangle([300, 200, 460, 300], fill=(60, 120, 220))
        _d.text((20, 20), "TASK %d" % i, fill=(0, 0, 0))
        _p = os.path.join(WORK, "smoke_%02d.png" % i)
        _im.save(_p)
        _msgs = [{"role": "system", "content": [{"type": "text", "text": SYS}]},
                 {"role": "user", "content": [{"type": "image"},
                                             {"type": "text",
                                              "text": "Task: Click the blue box"}]}]
        rows.append({"prompt": _msgs, "image": _im, "gt": "CLICK 100 100"})
    log("SMOKE: %d prompt san (gt = CLICK 100 100)" % len(rows))'''
    if OLD2 not in s:
        raise SystemExit("KHONG khop vong lap lay row")
    s = s.replace(OLD2, NEW2, 1)
    print("  ok: tao prompt tong hop")

    s = s.replace('max_steps=int(os.environ.get("GRPO_MAX_STEPS", "3")),',
                  'max_steps=int(os.environ.get("GRPO_MAX_STEPS", "2")),', 1)
    s = s.replace('num_generations=G,', 'num_generations=int(os.environ.get("GRPO_G", "4")),', 1)
    print("  ok: max_steps 2 / G 4")

    io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
    import py_compile
    py_compile.compile(DST, doraise=True)
    print("  ok: py_compile -> %s" % DST)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
