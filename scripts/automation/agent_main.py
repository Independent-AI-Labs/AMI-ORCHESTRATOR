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

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

# Standard /base imports pattern to find orchestrator root
_root = next(p for p in Path(__file__).resolve().parents if (p / "base").exists())
sys.path.insert(0, str(_root))
from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, MODULE_ROOT = setup_imports()

# Ensure scripts.automation is importable
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from scripts.automation.agent_cli import (
    AgentConfigPresets,
    AgentError,
    AgentExecutionError,
    get_agent_cli,
)
from scripts.automation.audit import AuditEngine
from scripts.automation.config import get_config
from scripts.automation.hooks import (
    CodeQualityValidator,
    CommandValidator,
    ResponseScanner,
)
from scripts.automation.logger import get_logger


def _create_mcp_config_file(config: Any) -> Path | None:
    """Create MCP configuration file from automation.yaml config.

    Args:
        config: Configuration object

    Returns:
        Path to created config file if MCP enabled and servers configured, None otherwise
    """
    mcp_enabled = config.get("mcp.enabled", True)
    if not mcp_enabled:
        return None

    mcp_servers = config.get("mcp.servers", {})
    if not mcp_servers:
        return None

    # Build MCP config from YAML configuration
    mcp_config: dict[str, Any] = {"mcpServers": {}}

    for server_name, server_config in mcp_servers.items():
        # Substitute {root} template in args
        args = []
        for arg in server_config.get("args", []):
            if isinstance(arg, str) and "{root}" in arg:
                args.append(arg.format(root=config.root))
            else:
                args.append(arg)

        mcp_config["mcpServers"][server_name] = {
            "command": server_config["command"],
            "args": args,
        }

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mcp_config_file:
            json.dump(mcp_config, mcp_config_file)
            file_name = mcp_config_file.name

        return Path(file_name)
    except (OSError, TypeError) as e:
        # Clean up file if it was created
        if "mcp_config_file" in locals() and hasattr(mcp_config_file, "name"):
            Path(mcp_config_file.name).unlink(missing_ok=True)
        raise RuntimeError(f"Failed to write MCP config: {e}") from e


def _create_settings_file(_config: Any) -> Path:
    """Create Claude settings file with hooks from config.

    Args:
        _config: Configuration object (unused, preserved for future use)

    Returns:
        Path to created settings file with hooks configuration

    Raises:
        RuntimeError: If hooks file not found or settings file write fails
    """
    # Delegate to agent_cli for hook settings file creation
    return get_agent_cli()._create_full_hooks_file()


def mode_interactive(continue_session: bool = False, resume: str | bool | None = None, fork_session: bool = False) -> int:
    """Interactive mode - Launch Claude Code with hooks.

    Args:
        continue_session: Continue the most recent conversation
        resume: Resume a conversation (True for interactive selection, string for specific session ID)
        fork_session: Create a new session ID when resuming

    Returns:
        Exit code (0=success, 1=failure)
    """
    config = get_config()
    logger = get_logger("ami-agent")

    # Load agent instruction from file
    prompts_dir = config.root / config.get("prompts.dir")
    agent_file = prompts_dir / config.get("prompts.agent")

    instruction = agent_file.read_text()

    # Inject current date
    instruction = instruction.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"))

    # Create MCP config file from automation.yaml
    mcp_config_file = _create_mcp_config_file(config)
    mcp_enabled = mcp_config_file is not None

    # Create settings file with hooks
    settings_file = _create_settings_file(config)

    # Debug: log settings file path
    logger.info("created_settings_file", path=str(settings_file))

    # Debug log file
    debug_log = config.root / "claude-debug.log"
    with debug_log.open("a") as f:
        f.write(f"=== Claude session started at {datetime.now()} ===\n")

    # Launch Claude Code
    logger.info("session_start", mode="interactive", mcp_enabled=mcp_enabled)

    try:
        # Get Claude CLI command from config
        claude_cmd = config.get("claude_cli.command", "claude")

        # Build command
        cmd = [
            claude_cmd,
        ]

        # Add resume/continue flags
        if continue_session:
            cmd.append("--continue")
        elif resume:
            if isinstance(resume, str):
                # Specific session ID provided
                cmd.extend(["--resume", resume])
            else:
                # Interactive selection
                cmd.append("--resume")

        # Add fork-session flag if requested
        if fork_session:
            cmd.append("--fork-session")

        # Add MCP config if enabled
        if mcp_config_file:
            cmd.extend(["--mcp-config", str(mcp_config_file)])

        cmd.extend(["--settings", str(settings_file), "--", instruction])

        # Debug: log the command being run
        logger.info("launching_claude", command=" ".join(cmd[:5]) + " ...")

        # Redirect stderr to debug log
        with debug_log.open("a") as log_file:
            subprocess.run(cmd, check=False, stderr=log_file)
        return 0
    finally:
        settings_file.unlink(missing_ok=True)
        if mcp_config_file:
            mcp_config_file.unlink(missing_ok=True)
        logger.info("session_end")


