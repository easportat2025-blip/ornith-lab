"""check_reward_js.py - validate reward JS cua kernel desktop-bench (GLM, 21/10).

Rui ro: reward_js la CHUOI JS chay bang page.evaluate; neu sai syntax hoac sai
id DOM => evaluate nem loi/None => reward = -1 => bench bao 'fail' ma khong
bao loi gi (silent). Check nay bat truoc khi ton GPU:

  1) reward_js parse duoc (node --check) cho tung task;
  2) moi id DOM ma reward_js tham chieu ton tai trong app HTML tuong ung;
  3) moi task co 'file' app trong tasks.json + app do ton tai;
  4) canh bao neu reward_js luon tra 0 (vi app chua load state).

Dung: python phase13-gui/check_reward_js.py [dir_kernel]
"""
import ast
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_KERNEL = os.path.join(HERE, "kernel_desktop_bench")
NODE = "node"


def log(m):
    print("[rewardjs] %s" % m, flush=True)


def load_table(kernel_dir):
    pyfiles = [f for f in os.listdir(kernel_dir) if f.endswith(".py")]
    assert pyfiles, "khong co file .py trong %s" % kernel_dir
    src = io.open(os.path.join(kernel_dir, pyfiles[0]), encoding="utf-8",
                  errors="replace").read()
    tree = ast.parse(src)
    for n in tree.body:
        if isinstance(n, ast.Assign) and \
                getattr(n.targets[0], "id", "") == "TASK_TABLE":
            return ast.literal_eval(n.value)
    raise SystemExit("khong tim thay TASK_TABLE trong %s" % kernel_dir)


def js_ok(expr):
    """node --check tren bieu thuc (boc trong () de parse nhu expression)."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("var __r = (" + expr + ");\n")
        p = fh.name
    try:
        r = subprocess.run([NODE, "--check", p], capture_output=True,
                           text=True, timeout=60)
        return r.returncode == 0, (r.stderr or "")[:200]
    except FileNotFoundError:
        return None, "node khong co"
    finally:
        try:
            os.remove(p)
        except Exception:
            pass


def main():
    kdir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_KERNEL
    tbl = load_table(kdir)
    apps_dir = os.path.join(kdir, "apps")
    fails = 0
    log("kernel: %s | %d task" % (kdir, len(tbl)))
    for tid, t in sorted(tbl.items()):
        expr = t.get("reward_js") or ""
        app = t.get("app") or ""
        app_path = os.path.join(apps_dir, app)
        if not expr:
            log("  [FAIL] %-20s thieu reward_js" % tid)
            fails += 1
            continue
        if not os.path.exists(app_path):
            log("  [FAIL] %-20s khong thay app %s" % (tid, app))
            fails += 1
            continue
        ok, err = js_ok(expr)
        if ok is None:
            log("  [WARN] %-20s khong co node -> bo qua check syntax" % tid)
        elif not ok:
            log("  [FAIL] %-20s reward_js SAI SYNTAX: %s" % (tid, err.replace("\n", " ")[:150]))
            fails += 1
            continue
        html = io.open(app_path, encoding="utf-8", errors="replace").read()
        ids = sorted(set(re.findall(r"getElementById\(['\"](\w+)['\"]\)", expr)))
        miss = [i for i in ids if ("id=\"%s\"" % i) not in html
                and ("id='%s'" % i) not in html]
        if miss:
            log("  [FAIL] %-20s reward_js tham chieu id KHONG TON TAI: %s"
                % (tid, miss))
            fails += 1
            continue
        log("  [OK]   %-20s js hop le, %d id DOM dung" % (tid, len(ids)))
    # tasks.json: task co 'file' ton tai
    tj = os.path.join(apps_dir, "tasks.json")
    if os.path.exists(tj):
        d = json.load(io.open(tj, encoding="utf-8"))
        for t in d.get("tasks", []):
            f = t.get("file") or ""
            if not f or not os.path.exists(os.path.join(apps_dir, f)):
                log("  [FAIL] tasks.json: %s -> file %r khong ton tai"
                    % (t.get("task_id"), f))
                fails += 1
            elif not (t.get("instruction") or "").strip():
                log("  [WARN] tasks.json: %s thieu instruction" % t.get("task_id"))
    log("--- KET QUA: %d loi ---" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
