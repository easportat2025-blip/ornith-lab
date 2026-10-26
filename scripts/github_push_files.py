# -*- coding: utf-8 -*-
"""Push a set of local files to GitHub as one commit via the Git Data API.

Useful when `git push` over HTTPS is blocked/hangs but the REST API works.
Token comes from GH_TOKEN (never written to disk).

Example:
  python scripts/github_push_files.py --repo owner/name --branch main \
      --message "ops: update" docs/HANDOFF.md configs/kaggle_queue.json
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

API = "https://api.github.com"


def call(method, url, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API + url, data=data, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "ornith-push",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    return json.loads(raw.decode("utf-8")) if raw else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--message", required=True)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("GH_TOKEN missing", file=sys.stderr)
        return 2

    ref = call("GET", "/repos/%s/git/ref/heads/%s" % (a.repo, a.branch), token)
    parent = ref["object"]["sha"]
    commit = call("GET", "/repos/%s/git/commits/%s" % (a.repo, parent), token)
    base_tree = commit["tree"]["sha"]

    entries = []
    for path in a.files:
        with open(path, "rb") as f:
            content = f.read()
        blob = call("POST", "/repos/%s/git/blobs" % a.repo, token, {
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64"})
        entries.append({"path": path.replace("\\", "/"), "mode": "100644",
                        "type": "blob", "sha": blob["sha"]})
        print("blob", path, blob["sha"][:8], len(content))

    tree = call("POST", "/repos/%s/git/trees" % a.repo, token,
                {"base_tree": base_tree, "tree": entries})
    new_commit = call("POST", "/repos/%s/git/commits" % a.repo, token, {
        "message": a.message, "tree": tree["sha"], "parents": [parent]})
    call("PATCH", "/repos/%s/git/refs/heads/%s" % (a.repo, a.branch), token,
         {"sha": new_commit["sha"], "force": False})
    print("pushed", a.repo, a.branch, new_commit["sha"])
    print("https://github.com/%s/commit/%s" % (a.repo, new_commit["sha"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
