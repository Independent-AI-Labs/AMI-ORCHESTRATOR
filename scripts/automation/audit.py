"""Audit orchestration engine.

Coordinates multi-file code audits using LLM-based analysis.
Supports parallel processing, caching, and pattern consolidation.
"""

import fnmatch
import hashlib
import json
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from base.backend.utils.uuid_utils import uuid7

from .agent_cli import AgentConfigPresets, get_agent_cli
from .config import get_config
from .logger import get_logger

# Resource limits
MAX_FILE_SIZE = 1024 * 1024  # 1MB
MAX_WORKERS = 8


class FileResult(BaseModel):
    """Audit result for a single file.

    Attributes:
        file_path: Path to audited file
        status: PASS, FAIL, or ERROR
        violations: List of violation dictionaries
        execution_time: Seconds taken to audit file
    """

    file_path: Path
    status: str  # PASS/FAIL/ERROR
    violations: list[dict[str, Any]]
    execution_time: float

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class AuditEngine:
    """Orchestrates multi-file code audits.

    Features:
    - Parallel processing with ProcessPoolExecutor
    - Result caching with TTL
    - Language detection
    - Include/exclude pattern scanning
    - Special __init__.py handling (skip empty files)
    - Progress tracking
    - Report generation with mirrored directory structure
    - Pattern consolidation for FAIL/ERROR files
    """

    def __init__(self) -> None:
        """Initialize audit engine."""
        self.config = get_config()
        self.session_id = uuid7()
        self.logger = get_logger("audit", session_id=self.session_id)

    def audit_directory(
        self,
        directory: Path,
        parallel: bool = True,
        max_workers: int = 4,
        retry_errors: bool = False,
        user_instruction: str | None = None,
    ) -> list[FileResult]:
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
            files = list(self._find_files(directory))

        # Create output directory with DD.MM.YYYY format
        date_str = datetime.now().strftime("%d.%m.%Y")
        output_dir = directory / "docs" / "audit" / date_str
        output_dir.mkdir(parents=True, exist_ok=True)

        # Consolidated report path
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
            from functools import partial

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
                        current_file=str(result.file_path),
                        status=result.status,
                    )

                    # Save report (mirror directory structure)
                    self._save_report(result, directory, output_dir)

                    # Consolidate patterns (only for FAIL/ERROR)
                    if result.status in ("FAIL", "ERROR"):
                        self._consolidate_patterns(result, directory, output_dir, consolidated_file)
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
                    current_file=str(result.file_path),
                    status=result.status,
                )

                # Save report
                self._save_report(result, directory, output_dir)

                # Consolidate patterns (only for FAIL/ERROR)
                if result.status in ("FAIL", "ERROR"):
                    self._consolidate_patterns(result, directory, output_dir, consolidated_file)

        self.logger.info(
            "audit_completed",
            total=len(results),
            passed=sum(1 for r in results if r.status == "PASS"),
            failed=sum(1 for r in results if r.status == "FAIL"),
            errors=sum(1 for r in results if r.status == "ERROR"),
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

    def _find_files(self, directory: Path) -> Iterator[Path]:
        """Find all auditable files.

        Args:
            directory: Root directory to scan

        Yields:
            File paths matching include patterns and not excluded
        """
        patterns = self.config.get("audit.scanning.include_patterns", [])

        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if not file_path.is_file():
                    continue

                # Check exclusions
                if self._should_exclude(file_path):
                    continue

                # Special handling for __init__.py
                if file_path.name == "__init__.py" and file_path.read_text().strip() == "":
                    continue  # Skip empty __init__.py

                # Check file size
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    self.logger.warning(
                        "file_too_large",
                        file=str(file_path),
                        size=file_path.stat().st_size,
                    )
                    continue

                yield file_path

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded.

        Args:
            file_path: File path to check

        Returns:
            True if file matches exclusion pattern
        """
        exclude_patterns = self.config.get("audit.scanning.exclude_patterns", [])
        path_str = str(file_path)

        return any(fnmatch.fnmatch(path_str, pattern) for pattern in exclude_patterns)

    def _parse_audit_output(
        self, output: str, file_path: Path
    ) -> tuple[str, list[dict[str, Any]]]:  # Any: violation dicts have mixed types (line: int, message: str, severity: str, pattern_id: str)
        """Parse audit output from LLM into status and violations.

        Args:
            output: Raw output from audit agent
            file_path: File path being audited (for logging)

        Returns:
            Tuple of (status, violations list)
        """
        output_stripped = output.strip()

        # Check for PASS (exact match)
        if output_stripped == "PASS":
            return "PASS", []

        # Check for FAIL anywhere in output (extract from LLM preamble if needed)
        if "FAIL:" in output_stripped:
            # Extract FAIL line (may be buried in preamble)
            fail_line = None
            for line in output_stripped.split("\n"):
                if line.startswith("FAIL:"):
                    fail_line = line
                    break

            if fail_line:
                violations = [{"line": 0, "pattern_id": "llm_audit", "severity": "CRITICAL", "message": fail_line}]
            else:
                # FAIL: found but not at line start, use full output
                violations = [{"line": 0, "pattern_id": "llm_audit", "severity": "CRITICAL", "message": output_stripped}]
            return "FAIL", violations

        # Check for ERROR
        if "ERROR:" in output_stripped:
            violations = [{"line": 0, "pattern_id": "audit_error", "severity": "ERROR", "message": output_stripped}]
            return "ERROR", violations

        # Non-compliant output format - treat as ERROR
        first_line = output_stripped.split("\n")[0] if output_stripped else ""
        violations = [
            {
                "line": 0,
                "pattern_id": "audit_format_violation",
                "severity": "ERROR",
                "message": f"Audit agent violated output format. Expected 'PASS' or 'FAIL: <reasons>', got: {first_line[:200]}",
            }
        ]
        self.logger.error("audit_output_format_violation", file=str(file_path), first_line=first_line[:100])
        return "ERROR", violations

    def _audit_file(self, file_path: Path, user_instruction: str | None = None) -> FileResult:
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
            language = self._detect_language(file_path)
            if not language:
                return FileResult(
                    file_path=file_path,
                    status="PASS",
                    violations=[],
                    execution_time=time.time() - start,
                )

            # Check cache
            cached_result = self._check_cache(file_path)
            if cached_result:
                return cached_result

            # Read file content
            code = file_path.read_text()

            # Run LLM-based audit (matches current claude-audit.sh behavior)
            cli = get_agent_cli()
            prompts_dir = self.config.root / self.config.get("prompts.dir")
            audit_instruction = prompts_dir / self.config.get("prompts.audit")

            # Build audit prompt
            audit_prompt = ""
            if user_instruction:
                audit_prompt = f"{user_instruction}\n\n"

            audit_prompt += f"""## CODE TO ANALYZE

```
{code}
```
"""

            audit_config = AgentConfigPresets.audit(self.session_id)
            audit_config.enable_streaming = True
            output, _ = cli.run_print(
                instruction_file=audit_instruction,
                stdin=audit_prompt,
                agent_config=audit_config,
            )

            # Parse result
            status, violations = self._parse_audit_output(output, file_path)

            result = FileResult(
                file_path=file_path,
                status=status,
                violations=violations,
                execution_time=time.time() - start,
            )

            # Cache result
            self._cache_result(file_path, result)

            return result

        except Exception as e:
            self.logger.error("audit_error", file=str(file_path), error=str(e))
            return FileResult(
                file_path=file_path,
                status="ERROR",
                violations=[],
                execution_time=time.time() - start,
            )

    def _detect_language(self, file_path: Path) -> str | None:
        """Detect language from file extension.

        Args:
            file_path: File path

        Returns:
            Language name or None if unknown
        """
        ext = file_path.suffix.lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
        }
        return mapping.get(ext)

    def _check_cache(self, file_path: Path) -> FileResult | None:
        """Check if file result is cached.

        Args:
            file_path: File path

        Returns:
            Cached result or None if not cached/stale
        """
        cache_enabled = self.config.get("audit.cache.enabled", False)
        if not cache_enabled:
            return None

        cache_file = self._get_cache_path(file_path)
        if not cache_file.exists():
            return None

        # Check if cache is stale
        ttl = self.config.get("audit.cache.ttl", 3600)
        if time.time() - cache_file.stat().st_mtime > ttl:
            return None

        # Load cached result
        try:
            data = json.loads(cache_file.read_text())
            # Reconstruct FileResult
            return FileResult(
                file_path=Path(data["file_path"]),
                status=data["status"],
                violations=data["violations"],
                execution_time=data["execution_time"],
            )
        except Exception:
            return None

    def _cache_result(self, file_path: Path, result: FileResult) -> None:
        """Cache audit result.

        Args:
            file_path: File path
            result: Audit result to cache
        """
        cache_enabled = self.config.get("audit.cache.enabled", False)
        if not cache_enabled:
            return

        cache_file = self._get_cache_path(file_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        cache_file.write_text(
            json.dumps(
                {
                    "file_path": str(result.file_path),
                    "status": result.status,
                    "violations": result.violations,
                    "execution_time": result.execution_time,
                }
            )
        )

    def _get_cache_path(self, file_path: Path) -> Path:
        """Get cache file path for given file.

        Args:
            file_path: File path

        Returns:
            Path to cache file
        """
        cache_dir = Path(self.config.get("audit.cache.storage"))
        file_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
        return cache_dir / f"{file_hash}.json"

    def _save_report(self, result: FileResult, root_dir: Path, output_dir: Path) -> None:
        """Save audit report with mirrored directory structure.

        Args:
            result: Audit result
            root_dir: Root directory being audited
            output_dir: Output directory (e.g., docs/audit/DD.MM.YYYY)

        Example:
            automation/config.py -> docs/audit/18.10.2025/automation/config.py.md
        """
        # Create relative path for mirrored structure
        try:
            rel_path = result.file_path.relative_to(root_dir)
        except ValueError:
            rel_path = Path(result.file_path.name)

        # Mirror directory structure
        report_path = output_dir / rel_path.with_suffix(rel_path.suffix + ".md")

        # Create parent directories
        report_path.parent.mkdir(parents=True, exist_ok=True)

        # Format violations
        violations_text = ""
        if result.violations:
            violations_text = "\n".join([f"- Line {v['line']}: {v['message']} (severity: {v['severity']})" for v in result.violations])

        # Write report
        with report_path.open("w") as f:
            f.write("# AUDIT REPORT\n\n")
            f.write(f"**File**: `{rel_path}`\n")
            f.write(f"**Status**: {result.status}\n")
            f.write(f"**Audit Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Execution Time**: {result.execution_time:.2f}s\n\n")
            f.write("---\n\n")

            if result.status == "PASS":
                f.write("✅ No violations detected.\n")
            else:
                f.write(f"## Violations ({len(result.violations)})\n\n")
                f.write(violations_text)
                f.write("\n")

    def _consolidate_patterns(
        self,
        result: FileResult,
        root_dir: Path,
        output_dir: Path,
        consolidated_file: Path,
    ) -> None:
        """Consolidate patterns from failed audit into CONSOLIDATED.md.

        Only called for FAIL/ERROR files to extract patterns.

        Args:
            result: Failed audit result
            root_dir: Root directory being audited
            output_dir: Output directory
            consolidated_file: Path to CONSOLIDATED.md
        """
        from .agent_cli import AgentConfigPresets, get_agent_cli

        # Get audit report path
        try:
            rel_path = result.file_path.relative_to(root_dir)
        except ValueError:
            rel_path = Path(result.file_path.name)

        report_path = output_dir / rel_path.with_suffix(rel_path.suffix + ".md")

        # Read audit report
        if not report_path.exists():
            return

        audit_content = report_path.read_text()

        # Read current consolidated (if exists)
        if consolidated_file.exists():
            consolidated_content = consolidated_file.read_text()
        else:
            consolidated_content = "# CONSOLIDATED AUDIT PATTERNS\n\nNo patterns consolidated yet.\n"

        # Run consolidation via agent CLI
        cli = get_agent_cli()
        prompts_dir = self.config.root / self.config.get("prompts.dir")
        consolidate_instruction = prompts_dir / self.config.get("prompts.consolidate")

        # Build context
        context = f"""
## CURRENT CONSOLIDATED REPORT

File path: `{consolidated_file}`

```markdown
{consolidated_content}
```

---

## NEW AUDIT REPORT

File path: `{report_path}`

```markdown
{audit_content}
```

---

**REMEMBER**: Use Read/Write/Edit tools to update `{consolidated_file}`. Output ONLY 'UPDATED' or 'NO_CHANGES' when done.
"""

        # run_print() raises AgentExecutionError on non-zero exit
        # If we reach this line, execution was successful
        consolidate_config = AgentConfigPresets.consolidate(session_id=self.session_id)
        consolidate_config.enable_streaming = True
        output, _ = cli.run_print(
            instruction_file=consolidate_instruction,
            stdin=context,
            agent_config=consolidate_config,
        )

        self.logger.info("consolidation_result", result=output.strip())