def mode_print(instruction_path: str) -> int:
    """Non-interactive mode - Run agent with --print.

    Uses worker agent preset (hooks enabled, all tools).
    Audit operations use different presets (audit, audit_diff, consolidate).

    Args:
        instruction_path: Path to instruction file

    Returns:
        Exit code (0=success, 1=failure)
    """
    instruction_file = Path(instruction_path)

    if not instruction_file.exists():
        print(f"Instruction file not found: {instruction_path}", file=sys.stderr)
        return 1

    # Read stdin
    stdin = sys.stdin.read()

    # Run with worker agent preset (hooks enabled, all tools)
    cli = get_agent_cli()
    try:
        session_id = str(uuid.uuid4())
        output = cli.run_print(
            instruction_file=instruction_file,
            stdin=stdin,
            agent_config=AgentConfigPresets.worker(session_id=session_id),
        )
        # Print output
        print(output)
        return 0
    except AgentExecutionError as e:
        # Print output even on failure
        print(e.stdout, end="")
        return e.exit_code
    except AgentError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def mode_hook(validator_name: str) -> int:
    """Hook validator mode - Validate hook input from stdin.

    Args:
        validator_name: Name of validator (command-guard, code-quality, response-scanner)

    Returns:
        Exit code (0=success, 1=failure)
    """
    validators = {
        "command-guard": CommandValidator,
        "code-quality": CodeQualityValidator,
        "response-scanner": ResponseScanner,
    }

    validator_class = validators.get(validator_name)

    if not validator_class:
        print(f"Unknown validator: {validator_name}", file=sys.stderr)
        print(f"Available: {', '.join(validators.keys())}", file=sys.stderr)
        return 1

    validator = validator_class()
    return validator.run()


def mode_audit(directory_path: str, retry_errors: bool = False) -> int:
    """Batch audit mode - Audit directory for code quality issues.

    Args:
        directory_path: Path to directory to audit
        retry_errors: If True, only re-audit files with ERROR status from previous run

    Returns:
        Exit code (0=success, 1=failure)
    """
    directory = Path(directory_path)

    if not directory.exists():
        print(f"Directory not found: {directory_path}", file=sys.stderr)
        return 1

    engine = AuditEngine()

    # Run audit
    results = engine.audit_directory(directory, parallel=True, max_workers=4, retry_errors=retry_errors)

    # Print summary
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    errors = sum(1 for r in results if r.status == "ERROR")

    print("\nAudit Summary:")
    print(f"  Total: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Errors: {errors}")

    # Print failures
    if failed > 0:
        print("\nFailures:")
        for result in results:
            if result.status == "FAIL":
                print(f"\n  {result.file_path}:")
                for violation in result.violations:
                    print(f"    Line {violation['line']}: {violation['message']}")

    return 1 if (failed > 0 or errors > 0) else 0


def mode_tasks(directory_path: str, root_dir: str | None = None, parallel: bool = False, user_instruction: str | None = None) -> int:
    """Task execution mode - Execute all .md task files in directory.

    Args:
        directory_path: Path to directory containing task files
        root_dir: Root directory where tasks execute (defaults to current directory)
        parallel: Enable parallel task execution
        user_instruction: Optional prepended instruction for all tasks

    Returns:
        Exit code (0=success, 1=failure)
    """
    directory = Path(directory_path)

    if not directory.exists():
        print(f"Directory not found: {directory_path}", file=sys.stderr)
        return 1

    # Convert root_dir to Path if provided
    root_path = Path(root_dir) if root_dir else None

    if root_path and not root_path.exists():
        print(f"Root directory not found: {root_dir}", file=sys.stderr)
        return 1

    from scripts.automation.tasks import TaskExecutor

    executor = TaskExecutor()

    # Execute tasks
    results = executor.execute_tasks(directory, parallel=parallel, root_dir=root_path, user_instruction=user_instruction)

    # Print summary
    completed = sum(1 for r in results if r.status == "completed")
    feedback = sum(1 for r in results if r.status == "feedback")
    failed = sum(1 for r in results if r.status == "failed")
    timeout = sum(1 for r in results if r.status == "timeout")

    print("\nTask Execution Summary:")
    print(f"  Total: {len(results)}")
    print(f"  Completed: {completed}")
    print(f"  Needs Feedback: {feedback}")
    print(f"  Failed: {failed}")
    print(f"  Timeout: {timeout}")

    # Print feedback files
    if feedback > 0:
        print("\nFeedback Files:")
        for result in results:
            if result.status == "feedback":
                print(f"  - {result.task_file.name}: See feedback-*-{result.task_file.stem}.md")

    # Print failed tasks
    if failed > 0:
        print("\nFailed Tasks:")
        for result in results:
            if result.status == "failed":
                print(f"  - {result.task_file.name}: {result.error}")

    return 1 if (failed > 0 or timeout > 0) else 0


