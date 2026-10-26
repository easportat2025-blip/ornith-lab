# -*- coding: utf-8 -*-
"""Publish a sanitized source snapshot of this repo to a private HF dataset.

Only tracked files are archived (`git archive`), so ignored secrets, logs,
adapters and local state never leave the machine. A secret scan runs first
unless --skip-scan is passed. HF_TOKEN is read from the environment only.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPO = "kkouadn/ornith-lab-code"
MAX_BYTES = 60 * 1024 * 1024


def git(args):
    return subprocess.run(["git"] + args, cwd=ROOT, check=True,
                          capture_output=True, text=True, timeout=120)


def scan():
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "secret_scan.py"),
         "--tracked-only"],
        cwd=ROOT).returncode


def archive(ref, out):
    subprocess.run(["git", "archive", "--format=zip", "--output", out, ref],
                   cwd=ROOT, check=True, timeout=300)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--out", default="")
    ap.add_argument("--skip-scan", action="store_true")
    ap.add_argument("--require-token", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not a.skip_scan:
        rc = scan()
        if rc != 0:
            print("secret scan failed; refusing to upload", file=sys.stderr)
            return 1

    token = os.environ.get("HF_TOKEN", "")
    if not token and not a.dry_run:
        print("WARN: HF_TOKEN missing; nothing uploaded.")
        return 2 if a.require_token else 0

    commit = git(["rev-parse", a.ref]).stdout.strip()
    tmp = None
    out = a.out
    if not out:
        tmp = tempfile.mkdtemp(prefix="ornith_code_")
        out = os.path.join(tmp, "ornith-lab.zip")
    try:
        archive(a.ref, out)
        size = os.path.getsize(out)
        print("archive %s (%d bytes) ref=%s commit=%s" % (
            out, size, a.ref, commit[:12]))
        if size > MAX_BYTES:
            print("archive too large (limit %d); refusing" % MAX_BYTES,
                  file=sys.stderr)
            return 2
        manifest = {
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repo": "easportat2025-blip/ornith-lab",
            "ref": a.ref,
            "commit": commit,
            "bytes": size,
            "note": ("Tracked files only; secret scan passed."
                     if not a.skip_scan else "Secret scan skipped."),
        }
        with zipfile.ZipFile(out, "a") as z:
            z.writestr("ornith_code_manifest.json",
                       json.dumps(manifest, ensure_ascii=False, indent=2))
        print("manifest added")
        if a.dry_run:
            print("dry-run: not uploading")
            return 0

        from huggingface_hub import HfApi
        api = HfApi(token=token)
        api.create_repo(repo_id=a.repo, repo_type="dataset", private=True,
                        exist_ok=True)
        api.upload_file(path_or_fileobj=out, path_in_repo="ornith-lab.zip",
                        repo_id=a.repo, repo_type="dataset",
                        commit_message="code snapshot %s" % commit[:12])
        readme = os.path.join(ROOT, "README.md")
        if os.path.isfile(readme):
            api.upload_file(path_or_fileobj=readme, path_in_repo="README.md",
                            repo_id=a.repo, repo_type="dataset",
                            commit_message="code snapshot %s" % commit[:12])
        print("uploaded to https://huggingface.co/datasets/%s" % a.repo)
        return 0
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
