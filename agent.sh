#!/usr/bin/env bash
# Thin wrapper to start Codex CLI with strict guardrails.
# - Uses YOLO mode and a 20-minute default timeout
# - Embeds explicit instructions: no branch creation unless told; never bypass hooks
# - Enforces: NO DETACHED HEADS (do not enforce branch name)

set -euo pipefail

# Enforce only: no detached HEADs in repo or submodules
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)
  if [[ "$branch" == "HEAD" ]]; then
    echo "ERROR: Detached HEAD detected. NO DETACHED HEADS. Switch to a named branch (e.g., 'main')." >&2
  fi
  if git submodule status >/dev/null 2>&1; then
    mapfile -t offenders < <(git submodule foreach --quiet '
      b=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)
      if [[ "$b" == "HEAD" ]]; then
        echo "$path (detached)"
      fi
    ' || true)
    if (( ${#offenders[@]} > 0 )); then
      echo "ERROR: Detached HEAD detected in submodules:" >&2
      for o in "${offenders[@]}"; do echo " - $o" >&2; done
    fi
  fi
else
  echo "WARNING: Not in a git repository; cannot check HEAD state." >&2
fi

INSTRUCTION="\
NO FUCKING DETACHED HEADS — WE ARE WORKING ONLY IN MAIN ALWAYS UNLESS I SAY OTHERWISE!!!!!!\n\nYou are operating in this repository with strict guardrails:\n\n- Work only on 'main' unless the user explicitly says otherwise.\n- Never, ever commit or push using --no-verify, and never bypass pre-commit or pre-push hooks.\n- Only commit and push after ALL linters, type checks, and tests pass locally.\n- Prefer uv-native workflows and per-module environments; avoid PATH/PYTHONPATH hacks.\n- Use explicit, reproducible commands; surface failures clearly and stop.\n\nNotes:\n- Default command timeout is 1200 seconds (20 minutes).\n- Ask before any potentially destructive operation.\n"

exec codex -m gpt-5-codex --yolo -- "$INSTRUCTION"
