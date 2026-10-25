import argparse
import json
import os
import random
import time

from playwright.sync_api import sync_playwright

W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

TEMPLATES = [
    "Click the {label}.",
    "Click on the {label}.",
    "Tap the {label}.",
    "Find the {label} and click it.",
    "Where do you click to use the {label}?",
]


def norm(v, total):
    return max(0, min(1000, int(round(v / total * 1000))))


def harvest(pw, html, out_img_dir, shot_id):
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": W, "height": H})
    page.goto("file:///" + os.path.join(FIX, html).replace("\\", "/"))
    page.wait_for_timeout(250)
    shot = os.path.join(out_img_dir, f"{shot_id}.png")
    page.screenshot(path=shot)
    items = []
    els = page.query_selector_all("[data-label]")
    for el in els:
        label = el.get_attribute("data-label")
        box = el.bounding_box()
        if not box or box["width"] < 4 or box["height"] < 4:
            continue
        cx = box["x"] + box["width"] / 2.0
        cy = box["y"] + box["height"] / 2.0
        if cx < 0 or cy < 0 or cx >= W or cy >= H:
            continue
        items.append({
            "label": label,
            "point": [norm(cx, W), norm(cy, H)],
            "bbox": [norm(box["x"], W), norm(box["y"], H),
                     norm(box["x"] + box["width"], W),
                     norm(box["y"] + box["height"], H)],
        })
    browser.close()
    return shot, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out_data"))
    ap.add_argument("--views", type=int, default=6)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()
    random.seed(args.seed)
    img_dir = os.path.join(args.out, "images")
    os.makedirs(img_dir, exist_ok=True)
    fixs = sorted(f for f in os.listdir(FIX) if f.endswith(".html"))
    rows = []
    with sync_playwright() as pw:
        for view in range(args.views):
            for f in fixs:
                sid = f"{os.path.splitext(f)[0]}_v{view:02d}"
                shot, items = harvest(pw, f, img_dir, sid)
                for it in items:
                    if view > 0 and random.random() < 0.5:
                        pass
                    instr = random.choice(TEMPLATES).format(
                        label=it["label"].lower())
                    rows.append({
                        "image": os.path.relpath(shot, args.out)
                        .replace("\\", "/"),
                        "instruction": instr,
                        "point": it["point"],
                        "bbox": it["bbox"],
                    })
    data = os.path.join(args.out, "grounding.jsonl")
    with open(data, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("rows:", len(rows), "->", data)


if __name__ == "__main__":
    main()