def mode_sync(module_path: str) -> int:
    """Git sync mode - Ensure module is fully committed and pushed.

    Args:
        module_path: Path to git module directory

    Returns:
        Exit code (0=success, 1=failure)
    """
    module = Path(module_path)

    if not module.exists():
        print(f"Module not found: {module_path}", file=sys.stderr)
        return 1

    if not (module / ".git").exists():
        print(f"Not a git repository: {module_path}", file=sys.stderr)
        return 1

    from scripts.automation.sync import SyncExecutor

    executor = SyncExecutor()

    # Sync module
    result = executor.sync_module(module)

    # Print result
    print(f"\nSync Result: {result.status.upper()}")
    print(f"  Module: {result.module_path}")
    print(f"  Attempts: {len(result.attempts)}")
    print(f"  Duration: {result.total_duration:.1f}s")

    if result.error:
        print(f"  Error: {result.error}")

    if result.status == "feedback":
        print("\n  Needs Feedback: See .sync-progress-*.md in module directory")

    return 0 if result.status == "synced" else 1


def mode_docs(directory_path: str, root_dir: str | None = None, parallel: bool = False) -> int:
    """Documentation maintenance mode - Maintain all .md docs in directory.

    Args:
        directory_path: Path to directory containing documentation files
        root_dir: Root directory for codebase inspection (defaults to current directory)
        parallel: Enable parallel doc maintenance

    Returns:
        Exit code (0=success, 1=failure)
    """
    directory = Path(directory_path)

    if not directory.exists():
        print(f"Directory not found: {directory_path}", file=sys.stderr)
        return 1

    # Convert root_dir to Path if provided
    root_path = Path(root_dir) if root_dir else None

    if root_path and not root_path.exists():
        print(f"Root directory not found: {root_dir}", file=sys.stderr)
        return 1

    from scripts.automation.docs import DocsExecutor

    executor = DocsExecutor()

    # Execute docs maintenance
    results = executor.execute_docs(directory, parallel=parallel, root_dir=root_path)

    # Print summary
    completed = sum(1 for r in results if r.status == "completed")
    feedback = sum(1 for r in results if r.status == "feedback")
    failed = sum(1 for r in results if r.status == "failed")
    timeout = sum(1 for r in results if r.status == "timeout")

    print("\nDocumentation Maintenance Summary:")
    print(f"  Total: {len(results)}")
    print(f"  Completed: {completed}")
    print(f"  Needs Feedback: {feedback}")
    print(f"  Failed: {failed}")
    print(f"  Timeout: {timeout}")

    # Print action breakdown for completed docs
    if completed > 0:
        updated = sum(1 for r in results if r.status == "completed" and r.action == "UPDATE")
        archived = sum(1 for r in results if r.status == "completed" and r.action == "ARCHIVE")
        deleted = sum(1 for r in results if r.status == "completed" and r.action == "DELETE")

        print("\nActions Taken:")
        print(f"  Updated: {updated}")
        print(f"  Archived: {archived}")
        print(f"  Marked for Deletion: {deleted}")

    # Print feedback files
    if feedback > 0:
        print("\nDocs Needing Feedback:")
        for result in results:
            if result.status == "feedback" and result.feedback:
                print(f"  - {result.doc_file.name}: {result.feedback[:100]}...")

    # Print failed docs
    if failed > 0:
        print("\nFailed Docs:")
        for result in results:
            if result.status == "failed":
                print(f"  - {result.doc_file.name}: {result.error}")

    return 1 if (failed > 0 or timeout > 0) else 0


def main() -> int:
    """Main entry point - Route to appropriate mode."""
    import argparse

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
        help="Hook validator mode (command-guard, code-quality, response-scanner)",
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
        metavar="DIRECTORY",
        help="Task execution mode - process all .md files as tasks",
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
        help="Prepend instruction to all tasks (for --tasks mode)",
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
    mode_handlers: list[tuple[str | bool | None, Callable[[], int]]] = [
        (args.print, lambda: mode_print(args.print) if args.print else 1),
        (args.hook, lambda: mode_hook(args.hook) if args.hook else 1),
        (args.audit, lambda: mode_audit(args.audit, retry_errors=args.retry_errors) if args.audit else 1),
        (
            args.tasks,
            lambda: mode_tasks(args.tasks, root_dir=args.root_dir, parallel=args.parallel, user_instruction=args.user_instruction) if args.tasks else 1,
        ),
        (args.sync, lambda: mode_sync(args.sync) if args.sync else 1),
        (args.docs, lambda: mode_docs(args.docs, root_dir=args.root_dir, parallel=args.parallel) if args.docs else 1),
    ]

    for condition, handler in mode_handlers:
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
