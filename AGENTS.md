# Agent Guidelines

NO FUCKING DETACHED HEADS — WE ARE WORKING ONLY IN MAIN ALWAYS UNLESS I SAY OTHERWISE!!!!!!

Scope: This file applies to the entire AMI-ORCHESTRATOR repository and all directories under it, including submodules referenced by this repo.

Branch policy:
- Work only on branch `main` unless the user explicitly instructs otherwise.
- Never work on a detached HEAD. If you find yourself detached, switch to a named branch immediately.
- Submodules should also be on their respective `main` branches unless explicitly instructed otherwise.

Enforcement:
- `agent.sh` only prints an error when a detached HEAD is detected in the root repo or any submodule. It does not exit, and it does not enforce being on `main`.

Commit discipline:
- Do not bypass hooks (no `--no-verify`).
- Commit only after linters, type checks, and tests pass.

Process management:
- Run `npm run dev` for the UX app in the background (for example, `npm run dev &`) or in a separate terminal since it blocks the current shell.

Reference code:
- `ux/ui-concept` is prototype/reference code; do not spend cycles fixing lint or build failures there unless explicitly asked.
