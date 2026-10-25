# -*- coding: utf-8 -*-
"""Minimal LLM fallback for when the primary agent quota is exhausted.

Providers: Gemini -> Mistral (auto), or force one. Keys come from environment
only (GEMINI_API_KEY / MISTRAL_API_KEY); nothing is written to disk.

Example:
  python scripts/llm_fallback.py --file docs/HANDOFF.md \
      --prompt "Tom tat trang thai va de xuat 3 viec tiep theo"
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def post_json(url, payload, headers, timeout=90):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers,
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:"
           "generateContent?key=%s" % (model, key))
    data = post_json(url, {"contents": [{"parts": [{"text": prompt}]}]},
                     {"Content-Type": "application/json"})
    return data["candidates"][0]["content"]["parts"][0]["text"]


def mistral(prompt):
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY missing")
    model = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
    data = post_json(
        "https://api.mistral.ai/v1/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}],
         "temperature": 0.2},
        {"Content-Type": "application/json",
         "Authorization": "Bearer " + key})
    return data["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["auto", "gemini", "mistral"],
                    default="auto")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--file", default="")
    a = ap.parse_args()

    text = a.prompt
    if a.file:
        with open(a.file, encoding="utf-8", errors="replace") as f:
            text = (text + "\n\n" if text else "") + f.read()
    if not text.strip():
        print("empty prompt", file=sys.stderr)
        return 2

    order = ["gemini", "mistral"] if a.provider == "auto" else [a.provider]
    errors = []
    for name in order:
        try:
            out = gemini(text) if name == "gemini" else mistral(text)
            print(out)
            return 0
        except Exception as e:
            errors.append("%s: %s" % (name, e))
    print("all providers failed:\n  " + "\n  ".join(errors), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
