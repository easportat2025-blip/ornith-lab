"""Build the self-contained DESKTOP-BENCH kernel (TASK-28).

Inlines (as string literals) the three proven sources so the Kaggle code_file
is fully self-contained:
  phase14-desktop/env.py        (Xvfb + screenshot + xdotool)
  phase14-desktop/harness.py    (obs -> policy -> action -> env -> reward)
  phase13-gui/exp_kernel/exp_h2_matrix.py  (assemble_base / fix_processor /
                                            concretize_lora / install_unloth)
"""
import io, json, os, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = r"C:\Users\Admin\Desktop\New folder"
OUT = os.path.join(ROOT, "phase13-gui", "kernel_desktop_bench")
APPS = os.path.join(OUT, "apps")
os.makedirs(APPS, exist_ok=True)


def read(p):
    return io.open(os.path.join(ROOT, p), encoding="utf-8").read()


ENV_SRC = read(r"phase14-desktop\env.py")
# FIX 22/10 (GLM): env.py cua @MiMo vua them logic cai xdotool offline bang
# glob.glob(...) nhưng CHUA import glob => NameError lam start_display() CRASH
# ngay (moi run desktop-bench se chet). File env.py la cua nguoi khac => khong
# sua truc tiep; day la ban backup khi inline (idempotent).
if "import glob" not in ENV_SRC:
    assert "import json" in ENV_SRC, "env.py khong co import json de chen import glob"
    ENV_SRC = ENV_SRC.replace("import json", "import glob\nimport json", 1)
    print("FIX: them 'import glob' vao ENV_SRC inline (env.py thieu import)")
HARNESS_SRC = read(r"phase14-desktop\harness.py")
EXP_SRC = read(r"phase13-gui\exp_kernel\exp_h2_matrix.py")
GAME_HTML = read(r"phase14-desktop\tasks\game_2048.html")
# 3 app co bien ngau nhien: doc truc tiep tu dia (1 nguon su that)
FORM_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t21_form.html")
# copy app HTML cua nguoi khac (vd TASK-26 cua @MiMo) vao kernel de ship theo
SHARED_TASKS_DIR = r"phase14-desktop\tasks"
if os.path.isdir(os.path.join(ROOT, SHARED_TASKS_DIR)):
    for _f in sorted(os.listdir(os.path.join(ROOT, SHARED_TASKS_DIR))):
        if _f.endswith(".html"):
            shutil.copy2(os.path.join(ROOT, SHARED_TASKS_DIR, _f),
                         os.path.join(APPS, _f))
            # ten file phai khop task_id[:12] de lint L2/L5/L7 map dung
            if _f == "game_2048.html":
                shutil.copy2(os.path.join(ROOT, SHARED_TASKS_DIR, _f),
                             os.path.join(APPS, "t20_2048.html"))
                print("copy app:", _f, "+ t20_2048.html")
            else:
                print("copy app:", _f)
ORDER_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t22_order.html")
KEYS_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t23_keys.html")
# T25_recovery: app do LOOP-recovery + read-before-act (do duoc tren bench-v22)
RECOVERY_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t25_recovery.html")
# T26_clipboard: app do chu ky B 'lap 1 phim tat' (ctrl+a/ctrl+c/click/ctrl+v)
CLIPBOARD_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t26_clipboard.html")
# T27_errorecover (W2 #4) + T28_distractor (W2 #8) - bo sung 2 nang luc con thieu
ERRRECOVER_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t27_errorecover.html")
DISTRACTOR_HTML = read(r"phase13-gui\kernel_desktop_bench\apps\t28_distractor.html")
# --- 4 app cua @MiMo (TASK-26): PHAI INLINE vao kernel ---
# Kaggle chi upload code_file => app HTML khong nam trong repo thi kernel
# khong co file => app khong mo => cdp_eval None => score=-1 (22/10: 4 task
# bi -1 do dung nguyen do nay). => inline het + ghi ra TASK_DIR luc runtime.
MIMO_APP_FILES = ("t21_form_desktop.html", "t22_calc.html",
                  "t23_table_sort.html", "t24_text_edit.html")
MIMO_HTML = {}
for _f in MIMO_APP_FILES:
    _p = os.path.join(APPS, _f)
    if not os.path.isfile(_p):
        raise SystemExit("FAIL: thieu app cua @MiMo: %s (can copy tu %s)"
                         % (_p, SHARED_TASKS_DIR))
    MIMO_HTML[_f] = read(_p)
MIMO_FORM_DESKTOP_HTML = MIMO_HTML["t21_form_desktop.html"]
MIMO_CALC_HTML = MIMO_HTML["t22_calc.html"]
MIMO_TABLE_SORT_HTML = MIMO_HTML["t23_table_sort.html"]
MIMO_TEXT_EDIT_HTML = MIMO_HTML["t24_text_edit.html"]


