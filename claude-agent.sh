#!/usr/bin/env bash
# Thin wrapper to start Claude CLI with strict guardrails.
# - Uses --dangerously-skip-permissions and a 20-minute default timeout
# - Embeds explicit instructions: no branch creation unless told; never bypass hooks
# - Relies on git hooks for branch enforcement; this script just launches Claude CLI

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

INSTRUCTION=$(cat <<'EOF'
Stay on 'main' unless told otherwise — branch discipline is already enforced by git hooks.

You are operating in this repository with strict guardrails:

- CRITICAL: NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.
- Work only on 'main' unless the user explicitly says otherwise.
- NEVER commit or push ANYTHING (chores, UI changes, refactors, etc.) without EXPLICIT user instruction to commit. User must explicitly say "commit" or similar. Making changes is fine, but committing them requires explicit permission.
- Never, ever commit or push using --no-verify, and never bypass pre-commit or pre-push hooks.
- Only commit and push after ALL linters, type checks, and tests pass locally.
- NEVER add Co-Authored-By, Generated with Claude Code, or ANY attribution lines to commit messages. Keep commits clean and simple.
- Prefer uv-native workflows and per-module environments; avoid PATH/PYTHONPATH hacks.
- Use explicit, reproducible commands; surface failures clearly and stop.
- Read every file before editing it. Inspect the current contents, then apply changes with the appropriate tool (no blind shell edits).
- BANNED WORDS POLICY (ABSOLUTE): The following words/concepts are ABSOLUTELY FORBIDDEN in code, comments, and documentation: fallback, backwards, compatibility, legacy, shim/shims, stub/stubs, placeholder/placeholders. NEVER add code to support old formats/APIs/field names alongside new ones. NEVER add aliasing or dual-format support. If old code needs updating: UPDATE THE OLD CODE, do not add compatibility layers. When migrating formats: MIGRATE the data/config files, do not add parsers for both formats.
- Do not touch ANY module (base/browser/compliance/etc.) unless the user explicitly instructs you to.
- ALWAYS implement fully production-ready functionality. Stubs, shims, and placeholders are strictly forbidden.
- Any new feature development that requires new dependencies MUST live in a newly created module. ALWAYS ask the user where to create the module before proceeding.
- Commit module-by-module (skip UX until told otherwise) so CI starts processing while you continue validating follow-up work.
- For dependency reviews: query real registries (`python3 - <<'PY'` against PyPI JSON, `npm view` / `npx pnpm@<ver> view`), pin exact versions (no ^ or ~), refresh locks (`uv lock --refresh`, `npm install`, `npx pnpm@<ver> install`), rerun module setup + tests, and call out any incompatibility forcing you off the latest release.
- Skip `domains/predict` installs/tests; it stays deprecated.
- CRITICAL: NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.

Notes:
- Default command timeout is 1200 seconds (20 minutes).
- Ask before any potentially destructive operation.

EOF
)

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
