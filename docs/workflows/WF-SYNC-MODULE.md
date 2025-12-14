# Module Sync Process: Development Workflow

This document outlines the steps to safely update a module in the AMI Orchestrator system.

## Key Principle: No Cheating
You must properly fix all issues. No taking shortcuts, bypassing quality checks, or skipping required steps.
- Use --fix flag for most formatting/linting issues but address complex issues manually
- Never bypass quality checks
- No noqa, # pylint: disable, or other suppressions unless architecturally required
- Address root causes, not symptoms

## CRITICAL: NO CD ALLOWED - USE MODULE PATHS INSTEAD
You MUST NOT use `cd` to navigate into module directories. All operations must be performed from the orchestrator root using alternative git syntax with module paths:
- Instead of `cd module_name && git status`, use `git -C module_name status`
- Instead of `cd module_name && git diff`, use `git -C module_name diff HEAD`
- This ensures consistent execution context and prevents path-related errors

## Phase 1: Assessment & Preparation

1. **Identify Module Changes**: Use git with module path parameter from orchestrator root:
   - Check status: `git -C <modulename> status` (e.g., `git -C browser status`)
     - NOTE: This step may reveal that changes are already committed, showing "ahead of origin/main by X commits" with a clean working tree
   - Get source code specific diff: `git -C <modulename> diff HEAD -- '*.py' '*.md' '*.txt' '*.json' '*.yaml' '*.yml' '*.toml' '*.sh' '*.js' '*.ts' '*.html' '*.css' '*.rs' '*.go' '*.java' '*.cpp' '*.c' '*.h' '*.hpp'`
   - Document scope: new features, bug fixes, refactoring, etc.

2. **Create Commit Message** (IF CHANGES ARE UNCOMMITTED):
   - Create `/tmp/<modulename>/COMMIT_MSG.txt` with detailed description of changes (replace <modulename> with the actual module name like launcher, base, browser, etc.)
   - Focus only on source code changes
   - Use the echo command to create the commit message: `echo "feat: description of changes" > /tmp/<modulename>/COMMIT_MSG.txt`
   - NOTE: Skip this step if changes are already committed (clean working tree but ahead of origin)

## Phase 2: Commit Process (IF CHANGES ARE UNCOMMITTED)

1. **Execute Commit Script** (ONLY IF CHANGES ARE UNCOMMITTED): `scripts/git_commit.sh --fix <modulename> -F /tmp/<modulename>/COMMIT_MSG.txt`
   - Execute from orchestrator root (do NOT cd to module directory first)
   - This script includes ALL quality tools (formatting, linting, security checks) and auto-staging
   - The --fix flag will address many issues automatically, but all remaining issues must still be addressed systematically
   - NOTE: Skip this step if changes are already committed (verify with `git -C <modulename> status` - if it shows "working tree clean" but "ahead of origin/main by X commits", then changes are already committed)

2. **Handle Commit Failures**:
   - Create TODOs for ALL issues identified
   - Address issues systematically (no cheating/skipping quality checks)
   - Track with TODOs, address incrementally
   - Retry commit only after addressing issues
   - Iterate until successful

## Phase 3: Push Process

1. **Execute Push Script**: `scripts/git_push.sh <modulename>` after successful commit OR if changes are already committed but unpushed
   - Execute from orchestrator root (do NOT cd to module directory first)
   - NOTE: This step is also necessary when changes are already committed but not pushed (when git status shows "ahead of origin/main by X commits")

2. **Handle Push Failures**:
   - Add TODOs for failing tests
   - Fix tests and retry
   - Iterate until successful

3. **Nested Submodules Check**:
   - Check with `git status` after push
   - If nested submodule is 'dirty', repeat full sync process for that submodule
   - For nested submodule handling, always process from the deepest level of nesting outward
   - Start with the most deeply nested submodules first, then proceed to their parent modules
   - Continue until all submodules are clean

## Quality Assurance Rules
1. Never bypass quality checks - Always resolve issues properly
2. Fix root causes - Address actual problems, not symptoms
3. Security first - Address all vulnerabilities before proceeding
4. No quality avoidance tricks - Follow proper procedures only