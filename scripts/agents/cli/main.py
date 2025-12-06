#!/usr/bin/env bash
""":'
exec "$(dirname "$0")/../scripts/ami-run" "$(dirname "$0")/agent_main.py" "$@"
"""

from __future__ import annotations

"""AMI Agent - Unified automation entry point.

Replaces multiple bash scripts (claude-agent.sh, claude-audit.sh, etc.)
with a single Python entry point supporting multiple non-interactive modes.

Called via ami-run wrapper (scripts/ami-agent).

Usage:
    ami-agent --print <instruction>     # Non-interactive mode
    ami-agent --hook <validator>        # Hook validator mode
    ami-agent --audit <directory>       # Batch audit mode
    ami-agent --tasks <directory>       # Task execution mode
    ami-agent --sync <module>           # Git sync mode
    ami-agent --docs <directory>        # Documentation maintenance mode

Examples:
    # Non-interactive audit from stdin
    cat file.py | ami-agent --print config/prompts/audit.txt

    # Hook validator (called by Claude Code)
    ami-agent --hook code-quality < hook_input.json

    # Batch audit
    ami-agent --audit base/

    # Task execution
    ami-agent --tasks tasks/

    # Documentation maintenance
    ami-agent --docs docs/

    # Git synchronization
    ami-agent --sync base/
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

# Standard /base imports pattern to find orchestrator root
_root = next(p for p in Path(__file__).resolve().parents if (p / "base").exists())
sys.path.insert(0, str(_root))
from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

# Additional imports after path setup

# Load .env file before importing automation modules (ensures env vars available for Config)
from dotenv import load_dotenv

load_dotenv(ORCHESTRATOR_ROOT / ".env")

# Ensure scripts.automation is importable
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from scripts.agents.cli.mode_handlers import (
    mode_audit,
    mode_docs,
    mode_hook,
    mode_interactive_editor,
    mode_print,
    mode_query,
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

    # New argument for editor mode
    parser.add_argument(
        "--interactive-editor",
        action="store_true",
        help="Interactive editor mode - opens text editor first, Ctrl+S sends to agent",
    )

    parser.add_argument(
        "--query",
        metavar="QUERY",
        help="Non-interactive mode - run Claude CLI with provided query string",
    )

    args = parser.parse_args()

    # Route to appropriate mode using dispatch
    mode_handlers_list: list[tuple[str | bool | None, Callable[[], int]]] = [
        (args.interactive_editor, lambda: mode_interactive_editor() if args.interactive_editor else 1),
        (args.query, lambda: mode_query(args.query) if args.query else 1),
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

    # NEW: If no arguments provided, default to interactive editor mode
    if not any([args.print, args.hook, args.audit, args.tasks, args.sync, args.docs, args.interactive_editor]):
        return mode_interactive_editor()

    # Show help if no mode specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
