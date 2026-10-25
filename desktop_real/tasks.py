"""tasks.py - six native-app desktop tasks with deterministic checkers.

Every task has:
  id, instruction, setup(ctx), checker(ctx), max_steps
An optional expert(ctx) is a scripted solution used by --selftest.

Checkers use real OS state: file contents, clipboard text, PDF text and
wmctrl/xdotool window geometry. There are no pixel-only checks and no model
or GPU is required.

Usage:
  python tasks.py --list
  python tasks.py --selftest
  python tasks.py --selftest --task writer_export_pdf --keep
  python tasks.py --task calculator_copy_result

On Windows the module imports safely; --selftest prints SKIP and exits 2.
ASCII-only source on purpose (Windows cp1252 lesson).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import sys
import time
import traceback
import zipfile
from dataclasses import dataclass
from typing import Callable, Optional

import env

WORK = os.environ.get("DESKTOP_TASK_WORK", "/tmp/ornith_desktop_tasks")

TERM_DIR = os.path.join(WORK, "terminal_file_create")
GEDIT_DIR = os.path.join(WORK, "gedit_edit_save")
FILE_DIR = os.path.join(WORK, "file_manager_rename")
CALC_DIR = os.path.join(WORK, "calculator_copy_result")
WRITER_DIR = os.path.join(WORK, "writer_export_pdf")
WIN_DIR = os.path.join(WORK, "window_management")


def log(msg):
    print("[tasks] %s" % msg, flush=True)


class SkipTask(Exception):
    """Raised when a task cannot run because an app is unavailable."""


class TaskContext:
    """Per-task paths, launched apps and cleanup list."""

    def __init__(self, task_id, root):
        self.task_id = task_id
        self.root = os.path.join(root, task_id)
        os.makedirs(self.root, exist_ok=True)
        self.artifacts = {}
        self.apps = []
        self.started_at = time.time()

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def write(self, name, text):
        path = self.path(name)
        env.write_text(path, text)
        return path

    def add_app(self, app):
        self.apps.append(app)
        return app

    def cleanup(self):
        for app in reversed(self.apps):
            try:
                app.close(force=True)
            except Exception:
                pass
        self.apps = []


@dataclass
class Task:
    id: str
    instruction: str
    setup: Callable[[TaskContext], None]
    checker: Callable[[TaskContext], tuple]
    max_steps: int
    apps: tuple = ()
    expert: Optional[Callable[[TaskContext], str]] = None
    notes: str = ""

    def meta(self):
        return {
            "id": self.id,
            "instruction": self.instruction,
            "max_steps": self.max_steps,
            "apps": list(self.apps),
            "has_expert": bool(self.expert),
            "notes": self.notes,
        }


def app_available(key):
    if key == "xterm":
        return bool(env.which("xterm"))
    if key == "gedit":
        return bool(env.which("gedit"))
    if key == "filemanager":
        return bool(env.which("pcmanfm") or env.which("thunar"))
    if key == "calculator":
        return bool(env.which("galculator"))
    if key == "writer":
        return bool(env.which("libreoffice") or env.which("soffice"))
    return True


def require_app(key):
    if not app_available(key):
        raise SkipTask("app not installed: %s" % key)


def missing_apps(task):
    return [key for key in task.apps if not app_available(key)]


def _focus_app(app, x, y, settle=0.4):
    if not app or not app.window:
        raise RuntimeError("app has no window")
    env.focus_window(app.window)
    env.click(x, y)
    time.sleep(settle)


def _focus_titlebar(app):
    """Focus an app by clicking its title bar (safe for a calculator)."""
    if not app or not app.window:
        raise RuntimeError("app has no window")
    geo = env.window_geometry(app.window)
    if geo:
        env.click(geo["x"] + 80, geo["y"] + 10)
    else:
        env.focus_window(app.window)
    time.sleep(0.4)


def write_minimal_odt(path, text):
    """Write a minimal but valid ODF text document (no LibreOffice needed)."""
    from xml.sax.saxutils import escape
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    body = escape(str(text))
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'office:version="1.2">'
        '<office:body><office:text><text:p>%s</text:p></office:text>'
        '</office:body></office:document-content>' % body)
    styles = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<office:document-styles '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'office:version="1.2"><office:styles/></office:document-styles>')
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<manifest:manifest '
        'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.2">'
        '<manifest:file-entry manifest:full-path="/" '
        'manifest:media-type="application/vnd.oasis.opendocument.text"/>'
        '<manifest:file-entry manifest:full-path="content.xml" '
        'manifest:media-type="text/xml"/>'
        '<manifest:file-entry manifest:full-path="styles.xml" '
        'manifest:media-type="text/xml"/>'
        '</manifest:manifest>')
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text",
                    compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", content,
                    compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("styles.xml", styles,
                    compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("META-INF/manifest.xml", manifest,
                    compress_type=zipfile.ZIP_DEFLATED)


def setup_terminal(ctx):
    require_app("xterm")
    target = ctx.path("hello.txt")
    try:
        os.remove(target)
    except FileNotFoundError:
        pass
    app = ctx.add_app(env.launch_xterm(
        cwd=ctx.root, title="OrnithTaskTerminal"))
    ctx.artifacts.update(app=app, target=target)
    env.focus_window(app.window)
    time.sleep(0.8)


def check_terminal(ctx):
    target = ctx.artifacts.get("target")
    if not target or not os.path.isfile(target):
        return False, "missing file: %s" % target
    text = env.read_text(target)
    if text.strip() != "REAL_TERMINAL":
        return False, "unexpected content: %r" % text[:120]
    return True, "hello.txt contains exactly REAL_TERMINAL"


def expert_terminal(ctx):
    app = ctx.artifacts["app"]
    target = ctx.artifacts["target"]
    _focus_app(app, 400, 300, 0.5)
    command = "echo REAL_TERMINAL > %s" % shlex.quote(target)
    if not env.type_text(command):
        raise RuntimeError("xdotool type failed")
    env.key("Return")
    if not env.wait_for_file(target, 6, contains="REAL_TERMINAL"):
        raise RuntimeError("file was not created by the terminal")
    return "typed: %s" % command


def setup_gedit(ctx):
    require_app("gedit")
    path = ctx.write("notes.txt", "original text\n")
    app = ctx.add_app(env.launch_gedit(path))
    env.maximize_window(app.window)
    env.focus_window(app.window)
    time.sleep(1.2)
    ctx.artifacts.update(app=app, path=path)


def check_gedit(ctx):
    path = ctx.artifacts.get("path")
    if not path or not os.path.isfile(path):
        return False, "missing file: %s" % path
    text = env.read_text(path).strip()
    if text != "EDITED_BY_AGENT":
        return False, "file content is %r" % text[:120]
    return True, "notes.txt saved with EDITED_BY_AGENT"


def expert_gedit(ctx):
    app = ctx.artifacts["app"]
    path = ctx.artifacts["path"]
    _focus_app(app, 640, 400, 0.5)
    env.key("ctrl+a")
    time.sleep(0.2)
    if not env.type_text("EDITED_BY_AGENT"):
        raise RuntimeError("xdotool type failed")
    env.key("ctrl+s")
    if not env.wait_for_file(path, 6, contains="EDITED_BY_AGENT"):
        raise RuntimeError("gedit did not save the file")
    return "selected all, typed marker, pressed Ctrl+S"


def setup_filemanager(ctx):
    require_app("filemanager")
    folder = ctx.path("files")
    os.makedirs(folder, exist_ok=True)
    old = os.path.join(folder, "report_draft.txt")
    new = os.path.join(folder, "report_final.txt")
    for path in (old, new):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    env.write_text(old, "rename me\n")
    app = ctx.add_app(env.launch_file_manager(folder))
    env.maximize_window(app.window)
    env.focus_window(app.window)
    time.sleep(1.2)
    ctx.artifacts.update(app=app, old=old, new=new, folder=folder)


def check_filemanager(ctx):
    old = ctx.artifacts.get("old")
    new = ctx.artifacts.get("new")
    if not new or not os.path.isfile(new):
        return False, "missing renamed file: %s" % new
    if old and os.path.exists(old):
        return False, "old file still exists: %s" % old
    text = env.read_text(new).strip()
    if text != "rename me":
        return False, "content changed to %r" % text[:120]
    return True, "report_draft.txt renamed to report_final.txt"


def expert_filemanager(ctx):
    app = ctx.artifacts["app"]
    old = ctx.artifacts["old"]
    new = ctx.artifacts["new"]
    _focus_app(app, 800, 450, 0.5)
    env.key("ctrl+a")
    time.sleep(0.3)
    env.key("F2")
    time.sleep(1.0)
    dialog = env.find_windows(title="rename")
    if not dialog:
        # Fallback for file managers where the first click did not focus
        # the file view: type-ahead selects the only file, then F2.
        env.key("Escape")
        time.sleep(0.2)
        env.type_text(os.path.basename(old))
        time.sleep(0.5)
        env.key("F2")
        time.sleep(1.0)
        dialog = env.find_windows(title="rename")
    if not dialog:
        raise RuntimeError("rename dialog did not open")
    env.key("ctrl+a")
    time.sleep(0.2)
    if not env.type_text(os.path.basename(new)):
        raise RuntimeError("xdotool type failed in rename dialog")
    time.sleep(0.2)
    env.key("Return")
    if not env.wait_for_file(new, 6):
        raise RuntimeError("file manager did not rename the file")
    return "selected the file, pressed F2, typed report_final.txt"


def setup_calculator(ctx):
    require_app("calculator")
    app = ctx.add_app(env.launch_calculator())
    env.focus_window(app.window)
    time.sleep(0.8)
    env.clipboard_set("")
    ctx.artifacts.update(app=app)


def _result_regex(text):
    return re.search(r"(?<!\d)703(?:[.,]0+)?(?!\d)", text or "")


def check_calculator(ctx):
    text = env.clipboard_get().strip()
    if not text:
        return False, "clipboard is empty"
    if _result_regex(text):
        return True, "clipboard contains 703: %r" % text[:80]
    return False, "clipboard does not contain 703: %r" % text[:120]


def expert_calculator(ctx):
    app = ctx.artifacts["app"]
    _focus_titlebar(app)
    if not env.type_text("37*19"):
        raise RuntimeError("xdotool type failed")
    env.key("Return")
    time.sleep(0.8)
    env.key("ctrl+c")
    time.sleep(0.8)
    text = env.clipboard_get()
    if not _result_regex(text):
        # Some galculator versions use Edit > Copy instead of Ctrl+C.
        env.key("alt+e")
        time.sleep(0.4)
        env.key("c")
        time.sleep(0.8)
        text = env.clipboard_get()
    if not _result_regex(text):
        raise RuntimeError("calculator did not copy 703; clipboard=%r"
                           % text[:120])
    return "computed 37*19 and copied 703 to the clipboard"


PDF_MARKER = "PDF_MARKER_2026"


def setup_writer(ctx):
    require_app("writer")
    odt = ctx.path("report.odt")
    pdf = ctx.path("report.pdf")
    write_minimal_odt(odt, "Original report text")
    for path in (pdf,):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    for lock in glob.glob(os.path.join(ctx.root, ".~lock.*")):
        try:
            os.remove(lock)
        except OSError:
            pass
    app = ctx.add_app(env.launch_writer(odt, timeout=90))
    env.maximize_window(app.window)
    env.focus_window(app.window)
    time.sleep(2.0)
    ctx.artifacts.update(app=app, odt=odt, pdf=pdf)


def _pdf_ready(path):
    try:
        if not os.path.isfile(path) or os.path.getsize(path) < 1000:
            return False
        with open(path, "rb") as fh:
            return fh.read(5) == b"%PDF-"
    except Exception:
        return False


def _wait_pdf(path, timeout=5):
    end = time.time() + max(0.1, float(timeout))
    while time.time() < end:
        if _pdf_ready(path):
            return True
        time.sleep(0.3)
    return False


def check_writer(ctx):
    pdf = ctx.artifacts.get("pdf")
    if not pdf or not os.path.isfile(pdf):
        return False, "missing PDF: %s" % pdf
    size = os.path.getsize(pdf)
    if size < 1000:
        return False, "PDF is too small (%d bytes)" % size
    with open(pdf, "rb") as fh:
        magic = fh.read(5)
    if magic != b"%PDF-":
        return False, "file is not a PDF (magic=%r)" % magic
    pdftotext = env.which("pdftotext")
    if not pdftotext:
        return False, "pdftotext missing (install poppler-utils)"
    res = env.sh([pdftotext, "-layout", pdf, "-"], timeout=20)
    if not res.ok:
        return False, "pdftotext failed: %s" % res.err[:160]
    if PDF_MARKER not in res.out:
        return False, "PDF text does not contain %s: %r" % (
            PDF_MARKER, res.out[:200])
    return True, "PDF exported (%d bytes) and contains %s" % (
        size, PDF_MARKER)


def _writer_menu_export(letter, pdf):
    env.key("Escape")
    time.sleep(0.3)
    env.key("alt+f")
    time.sleep(0.5)
    env.key(letter)
    time.sleep(0.5)
    env.key("p")
    time.sleep(1.0)
    env.key("Return")
    time.sleep(2.0)
    return _wait_pdf(pdf, 4)


def expert_writer(ctx):
    app = ctx.artifacts["app"]
    pdf = ctx.artifacts["pdf"]
    _focus_app(app, 640, 400, 0.5)
    env.key("ctrl+a")
    time.sleep(0.2)
    if not env.type_text(PDF_MARKER):
        raise RuntimeError("xdotool type failed")
    time.sleep(0.5)

    # LibreOffice's File > Export As > Export as PDF menu has changed
    # mnemonics across versions. Try the two common mnemonics, then Save As
    # with a .pdf name. Every attempt is a normal GUI action.
    if _writer_menu_export("x", pdf):
        return "File > Export As > Export as PDF (mnemonic x)"
    if _writer_menu_export("e", pdf):
        return "File > Export As > Export as PDF (mnemonic e)"

    env.key("Escape")
    env.key("Escape")
    time.sleep(0.4)
    env.key("ctrl+shift+s")
    time.sleep(1.5)
    env.key("ctrl+a")
    time.sleep(0.2)
    if not env.type_text(pdf):
        raise RuntimeError("xdotool type failed in Save As dialog")
    time.sleep(0.3)
    env.key("Return")
    time.sleep(2.0)
    # If LibreOffice asks to confirm the PDF filter, accept it.
    env.key("Return")
    time.sleep(2.0)
    if _wait_pdf(pdf, 5):
        return "Save As with a .pdf name"
    raise RuntimeError("PDF export failed (missing %s)" % pdf)


def setup_window(ctx):
    require_app("xterm")
    require_app("gedit")
    term = ctx.add_app(env.launch_xterm(
        cwd=ctx.root, title="OrnithWinTerm", geometry="80x24+40+40"))
    gpath = ctx.write("window.txt", "window task\n")
    edit = ctx.add_app(env.launch_gedit(gpath))
    env.set_window_geometry(term.window, 40, 40, 500, 300)
    env.set_window_geometry(edit.window, 40, 420, 600, 350)
    env.focus_window(term.window)
    time.sleep(1.0)
    ctx.artifacts.update(term=term, edit=edit, gpath=gpath)


def check_window(ctx):
    term = ctx.artifacts.get("term")
    edit = ctx.artifacts.get("edit")
    if not term or not edit:
        return False, "missing app handles"
    geo = env.window_geometry(term.window)
    if not geo:
        return False, "xterm window disappeared"
    checks = {
        "x>=700": geo["x"] >= 700,
        "width_480_640": 480 <= geo["w"] <= 640,
        "height_340_500": 340 <= geo["h"] <= 500,
    }
    active = env.active_window()
    checks["gedit_active"] = bool(
        active and active.get("id") == edit.window)
    if all(checks.values()):
        return True, "xterm=%s active=%s" % (geo, active)
    failed = [name for name, ok in checks.items() if not ok]
    return False, "xterm=%s active=%s failed=%s" % (
        geo, active, ",".join(failed))


def expert_window(ctx):
    term = ctx.artifacts["term"]
    edit = ctx.artifacts["edit"]
    env.set_window_geometry(term.window, 720, 120, 540, 400)
    env.focus_window(edit.window)
    time.sleep(0.8)
    return "moved/resized xterm with wmctrl and focused gedit"


TASKS = {
    "terminal_file_create": Task(
        id="terminal_file_create",
        instruction=(
            "In the xterm window, run a shell command that writes exactly "
            "REAL_TERMINAL (one line, no extra text) to %s/hello.txt."
            % TERM_DIR),
        setup=setup_terminal,
        checker=check_terminal,
        max_steps=8,
        apps=("xterm",),
        expert=expert_terminal,
        notes="Filesystem check; no OCR or pixels."),
    "gedit_edit_save": Task(
        id="gedit_edit_save",
        instruction=(
            "The file %s/notes.txt is open in gedit. Replace all of its "
            "text with EDITED_BY_AGENT and save the file." % GEDIT_DIR),
        setup=setup_gedit,
        checker=check_gedit,
        max_steps=12,
        apps=("gedit",),
        expert=expert_gedit,
        notes="Checks the saved file, not the editor buffer."),
    "file_manager_rename": Task(
        id="file_manager_rename",
        instruction=(
            "The file manager is open at %s/files. Rename "
            "report_draft.txt to report_final.txt without changing its "
            "content." % FILE_DIR),
        setup=setup_filemanager,
        checker=check_filemanager,
        max_steps=10,
        apps=("filemanager",),
        expert=expert_filemanager,
        notes="Filesystem check for old/new names and content."),
    "calculator_copy_result": Task(
        id="calculator_copy_result",
        instruction=(
            "Use galculator to compute 37 * 19, then copy the result to the "
            "clipboard."),
        setup=setup_calculator,
        checker=check_calculator,
        max_steps=12,
        apps=("calculator",),
        expert=expert_calculator,
        notes="Clipboard check accepts 703 or 703.000000."),
    "writer_export_pdf": Task(
        id="writer_export_pdf",
        instruction=(
            "LibreOffice Writer is open with %s/report.odt. Replace the "
            "document text with PDF_MARKER_2026 and export it as "
            "%s/report.pdf." % (WRITER_DIR, WRITER_DIR)),
        setup=setup_writer,
        checker=check_writer,
        max_steps=20,
        apps=("writer",),
        expert=expert_writer,
        notes="PDF magic + pdftotext marker; export menu is version-sensitive."),
    "window_management": Task(
        id="window_management",
        instruction=(
            "Move the xterm window so its left edge is at x >= 700, resize "
            "it to about 540x400, and make the gedit window active."),
        setup=setup_window,
        checker=check_window,
        max_steps=10,
        apps=("xterm", "gedit"),
        expert=expert_window,
        notes="wmctrl geometry + active window id; expert uses wmctrl."),
}


def list_tasks():
    print("%-24s %4s %-20s %s" % ("ID", "MAX", "APPS", "EXPERT"))
    for task_id in sorted(TASKS):
        task = TASKS[task_id]
        print("%-24s %4d %-20s %s" % (
            task.id, task.max_steps, ",".join(task.apps),
            "yes" if task.expert else "no"))
        print("  %s" % task.instruction)
    print("")
    print("Run: python tasks.py --selftest")
    print("One: python tasks.py --task writer_export_pdf --keep")


def run_selftest(task_ids, out_root, keep=False):
    if not env.IS_LINUX:
        log("SKIP: real X11 tasks require Linux (current: %s)"
            % env.platform.system())
        return 2
    if not env.which("Xvfb"):
        log("FAIL: Xvfb is missing; run setup_linux.sh first")
        return 1
    os.makedirs(out_root, exist_ok=True)
    info = env.start_display()
    if not info.get("ok"):
        log("FAIL: %s" % info.get("error", "display start failed"))
        if info.get("log"):
            log(info["log"][-1500:])
        return 1
    started_here = not info.get("reused", False)
    log("display %s %dx%d wm=%s" % (
        info.get("display"), info.get("width"), info.get("height"),
        info.get("wm")))

    results = []
    for task_id in task_ids:
        task = TASKS[task_id]
        ctx = TaskContext(task_id, out_root)
        status = "FAIL"
        detail = ""
        log("=== %s ===" % task_id)
        try:
            missing = missing_apps(task)
            if missing:
                raise SkipTask("missing app(s): %s" % ", ".join(missing))
            task.setup(ctx)
            if not task.expert:
                raise SkipTask("no scripted expert for this task")
            expert_detail = task.expert(ctx) or "expert completed"
            ok, check_detail = task.checker(ctx)
            status = "PASS" if ok else "FAIL"
            detail = "%s | %s" % (expert_detail, check_detail)
        except SkipTask as exc:
            status = "SKIP"
            detail = str(exc)
        except Exception as exc:
            status = "FAIL"
            detail = "%s: %s" % (type(exc).__name__, exc)
            traceback.print_exc()
        finally:
            try:
                ctx.cleanup()
            except Exception:
                pass
            if not keep:
                env.stop_apps()
        log("[%s] %s - %s" % (status, task_id, detail))
        results.append({
            "id": task_id,
            "status": status,
            "detail": detail,
            "max_steps": task.max_steps,
        })

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = sum(1 for item in results if item["status"] == "FAIL")
    skipped = sum(1 for item in results if item["status"] == "SKIP")
    summary = {
        "ok": failed == 0,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "display": info,
        "results": results,
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    json_path = os.path.join(out_root, "selftest.json")
    try:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=1, sort_keys=True)
    except Exception as exc:
        log("warning: cannot write %s: %s" % (json_path, exc))
    log("summary: %d PASS, %d FAIL, %d SKIP -> %s" % (
        passed, failed, skipped, json_path))

    if not keep:
        env.stop_apps()
        if started_here:
            env.stop_display()
    return 0 if failed == 0 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Six native-app desktop tasks with deterministic checks.")
    parser.add_argument("--selftest", action="store_true",
                        help="run setup + scripted expert + checker")
    parser.add_argument("--task", default=None,
                        help="run one task id (implies --selftest)")
    parser.add_argument("--list", action="store_true",
                        help="list tasks and exit")
    parser.add_argument("--out", default=WORK,
                        help="output root (default %s)" % WORK)
    parser.add_argument("--keep", action="store_true",
                        help="keep apps/display after the run")
    args = parser.parse_args(argv)

    if args.list or (not args.selftest and not args.task):
        list_tasks()
        return 0
    if args.task and args.task not in TASKS:
        log("unknown task: %s" % args.task)
        list_tasks()
        return 2
    task_ids = [args.task] if args.task else sorted(TASKS)
    return run_selftest(task_ids, args.out, args.keep)


if __name__ == "__main__":
    raise SystemExit(main())



