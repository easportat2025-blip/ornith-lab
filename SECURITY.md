# Security Policy

## Supported versions

`main` is the only supported branch. `ops-state` contains runtime state, not
code. Experiments live on short-lived branches until they pass the gate.

## Reporting a vulnerability

Do not open a public issue containing credentials, private dataset URLs, or
exploit details. Use GitHub's private vulnerability reporting
(**Security → Advisories → Report a vulnerability**) or contact the maintainers
directly.

If a credential may have leaked, **rotate it first**, then report the incident.
Never paste a live key into an issue, pull request, chat, or log.

## Secret handling

- Secrets live in **GitHub Actions secrets** or **Hugging Face secrets**.
  Local development may read them from environment variables or HKCU; they are
  never written into the repository.
- Never commit `.env`, `kaggle.json`, `token.json`, `oauth.json`,
  `sessions.json`, `scripts/colab_accounts/**`, private keys, or logs.
- `scripts/secret_scan.py --tracked-only` runs in `ci.yml` and `hf-sync.yml`.
  It prints only `file:line` and the pattern name, never the matched value.
- `scripts/hf_code_sync.py` archives **tracked files only** with
  `git archive`, runs the secret scan first, and refuses archives over 60 MB.
- `scripts/hf_chat_sync.py` redacts known token patterns before uploading
  sanitized ops docs to the private `kkouadn/ornith-chat` dataset.
- Do not put credentials in kernel metadata, dataset cards, screenshots,
  benchmark outputs, or GitHub issue bodies.

## Rotation

Rotate immediately if a token was pasted into chat, committed, printed in a
workflow log, or included in an artifact:

1. Revoke the old token at the provider.
2. Create a replacement with the minimum required scopes.
3. Update GitHub Actions secrets and HF secrets.
4. Re-run the affected workflow and confirm it succeeds.
5. Record the incident in `docs/HANDOFF.md` **without the value**.

The Kaggle, Hugging Face, GitHub, Gemini, Mistral, DeepSeek, Groq, and OpenCode
keys are independent; rotate only the affected one, then verify the fallback
chain still works.

## CI and workflow controls

- Each workflow declares least-privilege `permissions`.
- `ci.yml`: compile checks, YAML/JSON validation, secret scan, pytest, job
  registry tests, and a headless API smoke test. It has `contents: read` only.
- `kaggle-watchdog.yml`: `contents: write` and `issues: write` so it can update
  the `ops-state` branch and the watchdog issue. It never stores credentials.
- `ops-tick.yml`: `actions: write` only, so it can dispatch the next watchdog
  run. It does not read repository contents.
- `ops-heartbeat.yml`: `contents: read` and `issues: write`.
- `hf-sync.yml`: `contents: read`; uploads use the `HF_TOKEN` secret.
- Dependabot keeps GitHub Actions and Python dependencies current.
- Third-party actions use major version tags; review Dependabot PRs before
  merging.

## Scope

This policy covers the code, workflows, scripts, and docs in this repository.
Kaggle kernels and Hugging Face datasets are separate systems, but the same
rules apply: no credentials in artifacts, no public upload of private state.
