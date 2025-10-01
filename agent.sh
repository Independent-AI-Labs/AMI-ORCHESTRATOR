#!/usr/bin/env bash
# Thin wrapper to start Codex CLI with strict guardrails.
# - Uses YOLO mode and a 20-minute default timeout
# - Embeds explicit instructions: no branch creation unless told; never bypass hooks
# - Relies on git hooks for branch enforcement; this script just launches Codex CLI

set -euo pipefail

INSTRUCTION=$(cat <<'EOF'
Stay on 'main' unless told otherwise — branch discipline is already enforced by git hooks.

You are operating in this repository with strict guardrails:

- Work only on 'main' unless the user explicitly says otherwise.
- Never, ever commit or push using --no-verify, and never bypass pre-commit or pre-push hooks.
- Only commit and push after ALL linters, type checks, and tests pass locally.
- Prefer uv-native workflows and per-module environments; avoid PATH/PYTHONPATH hacks.
- Use explicit, reproducible commands; surface failures clearly and stop.
- Do not touch ANY module (base/browser/compliance/etc.) unless the user explicitly instructs you to.
- Commit module-by-module (skip UX until told otherwise) so CI starts processing while you continue validating follow-up work.
- For dependency reviews: query real registries (`python3 - <<'PY'` against PyPI JSON, `npm view` / `npx pnpm@<ver> view`), pin exact versions (no ^ or ~), refresh locks (`uv lock --refresh`, `npm install`, `npx pnpm@<ver> install`), rerun module setup + tests, and call out any incompatibility forcing you off the latest release.
- Skip `domains/predict` installs/tests; it stays deprecated.

Notes:
- Default command timeout is 1200 seconds (20 minutes).
- Ask before any potentially destructive operation.

EOF
)

exec codex -m gpt-5-codex --yolo -- "$INSTRUCTION"