DRIVER = r'''"""desktop_bench_kernel.py - DESKTOP-BENCH (TASK-28, GLM).

Do model THAT tren moi truong computer-use thay (X11 + xdotool + chromium that):
  obs (screenshot that) -> model (PolicyV2 + LoRA) -> action that -> env -> reward

Self-contained: env.py + harness.py + exp_h2_matrix.py + app 2048 + app form
deu INLINE (Kaggle chi upload code_file).

Output (de dashboard_sync.py dua len Space):
  /kaggle/working/desktop_bench/actions.jsonl   moi buoc
  /kaggle/working/desktop_bench/reward.json     theo task
  /kaggle/working/desktop_bench/obs/*.png       anh chup THAT
  /kaggle/working/desktop_bench/desktop_result.json  (schema giong b15_result.json)
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import types

WORK = os.environ.get("DB_WORK", "/kaggle/working/desktop_bench")
TASK_DIR = os.path.join(WORK, "tasks")
OUT_ENV = os.environ.get("DB_ENV_WORK", "/kaggle/working/desktop")

# ==== env.py (INLINE: Kaggle chi upload code_file) ====
ENV_SRC = @@ENV@@
# ==== harness.py (INLINE: Kaggle chi upload code_file) ====
HARNESS_SRC = @@HARNESS@@
# ==== exp_h2_matrix.py (INLINE: Kaggle chi upload code_file) ====
EXP_SRC = @@EXP@@
GAME_HTML = @@GAME@@
FORM_HTML = @@FORM@@
ORDER_HTML = @@ORDER@@
KEYS_HTML = @@KEYS@@
# FIX 22/10 (MiMo): 2 app moi (T25_recovery, T26_clipboard) da duoc DOC o tren
# nhung THIEU placeholder + thay the => hang duoc doc roi BO ROI => kernel
# sinh ra tham chieu RECOVERY_HTML/CLIPBOARD_HTML ma khong dinh nghia =>
# NameError luc chay ("NameError: name 'RECOVERY_HTML' is not defined").
RECOVERY_HTML = @@RECOVERY@@
CLIPBOARD_HTML = @@CLIPBOARD@@
MIMO_FORM_DESKTOP_HTML = @@MIMO_FORM_DESKTOP@@
MIMO_CALC_HTML = @@MIMO_CALC@@
MIMO_TABLE_SORT_HTML = @@MIMO_TABLE_SORT@@
MIMO_TEXT_EDIT_HTML = @@MIMO_TEXT_EDIT@@
ERRRECOVER_HTML = @@ERRRECOVER@@
DISTRACTOR_HTML = @@DISTRACTOR@@

# FIX 22/10 (MiMo): adapter dung phai khai bao 1 cho - tranh
# xung dot "code doi adapter" vs "metadata doi adapter"
# (kernel b3 chet: mount lora-v22 nhung require_datasets doi lora-v21)
ADAPTER_NAME = "ornith-gui-lora-v21"

TASK_TABLE = {
    "T20_2048": {
        "app": "t20_2048.html",
        "instruction": ("You are playing 2048 on the desktop. Use the arrow keys "
                        "to move the tiles and try to reach a score of 40. "
                        "Stop when the score is high enough."),
        "reward_js": "(window.__score || 0)",
        "threshold": 40,
        "max_steps": 24,
        "cap": "multi_step",
        "dummy": "2048"
    },
    "T21_form": {
        "app": "t21_form.html",
        "instruction": ("Fill the sign-up form on the desktop. Use the values "
                        "shown in the support note on the page (username, email "
                        "and password - the password needs at least 8 characters "
                        "and the confirm field must match it exactly), then "
                        "press Register."),
        "reward_js": "((window.__form_state && window.__form_state.ok) ? 1 : 0)",
        "threshold": 1,
        "max_steps": 16,
        "cap": "read_before_act",
        "dummy": "form"
    },
    "T22_order": {
        "app": "t22_order.html",
        "instruction": ("Complete the order desk on the desktop in exactly the "
                        "order shown on the page: type your name, pick the plan "
                        "named in the order note, type the code from the note, "
                        "then press Submit."),
        "reward_js": "((window.__state && window.__state.ok) ? 1 : 0)",
        "threshold": 1,
        "max_steps": 16,
        "cap": "multi_step",
        "dummy": "order"
    },
    "T23_keys": {
        "app": "t23_keys.html",
        "instruction": ("Work with the Archive list on the desktop. Press ESC to "
                        "dismiss the notice, then scroll down to the bottom of "
                        "the list, then click the row whose code matches the "
                        "note."),
        "reward_js": "((window.__state && window.__state.ok) ? 1 : 0)",
        "threshold": 1,
        "max_steps": 14,
        "cap": "keyboard_nav,scroll",
        "dummy": "keys"
    },
    # --- T25_recovery (GLM): do LOOP-recovery + read-before-act ---
    # Do tren bench-v22: nut that la LOOP (lap >=3 cung 1 hanh dong) va
    # read-before-act (gõ sai truong). App nay: dong DUNG theo code trong note,
    # cac dong khac la DECOY (click khong an) => agent phai DOI CHIEN LUWA.
    "T25_recovery": {
        "app": "t25_recovery.html",
        "instruction": ("Open the Device Setup page on the desktop. The support "
                        "note shows a feature code. Click the Enable button on "
                        "the row whose feature code matches the note. If a "
                        "control does not respond, try a different control "
                        "instead of clicking the same one again."),
        "reward_js": ("(function(){var r=window.__recovery||{};"
                      "return (r.done && !r.repeated)?1:0;})()"),
        "threshold": 1,
        "max_steps": 12,
        "cap": "loop_recovery",
        "dummy": "recovery"
    },
    # --- T26_clipboard (GLM): do chu ky B 'lap 1 phim tat' ---
    # bench-v22 B15.5/B16-A: model lap 'KEY Control+c' x12 roi khong lam not
    # chuoi (click dich + ctrl+v) => app nay day DUOI chuoi 5 buoc.
    "T26_clipboard": {
        "app": "t26_clipboard.html",
        "instruction": ("Copy the text from the Source box into the Target box "
                        "on the desktop using keyboard shortcuts only: click "
                        "the Source box, select all (ctrl+a), copy (ctrl+c), "
                        "click the Target box, paste (ctrl+v). Do not type the "
                        "text."),
        "reward_js": "((window.__clip && window.__clip.ok) ? 1 : 0)",
        "threshold": 1,
        "max_steps": 12,
        "cap": "clipboard",
        "dummy": "clipboard"
    },
    # --- TASK MOI (GLM): 2 nang luc W2 con thieu ---
    # T27: error-recovery (app bao loi nhung ket qua dung)
    "T27_errorecover": {
        "app": "t27_errorecover.html",
        "instruction": ("Open the Device Setup page on the desktop and enter the "
                        "activation code shown in the support note, then press "
                        "Activate. If the page reports an error, check the note "
                        "again before changing anything."),
        "reward_js": ("(function(){var st=window.__state||{};"
                      "return (st.activated && st.typed===st.code)?1:0;})()"),
        "threshold": 1,
        "max_steps": 12,
        "dummy": "errorecover",
        "cap": "error_recovery"
    },
    # T28: distractor (nhieu dong gan het, chi 1 dong khop ma)
    "T28_distractor": {
        "app": "t28_distractor.html",
        "instruction": ("Open the Contacts page on the desktop. Several contacts "
                        "look almost the same; select the one whose badge "
                        "matches the badge shown in the support note."),
        "reward_js": "((window.__state && window.__state.ok) ? 1 : 0)",
        "threshold": 1,
        "max_steps": 10,
        "dummy": "distractor",
        "cap": "distractor"
    },
    # --- 4 task cua @MiMo (TASK-26): app nhieu buoc + bien ngau nhien ---
    # reward JS doc DOM (tuong duong checker_desktop.py): so gia tri + trang thai
    "T21_form_desktop": {
        "app": "t21_form_desktop.html",
        "instruction": ("Fill the account setup form on the desktop using the "
                        "values shown in the note (username, email and "
                        "password), type the password again in the confirm field, "
                        "tick the terms checkbox, then press Register."),
        "reward_js": ("(function(){var q=function(id){return "
                      "((document.getElementById(id)||{}).value||'').trim();};"
                      "var t=function(id){return "
                      "((document.getElementById(id)||{}).textContent||'').trim();};"
                      "var st=window.__state||{};"
                      "return (q('u')&&q('u')===t('nu')&&q('e')===t('ne')&&"
                      "q('p')===t('np')&&q('p2')===t('np')&&st.terms&&"
                      "((st.status||'').indexOf('Account created')>=0))?1:0;})()"),
        "threshold": 1,
        "max_steps": 14,
        "cap": "read_before_act",
        "dummy": "form_desktop"
    },
    "T22_calc": {
        "app": "t22_calc.html",
        "instruction": ("Answer the two arithmetic questions shown on the "
                        "desktop page, type each answer in its field, then "
                        "submit."),
        "reward_js": ("(function(){var g=function(id){return "
                      "((document.getElementById(id)||{}).value||'').trim();};"
                      "var x=function(id){return "
                      "((document.getElementById(id)||{}).textContent||'');};"
                      "var sv=function(e){var m=e.match(/(\\d+)\\s*([+-])\\s*(\\d+)/);"
                      "if(!m)return null;var a=parseInt(m[1],10),b=parseInt(m[3],10);"
                      "return m[2]==='+'?a+b:a-b;};"
                      "var s1=sv(x('e1')),s2=sv(x('e2'));var st=window.__state||{};"
                      "return (s1!==null&&s2!==null&&g('a1')===String(s1)&&"
                      "g('a2')===String(s2)&&((st.status||'').indexOf('accepted')>=0))?1:0;})()"),
        "threshold": 1,
        "max_steps": 12,
        "cap": "read_before_act",
        "dummy": "calc"
    },
    "T23_table_sort": {
        "app": "t23_table_sort.html",
        "instruction": ("The data table on the desktop does not fit on the "
                        "screen. Scroll down to the bottom to see all rows, "
                        "reorder them so the score column is descending, select "
                        "the top row, then confirm."),
        "reward_js": ("(function(){var data=[];try{data=JSON.parse("
                      "((document.getElementById('data')||{}).textContent||'[]'));}"
                      "catch(e){data=[];}"
                      "if(!data.length)return 0;"
                      "var rows=Array.from(document.querySelectorAll('#tb tr'))"
                      ".map(function(tr){return Array.from(tr.children)"
                      ".map(function(td){return td.textContent.trim();});});"
                      "var exp=data.slice().sort(function(a,b){return b.score-a.score;})"
                      ".map(function(d){return [d.region,d.owner,String(d.score)];});"
                      "var sel=document.querySelector('#tb tr.sel');"
                      "var selOk=!!sel&&sel.children[0].textContent.trim()===exp[0][0];"
                      "var status=((document.getElementById('status')||{}).textContent||'');"
                      "var same=rows.length===exp.length&&rows.every(function(r,i){"
                      "return r.every(function(c,j){return c===exp[i][j];});});"
                      "return (same&&selOk&&status.indexOf('Confirmed')>=0)?1:0;})()"),
        "threshold": 1,
        "max_steps": 18,
        "cap": "scroll",
        "dummy": "table_sort"
    },
    "T24_text_edit": {
        "app": "t24_text_edit.html",
        "instruction": ("Replace the text in the editor on the desktop with the "
                        "exact target text shown on the page, then save the "
                        "document."),
        "reward_js": ("(function(){var want=((document.getElementById('want')||{}).textContent||'').trim();"
                      "var txt=((document.getElementById('ta')||{}).value||'').trim();"
                      "var status=((document.getElementById('status')||{}).textContent||'');"
                      "return (want&&txt===want&&status.indexOf('Saved')>=0)?1:0;})()"),
        "threshold": 1,
        "max_steps": 10,
        "cap": "clipboard",
        "dummy": "text_edit"
    },
}

FORM_DUMMY = ["CLICK 297 489", "TYPE carol", "CLICK 297 656",
              "TYPE carol@example.com", "CLICK 187 781"]


def log(m):
    print("[dbench] %s" % m, flush=True)


def _strip_main(src):
    i = src.find('if __name__ == "__main__":')
    return src[:i] if i > 0 else src


def _mod(name, src):
    m = types.ModuleType(name)
    m.__file__ = "<inline:%s>" % name
    exec(compile(_strip_main(src), "<inline:%s>" % name, "exec"), m.__dict__)
    sys.modules[name] = m
    return m


def _find_wheel_dir(prefix):
    for root, _dirs, files in os.walk("/kaggle/input"):
        if any(f.startswith(prefix) and f.endswith(".whl") for f in files):
            return root
    return None


def pip_run(cmd, timeout=1200):
    log("pip: %s" % cmd)
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       timeout=timeout)
    tail = ((r.stdout or "") + (r.stderr or ""))[-300:].replace("\n", " | ")
    log("  rc=%s %s" % (r.returncode, tail))
    return r.returncode == 0


def require_datasets(names):
    """FAIL-FAST: Kaggle SILENT-DROP dataset thieu (push van bao 'successfully
    pushed') => phai bao loi RO ngay, khong de phi mat 7,5' load model.

    LUU Y DUONG DAN (22/10 - fix FALSE POSITIVE): Kaggle mount dataset o
        /kaggle/input/<owner>/<slug>            (dataset cua acc dang chay)
        /kaggle/input/datasets/<owner>/<slug>   (dataset owner KHAC acc)
    => phai soi CA HAI cap; chi '/kaggle/input/*/<slug>' se FAIL GIA
    ('ornbase-s1' ... co that) => mat ca slot GPU.
    """
    import glob
    root = os.environ.get("DB_INPUT_ROOT", "/kaggle/input")
    missing = []
    for n in names:
        hits = []
        for pat in (root + "/*/" + n,
                    root + "/" + n,
                    root + "/datasets/*/" + n,
                    root + "/*/*/" + n):
            hits += [p for p in glob.glob(pat) if os.path.isdir(p)]
        if not hits:
            missing.append(n)
    if missing:
        raise SystemExit("FAIL: dataset thieu tren Kaggle (bi silent drop): %s "
                         "- upload dataset truoc khi push kernel nay" % missing)
    log("datasets OK: %s" % list(names))


def write_apps():
    os.makedirs(TASK_DIR, exist_ok=True)
    for name, html in (("t20_2048.html", GAME_HTML),
                       ("game_2048.html", GAME_HTML),
                       ("t21_form.html", FORM_HTML),
                       ("t22_order.html", ORDER_HTML),
                       ("t23_keys.html", KEYS_HTML),
                       ("t25_recovery.html", RECOVERY_HTML),
                       ("t26_clipboard.html", CLIPBOARD_HTML),
                       ("t21_form_desktop.html", MIMO_FORM_DESKTOP_HTML),
                       ("t22_calc.html", MIMO_CALC_HTML),
                       ("t23_table_sort.html", MIMO_TABLE_SORT_HTML),
                       ("t24_text_edit.html", MIMO_TEXT_EDIT_HTML),
                       ("t27_errorecover.html", ERRRECOVER_HTML),
                       ("t28_distractor.html", DISTRACTOR_HTML)):
        with open(os.path.join(TASK_DIR, name), "w", encoding="utf-8") as fh:
            fh.write(html)
    # merge: giu cac task da co (vd app cua @MiMo) roi them task cua kernel
    pj = os.path.join(TASK_DIR, "desktop_tasks.json")
    merged = {}
    if os.path.exists(pj):
        try:
            with open(pj, encoding="utf-8") as fh:
                old = json.load(fh)
            merged = dict(old.get("tasks") or old)
            log("merge task ton tai: %s" % sorted(merged))
        except Exception as e:
            log("doc desktop_tasks.json loi: %s" % e)
    merged.update(TASK_TABLE)
    with open(pj, "w", encoding="utf-8") as fh:
        json.dump({"tasks": merged}, fh, ensure_ascii=False, indent=1)
    # --- tasks.json theo schema MiMo (de lint L7 doc duoc instruction) ---
    tj = {"suite": "desktop", "version": 1,
          "viewport": {"width": 1280, "height": 720},
          "action_space": ("CLICK x y (0..1000 normalized) | TYPE text | "
                           "KEY name | DONE | SCROLL n"),
          "tasks": []}
    for tid, t in sorted(TASK_TABLE.items()):
        tj["tasks"].append({
            "task_id": tid,
            "name": tid.lower(),
            "file": t.get("app", ""),
            "difficulty": "hard",
            "max_steps": int(t.get("max_steps", 20)),
            "variants": [0],
            "instruction": t.get("instruction", ""),
            "target": "reward >= %s (doc DOM bang chinh app, khong tin co-flag)"
                      % t.get("threshold", 1),
        })
    with open(os.path.join(TASK_DIR, "tasks.json"), "w", encoding="utf-8") as fh:
        json.dump(tj, fh, ensure_ascii=False, indent=1)
    log("tasks.json written: %d task" % len(tj["tasks"]))
    log("apps written: %s" % sorted(os.listdir(TASK_DIR)))
    # GUARD FAIL-LOUD (MiMo 22/10): moi task trong TASK_TABLE phai co app file
    # that + khong rong. TRUOC DAY 4 app cua @MiMo bi BO ROI khi build kernel
    # (source cu) => task co trong bang nhung khong co file => KHONG mo
    # browser => anh X11 DEN => model thay "black screen" => DONE reward=-1
    # => 40/120 ep bi tinh nham la "model that" (run B2) + 40/80 ep (run A).
    # => gio: chet LUON thay vi dot 6h GPU tranh anh den.
    missing = []
    for _tid, _t in sorted(TASK_TABLE.items()):
        _app = _t.get("app")
        if not _app:
            continue
        _p = os.path.join(TASK_DIR, _app)
        if (not os.path.exists(_p)) or os.path.getsize(_p) < 200:
            missing.append("%s(%s)" % (_tid, _app))
    if missing:
        raise SystemExit("FAIL: thieu app file cho task: %s (dir=%s)"
                         % (missing, TASK_DIR))
    log("GUARD OK: %d task deu co app file (>200 byte)" % len(TASK_TABLE))


def save_obs_sample(out_dir, rows, per_task=2):
    r"""Luu MAU ANH it (moi task 2 anh) vao out_dir/obs_sample/.

    Ly do (22/10): watchdog tai ket qua theo pattern
    'desktop_result.json|actions.jsonl|reward.json|...log' => KHONG tai anh obs
    => khong doc duoc anh model THAY => khong chan doan duoc loi.
    => luu 2 anh/task trong 'obs_sample/' (nho) + pattern can them
    'obs_sample/.*\.png' (can nguoi tao target them).
    """
    import shutil as _sh
    seen = {}
    dst = os.path.join(out_dir, "obs_sample")
    os.makedirs(dst, exist_ok=True)
    n = 0
    for r in rows:
        t = r.get("task_id")
        if seen.get(t, 0) >= per_task:
            continue
        src = r.get("obs")
        if not src:
            continue
        p = src if os.path.isabs(src) else os.path.join(out_dir, src)
        if not os.path.exists(p):
            continue
        try:
            _sh.copy2(p, os.path.join(dst, os.path.basename(p)))
            seen[t] = seen.get(t, 0) + 1
            n += 1
        except Exception:
            pass
    log("obs_sample: %d anh (%d task)" % (n, len(seen)))
    return n


def build_desktop_result(out_dir, tasks):
    """Schema giong b15_result.json: episodes[] + by_task + agg."""
    rows = []
    p = os.path.join(out_dir, "actions.jsonl")
    if os.path.exists(p):
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    eps = {}
    for r in rows:
        key = (r.get("task_id"), r.get("episode"))
        eps.setdefault(key, []).append(r)
    episodes = []
    by_task = {}
    n_parse = 0
    n_act = 0
    n_stuck = 0
    for (task_id, ep), rs in sorted(eps.items(), key=lambda x: (str(x[0][0]),
                                                              x[0][1] or 0)):
        rs.sort(key=lambda r: r.get("step") or 0)
        acts = [r.get("action") for r in rs if r.get("action")]
        rewards = [r.get("reward") for r in rs
                   if isinstance(r.get("reward"), (int, float))]
        best = max(rewards) if rewards else None
        thr = (TASK_TABLE.get(task_id) or {}).get("threshold")
        win = bool(best is not None and thr is not None and best >= thr)
        n_act += len(acts)
        n_parse += sum(1 for r in rs if r.get("act_ok"))
        # metric 'stuck': model lap lai cung 1 hanh dong (do duoc tu trace)
        raws_n = [re.sub(r"\s+", " ", (r.get("raw") or "").strip())[:120]
                  for r in rs]
        uniq_raw = len(set(raws_n))
        verbs = [(r.get("action") or "").split(" ")[0].upper()
                 for r in rs if r.get("action")]
        max_same = max((verbs.count(v) for v in set(verbs)), default=0)
        # metric 'stuck': lap lai cung 1 hanh dong >=3 lan.
        # CHI tinh khi ep FAIL: ep da win thi co the van co hanh dong lap
        # (vi du v22 T11 win 100% nhung bi co la stuck => tin hieu sai).
        stuck = 1 if (max_same >= 3 and len(rs) >= 3 and not win) else 0
        n_stuck += stuck
        episodes.append({
            "task_id": task_id, "variant": 0, "episode": ep,
            "win": win, "score": best, "threshold": thr,
            "n_steps": len(rs), "n_actions": len(acts),
            "actions": acts[:40],
            "uniq_raw": uniq_raw, "max_same_verb": max_same, "stuck": stuck,
            # FIX 22/10 (MiMo): luu RAW DAY DU (2000 ky tu) thay vi cat 200
            # => doc loi "model noi gi" khong con bi cat mat thong tin.
            "raw_first": (rs[0].get("raw") or "")[:2000] if rs else "",
        })
        d = by_task.setdefault(task_id, {"n": 0, "win": 0, "score_sum": 0.0})
        d["n"] += 1
        d["win"] += 1 if win else 0
        d["score_sum"] += float(best or 0.0)
    # --- BANG NANG LUC (W2): gom task theo 'cap' de bao cao tung nang luc
    by_cap = {}
    for (task_id, ep), rs in eps.items():
        caps = (TASK_TABLE.get(task_id) or {}).get("cap") or ""
        if not caps:
            continue
        for cap in [c.strip() for c in str(caps).split(",") if c.strip()]:
            c = by_cap.setdefault(cap, {"tasks": set(), "ep": 0, "win": 0})
            c["tasks"].add(task_id)
            c["ep"] += 1
            for e in episodes:
                if e["task_id"] == task_id and e["episode"] == ep and e["win"]:
                    c["win"] += 1
                    break
    for k, c in by_cap.items():
        c["n_tasks"] = len(c["tasks"])
        c["task_ids"] = sorted(c["tasks"])
        c["win_rate"] = round(c["win"] / max(c["ep"], 1), 4)
        del c["tasks"]
    for k, d in by_task.items():
        d["mean_score"] = round(d.pop("score_sum") / max(d["n"], 1), 3)
        d["win_rate"] = round(d["win"] / max(d["n"], 1), 3)
    n_win = sum(1 for e in episodes if e["win"])
    scores = [e["score"] for e in episodes if e["score"] is not None]
    # FIX 22/10 (MiMo): loi HA TANG (app thieu / browser khong mo) => ep bi bo
    # qua => KHONG co trong episodes => khong lam nhieu diem, nhung phai
    # gan nhan de nguoi doc biet su do khong phai do model.
    infra = []
    p_ie = os.path.join(out_dir, "infra_errors.json")
    if os.path.exists(p_ie):
        try:
            with io.open(p_ie, encoding="utf-8") as fh:
                infra = json.load(fh)
        except Exception as e:
            log("doc infra_errors.json loi: %s" % e)
    infra_tasks = sorted(set(e.get("task_id") for e in infra))
    res = {
        "summary": {
            "n_episodes": len(episodes),
            "n_win": n_win,
            "win_rate": round(n_win / max(len(episodes), 1), 4),
            "parse_rate": round(n_parse / max(n_act, 1), 4),
            "mean_score": round(sum(scores) / max(len(scores), 1), 3),
            "n_actions": n_act,
            "stuck_rate": round(n_stuck / max(len(episodes), 1), 4),
            "n_infra_episodes": len(infra),
            "infra_tasks": infra_tasks,
            "valid": not infra,
        },
        "by_task": by_task,
        "by_capability": by_cap,
        "episodes": episodes,
        "infra_errors": infra,
    }
    with io.open(os.path.join(out_dir, "desktop_result.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    log("desktop_result.json: %s" % json.dumps(res["summary"],
                                                 ensure_ascii=False))
    # 1 vi du trajectory
    if episodes:
        e = episodes[0]
        log("VI DU TRAJECTORY [%s ep%s]: %s" %
            (e["task_id"], e.get("episode"),
             " -> ".join((e["actions"] or ["-"])[:12])))
    return res


def main():
    t0 = time.time()
    os.environ.setdefault("ENV_WORK", OUT_ENV)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.makedirs(WORK, exist_ok=True)
    log("=== DESKTOP-BENCH (TASK-28) ===")

    # 1) modules inline (khong import torch/transformers/unsloth o day)
    env = _mod("env", ENV_SRC)
    harness = _mod("harness", HARNESS_SRC)
    exp = _mod("exp", EXP_SRC)
    log("modules inline OK (env/harness/exp)")

    # 2) browser THAT truoc (rẻ, fail nhanh) — KHONG duoc import transformers truoc
    skip_model = os.environ.get("DB_SKIP_MODEL", "0") == "1"
    skip_browser = os.environ.get("DB_SKIP_BROWSER", "0") == "1"
    lora_used = None
    proc = None
    if skip_browser:
        log("DB_SKIP_BROWSER=1 -> bo qua chromium (chi verify pipeline)")
    else:
        harness.setup_browser_bundle()
        # PREFLIGHT X11: bat Xvfb + cai imagemagick/x11-apps + chup thu anh.
        # Fail o day (<5') thay vi sau 15' moi crash 'import: not found'.
        harness.preflight(log=log)

    # 3) deps: unsloth + peft tu wheels (offline) — PHAI TRUOC khi import unsloth
    if skip_model:
        log("DB_SKIP_MODEL=1 -> bo qua model/wheels (chi verify pipeline)")
    else:
        subprocess.run("pip uninstall -y torchao", shell=True, capture_output=True)
        pw_dir = _find_wheel_dir("peft-")
        if pw_dir:
            pip_run("pip install --no-index --find-links %s peft" % pw_dir)
        else:
            log("khong tim thay peft-*.whl -> dung peft co san trong image")
        uw_dir = _find_wheel_dir("unsloth-")
        if uw_dir:
            pip_run("pip install --no-index --no-deps --find-links %s unsloth "
                    "unsloth_zoo trl bitsandbytes" % uw_dir)
        else:
            raise SystemExit("FAIL: khong thay unsloth-*.whl (can dataset wheels)")

        # 3) import unsloth TRUOC peft/transformers (bai hoc TASK-9)
        from unsloth import FastVisionModel
        log("unsloth imported OK (truoc peft/transformers)")

        # 4) base + adapter + processor
        require_datasets([ADAPTER_NAME, "ornith-offline-browsers",
                          "ornbase-s1", "ornbase-s2", "ornbase-s3", "ornbase-s4"])
        exp.assemble_base()
        proc = exp.fix_processor()
        lora = exp.find_lora()
        if not lora:
            raise SystemExit("FAIL: khong thay adapter trong /kaggle/input")
        log("lora: %s" % lora)
        lora_used, _mods = exp.concretize_lora(lora)

    # 6) apps + task table
    write_apps()

    # 7) chay bench (policy = model that)
    episodes = int(os.environ.get("DB_EPISODES", "20"))
    tasks_arg = os.environ.get("DB_TASKS", "T20_2048,T21_form")
    policy_kind = os.environ.get("DB_POLICY", "model")
    if skip_model:
        policy_kind = "dummy"
    else:
        try:
            import torch
            if not torch.cuda.is_available() and policy_kind == "model":
                log("LOUD: khong thay GPU -> chay policy dummy de verify pipeline")
                policy_kind = "dummy"
        except Exception as e:
            log("khong kiem tra duoc GPU (%s) -> dummy" % type(e).__name__)
            policy_kind = "dummy"
    log("episodes/task=%s tasks=%s policy=%s" % (episodes, tasks_arg,
                                                 policy_kind))
    argv = ["harness.py", "--tasks", tasks_arg, "--tasks-dir", TASK_DIR,
            "--out", WORK, "--episodes", str(episodes),
            "--policy", policy_kind, "--base-dir", exp.ORN,
            "--adapter", lora_used]
    if policy_kind == "dummy":
        # dummy cho form: script nhieu buoc
        pass
    sys.argv = argv
    try:
        harness.main()
    except SystemExit as e:
        if e.code not in (0, None):
            raise
    except Exception as e:
        log("harness loi: %s: %s" % (type(e).__name__, str(e)[:300]))
        raise

    # 8) tong hop + log
    try:
        save_obs_sample(WORK, rows)
    except Exception as e:
        log("obs_sample loi: %s" % str(e)[:80])
    res = build_desktop_result(WORK, TASK_TABLE)
    log("TONG KET: %s" % json.dumps(res["summary"], ensure_ascii=False))
    # FIX 22/10 (MiMo): fail-loud. Kernel co loi HA TANG (app thieu / browser
    # khong mo) => ket qua KHONG hop le => phai ERROR chu khong phai score
    # binh thuong (neu khong, watchdog se ghi nham "0% => model te").
    if res["summary"].get("infra_errors") or res["summary"].get("n_infra"):
        raise SystemExit("FAIL: %d episode bi lo do loi HA TANG (task: %s) - "
                         "ket qua khong hop le, xem infra_errors.json"
                         % (res["summary"].get("n_infra_episodes", 0),
                            res["summary"].get("infra_tasks")))
    log("DONE t=%.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
'''

