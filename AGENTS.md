# Agent Guidelines

- Read the relevant source before doing or saying anything.
- Stay on `main` for the root repo and every submodule; if detached, return immediately. This scope covers the entire tree and its submodules.
- Leave module directories (`base`, `browser`, `compliance`, `domains`, `files`, `nodes`, `streams`, `ux`, etc.) alone unless the user explicitly directs work there.
- Ship production-ready changes only; absolutely forbid the words `fallback`, `backwards`, `compatibility`, `legacy`, `shim`, `stub`, `placeholder`. Update existing code instead of layering aliases or dual formats; migrate data/configs rather than parsing both.
- New dependencies must live in a new module; ask where to put it first. Never bolt fresh dependencies onto an existing module.
- Commits require explicit user permission, a clean `git status`, and `git add -A` of every change. Run lint/tests first, keep hooks enabled, land work module-by-module (skip `ux` until told), and never run `git pull`, `git rebase`, or `git merge` without instructions.
- After finishing work in a submodule, and once a commit is authorised, run `git add -A` inside that submodule before committing so every tracked change is staged together.
- Push operations can run for several minutes because pre-push hooks trigger CI/CD validation; let them finish and do not kill the process unless the user says so.
- Prefer uv-native and module-scoped tooling; no PATH/PYTHONPATH hacks or silent storage-mode fallbacks.
- Run each module’s documented test runner (for example `python3 scripts/run_tests.py`); skip `domains/predict` entirely.
- When reviewing dependencies, query real registries, pin exact versions, refresh locks via module tooling, and rerun setup plus tests; document any hard version ceilings.
- Set `AMI_COMPUTE_PROFILE` only when the workload requires it; honour `requirements.env.<profile>.txt`. Keep `.env` host overrides, SSH defaults, and auth stack secrets current.
- Manage processes only through `python nodes/scripts/setup_service.py {start|stop|restart} <service>`; never touch `pkill`/`kill*`. Run `npm run dev` in a separate shell or background job.
- Use `setup_service.py preinstall` and `setup_service.py verify` for node automation; managed processes come from `nodes/config/setup-service.yaml`.
- Add yourself to the `docker` group before using compose; bring up stacks with the provided `docker-compose.*.yml` files when tests need them.
- Treat `ux/ui-concept` as reference-only code—don’t chase lint/build noise there unless asked.
- Never introduce “fallback” behaviour; surface optional storage or features explicitly.
- Ask before destructive actions. Default command timeout is 20 minutes.

CRITICAL: NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.
