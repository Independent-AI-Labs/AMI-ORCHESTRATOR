"""Git module synchronization - moderator-worker pattern for commit/push operations.

Ensures git modules are fully committed and pushed upstream with zero tolerance for:
- Uncommitted changes
- Unpushed commits
- Test deletions
- Test skips
- Illegal file deletions
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .agent_cli import AgentConfigPresets, get_agent_cli
from .config import get_config
from .logger import get_logger


@dataclass
class SyncAttempt:
    """Single sync attempt record."""

    attempt_num: int
    worker_output: str
    moderator_decision: str
    duration: float


@dataclass
class SyncResult:
    """Sync operation result."""

    module_path: Path
    status: str  # "synced", "feedback", "failed", "timeout"
    attempts: list[SyncAttempt] = field(default_factory=list)
    error: str | None = None
    total_duration: float = 0.0


class SyncExecutor:
    """Execute git sync operations with moderator-worker pattern."""

    def __init__(self) -> None:
        """Initialize sync executor."""
        self.config = get_config()
        self.logger = get_logger("sync")
        self.cli = get_agent_cli()

    def sync_module(self, module_path: Path) -> SyncResult:
        """Sync a single git module.

        Args:
            module_path: Path to git module directory

        Returns:
            Sync result
        """
        start_time = time.time()
        attempts = []
        timeout = self.config.get("sync.timeout", 1800)

        # Progress file
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        module_name = module_path.name
        progress_file = module_path / f".sync-progress-{timestamp_str}.md"

        # Initialize progress
        progress_file.write_text(f"# Sync Progress: {module_name}\n\nStarted: {datetime.now()}\n\n")

        prompts_dir = self.config.root / self.config.get("prompts.dir")

        # Worker loop
        attempt_num = 0
        additional_context = ""

        while time.time() - start_time < timeout:
            attempt_num += 1
            attempt_start = time.time()

            self.logger.info("worker_attempt", module=module_name, attempt=attempt_num)

            # Update progress
            with progress_file.open("a") as f:
                f.write(f"## Attempt {attempt_num} ({datetime.now()})\n\n")

            # Worker instruction
            worker_instruction = f"""# Git Sync Task

MODULE: {module_path}

Your task is to ensure this git module is fully committed and pushed upstream.

Requirements:
1. Stage all changes (git add -A)
2. Create commit if needed (use scripts/git_commit.sh)
3. Push to upstream (use scripts/git_push.sh)
4. Pass all pre-commit and pre-push hooks
5. Zero tolerance for test deletions, test skips, or illegal file deletions

Signal completion:
- "WORK DONE" when module is fully synced
- "FEEDBACK: <reason>" if blocked

{additional_context}
"""

            # Execute worker
            worker_prompt = prompts_dir / "sync_worker.txt"
            worker_output = self.cli.run_print(
                instruction_file=worker_prompt,
                stdin=worker_instruction,
                agent_config=AgentConfigPresets.sync_worker(),
            )

            # Parse completion marker
            if "WORK DONE" in worker_output:
                worker_status = "completed"
            elif "FEEDBACK:" in worker_output:
                worker_status = "feedback"
                feedback_reason = worker_output.split("FEEDBACK:", 1)[1].strip()
                self.logger.info("worker_feedback", reason=feedback_reason)
            else:
                worker_status = "incomplete"

            # Update progress
            with progress_file.open("a") as f:
                f.write(f"Worker Status: {worker_status}\n\n")
                f.write(f"Output:\n```\n{worker_output}\n```\n\n")

            # Moderator validation
            moderator_prompt = prompts_dir / "sync_moderator.txt"
            validation_context = f"""MODULE: {module_path}

WORKER OUTPUT:
{worker_output}

WORKER STATUS: {worker_status}
"""

            moderator_output = self.cli.run_print(
                instruction_file=moderator_prompt,
                stdin=validation_context,
                agent_config=AgentConfigPresets.sync_moderator(),
            )

            # Record attempt
            attempt_duration = time.time() - attempt_start
            attempts.append(
                SyncAttempt(
                    attempt_num=attempt_num,
                    worker_output=worker_output,
                    moderator_decision=moderator_output,
                    duration=attempt_duration,
                )
            )

            # Parse moderator decision
            if "PASS" in moderator_output:
                total_duration = time.time() - start_time
                self.logger.info("sync_success", module=module_name, attempts=attempt_num)
                progress_file.unlink()
                return SyncResult(
                    module_path=module_path,
                    status="synced",
                    attempts=attempts,
                    total_duration=total_duration,
                )
            if "FAIL:" in moderator_output:
                fail_reason = moderator_output.split("FAIL:", 1)[1].strip()
                self.logger.info("moderator_fail", reason=fail_reason)
                additional_context = f"\n\n## Previous Attempt Failed\n\n{fail_reason}\n\nPlease fix and retry.\n"
                # Continue to next attempt
            else:
                self.logger.warning("moderator_unexpected_output", output=moderator_output[:200])
                additional_context = "\n\n## Moderator Error\n\nModerator did not return PASS or FAIL. Please ensure you signal completion correctly.\n"

            # Update progress
            with progress_file.open("a") as f:
                f.write(f"Moderator Decision: {moderator_output}\n\n")

        # Timeout
        total_duration = time.time() - start_time
        self.logger.error("sync_timeout", module=module_name, attempts=attempt_num)
        return SyncResult(
            module_path=module_path,
            status="timeout",
            attempts=attempts,
            error=f"Timeout after {timeout}s",
            total_duration=total_duration,
        )