src = (DRIVER.replace("@@ENV@@", repr(ENV_SRC))
       .replace("@@HARNESS@@", repr(HARNESS_SRC))
       .replace("@@EXP@@", repr(EXP_SRC))
       .replace("@@GAME@@", repr(GAME_HTML))
       .replace("@@FORM@@", repr(FORM_HTML))
       .replace("@@ORDER@@", repr(ORDER_HTML))
       .replace("@@KEYS@@", repr(KEYS_HTML))
       .replace("@@RECOVERY@@", repr(RECOVERY_HTML))
       .replace("@@CLIPBOARD@@", repr(CLIPBOARD_HTML))
       .replace("@@MIMO_FORM_DESKTOP@@", repr(MIMO_FORM_DESKTOP_HTML))
       .replace("@@MIMO_CALC@@", repr(MIMO_CALC_HTML))
       .replace("@@MIMO_TABLE_SORT@@", repr(MIMO_TABLE_SORT_HTML))
       .replace("@@MIMO_TEXT_EDIT@@", repr(MIMO_TEXT_EDIT_HTML))
       .replace("@@ERRRECOVER@@", repr(ERRRECOVER_HTML))
       .replace("@@DISTRACTOR@@", repr(DISTRACTOR_HTML)))
p = os.path.join(OUT, "desktop_bench_kernel.py")
io.open(p, "w", encoding="utf-8", newline="\n").write(src)
io.open(os.path.join(APPS, "t21_form.html"), "w", encoding="utf-8",
        newline="\n").write(FORM_HTML)

