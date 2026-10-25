import argparse
import json
import os
import random

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

TEMPLATES = [
    "Click the {label}.", "Click on the {label}.", "Tap the {label}.",
    "Find the {label} and click it.", "Where do you click to use the {label}?",
]
BGS = ["#f4f4f4", "#ffffff", "#eef1f5", "#faf7f0", "#e8f0e8",
       "#f0eef8", "#f7f7fa", "#eef6ff", "#fdf6ec", "#f2f6f2"]
VIEWPORTS = [(1280, 720), (1024, 768), (800, 600), (1440, 900)]
MAX_ROWS_PER_SHOT = 4

MUT_JS = """(cfg) => {
  document.body.style.background = cfg.bg;
  if (cfg.pad !== null) document.body.style.padding = cfg.pad + 'px';
  const g = document.querySelector('.grid');
  if (g) {
    if (cfg.gap !== null) g.style.gap = cfg.gap + 'px';
    if (cfg.shuffle) {
      const kids = Array.from(g.children);
      for (let i = kids.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [kids[i], kids[j]] = [kids[j], kids[i]];
      }
      kids.forEach(el => g.appendChild(el));
    }
  }
  const card = document.querySelector('.card');
  if (card && cfg.cardW) card.style.width = cfg.cardW + 'px';
  return true;
}"""


def norm(v, total):
    return max(0, min(1000, int(round(v / total * 1000))))


def cfg_for(rng, fixture):
    cfg = {"bg": rng.choice(BGS), "pad": None, "gap": None,
           "shuffle": False, "cardW": None}
    if fixture == "click_button":
        cfg["gap"] = rng.randint(8, 26)
        cfg["pad"] = rng.randint(16, 40)
        cfg["shuffle"] = rng.random() < 0.7
    elif fixture == "counter":
        cfg["pad"] = rng.choice([40, 56, 80, 100])
    elif fixture == "login_form":
        cfg["pad"] = rng.randint(20, 80)
        cfg["cardW"] = rng.choice([340, 380, 420, 460])
    return cfg


def harvest_variant(page, w, h, rng, shot_path, anchor_rows):
    els = page.query_selector_all("[data-label]")
    items = []
    for el in els:
        label = el.get_attribute("data-label")
        try:
            box = el.bounding_box()
        except Exception:
            continue
        if not box or box["width"] < 4 or box["height"] < 4:
            continue
        cx = box["x"] + box["width"] / 2.0
        cy = box["y"] + box["height"] / 2.0
        if cx < 0 or cy < 0 or cx >= w or cy >= h:
            continue
        items.append({
            "label": label,
            "point": [norm(cx, w), norm(cy, h)],
            "bbox": [norm(box["x"], w), norm(box["y"], h),
                     norm(box["x"] + box["width"], w),
                     norm(box["y"] + box["height"], h)],
        })
    if not items:
        return []
    rng.shuffle(items)
    rows = []
    for it in items[:MAX_ROWS_PER_SHOT]:
        instr = rng.choice(TEMPLATES).format(label=it["label"].lower())
        rows.append({"image": shot_path, "instruction": instr,
                     "point": it["point"], "bbox": it["bbox"],
                     "label": it["label"]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out_real"))
    ap.add_argument("--variants", type=int, default=18)
    ap.add_argument("--seed", type=int, default=23)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    img_dir = os.path.join(args.out, "images")
    os.makedirs(img_dir, exist_ok=True)
    fixs = sorted(f for f in os.listdir(FIX) if f.endswith(".html"))
    rows = []
    n_shots = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for f in fixs:
            name = os.path.splitext(f)[0]
            url = "file:///" + os.path.join(FIX, f).replace("\\", "/")
            for w, h in VIEWPORTS:
                page = browser.new_page(viewport={"width": w, "height": h})
                for v in range(args.variants):
                    page.goto(url)
                    cfg = cfg_for(rng, name)
                    try:
                        page.evaluate(MUT_JS, cfg)
                    except Exception:
                        pass
                    page.wait_for_timeout(60)
                    rel = f"images/{name}_{w}x{h}_v{v:02d}.png"
                    page.screenshot(path=os.path.join(args.out,
                                                      rel.replace("/", os.sep)))
                    n_shots += 1
                    rows.extend(harvest_variant(page, w, h, rng, rel, None))
                page.close()
        browser.close()
    data = os.path.join(args.out, "grounding.jsonl")
    with open(data, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"shots={n_shots} rows={len(rows)} -> {data}")


if __name__ == "__main__":
    main()
