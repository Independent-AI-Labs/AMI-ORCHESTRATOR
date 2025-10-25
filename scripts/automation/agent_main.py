"""AMI Agent - Unified automation entry point.

Replaces multiple bash scripts (claude-agent.sh, claude-audit.sh, etc.)
with a single Python entry point supporting multiple modes.

Called via ami-run wrapper (scripts/ami-agent).

Usage:
    ami-agent                           # Interactive mode (default)
    ami-agent --interactive             # Interactive mode (explicit)
    ami-agent --print <instruction>     # Non-interactive mode
    ami-agent --hook <validator>        # Hook validator mode
    ami-agent --audit <directory>       # Batch audit mode

Examples:
    # Interactive agent with hooks
    ami-agent

    # Non-interactive audit from stdin
    cat file.py | ami-agent --print config/prompts/audit.txt

    # Hook validator (called by Claude Code)
    ami-agent --hook code-quality < hook_input.json

    # Batch audit
    ami-agent --audit base/
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

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


def _create_settings_file(config: Any) -> Path:
    """Create Claude settings file with hooks from config.

    Args:
        config: Configuration object

    Returns:
        Path to created settings file with hooks configuration

    Raises:
        RuntimeError: If hooks file not found or settings file write fails
    """
    # Load hooks from config
    hooks_file = config.root / config.get("hooks.file")
    if not hooks_file.exists():
        raise RuntimeError(f"Hooks file not found: {hooks_file}")

    with hooks_file.open() as f:
        hooks_config = yaml.safe_load(f)

    # Convert to Claude Code settings format
    settings: dict[str, Any] = {"hooks": {}}

    for hook in hooks_config["hooks"]:
        event = hook["event"]
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        # Build hook command with timeout
        hook_command = {
            "type": "command",
            "command": f"{config.root}/scripts/ami-agent --hook {hook['command']}",
        }

        if "timeout" in hook:
            hook_command["timeout"] = hook["timeout"]

        # Build hook entry with matcher first (for correct JSON order)
        hook_entry: dict[str, Any] = {}
        if "matcher" in hook:
            # Convert array matcher to regex string (e.g., ["Edit", "Write"] -> "Edit|Write")
            matcher = hook["matcher"]
            if isinstance(matcher, list):
                hook_entry["matcher"] = "|".join(matcher)
            else:
                hook_entry["matcher"] = matcher

        hook_entry["hooks"] = [hook_command]

        settings["hooks"][event].append(hook_entry)

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as settings_file:
            json.dump(settings, settings_file)
            file_name = settings_file.name

        return Path(file_name)
    except (OSError, TypeError) as e:
        # Clean up file if it was created
        if "settings_file" in locals() and hasattr(settings_file, "name"):
            Path(settings_file.name).unlink(missing_ok=True)
        raise RuntimeError(f"Failed to write settings file: {e}") from e


def mode_interactive() -> int:
    """Interactive mode - Launch Claude Code with hooks.

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
        output = cli.run_print(
            instruction_file=instruction_file,
            stdin=stdin,
            agent_config=AgentConfigPresets.worker(),
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
        help="Enable parallel execution (for --tasks or --audit)",
    )

    args = parser.parse_args()

    # Route to appropriate mode
    if args.print:
        return mode_print(args.print)
    if args.hook:
        return mode_hook(args.hook)
    if args.audit:
        return mode_audit(args.audit, retry_errors=args.retry_errors)
    if args.tasks:
        return mode_tasks(args.tasks, root_dir=args.root_dir, parallel=args.parallel, user_instruction=args.user_instruction)
    if args.sync:
        return mode_sync(args.sync)
    # Default to interactive
    return mode_interactive()


if __name__ == "__main__":
    sys.exit(main())