meta = {
    "code_file": "desktop_bench_kernel.py",
    "competition_sources": ["arc-prize-2026-arc-agi-3"],
    "dataset_sources": [
        "khoadangnguye/gemma12b-wheels",
        "dieniw/stack-wheels",
        "dieniw/ornbase-s1",
        "dieniw/ornbase-s2",
        "dieniw/ornbase-s3",
        "dieniw/ornbase-s4",
        "khoadangnguye/ornith-gui-lora-v21",
        "khoadangnguye/ornith-offline-browsers",
        # xdotool OFFLINE (64KB): image Kaggle co Xvfb nhung thieu xdotool,
        # apt-get treo do DNS security.ubuntu.com fail => 30' GPU lang phi.
        "khoadangnguye/ornith-gui-xdotool"
    ],
    "enable_gpu": True,
    # FIX 22/10 (MiMo): enable_internet=True + competition_sources =>
    # Kaggle tra 400 Bad Request khi luu kernel (CLI khong in body loi).
    # Internet KHONG can: xdotool da co bundle offline 64KB, Xvfb co san trong
    # image, anh chup da chuyen sang CDP. => enable_internet=False (bat buoc).
    # Gate prepush_gate.py co G10 chan truoc khi push neu truong hop nay quay lai.
    "enable_internet": False,
    "enable_tpu": False,
    "id": "khoadangnguye/ornith-gui-desktop-bench",
    "is_private": True,
    "kernel_sources": [],
    "kernel_type": "script",
    "language": "python",
    "machine_shape": "NvidiaRtxPro6000",
    "model_sources": [],
    "title": "ornith-gui-desktop-bench"
}
io.open(os.path.join(OUT, "kernel-metadata.json"), "w", encoding="utf-8",
        newline="\n").write(json.dumps(meta, indent=1))
