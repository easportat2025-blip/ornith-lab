# -*- coding: utf-8 -*-
"""secret_scan.py - fail fast before a key reaches GitHub.

Usage:
  python scripts/secret_scan.py                 # walk curated tree
  python scripts/secret_scan.py --tracked-only  # git ls-files (CI)
  python scripts/secret_scan.py --all           # include ignored-looking dirs

Prints file:line and pattern name, never the matched value.
ASCII-only source on purpose.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "scripts/colab_accounts", "scripts/logs", "scripts/artifacts",
    "scripts/jobs/artifacts", "data", "dl-loop", "harness", "cmp",
    "phase14-space", ".glm_tmp",
}
SKIP_PREFIX = (".tmp_", "phase13-gui/out_", "phase13-gui\\out_",
               "phase0-probe", "phase1-")
SKIP_FILES = {"agent.md", "kaggle.json", "token.json", "oauth.json",
              "sessions.json", "scripts/secret_scan.py"}
TEXT_EXT = {".py", ".ps1", ".cmd", ".bat", ".json", ".jsonl", ".yaml", ".yml",
            ".toml", ".ini", ".cfg", ".md", ".txt", ".sh", ".env", ".js",
            ".ts", ".html", ".css", ".xml"}

PATTERNS = [
    ("hf_token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key", re.compile(
        r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("assigned_secret", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*"
        r"[\"'][^\"']{12,}[\"']")),
    ("kaggle_key", re.compile(
        r"(?i)(kaggle[_-]?key|\"key\")\s*[:=]\s*[\"'][0-9a-f]{32}[\"']")),
    ("github_classic", re.compile(
        r"(?i)(github[_-]?token|gh[_-]?token)\s*[:=]\s*"
        r"[\"'][0-9a-f]{40}[\"']")),
]
ALLOW_LINE = re.compile(
    r"(?i)(os\.environ|getenv|your[_-]|example|placeholder|change[_-]?me|"
    r"\*\*\*|redacted|<[^>]+>|HKCU|winreg|secret_scan)")


def is_skipped(path):
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    if rel in SKIP_FILES:
        return True
    for d in SKIP_DIRS:
        if rel == d or rel.startswith(d + "/"):
            return True
    for p in SKIP_PREFIX:
        if rel.startswith(p.replace("\\", "/")):
            return True
    return False


def tracked_files():
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT,
            stderr=subprocess.DEVNULL)
        return [os.path.join(ROOT, x.decode("utf-8", "replace"))
                for x in out.split(b"\x00") if x]
    except Exception:
        return None


def walk_files(include_all=False):
    out = []
    for base, dirs, files in os.walk(ROOT):
        if not include_all:
            dirs[:] = [d for d in dirs
                       if not is_skipped(os.path.join(base, d))]
        for name in files:
            p = os.path.join(base, name)
            if include_all or not is_skipped(p):
                out.append(p)
    return out


def scan_file(path):
    try:
        if os.path.getsize(path) > 2 * 1024 * 1024:
            return []
        ext = os.path.splitext(path)[1].lower()
        if ext and ext not in TEXT_EXT:
            return []
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception:
        return []
    hits = []
    for i, line in enumerate(lines, 1):
        if ALLOW_LINE.search(line):
            continue
        for name, rx in PATTERNS:
            if rx.search(line):
                hits.append((i, name))
                break
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracked-only", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    files = None
    if args.tracked_only:
        files = tracked_files()
        if files is None:
            print("[secret_scan] not a git repo; falling back to walk",
                  file=sys.stderr)
    if files is None:
        files = walk_files()
    if args.all:
        files = walk_files(include_all=True)

    findings = []
    for p in files:
        if not os.path.isfile(p):
            continue
        for line, name in scan_file(p):
            findings.append((os.path.relpath(p, ROOT), line, name))
    if not findings:
        print("[secret_scan] OK: no credential patterns in %d files" % len(files))
        return 0
    print("[secret_scan] FAIL: %d potential secret(s)" % len(findings))
    for rel, line, name in findings[:200]:
        print("  %s:%d  %s" % (rel.replace("\\", "/"), line, name))
    if len(findings) > 200:
        print("  ... %d more" % (len(findings) - 200))
    print("[secret_scan] remove/rotate before committing; values not printed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
