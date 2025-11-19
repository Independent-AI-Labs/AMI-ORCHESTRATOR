"""Audit orchestration engine.

Coordinates multi-file code audits using LLM-based analysis.
Security CRITICAL: CACHING IS STRICTLY FORBIDDEN to ensure real-time analysis for security audits.
Supports parallel processing and pattern consolidation.
"""

import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from loguru import logger

from scripts.agents.audit_utils.processing import consolidate_patterns, parse_audit_output, save_report
from scripts.agents.cli.config import AgentConfigPresets
from scripts.agents.cli.factory import get_agent_cli
from scripts.agents.common import GenericExecutor, detect_language
from scripts.agents.core.models import ExecutionStatus, UnifiedExecutionResult

# Resource limits
MAX_FILE_SIZE = 1024 * 1024  # 1MB
MAX_WORKERS = 8


class AuditEngine(GenericExecutor[UnifiedExecutionResult]):
    """Orchestrates multi-file code audits.

    Features:
    - Parallel processing with ProcessPoolExecutor
    - Language detection
    - Include/exclude pattern scanning
    - Special __init__.py handling (skip empty files)
    - Progress tracking
    - Report generation with mirrored directory structure
    - Pattern consolidation for FAIL/ERROR files
    - SECURITY CRITICAL: Real-time analysis only (no caching)
    """

    def __init__(self) -> None:
        """Initialize audit engine."""
        super().__init__(UnifiedExecutionResult)

    def _get_agent_cli(self) -> Any:
        """Get the agent CLI instance from the audit module (where tests apply patches)."""
        # Access the get_agent_cli function that was imported in this module
        # The import at the top of the file: `from .cli.factory import get_agent_cli`
        # creates a reference that gets patched when the test patches "scripts.automation.audit.get_agent_cli"
        return get_agent_cli()

    def get_executor_name(self) -> str:
        """Get the name of this executor for logging purposes."""
        return "audit"

    def get_include_patterns(self) -> list[str]:
        """Get the file inclusion patterns for this executor."""
        result: list[str] = self.config.get("audit.scanning.include_patterns", ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx", "**/*.go", "**/*.rs"])
        return result

    def get_exclude_patterns(self) -> list[str]:
        """Get the file exclusion patterns for this executor."""
        result: list[str] = self.config.get(
            "audit.scanning.exclude_patterns",
            [
                "**/node_modules/**",
                "**/.git/**",
                "**/.venv/**",
                "**/venv/**",
                "**/__pycache__/**",
                "**/*.egg-info/**",
                "**/.cache/**",
                "**/.pytest_cache/**",
                "**/.mypy_cache/**",
                "**/dist/**",
                "**/build/**",
            ],
        )
        return result

    def _has_valid_extension(self, file_path: Path) -> bool:
        """Check if the file has a valid extension for this executor with special __init__.py handling.

        Args:
            file_path: Path to check

        Returns:
            True if file extension is valid
        """
        # First check if it matches include patterns
        has_valid_ext = any(file_path.match(pattern) for pattern in self.get_include_patterns())
        if not has_valid_ext:
            return False

        # Special handling for __init__.py files - skip empty ones
        if file_path.name == "__init__.py":
            try:
                content = file_path.read_text()
                # Skip empty __init__.py files (only whitespace/comments)
                stripped = content.strip()
                if not stripped or stripped in ["", '""""""', "''''''", "#", "# ", "# Copyright", "#!/usr/bin/env python"]:
                    # Check if it only contains comments and whitespace
                    lines = content.splitlines()
                    non_empty_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
                    if not non_empty_lines:
                        return False  # Skip empty __init__.py files
            except Exception as e:
                # If we can't read the file, don't skip it by default
                logger.warning(f"Could not read {file_path} for audit check: {e}")

        return True

    def execute_single_item(self, item_path: Path, _root_dir: Path | None = None, user_instruction: str | None = None) -> UnifiedExecutionResult:
        """Execute a single item with audit process.

        Args:
            item_path: Path to the item to audit
            _root_dir: Root directory for codebase inspection (not used in audit)
            user_instruction: Optional prepended instruction for the worker

        Returns:
            Audit result for the item
        """
        # Delegate to the original _audit_file with file_path
        # _root_dir is intentionally unused in audit process
        return self._audit_file(item_path, user_instruction)

    def audit_directory(
        self,
        directory: Path,
        parallel: bool = True,
        max_workers: int = 4,
        retry_errors: bool = False,
        user_instruction: str | None = None,
    ) -> list[UnifiedExecutionResult]:
        """Audit all files in directory.

        Args:
            directory: Root directory to audit
            parallel: Enable parallel processing
            max_workers: Max worker processes (default 4, max 8)
            retry_errors: If True, only audit files with ERROR status from previous run
            user_instruction: Optional prepended instruction for the audit workers

        Returns:
            List of file audit results
        """
        max_workers = min(max_workers, MAX_WORKERS)

        # If retry_errors mode, filter to only ERROR files
        if retry_errors:
            files = self._find_error_files(directory)
            if not files:
                self.logger.info("no_error_files_found", directory=str(directory))
                return []
        else:
            files = self._find_item_files(directory)

        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%d.%m.%Y")
        output_dir = directory / "docs" / "audit" / timestamp
        consolidated_file = output_dir / "CONSOLIDATED.md"

        self.logger.info(
            "audit_started",
            directory=str(directory),
            file_count=len(files),
            parallel=parallel,
            output_dir=str(output_dir),
        )

        # Progress tracking
        start_time = time.time()
        results = []

        if parallel:
            audit_func = partial(self._audit_file, user_instruction=user_instruction)
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                for i, result in enumerate(executor.map(audit_func, files), 1):
                    results.append(result)

                    # Print progress to stderr so it's visible in logs
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = (len(files) - i) * avg_time
                    self.logger.info(
                        "audit_progress",
                        current=i,
                        total=len(files),
                        percent=i * 100 // len(files),
                        elapsed_sec=round(elapsed, 1),
                        remaining_sec=round(remaining, 1),
                        current_file=str(result.item_path),
                        status=result.status,
                    )

                    # Save report (mirror directory structure) using imported utility
                    save_report(result, directory, output_dir)

                    # Consolidate patterns (only for failed statuses) using imported utility
                    if result.status in ("failed", "timeout"):
                        consolidate_patterns(result, directory, output_dir, consolidated_file)
        else:
            for i, file_path in enumerate(files, 1):
                result = self._audit_file(file_path, user_instruction=user_instruction)
                results.append(result)

                # Print progress to stderr so it's visible in logs
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (len(files) - i) * avg_time
                self.logger.info(
                    "audit_progress",
                    current=i,
                    total=len(files),
                    percent=i * 100 // len(files),
                    elapsed_sec=round(elapsed, 1),
                    remaining_sec=round(remaining, 1),
                    current_file=str(result.item_path),
                    status=result.status,
                )

                # Save report using imported utility
                save_report(result, directory, output_dir)

                # Consolidate patterns (only for failed statuses) using imported utility
                if result.status in ("failed", "timeout"):
                    consolidate_patterns(result, directory, output_dir, consolidated_file)

        self.logger.info(
            "audit_completed",
            total=len(results),
            passed=sum(1 for r in results if r.status == "completed"),
            failed=sum(1 for r in results if r.status == "failed"),
            errors=sum(1 for r in results if r.status == "timeout"),
        )

        return results

    def _find_error_files(self, directory: Path) -> list[Path]:
        """Find files with ERROR status from most recent audit.

        Args:
            directory: Root directory being audited

        Returns:
            List of file paths that had ERROR status in last audit
        """
        # Find most recent audit directory
        audit_base = directory / "docs" / "audit"
        if not audit_base.exists():
            self.logger.warning("no_previous_audit_found", directory=str(directory))
            return []

        # Get most recent audit directory (sorted by date DD.MM.YYYY)
        audit_dirs = sorted(
            [d for d in audit_base.iterdir() if d.is_dir()],
            key=lambda d: d.name,
            reverse=True,
        )

        if not audit_dirs:
            self.logger.warning("no_previous_audit_found", directory=str(directory))
            return []

        most_recent = audit_dirs[0]
        self.logger.info("scanning_previous_audit", audit_dir=str(most_recent))

        # Scan all .md reports for ERROR status
        error_files = []
        for report_path in most_recent.rglob("*.md"):
            if report_path.name == "CONSOLIDATED.md":
                continue

            # Read report and check for ERROR status
            content = report_path.read_text()
            if "**Status**: ERROR" in content:
                # Extract original file path from report
                # Report structure: directory/docs/audit/DD.MM.YYYY/relative/path/file.ext.md
                # Need to reconstruct: directory/relative/path/file.ext
                rel_path = report_path.relative_to(most_recent)
                # Remove .md extension
                original_path = directory / rel_path.with_suffix("")
                # Remove extra .md suffix if it was added to .py.md -> .py
                if original_path.suffix == ".md":
                    original_path = original_path.with_suffix("")

                if original_path.exists():
                    error_files.append(original_path)
                else:
                    self.logger.warning(
                        "error_file_not_found",
                        report=str(report_path),
                        expected_path=str(original_path),
                    )

        self.logger.info(
            "error_files_found",
            count=len(error_files),
            audit_dir=str(most_recent),
        )

        return error_files

    def _audit_file(self, file_path: Path, user_instruction: str | None = None) -> UnifiedExecutionResult:
        """Audit a single file using LLM-based analysis.

        Args:
            file_path: Path to file to audit
            user_instruction: Optional prepended instruction for the audit worker

        Returns:
            Audit result with status and violations
        """
        start = time.time()

        try:
            # Determine language
            language = detect_language(file_path)
            if not language:
                return UnifiedExecutionResult(
                    item_path=file_path,
                    status="completed",
                    violations=[],
                    audit_execution_time=time.time() - start,
                    total_duration=time.time() - start,
                )

            # SECURITY CRITICAL: Always perform real-time analysis for security audits
            # Caching has been completely removed to prevent security gaps
            # where newly introduced vulnerabilities are missed due to cached results

            # Read file content
            code = file_path.read_text()

            # Run LLM-based audit (matches current claude-audit.sh behavior)
            output, _ = self.cli.run_print(
                instruction_file=self.prompts_dir / self.config.get("prompts.audit"),
                stdin=f"{user_instruction + chr(10) if user_instruction else ''}## CODE TO ANALYZE\n\n```\n{code}\n```",
                agent_config=AgentConfigPresets.audit(self.session_id),
            )

            # Parse result using imported utility function
            parsed_status, violations = parse_audit_output(output, file_path)

            # Convert audit-specific status to UnifiedExecutionResult compatible status
            if parsed_status == "PASS":
                result_status: ExecutionStatus = "completed"
            elif parsed_status in ("FAIL", "ERROR"):
                result_status = "failed"
            else:
                # Default to 'failed' for any unexpected status values
                result_status = "failed"

            return UnifiedExecutionResult(
                item_path=file_path,
                status=result_status,
                violations=violations,
                audit_execution_time=time.time() - start,
                total_duration=time.time() - start,
            )

            # No caching - always perform fresh analysis for security

        except Exception as e:
            logger.error("audit_error", file=str(file_path), error=str(e))
            return UnifiedExecutionResult(
                item_path=file_path,
                status="failed",
                violations=[],
                audit_execution_time=time.time() - start,
                total_duration=time.time() - start,
                error=str(e),
            )
