# -*- coding: utf-8 -*-
"""Minimal LLM fallback for when the primary agent quota is exhausted.

Providers (auto order): Groq -> Gemini -> OpenCode -> Mistral -> DeepSeek.
Keys come from environment only; nothing is written to disk. Multiple keys are
supported as NAME, NAME_2, NAME_3, ... and are rotated on 401/402/429/5xx.

Examples:
  python scripts/llm_fallback.py --file docs/HANDOFF.md \
      --prompt "Tom tat trang thai va de xuat 3 viec tiep theo"
  python scripts/llm_fallback.py --provider groq --prompt "Say OK"
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_MODELS = {
    "groq": ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"],
    "gemini": ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-flash-latest"],
    "mistral": ["mistral-small-latest", "ministral-8b-latest", "mistral-medium-latest"],
    "deepseek": ["deepseek-chat"],
    "opencode": ["deepseek-v4.1-flash-free", "mimo-v2.6-flash-free", "big-pickle"],
}

ENDPOINTS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "opencode": "https://opencode.ai/zen/v1/chat/completions",
}


def keys_for(provider):
    base = provider.upper() + "_API_KEY"
    out = []
    for name in [base] + [base + "_%d" % i for i in range(2, 10)]:
        v = os.environ.get(name, "")
        if v:
            out.append((name, v))
    return out


def post_json(url, payload, headers, timeout=120):
    headers = dict(headers)
    headers.setdefault("User-Agent", "ornith-fallback/1.0")
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers,
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def call_gemini(model, key, prompt):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:"
           "generateContent" % model)
    data = post_json(
        url, {"contents": [{"parts": [{"text": prompt}]}]},
        {"Content-Type": "application/json", "x-goog-api-key": key})
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_openai_compatible(provider, model, key, prompt):
    data = post_json(
        ENDPOINTS[provider],
        {"model": model,
         "messages": [{"role": "user", "content": prompt}],
         "temperature": 0.2},
        {"Content-Type": "application/json",
         "Authorization": "Bearer " + key})
    msg = data["choices"][0]["message"]
    return msg.get("content") or msg.get("reasoning") or ""


def try_provider(provider, prompt, model_override=""):
    keys = keys_for(provider)
    if not keys:
        return None, "%s: no key" % provider
    models = [model_override] if model_override else DEFAULT_MODELS[provider]
    errors = []
    for key_name, key in keys:
        for model in models:
            try:
                if provider == "gemini":
                    out = call_gemini(model, key, prompt)
                else:
                    out = call_openai_compatible(provider, model, key, prompt)
                if out and out.strip():
                    return out, "%s/%s via %s" % (provider, model, key_name)
                errors.append("%s/%s via %s: empty" % (provider, model, key_name))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:200]
                errors.append("%s/%s via %s: HTTP %s %s"
                              % (provider, model, key_name, e.code, body))
                # bad model -> try next model; bad key -> next key
                if e.code in (401, 402, 403, 429):
                    break
            except Exception as e:
                errors.append("%s/%s via %s: %s: %s"
                              % (provider, model, key_name,
                                 type(e).__name__, str(e)[:160]))
    return None, "\n  ".join(errors[-8:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="auto",
                    choices=["auto", "groq", "gemini", "mistral", "deepseek",
                             "opencode"])
    ap.add_argument("--model", default="")
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

    order = (["groq", "gemini", "opencode", "mistral", "deepseek"]
             if a.provider == "auto" else [a.provider])
    errors = []
    for name in order:
        out, info = try_provider(name, text, a.model)
        if out is not None:
            print(out)
            print("[fallback] " + info, file=sys.stderr)
            return 0
        errors.append(info)
    print("all providers failed:\n" + "\n".join(errors), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