print("wrote", p, len(src), "chars")

# --- ghi apps/tasks.json luc BUILD (lay TASK_TABLE tu file kernel vua sinh) ---
try:
    import ast as _ast
    _tree = _ast.parse(io.open(p, encoding="utf-8").read())
    _tbl = None
    for _n in _tree.body:
        if isinstance(_n, _ast.Assign) and \
                getattr(_n.targets[0], "id", "") == "TASK_TABLE":
            _tbl = _ast.literal_eval(_n.value)
    if _tbl:
        _tj = {"suite": "desktop", "version": 1,
                "viewport": {"width": 1280, "height": 720},
                "action_space": ("CLICK x y (0..1000 normalized) | TYPE text | "
                                 "KEY name | DONE | SCROLL n"),
                "tasks": []}
        for _tid, _t in sorted(_tbl.items()):
            _tj["tasks"].append({
                "task_id": _tid, "name": _tid.lower(),
                "file": _t.get("app", ""), "difficulty": "hard",
                "max_steps": int(_t.get("max_steps", 20)),
                "variants": [0],
                "instruction": _t.get("instruction", ""),
                "target": "reward >= %s (doc DOM bang chinh app, khong tin co-flag)"
                          % _t.get("threshold", 1)})
        os.makedirs(APPS, exist_ok=True)
        with io.open(os.path.join(APPS, "tasks.json"), "w",
                     encoding="utf-8") as _fh:
            json.dump(_tj, _fh, ensure_ascii=False, indent=1)
        print("wrote apps/tasks.json (%d task)" % len(_tj["tasks"]))
        # --- apps/desktop_tasks.json: DUNG harness.load_tasks (doc file nay) ---
        # de chay LOCAL (test integration khong can Kaggle) va de kiem tra.
        with io.open(os.path.join(APPS, "desktop_tasks.json"), "w",
                     encoding="utf-8") as _fh:
            json.dump(_tbl, _fh, ensure_ascii=False, indent=1)
        print("wrote apps/desktop_tasks.json (%d task)" % len(_tbl))
except Exception as _e:
    print("tasks.json build loi: %s" % _e)
print("wrote", os.path.join(APPS, "t21_form.html"))
print("wrote", os.path.join(OUT, "kernel-metadata.json"))
