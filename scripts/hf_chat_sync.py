# -*- coding: utf-8 -*-
"""Upload sanitized agent chat/state to a private HF dataset.

The source files may contain operational details, so the target is private.
Credentials are read from HF_TOKEN only and never written to disk.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPO = "kkouadn/ornith-chat"
DEFAULT_FILES = [
    "agent.md",
    "scripts/bus.jsonl",
    "scripts/oc_chat/events.jsonl",
    "docs/HANDOFF.md",
    "docs/CONTINUITY.md",
]

PATTERNS = [
    (re.compile(r"hf_[A-Za-z0-9]{20,}"), "hf_<redacted>"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "github_pat_<redacted>"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "gh_<redacted>"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "AIza<redacted>"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "sk-<redacted>"),
    (re.compile(r"(?i)(KAGGLE_KEY|HF_TOKEN|GEMINI_API_KEY|MISTRAL_API_KEY|GITHUB_TOKEN|GH_TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{12,}"),
     r"\1=<redacted>"),
    (re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{20,}"),
     r"\1=<redacted>"),
]


def redact(text):
    hits = 0
    for pat, repl in PATTERNS:
        text, n = pat.subn(repl, text)
        hits += n
    return text, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--files", nargs="*", default=DEFAULT_FILES)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("WARN: HF_TOKEN missing; nothing uploaded.")
        return 0

    out = tempfile.mkdtemp(prefix="ornith_chat_")
    manifest = []
    total_hits = 0
    try:
        for rel in a.files:
            src = os.path.join(ROOT, rel.replace("/", os.sep))
            if not os.path.isfile(src):
                continue
            with open(src, encoding="utf-8", errors="replace") as f:
                raw = f.read()
            clean, hits = redact(raw)
            total_hits += hits
            dst = os.path.join(out, rel.replace("/", "__"))
            with open(dst, "w", encoding="utf-8") as f:
                f.write(clean)
            manifest.append({
                "source": rel,
                "bytes_in": len(raw.encode("utf-8")),
                "bytes_out": len(clean.encode("utf-8")),
                "redactions": hits,
            })
            print("sanitized %-32s redactions=%d" % (rel, hits))

        with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "files": manifest, "redactions": total_hits},
                      f, ensure_ascii=False, indent=1)

        if a.dry_run:
            print("dry-run: %d file(s), %d redaction(s)" % (len(manifest), total_hits))
            return 0

        from huggingface_hub import HfApi
        api = HfApi(token=token)
        api.create_repo(repo_id=a.repo, repo_type="dataset", private=True,
                        exist_ok=True)
        api.upload_folder(folder_path=out, repo_id=a.repo, repo_type="dataset",
                          commit_message="chat sync %s" % time.strftime("%Y-%m-%d %H:%M"))
        print("uploaded to https://huggingface.co/datasets/%s" % a.repo)
        return 0
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
