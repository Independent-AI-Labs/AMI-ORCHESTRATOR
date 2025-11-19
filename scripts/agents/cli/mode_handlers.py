"""Mode handler functions for main CLI entry point."""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from base.backend.utils.uuid_utils import uuid7
from scripts.agents.audit import AuditEngine
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.exceptions import AgentError, AgentExecutionError
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.cli.hooks_utils import create_mcp_config_file, create_settings_file_from_hooks_config
from scripts.agents.cli.result_utils import count_status_types
from scripts.agents.config import get_config
from scripts.agents.docs import DocsExecutor
from scripts.agents.sync import SyncExecutor
from scripts.agents.tasks import TaskExecutor
from scripts.agents.utils.helpers import (
    validate_path_and_return_code,
)
from scripts.agents.workflows.quality_validators import (
    CoreQualityValidator,
    PythonQualityValidator,
    ShebangValidator,
)
from scripts.agents.workflows.research_validators import (
    ResearchValidator,
)
from scripts.agents.workflows.response_validators import (
    ResponseScanner,
)
from scripts.agents.workflows.security_validators import (
    CommandValidator,
    MaliciousBehaviorValidator,
)
from scripts.agents.workflows.todo_validators import (
    TodoValidatorHook,
)


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

    # Load agent instruction from file
    prompts_dir = config.root / config.get("prompts.dir")
    agent_file = prompts_dir / config.get("prompts.agent")

    instruction = agent_file.read_text()

    # Inject current date
    instruction = instruction.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"))

    # Create MCP config file from automation.yaml
    mcp_config_file = create_mcp_config_file(config)
    mcp_enabled = mcp_config_file is not None

    # Create settings file with hooks
    settings_file = create_settings_file_from_hooks_config(config)

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

        # Validate executable exists in PATH before running
        if cmd and cmd[0]:
            executable = shutil.which(cmd[0])
            if not executable:
                logger.error("claude_command_not_found", command=cmd[0])
                return 1
            # Replace with full path to validated executable
            cmd[0] = executable

        # Redirect stderr to debug log
        # S603: cmd[0] validated via shutil.which() above, replacing with full path to executable
        with debug_log.open("a") as log_file:
            subprocess.run(cmd, check=False, stderr=log_file)  # noqa: S603
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
    if validate_path_and_return_code(instruction_path) != 0:
        return 1

    instruction_file = Path(instruction_path)

    # Read stdin
    stdin = sys.stdin.read()

    # Run with worker agent preset (hooks enabled, all tools)
    cli = get_agent_cli()
    try:
        session_id = uuid7()
        cli.run_print(
            instruction_file=instruction_file,
            stdin=stdin,
            agent_config=AgentConfigPresets.worker(session_id=session_id),
        )
        # Print output
        return 0
    except AgentExecutionError as e:
        # Print output even on failure
        return e.exit_code
    except AgentError:
        return 1


def mode_hook(validator_name: str) -> int:
    """Hook validator mode - Validate hook input from stdin.

    Args:
        validator_name: Name of validator (malicious-behavior, command-guard, research-validator,
                        code-quality-core, code-quality-python, response-scanner, shebang-check,
                        todo-validator)

    Returns:
        Exit code (0=success, 1=failure)
    """
    validators = {
        "malicious-behavior": MaliciousBehaviorValidator,
        "command-guard": CommandValidator,
        "research-validator": ResearchValidator,
        "code-quality-core": CoreQualityValidator,
        "code-quality-python": PythonQualityValidator,
        "response-scanner": ResponseScanner,
        "shebang-check": ShebangValidator,
        "todo-validator": TodoValidatorHook,
    }

    validator_class = validators.get(validator_name)

    if not validator_class:
        return 1

    validator = validator_class()
    result: int = validator.run()
    return result


def mode_audit(directory_path: str, retry_errors: bool = False, user_instruction: str | None = None) -> int:
    """Batch audit mode - Audit directory for code quality issues.

    Args:
        directory_path: Path to directory to audit
        retry_errors: If True, only re-audit files with ERROR status from previous run
        user_instruction: Optional prepended instruction for the audit workers

    Returns:
        Exit code (0=success, 1=failure)
    """
    if validate_path_and_return_code(directory_path) != 0:
        return 1

    engine = AuditEngine()

    # Run audit
    results = engine.audit_directory(Path(directory_path), parallel=True, max_workers=4, retry_errors=retry_errors, user_instruction=user_instruction)

    # Print summary
    status_counts = count_status_types(results, ["failed", "timeout"])  # Using the standard status values
    failed = status_counts["failed"]
    errors = status_counts["timeout"]

    # Print failures
    if failed > 0:
        for result in results:
            if result.status in ("failed", "timeout"):  # Using the standard status values
                for _violation in result.violations:
                    pass

    return 1 if (failed > 0 or errors > 0) else 0


