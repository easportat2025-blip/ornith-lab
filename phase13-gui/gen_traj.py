"""Sinh data trajectory (multi-step) cho SFT v13: CLICK / TYPE / KEY / DONE.

Oracle kich ban chay Playwright tren fixtures local, chup anh tung buoc:
- click_button: 1 buoc CLICK (+ DONE neu variant req=done)
- counter:      N buoc CLICK plus (+ DONE)
- login_form:   click user -> TYPE user -> click pass -> TYPE pass -> click Sign in | KEY enter (+ DONE)

Output: out_traj/images/*.png + out_traj/traj.jsonl
  {"image": ..., "instruction": ..., "action": "CLICK 512 300" | "TYPE admin" | "KEY enter" | "DONE"}
"""
import argparse
import json
import os
import random

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")

BGS = ["#f4f4f4", "#ffffff", "#eef1f5", "#faf7f0", "#e8f0e8",
       "#f0eef8", "#f7f7fa", "#eef6ff", "#fdf6ec", "#f2f6f2"]
VIEWPORTS = [(1280, 720), (1024, 768), (800, 600), (1440, 900)]
COLORS = ["Red", "Green", "Blue", "Yellow", "Purple", "Orange"]
CREDS = [("admin", "1234"), ("user1", "pass123"),
         ("maria", "s3cret"), ("tom", "qwerty")]
N_COUNTS = [3, 4, 5, 6, 7, 8]
STARTS = [0, 0, 0, 1, 2]

CLICK_TPL = [
    "Click the {label}.", "Click on the {label}.", "Tap the {label}.",
    "Find the {label} and click it.", "Where do you click to use the {label}?",
]
COUNT_TPL = [
    "Increment the counter to {n}.", "Make the counter show {n}.",
    "Get the counter up to {n} using the + button.",
    "Use the + button until the counter reaches {n}.",
]
LOGIN_TPL = [
    "Log in with username {u} and password {p}.",
    "Sign in as {u} with password {p}.",
    "Fill the login form with username {u} and password {p} and sign in.",
]
DONE_SUFFIX = " When you are done, say DONE."
DONE_PROB = 0.25

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

FIXTURES = {
    "click_button": "click_button.html",
    "counter": "counter.html",
    "login_form": "login_form.html",
}


def norm(v, total):
    return max(0, min(1000, int(round(v / total * 1000))))


def cfg_for(rng, name):
    cfg = {"bg": rng.choice(BGS), "pad": None, "gap": None,
           "shuffle": False, "cardW": None}
    if name == "click_button":
        cfg["gap"] = rng.randint(8, 26)
        cfg["pad"] = rng.randint(16, 40)
        cfg["shuffle"] = rng.random() < 0.7
    elif name == "counter":
        cfg["pad"] = rng.choice([40, 56, 80, 100])
    elif name == "login_form":
        cfg["pad"] = rng.randint(20, 80)
        cfg["cardW"] = rng.choice([340, 380, 420, 460])
    return cfg


def plan_episode(rng, name):
    req = rng.random() < DONE_PROB
    q = "req=done" if req else "req="
    if name == "click_button":
        color = rng.choice(COLORS)
        inst = rng.choice(CLICK_TPL).format(label=color.lower() + " button")
        steps = [("click", color + " button")]
        params = f"target=btn-{color.lower()}&{q}"
    elif name == "counter":
        n = rng.choice(N_COUNTS)
        start = rng.choice(STARTS)
        if n - start < 2:
            start = 0
        inst = rng.choice(COUNT_TPL).format(n=n)
        steps = [("click", "Plus button")] * (n - start)
        params = f"goal={n}&start={start}&{q}"
    else:
        u, p = rng.choice(CREDS)
        method = "enter" if rng.random() < 0.5 else "click"
        inst = rng.choice(LOGIN_TPL).format(u=u, p=p)
        steps = [("click", "Username field"), ("type", u),
                 ("click", "Password field"), ("type", p),
                 (method, "Sign in button")]
        params = f"eu={u}&ep={p}&{q}"
    if req:
        inst += DONE_SUFFIX
    return params, inst, steps, req


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "out_traj"))
    ap.add_argument("--variants", type=int, default=18)
    ap.add_argument("--seed", type=int, default=41)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    img_dir = os.path.join(args.out, "images")
    os.makedirs(img_dir, exist_ok=True)
    rows = []
    n_shots = 0
    n_ep = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for name, fname in FIXTURES.items():
            url = "file:///" + os.path.join(FIX, fname).replace("\\", "/")
            for w, h in VIEWPORTS:
                for v in range(args.variants):
                    params, inst, steps, req = plan_episode(rng, name)
                    ep_rows = []
                    page = browser.new_page(viewport={"width": w, "height": h})
                    page.goto(url + "?" + params)
                    page.evaluate(MUT_JS, cfg_for(rng, name))
                    page.wait_for_timeout(60)
                    all_steps = list(steps) + ([("done", None)] if req else [])
                    ok = True
                    for i, (kind, arg) in enumerate(all_steps):
                        rel = f"images/{name}_{w}x{h}_v{v:02d}_s{i}.png"
                        page.screenshot(path=os.path.join(
                            args.out, rel.replace("/", os.sep)))
                        n_shots += 1
                        if kind == "click":
                            el = page.query_selector(f'[data-label="{arg}"]')
                            box = el.bounding_box() if el is not None else None
                            if not box:
                                ok = False
                                print(f"  [skip] khong thay '{arg}' "
                                      f"({name} v{v} s{i})")
                                break
                            cx = box["x"] + box["width"] / 2.0
                            cy = box["y"] + box["height"] / 2.0
                            x, y = norm(cx, w), norm(cy, h)
                            ep_rows.append({
                                "image": rel, "instruction": inst,
                                "action": f"CLICK {x} {y}",
                                "point": [x, y],
                                "bbox": [norm(box["x"], w), norm(box["y"], h),
                                         norm(box["x"] + box["width"], w),
                                         norm(box["y"] + box["height"], h)],
                                "label": arg})
                            page.mouse.click(cx, cy)
                        elif kind == "type":
                            ep_rows.append({"image": rel, "instruction": inst,
                                            "action": f"TYPE {arg}"})
                            page.keyboard.type(arg)
                        elif kind == "enter":
                            ep_rows.append({"image": rel, "instruction": inst,
                                            "action": "KEY enter"})
                            page.keyboard.press("Enter")
                        else:
                            ep_rows.append({"image": rel, "instruction": inst,
                                            "action": "DONE"})
                        page.wait_for_timeout(120)
                    page.close()
                    if ok:
                        rows.extend(ep_rows)
                        n_ep += 1
        browser.close()
    data = os.path.join(args.out, "traj.jsonl")
    with open(data, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"episodes={n_ep} shots={n_shots} rows={len(rows)} -> {data}")


if __name__ == "__main__":
    main()
