#!/usr/bin/env bash
# Thin wrapper to start Codex CLI with strict guardrails.
# - Uses YOLO mode and a 20-minute default timeout
# - Embeds explicit instructions: no branch creation unless told; never bypass hooks

set -euo pipefail

INSTRUCTION="\
You are operating in this repository with strict guardrails:

- Do NOT create branches unless the user explicitly instructs you to do so.
- Never, ever commit or push using --no-verify, and never bypass pre-commit or pre-push hooks.
- Only commit and push after ALL linters, type checks, and tests pass locally.
- Prefer uv-native workflows and per-module environments; avoid PATH/PYTHONPATH hacks.
- Use explicit, reproducible commands; surface failures clearly and stop.

Notes:
- Default command timeout is 1200 seconds (20 minutes).
- Ask before any potentially destructive operation.
"

exec codex --yolo --timeout 1200 -- "$INSTRUCTION"