def mode_tasks(path: str, root_dir: str | None = None, parallel: bool = False, user_instruction: str | None = None) -> int:
    """Task execution mode - Execute .md task file(s).

    Args:
        path: Path to .md task file OR directory containing task files
        root_dir: Root directory where tasks execute (defaults to current directory)
        parallel: Enable parallel task execution
        user_instruction: Optional prepended instruction for all tasks

    Returns:
        Exit code (0=success, 1=failure)
    """
    if validate_path_and_return_code(path) != 0:
        return 1

    # Convert root_dir to Path if provided
    root_path = Path(root_dir) if root_dir else None

    if root_path and not root_path.exists():
        return 1

    executor = TaskExecutor()

    # Execute tasks (handles both file and directory)
    results = executor.execute_tasks(Path(path), parallel=parallel, root_dir=root_path, user_instruction=user_instruction)

    # Print summary
    status_counts = count_status_types(results, ["feedback", "failed", "timeout"])
    feedback = status_counts["feedback"]
    failed = status_counts["failed"]
    timeout = status_counts["timeout"]

    # Print feedback files
    if feedback > 0:
        for result in results:
            if result.status == "feedback":
                pass

    # Print failed tasks
    if failed > 0:
        for result in results:
            if result.status == "failed":
                pass

    return 1 if (failed > 0 or timeout > 0) else 0


def mode_sync(module_path: str, user_instruction: str | None = None) -> int:
    """Git sync mode - Ensure module is fully committed and pushed.

    Args:
        module_path: Path to git module directory
        user_instruction: Optional prepended instruction for the sync worker

    Returns:
        Exit code (0=success, 1=failure)
    """
    if validate_path_and_return_code(module_path) != 0:
        return 1

    module = Path(module_path)
    if not (module / ".git").exists():
        return 1

    executor = SyncExecutor()

    # Sync module
    result = executor.sync_module(module, user_instruction=user_instruction)

    # Print result

    if result.error:
        pass

    if result.status == "feedback":
        pass

    return 0 if result.status == "synced" else 1


def mode_docs(directory_path: str, root_dir: str | None = None, parallel: bool = False, user_instruction: str | None = None) -> int:
    """Documentation maintenance mode - Maintain all .md docs in directory.

    Args:
        directory_path: Path to directory containing documentation files
        root_dir: Root directory for codebase inspection (defaults to current directory)
        parallel: Enable parallel doc maintenance
        user_instruction: Optional prepended instruction for the docs worker

    Returns:
        Exit code (0=success, 1=failure)
    """
    if validate_path_and_return_code(directory_path) != 0:
        return 1

    # Convert root_dir to Path if provided
    root_path = Path(root_dir) if root_dir else None

    if root_path and not root_path.exists():
        return 1

    executor = DocsExecutor()

    # Execute docs maintenance
    results = executor.execute_docs(Path(directory_path), parallel=parallel, root_dir=root_path, user_instruction=user_instruction)

    # Print summary
    status_counts = count_status_types(results, ["completed", "feedback", "failed", "timeout"])
    completed = status_counts["completed"]
    feedback = status_counts["feedback"]
    failed = status_counts["failed"]
    timeout = status_counts["timeout"]

    # Print action breakdown for completed docs
    if completed > 0:
        sum(1 for r in results if r.status == "completed" and r.action == "UPDATE")
        sum(1 for r in results if r.status == "completed" and r.action == "ARCHIVE")
        sum(1 for r in results if r.status == "completed" and r.action == "DELETE")

    # Print feedback files
    if feedback > 0:
        for result in results:
            if result.status == "feedback" and result.feedback:
                pass

    # Print failed docs
    if failed > 0:
        for result in results:
            if result.status == "failed":
                pass

    return 1 if (failed > 0 or timeout > 0) else 0
