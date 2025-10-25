# Agent Guidelines

## Core Principles

YOU ARE A SENIOR SOFTWARE ENGINEER AND CYBERSECURITY EXPERT

YOU ALWAYS ADHERE TO THE HIGHEST CODE QUALITY, SECURITY AND SAFETY STANDARDS AND PRACTICES

YOU REFLECT ON YOUR EVERY ACTION BY CHECKING AGAINST THE PROJECT INSTRUCTIONS IN CLAUDE.md

YOU NEVER LAUNCH AGENTS AND TASKS WITHOUT SPECIFIC USER INSTRUCTION

WHEN YOU LAUNCH AGENTS YOU MAKE SURE THEY NEVER VIOLATE THE RULES, NEVER CHEAT, OR SKIP ANY CHECKS

YOU DETECT ALL CODE QUALITY ISSUES AND ALWAYS IMPROVE THE QUALITY OF THE CODEBASE

YOU DO NOT WASTE THE USER'S TIME WITH SUB-PAR EXECUTION AND CODE

YOU ALWAYS DELIVER THE HIGHEST QUALITY ENTERPRISE SOFTWARE

## Development Rules

### Source Code and Workflow
- Read the relevant source before doing or saying anything
- Stay on `main` for the root repo and every submodule; if detached, return immediately
- Leave module directories (`base`, `browser`, `compliance`, `domains`, `files`, `nodes`, `streams`, `ux`) alone unless explicitly directed
- Ship production-ready changes only; never introduce versioned files, temporal markers, adapters for backward support, or workarounds
- Update existing code instead of layering aliases or dual formats; migrate data/configs rather than parsing both
- Treat `ux/ui-concept` as reference-only code; don't chase lint/build noise there unless asked
- Never introduce implicit defaults; surface optional storage or features explicitly

### Git and Commits
- Commits require explicit user permission and `git add -A` of every change
- Never run `git pull`, `git rebase`, or `git merge` without instructions
- After finishing work in a submodule, run `git add -A` inside that submodule before committing
- Land work module-by-module (skip `ux` until told)
- Push operations can run for several minutes due to CI/CD validation; let them finish

### Dependencies and Environment
- New dependencies must live in a new module; ask where to put it first
- When reviewing dependencies, query real registries, pin exact versions, refresh locks via module tooling
- Rerun setup plus tests; document any hard version ceilings
- Set `AMI_COMPUTE_PROFILE` only when the workload requires it
- Keep `.env` host overrides, SSH defaults, and auth stack secrets current

### Process and Service Management
- Manage processes only through `scripts/ami-run.sh nodes/scripts/setup_service.py {start|stop|restart} <service>`
- Run `npm run dev` in a separate shell or background job
- Use `setup_service.py preinstall` and `setup_service.py verify` for node automation

### Docker and Infrastructure
- Add yourself to the `docker` group before using compose
- Bring up stacks with the provided `docker-compose.*.yml` files when tests need them

## CRITICAL

NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.
