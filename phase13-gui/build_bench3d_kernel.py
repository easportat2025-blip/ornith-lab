"""build_bench3d_kernel.py - tao kernel GPU 'bench 3D grounding'.

Lay phan load model + parser tu kernel bench GUI (bi import lai mot lan
de dung chung policy/prompt), roi them vong eval 3D:
  moi episode: anh render 3D + instruction -> model -> CLICK x y
  checker: click co nam trong bbox CHIEU cua object target khong?
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = 'phase13-gui/kernel_bench_v15/bench_v15_kernel.py'
DST = 'phase13-gui/kernel_bench_3d'

src = open(SRC, encoding='utf-8').read()
part1 = src[:src.index('def run_task(')]
part2 = src[src.index('REASON_MAX = 256'):src.index('class _Suite:')]

MAIN = '''

# ================= BENCH 3D GROUNDING =================
def load_eps():
    """Doc episodes tu dataset: <ds>/bench3d.jsonl + <ds>/shots/*.png"""
    base = None
    for root, _dirs, files in os.walk("/kaggle/input"):
        if "bench3d.jsonl" in files:
            base = root
            break
    assert base, "khong thay bench3d.jsonl trong /kaggle/input"
    rows = [json.loads(l) for l in
            open(os.path.join(base, "bench3d.jsonl"), encoding="utf-8")
            if l.strip()]
    # anh: thu muc shots/ can dat dataset, dung lai thu muc dataset
    imgdir = os.path.join(base, "shots")
    if not os.path.isdir(imgdir):
        for root, _dirs, files in os.walk(base):
            if "e00000.png" in files:
                imgdir = root
                break
    eps = []
    for r in rows:
        p = os.path.join(imgdir, os.path.basename(r["image"]))
        if not os.path.exists(p):
            continue
        eps.append({"image": p, "instruction": r["instruction"],
                    "bbox": r["bbox"], "color": r.get("color"),
                    "shape": r.get("shape")})
    log("episodes: %d (image dir %s)" % (len(eps), imgdir))
    return eps


def hit(point, bbox):
    x, y = point
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def main_3d():
    t0 = time.time()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log("BENCH 3D grounding: click tren render Blender, bbox-hit checker")
    sh("pip uninstall -y torchao")
    import torch
    log("gpu: " + (torch.cuda.get_device_name(0)
                   if torch.cuda.is_available() else "NONE"))
    assemble_base()
    import transformers
    proc = fix_processor()
    model = load_model()
    lora = find_lora()
    assert lora, "khong thay adapter"
    log("lora: " + lora)
    probe = make_probe_image()
    model, used = load_adapter_robust(model, lora, proc,
                                      probe=(probe, "Click the blue square."))
    log("ADAPTER STRATEGY: " + used)
    policy = PolicyV2(model, proc)

    eps = load_eps()
    results = []
    n_parse = 0
    n_prose = 0
    for i, ep in enumerate(eps):
        try:
            ans, act = policy.act(ep["image"], ep["instruction"])
        except Exception as e:
            log("ep %d loi: %s" % (i, e))
            continue
        po = parse_output(ans)
        pt = parse_click(ans)
        ok = bool(pt) and hit(pt, ep["bbox"])
        if pt:
            n_parse += 1
        if po["prose_lines"] > 0:
            n_prose += 1
        results.append({"i": i, "instruction": ep["instruction"],
                        "color": ep["color"], "shape": ep["shape"],
                        "click": pt, "bbox": ep["bbox"], "hit": ok,
                        "mode": po["mode"], "prose_lines": po["prose_lines"],
                        "raw": ans[:200]})
        log("[3d %d] %-28s click=%s hit=%s" %
            (i, ep["instruction"][:28], pt, ok))
    n = max(len(results), 1)
    n_hit = sum(1 for r in results if r["hit"])
    by_color = {}
    for r in results:
        d = by_color.setdefault(r["color"] or "?", [0, 0])
        d[0] += 1
        d[1] += 1 if r["hit"] else 0
    summary = {"n": len(results), "n_hit": n_hit, "hit_rate": n_hit / n,
               "parse_rate": n_parse / n, "prose_leak_rate": n_prose / n,
               "by_color": {k: "%d/%d" % (v[1], v[0])
                            for k, v in by_color.items()},
               "adapter": lora, "adapter_strategy": used,
               "t_sec": round(time.time() - t0, 1)}
    with open(os.path.join(WORK, "bench3d_result.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"summary": summary, "episodes": results}, fh,
                  ensure_ascii=False, indent=1)
    log("BENCH3D XONG: hit %d/%d = %.3f parse=%.3f t=%.0fs" %
        (n_hit, len(results), summary["hit_rate"], summary["parse_rate"],
         summary["t_sec"]))


main = main_3d
'''

out = part1 + part2 + MAIN
os.makedirs(DST, exist_ok=True)
open(os.path.join(DST, 'bench3d_kernel.py'), 'w', encoding='utf-8').write(out)
print('wrote', DST, len(out), 'bytes')

md = json.load(open('phase13-gui/kernel_bench_v15/kernel-metadata.json',
                    encoding='utf-8'))
ds = []
for d in md['dataset_sources']:
    if d == 'hhjiji/ornith-gui-bench-v15':
        ds.append('hhjiji/ornith-gui-bench3d')
    elif d == 'hhjiji/ornith-gui-lora':
        ds.append('hhjiji/ornith-gui-lora')
    else:
        ds.append(d)
md['dataset_sources'] = ds
md['id'] = 'hhjiji/ornith-gui-bench-3d'
md['title'] = 'ornith-gui-bench-3d'
json.dump(md, open(os.path.join(DST, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('kernel id:', md['id'])
print('datasets:', ds)
