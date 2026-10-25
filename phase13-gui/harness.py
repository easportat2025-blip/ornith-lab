import argparse
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

W, H = 1280, 720
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")


class Env:
    def __init__(self, html, headless=True, viewport=(W, H), reload_delay=0.2):
        self.width, self.height = viewport
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=headless)
        self.page = self.browser.new_page(
            viewport={"width": self.width, "height": self.height})
        url = html if html.startswith(("http", "file:")) \
            else "file:///" + os.path.join(FIX, html).replace("\\", "/")
        self.url = url
        self.page.goto(url)
        self.page.wait_for_timeout(int(reload_delay * 1000))

    def screenshot(self, path):
        self.page.screenshot(path=path)
        return path

    def _px(self, nx, ny):
        x = max(1, min(self.width - 2, int(round(nx / 1000.0 * self.width))))
        y = max(1, min(self.height - 2, int(round(ny / 1000.0 * self.height))))
        return x, y

    def click(self, nx, ny):
        x, y = self._px(nx, ny)
        self.page.mouse.click(x, y)
        return f"clicked ({x},{y})"

    def type_text(self, text):
        self.page.keyboard.type(text)
        return f"typed {len(text)} chars"

    def key(self, name):
        names = {"enter": "Enter", "tab": "Tab", "esc": "Escape",
                 "escape": "Escape", "backspace": "Backspace",
                 "delete": "Delete", "space": "Space",
                 "up": "ArrowUp", "down": "ArrowDown",
                 "left": "ArrowLeft", "right": "ArrowRight",
                 "pageup": "PageUp", "pagedown": "PageDown",
                 "home": "Home", "end": "End"}
        parts = []
        for p in name.split("+"):
            k = p.strip().lower()
            parts.append(names.get(k, k))
        combo = "+".join(parts)
        self.page.keyboard.press(combo)
        return f"key {combo}"

    def scroll(self, direction, n):
        dy = int(n) * 240
        if direction.lower().startswith("up"):
            dy = -dy
        self.page.mouse.wheel(0, dy)
        return f"scroll {direction} {n}"

    def goal(self):
        return bool(self.page.evaluate("window.__goal_reached === true"))

    def close(self):
        try:
            self.browser.close()
        finally:
            self._pw.stop()


def parse_action(text):
    if not text:
        return ("WAIT",)
    line = text.strip().split("\n")[0].strip()
    m = re.match(r"CLICK\s+(\d+)\s+(\d+)", line, re.I)
    if m:
        return ("CLICK", int(m.group(1)), int(m.group(2)))
    m = re.match(r"TYPE\s+(.+)$", line, re.I)
    if m:
        return ("TYPE", m.group(1))
    m = re.match(r"KEY\s+([\w+]+)", line, re.I)
    if m:
        return ("KEY", m.group(1))
    m = re.match(r"SCROLL\s+(up|down)\s+(\d+)", line, re.I)
    if m:
        return ("SCROLL", m.group(1), int(m.group(2)))
    up = line.upper()
    if up == "DONE":
        return ("DONE",)
    if up == "FAIL":
        return ("FAIL",)
    if up == "WAIT":
        return ("WAIT",)
    return ("BAD", line)


def step_env(env, action):
    kind = action[0]
    if kind == "CLICK":
        res = env.click(action[1], action[2])
    elif kind == "TYPE":
        res = env.type_text(action[1])
    elif kind == "KEY":
        res = env.key(action[1])
    elif kind == "SCROLL":
        res = env.scroll(action[1], action[2])
    elif kind == "WAIT":
        env.page.wait_for_timeout(300)
        res = "waited"
    else:
        res = f"khong ho tro: {kind}"
    env.page.wait_for_timeout(80)
    return res


def run_episode(html, policy, out_dir, max_steps=15, tag="ep",
                task="Task", verbose=False):
    os.makedirs(out_dir, exist_ok=True)
    env = Env(html)
    hist = []
    try:
        for t in range(max_steps):
            shot = os.path.join(out_dir, f"{tag}_s{t:02d}.png")
            env.screenshot(shot)
            obs = (f"Task: {task}\nStep: {t}\n"
                   f"Last: {hist[-1][1] if hist else 'start'}")
            try:
                action = policy(obs, shot, t, hist, env)
            except TypeError:
                action = policy(obs, shot, t, hist)
            res = step_env(env, action)
            hist.append((action, res))
            if verbose:
                print(f"  [{tag}] t{t} {action} -> {res}")
            if env.goal():
                try:
                    env.screenshot(os.path.join(out_dir, f"{tag}_win.png"))
                except Exception:
                    pass
                env.close()
                return True, hist, shot if t == 0 else None
            if action[0] in ("DONE", "FAIL"):
                break
        env.close()
        return False, hist, None
    finally:
        try:
            env.close()
        except Exception:
            pass


def mock_policy(obs, shot, t, hist, env=None):
    import random
    if t % 3 == 2:
        return ("CLICK", random.randint(50, 950), random.randint(100, 650))
    if t % 3 == 1:
        return ("KEY", "tab")
    return ("WAIT",)


def scripted_policy_factory(target_label):
    def pol(obs, shot, t, hist):
        return ("CLICK", 0, 0)
    return pol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture", nargs="?", default="click_button.html")
    ap.add_argument("--out", default=os.path.join(HERE, "out_demo"))
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--head", action="store_true")
    args = ap.parse_args()
    ok, hist, _ = run_episode(args.fixture, mock_policy, args.out,
                              max_steps=args.steps, tag="mock")
    print("env:", args.fixture)
    for a, r in hist:
        print("  ", a, "->", r)
    print("goal reached:", ok)
    print("screenshots in", args.out)


if __name__ == "__main__":
    main()
