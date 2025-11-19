#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../scripts/ami-run" "$(dirname "$0")/agent_main.py" "$@"
"""

from __future__ import annotations

"""AMI Agent - Unified automation entry point.

Replaces multiple bash scripts (claude-agent.sh, claude-audit.sh, etc.)
with a single Python entry point supporting multiple modes.

Called via ami-run wrapper (scripts/ami-agent).

Usage:
    ami-agent                           # Interactive mode (default)
    ami-agent --interactive             # Interactive mode (explicit)
    ami-agent --continue                # Continue most recent conversation
    ami-agent --resume [SESSION_ID]     # Resume conversation (interactive or by ID)
    ami-agent --print <instruction>     # Non-interactive mode
    ami-agent --hook <validator>        # Hook validator mode
    ami-agent --audit <directory>       # Batch audit mode
    ami-agent --tasks <directory>       # Task execution mode
    ami-agent --sync <module>           # Git sync mode
    ami-agent --docs <directory>        # Documentation maintenance mode

Examples:
    # Interactive agent with hooks
    ami-agent

    # Continue most recent conversation
    ami-agent --continue

    # Resume specific conversation
    ami-agent --resume abc123

    # Resume with interactive selection
    ami-agent --resume

    # Fork session when resuming
    ami-agent --resume --fork-session

    # Non-interactive audit from stdin
    cat file.py | ami-agent --print config/prompts/audit.txt

    # Hook validator (called by Claude Code)
    ami-agent --hook code-quality < hook_input.json

    # Batch audit
    ami-agent --audit base/

    # Documentation maintenance
    ami-agent --docs docs/
"""

import argparse  # noqa: E402
import sys  # noqa: E402
from collections.abc import Callable  # noqa: E402
from pathlib import Path  # noqa: E402

# Standard /base imports pattern to find orchestrator root
_root = next(p for p in Path(__file__).resolve().parents if (p / "base").exists())
sys.path.insert(0, str(_root))
from base.scripts.env.paths import setup_imports  # noqa: E402

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

# Additional imports after path setup

# Load .env file before importing automation modules (ensures env vars available for Config)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ORCHESTRATOR_ROOT / ".env")

# Ensure scripts.automation is importable
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from scripts.agents.cli.mode_handlers import (  # noqa: E402
    mode_audit,
    mode_docs,
    mode_hook,
    mode_interactive,
    mode_print,
    mode_sync,
    mode_tasks,
)


def main() -> int:
    """Main entry point - Route to appropriate mode."""
    parser = argparse.ArgumentParser(
        description="AMI Agent - Unified automation entry point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode (default)",
    )

    parser.add_argument(
        "--print",
        metavar="INSTRUCTION_FILE",
        help="Non-interactive mode - run Claude CLI with --print",
    )

    parser.add_argument(
        "--hook",
        metavar="VALIDATOR",
        help=(
            "Hook validator mode (malicious-behavior, command-guard, research-validator, "
            "code-quality-core, code-quality-python, response-scanner, shebang-check, todo-validator)"
        ),
    )

    parser.add_argument(
        "--audit",
        metavar="DIRECTORY",
        help="Batch audit mode - audit directory for code quality issues",
    )

    parser.add_argument(
        "--retry-errors",
        action="store_true",
        help="Retry only ERROR status files from previous audit (requires --audit)",
    )

    parser.add_argument(
        "--tasks",
        metavar="PATH",
        help="Task execution mode - process .md task file or all .md files in directory",
    )

    parser.add_argument(
        "--sync",
        metavar="MODULE",
        help="Git sync mode - ensure module is fully committed and pushed",
    )

    parser.add_argument(
        "--docs",
        metavar="DIRECTORY",
        help="Documentation maintenance mode - maintain all .md docs in directory",
    )

    parser.add_argument(
        "--root-dir",
        metavar="DIRECTORY",
        help="Root directory where tasks execute (defaults to current directory)",
    )

    parser.add_argument(
        "--user-instruction",
        metavar="TEXT",
        help="Prepend instruction to all workers (for --tasks, --sync, --docs, --audit modes)",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel execution (for --tasks, --docs, or --audit)",
    )

    parser.add_argument(
        "-c",
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue the most recent conversation (interactive mode only)",
    )

    parser.add_argument(
        "-r",
        "--resume",
        nargs="?",
        const=True,
        metavar="SESSION_ID",
        help="Resume a conversation - provide a session ID or interactively select (interactive mode only)",
    )

    parser.add_argument(
        "--fork-session",
        action="store_true",
        help="Create a new session ID when resuming (use with --resume or --continue)",
    )

    args = parser.parse_args()

    # Route to appropriate mode using dispatch
    mode_handlers_list: list[tuple[str | bool | None, Callable[[], int]]] = [
        (args.print, lambda: mode_print(args.print) if args.print else 1),
        (args.hook, lambda: mode_hook(args.hook) if args.hook else 1),
        (args.audit, lambda: mode_audit(args.audit, retry_errors=args.retry_errors, user_instruction=args.user_instruction) if args.audit else 1),
        (
            args.tasks,
            lambda: mode_tasks(args.tasks, root_dir=args.root_dir, parallel=args.parallel, user_instruction=args.user_instruction) if args.tasks else 1,
        ),
        (args.sync, lambda: mode_sync(args.sync, user_instruction=args.user_instruction) if args.sync else 1),
        (args.docs, lambda: mode_docs(args.docs, root_dir=args.root_dir, parallel=args.parallel, user_instruction=args.user_instruction) if args.docs else 1),
    ]

    for condition, handler in mode_handlers_list:
        if condition:
            return handler()

    # Default to interactive
    return mode_interactive(
        continue_session=args.continue_session,
        resume=args.resume,
        fork_session=args.fork_session,
    )


if __name__ == "__main__":
    sys.exit(main())
