#!/usr/bin/env bash
# Thin wrapper to start Claude CLI with strict guardrails.
# - Uses --dangerously-skip-permissions and a 20-minute default timeout
# - Embeds explicit instructions: no branch creation unless told; never bypass hooks
# - Relies on git hooks for branch enforcement; this script just launches Claude CLI

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

# Inject current date and time for model awareness
CURRENT_DATETIME="Current date and time: $(date '+%Y-%m-%d %H:%M:%S %Z')"

INSTRUCTION=$(cat <<'EOF'
Stay on `main` for the root repo and every submodule; if you ever land on a detached HEAD, switch back immediately. Read the relevant source before taking any action or replying.

Rules:
- Touch module directories (`base`, `browser`, `compliance`, `domains`, `files`, `nodes`, `streams`, `ux`, etc.) only with explicit user direction. Ship production-ready changes, honour the banned terms (`fallback`, `backwards`, `compatibility`, `legacy`, `shim`, `stub`, `placeholder`), and migrate code/configs instead of layering aliases or dual formats.
- NEVER add lint suppressions (`# noqa`, `# type: ignore`, `# pylint: disable`, `# ruff: noqa`) unless explicitly requested. Fix the underlying issue.
- Add new dependencies only in a brand-new module after asking where it belongs; never bolt them onto existing modules.
- Commit only when the user orders it, after lint/tests pass, with every change staged via `git add -A`. Keep hooks enabled, land work module-by-module (skip `ux` until told), and never run `git pull`, `git rebase`, or `git merge` without explicit instruction.
- After wrapping work in any submodule, and when told to commit, run `git add -A` inside that submodule before committing so all changes land together.
- Push operations can run for several minutes because the hooks trigger CI/CD validation; let them finish.
- Prefer uv-native, module-scoped tooling; no PATH/PYTHONPATH hacks or silent storage defaults. Run each module’s test runner (e.g. `python3 scripts/run_tests.py`) and skip `domains/predict`.
- For dependency bumps, query real registries, pin exact versions, refresh locks through module tooling, rerun setup plus tests, and note any enforced ceilings.
- Set `AMI_COMPUTE_PROFILE` only when necessary; keep `.env` hosts, SSH defaults, and auth stack secrets current.
- Manage processes solely via `python nodes/scripts/setup_service.py {start|stop|restart} <service>`; never use `pkill`/`kill*`. Run `npm run dev` in another shell or background job.
- Use `setup_service.py preinstall`/`verify` and the tracked `docker-compose.*.yml` files; join the `docker` group before using compose.
- Leave `ux/ui-concept` alone unless asked; never introduce “fallback” behaviour. Ask before destructive operations. Default command timeout is 20 minutes.
- CRITICAL: NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.
EOF
)

# Prepend current date/time to instruction
INSTRUCTION="${CURRENT_DATETIME}

${INSTRUCTION}"

# Create temporary MCP config
MCP_CONFIG_FILE="$(mktemp)"
cleanup() {
  rm -f "$MCP_CONFIG_FILE"
}
trap cleanup EXIT

cat >"$MCP_CONFIG_FILE" <<JSON
{
  "mcpServers": {
    "browser": {
      "command": "python3",
      "args": [
        "${REPO_ROOT}/browser/scripts/run_chrome.py"
      ]
    }
  }
}
JSON

exec claude --dangerously-skip-permissions --mcp-config "$MCP_CONFIG_FILE" -- "$INSTRUCTION"
