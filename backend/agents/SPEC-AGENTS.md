# FULL AGENT FRAMEWORK MIGRATION SPECIFICATION

**Version**: 1.0
**Date**: 2025-11-07
**Status**: Planning - Awaiting Approval

---

## Overview

Migrate entire agent automation framework from `/scripts/automation` to `/backend/agents` with proper architecture, provider abstraction, and full Gemini CLI streaming support.

**Strategy**: Leave `/scripts` intact as backup, build new framework in `/backend/agents`, then update entry points.

---

## Directory Structure

```
backend/agents/
├── __init__.py                      # Public API exports
├── README.md                        # Framework documentation
│
├── core/                            # Core abstractions
│   ├── __init__.py
│   ├── exceptions.py                # All agent exceptions
│   ├── base.py                      # AgentCLI ABC
│   ├── config.py                    # AgentConfig dataclass
│   └── presets.py                   # AgentConfigPresets
│
├── providers/                       # CLI provider implementations
│   ├── __init__.py
│   ├── base.py                      # Provider ABC
│   ├── claude.py                    # ClaudeProvider (from ClaudeAgentCLI)
│   ├── gemini.py                    # GeminiProvider (NEW - full streaming)
│   ├── models.py                    # CLIProvider enum, model enums
│   └── tool_mapping.py              # Tool name translation
│
├── factory.py                       # get_agent_cli() factory
│
├── hooks/                           # Hook validation framework
│   ├── __init__.py
│   ├── base.py                      # HookValidator ABC, HookInput, HookResult
│   ├── validators.py                # All validator implementations
│   └── transcript.py                # Transcript parsing utilities
│
├── executors/                       # High-level executors
│   ├── __init__.py
│   ├── audit.py                     # AuditEngine
│   ├── tasks.py                     # TaskExecutor
│   ├── sync.py                      # SyncExecutor
│   └── docs.py                      # DocsExecutor
│
├── utils/                           # Shared utilities
│   ├── __init__.py
│   ├── config.py                    # Config loader (automation.yaml)
│   ├── logger.py                    # Structured logging
│   └── validators.py                # Shared validation (LLM-based, patterns)
│
└── cli/                             # CLI entry point
    ├── __init__.py
    └── main.py                      # ami-agent command router
```

---

## Phase 1: Core Abstractions

### 1.1 Core Exceptions (`core/exceptions.py`)

Extract from `scripts/automation/agent_cli.py:31-100`

```python
"""Agent execution exceptions."""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all agent execution errors."""


class AgentTimeoutError(AgentError):
    """Agent execution exceeded timeout."""

    def __init__(self, timeout: int, cmd: list[str], duration: float | None = None):
        self.timeout = timeout
        self.cmd = cmd
        self.duration = duration
        msg = f"Agent execution timeout after {timeout}s"
        if duration:
            msg += f" (actual: {duration:.1f}s)"
        super().__init__(msg)


class AgentCommandNotFoundError(AgentError):
    """Agent command not found in PATH."""

    def __init__(self, cmd: str):
        self.cmd = cmd
        super().__init__(f"Command not found: {cmd}")


class AgentExecutionError(AgentError):
    """Agent execution failed with non-zero exit code."""

    def __init__(self, exit_code: int, stdout: str, stderr: str, cmd: list[str]):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        super().__init__(f"Agent execution failed with exit code {exit_code}")


class AgentProcessKillError(AgentError):
    """Failed to kill hung agent process."""

    def __init__(self, pid: int, reason: str):
        self.pid = pid
        self.reason = reason
        super().__init__(f"Failed to kill hung process {pid}: {reason}")
```

### 1.2 Base CLI Interface (`core/base.py`)

Extract from `scripts/automation/agent_cli.py:274-320`

```python
"""Abstract base class for agent CLI implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TextIO


class AgentCLI(ABC):
    """Abstract interface for agent CLI operations."""

    @abstractmethod
    def run_print(
        self,
        instruction: str | None = None,
        instruction_file: Path | None = None,
        stdin: str | TextIO | None = None,
        agent_config: Any | None = None,
        cwd: Path | None = None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent in non-interactive (print) mode.

        Args:
            instruction: Instruction text
            instruction_file: Path to instruction file
            stdin: Input data
            agent_config: Agent configuration
            cwd: Working directory
            audit_log_path: Audit log path for streaming output

        Returns:
            Tuple of (agent output text, execution metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentCommandNotFoundError: CLI command not found
            AgentExecutionError: Non-zero exit code
            AgentProcessKillError: Failed to kill hung process
        """

    @abstractmethod
    def run_interactive(
        self,
        instruction: str,
        agent_config: Any,
    ) -> int:
        """Run agent in interactive mode.

        Args:
            instruction: Initial instruction/prompt
            agent_config: Agent configuration

        Returns:
            Exit code (0=success, non-zero=failure)
        """

    @abstractmethod
    def kill_current_process(self) -> bool:
        """Kill currently running subprocess if exists.

        Returns:
            True if process was killed, False otherwise
        """
```

### 1.3 Configuration (`core/config.py`)

Extract from `scripts/automation/agent_cli.py:103-120`

```python
"""Agent configuration dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CLIProvider(Enum):
    """CLI provider selection."""

    CLAUDE = "claude"
    GEMINI = "gemini"


@dataclass
class AgentConfig:
    """Configuration for an agent execution.

    Defines provider, model, tools, hooks, timeout, and session settings.
    """

    provider: CLIProvider
    model: str
    session_id: str
    allowed_tools: list[str] | None = None  # None = all tools allowed
    enable_hooks: bool = True
    enable_streaming: bool = False
    timeout: int | None = 180  # None = no timeout (interactive)
    mcp_servers: dict[str, Any] | None = None
```

### 1.4 Presets (`core/presets.py`)

Extract from `scripts/automation/agent_cli.py:122-271`

```python
"""Common agent configuration presets."""

from __future__ import annotations

from typing import Any

from .config import AgentConfig, CLIProvider


class AgentConfigPresets:
    """Common agent configuration presets."""

    @staticmethod
    def audit(session_id: str, provider: CLIProvider = CLIProvider.CLAUDE) -> AgentConfig:
        """Code audit agent: WebSearch/WebFetch only, hooks disabled."""
        return AgentConfig(
            provider=provider,
            model="claude-sonnet-4-5" if provider == CLIProvider.CLAUDE else "gemini-2.5-pro",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

    @staticmethod
    def audit_diff(session_id: str, provider: CLIProvider = CLIProvider.CLAUDE) -> AgentConfig:
        """Diff audit agent: For PreToolUse hooks checking code quality."""
        return AgentConfig(
            provider=provider,
            model="claude-sonnet-4-5" if provider == CLIProvider.CLAUDE else "gemini-2.5-flash",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=60,
        )

    @staticmethod
    def worker(session_id: str, provider: CLIProvider = CLIProvider.CLAUDE) -> AgentConfig:
        """General worker agent: All tools, hooks enabled."""
        return AgentConfig(
            provider=provider,
            model="claude-sonnet-4-5" if provider == CLIProvider.CLAUDE else "gemini-2.5-pro",
            session_id=session_id,
            allowed_tools=None,  # All tools
            enable_hooks=True,
            timeout=180,
        )

    @staticmethod
    def completion_moderator(session_id: str, provider: CLIProvider = CLIProvider.GEMINI) -> AgentConfig:
        """Completion validation moderator: No tools, analyzes conversation only.

        Defaults to Gemini Flash for speed (validation workload).
        Timeout: 100s to allow large context processing (up to 100K tokens).
        """
        return AgentConfig(
            provider=provider,
            model="gemini-2.5-flash" if provider == CLIProvider.GEMINI else "claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=[],
            enable_hooks=False,
            timeout=100,
        )

    # ... other presets (task_worker, task_moderator, sync_worker, etc.)
```

---

## Phase 2: Provider Abstraction

### 2.1 Provider Base (`providers/base.py`)

**NEW** - Abstract provider interface

```python
"""Abstract provider interface for CLI backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Provider(ABC):
    """Abstract provider for CLI backends."""

    @abstractmethod
    def build_command(
        self,
        instruction: str,
        config: Any,  # AgentConfig
        settings_file: Path | None,
    ) -> list[str]:
        """Build CLI command with all arguments.

        Args:
            instruction: Instruction for the agent
            config: Agent configuration
            settings_file: Optional settings file path (for hooks)

        Returns:
            Command list ready for subprocess execution
        """

    @abstractmethod
    def execute_streaming(
        self,
        cmd: list[str],
        stdin_data: str | None,
        config: Any,  # AgentConfig
        cwd: Path | None,
        audit_log_path: Path | None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute command with streaming output.

        Args:
            cmd: Command to execute
            stdin_data: Optional stdin input
            config: Agent configuration
            cwd: Working directory
            audit_log_path: Audit log path for first-output tracking

        Returns:
            Tuple of (accumulated output text, metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentExecutionError: Non-zero exit code
        """

    @abstractmethod
    def execute_blocking(
        self,
        cmd: list[str],
        stdin_data: str | None,
        config: Any,  # AgentConfig
        cwd: Path | None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute command with blocking (non-streaming) output.

        Args:
            cmd: Command to execute
            stdin_data: Optional stdin input
            config: Agent configuration
            cwd: Working directory

        Returns:
            Tuple of (output text, metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentExecutionError: Non-zero exit code
        """

    @abstractmethod
    def map_tool_name(self, canonical_name: str) -> str:
        """Map canonical tool name to provider-specific name.

        Args:
            canonical_name: Claude-style PascalCase tool name (e.g., "Read")

        Returns:
            Provider-specific tool name (e.g., "read_file" for Gemini)
        """

    @abstractmethod
    def kill_current_process(self) -> bool:
        """Kill currently running subprocess if exists.

        Returns:
            True if process was killed, False otherwise
        """
```

### 2.2 Claude Provider (`providers/claude.py`)

Extract from `scripts/automation/agent_cli.py:322-1208`

- All existing `ClaudeAgentCLI` implementation
- Streaming execution with first-output markers
- Hook file creation (`_create_full_hooks_file`, `_create_bash_only_hooks_file`)
- Tool restriction via complement computation
- Privilege dropping for sudo execution

### 2.3 Gemini Provider (`providers/gemini.py`) - **NEW IMPLEMENTATION**

**CRITICAL**: This is the 300+ lines of LOST CODE that needs full rewrite

```python
"""Gemini CLI provider with full streaming support."""

from __future__ import annotations

import json
import os
import pwd
import select
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from backend.agents.core.exceptions import (
    AgentCommandNotFoundError,
    AgentExecutionError,
    AgentTimeoutError,
)
from backend.agents.providers.base import Provider
from backend.agents.utils.config import get_config
from backend.agents.utils.logger import get_logger


class GeminiProvider(Provider):
    """Gemini CLI provider with full streaming support.

    Implements complete streaming execution with:
    - Gemini JSON format parsing ({"type":"message","role":"assistant",...})
    - First-output timing markers for hang detection
    - Tool restrictions via --allowed-tools
    - Process cleanup for retry mechanism
    """

    # Canonical list of ALL Gemini CLI tools
    ALL_TOOLS = [
        "read_file",
        "write_file",
        "edit",
        "run_shell_command",
        "search_file_content",
        "glob",
        "google_web_search",
        "web_fetch",
        "write_todos",
    ]

    def __init__(self) -> None:
        """Initialize Gemini provider."""
        self.config = get_config()
        self.logger = get_logger("gemini-provider")
        self._current_process: subprocess.Popen[str] | None = None

    def build_command(
        self,
        instruction: str,
        config: Any,
        settings_file: Path | None,
    ) -> list[str]:
        """Build Gemini CLI command.

        Gemini format: gemini "prompt text" --model gemini-2.5-pro --output-format stream-json

        Args:
            instruction: Instruction text (passed as positional argument)
            config: Agent configuration
            settings_file: Ignored (Gemini has no hooks support)

        Returns:
            Command list for Gemini CLI
        """
        gemini_cmd = self.config.get("gemini_cli.command", "gemini")
        cmd = [gemini_cmd]

        # Positional prompt argument (Gemini appends to stdin automatically)
        cmd.append(instruction)

        # Model
        cmd.extend(["--model", config.model])

        # Streaming JSON output
        cmd.extend(["--output-format", "stream-json"])

        # Tool restrictions
        if config.allowed_tools is not None:
            gemini_tools = [self.map_tool_name(t) for t in config.allowed_tools]
            if gemini_tools:
                cmd.extend(["--allowed-tools", ",".join(gemini_tools)])
            else:
                # Empty tools list = no tools allowed
                cmd.extend(["--allowed-tools", ""])

        return cmd

    def execute_streaming(
        self,
        cmd: list[str],
        stdin_data: str | None,
        config: Any,
        cwd: Path | None,
        audit_log_path: Path | None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute Gemini with streaming JSON parsing.

        Gemini streaming format:
        {"type":"init","timestamp":"...","session_id":"...","model":"..."}
        {"type":"message","role":"user","content":"..."}
        {"type":"message","role":"assistant","content":"ALLOW","delta":true}
        {"type":"result","status":"success","stats":{...}}

        Args:
            cmd: Gemini command
            stdin_data: Input data (appended to prompt automatically by Gemini)
            config: Agent configuration
            cwd: Working directory
            audit_log_path: Audit log for first-output markers

        Returns:
            Tuple of (accumulated assistant text, metadata dict)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentExecutionError: Non-zero exit code
        """
        start_time = time.time()
        process = None
        assistant_text: list[str] = []
        metadata: dict[str, Any] | None = None
        first_output_received = False

        try:
            # Start streaming process
            process = self._start_streaming_process(cmd, stdin_data, cwd)

            # Write process start marker
            if audit_log_path:
                try:
                    with audit_log_path.open("a") as f:
                        f.write(f"\n=== PROCESS STARTED (PID: {process.pid}) ===\n")
                except OSError as e:
                    self.logger.warning("audit_log_write_failed", error=str(e))

            # Read loop
            line_count = 0
            while True:
                elapsed = time.time() - start_time

                # Check timeout
                if config.timeout and elapsed > config.timeout:
                    self.logger.error("gemini_streaming_timeout", elapsed=elapsed, timeout=config.timeout)
                    raise subprocess.TimeoutExpired(cmd, config.timeout)

                # Read line with timeout
                line, process_exited = self._read_streaming_line(process, 1.0, cmd)

                if process_exited:
                    self.logger.info("gemini_streaming_process_exited", line_count=line_count)
                    break

                if line:
                    line_count += 1

                    # Write first-output marker (CRITICAL for hang detection)
                    if not first_output_received:
                        first_output_received = True
                        first_output_time = time.time() - start_time
                        self.logger.info("gemini_streaming_first_output", elapsed=first_output_time)

                        if audit_log_path:
                            try:
                                with audit_log_path.open("a") as f:
                                    f.write(f"\n=== FIRST OUTPUT: {first_output_time:.4f}s ===\n\n")
                            except OSError:
                                pass

                    # Write raw JSON to audit log
                    if audit_log_path:
                        try:
                            with audit_log_path.open("a") as f:
                                f.write(line)
                        except OSError:
                            pass

                    # Parse Gemini JSON
                    text, msg_metadata = self._parse_gemini_message(line, cmd)
                    if text:
                        assistant_text.append(text)
                    if msg_metadata:
                        metadata = msg_metadata

            # Wait for process completion
            process.wait(timeout=10)
            duration = time.time() - start_time

            # Check exit code
            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else ""
                self.logger.error("gemini_execution_failed", exit_code=process.returncode, stderr=stderr[:1000])
                raise AgentExecutionError(
                    exit_code=process.returncode,
                    stdout="".join(assistant_text),
                    stderr=stderr,
                    cmd=cmd,
                )

            if audit_log_path:
                try:
                    with audit_log_path.open("a") as f:
                        f.write(f"\n=== PROCESS COMPLETED (exit code: 0, duration: {duration:.1f}s) ===\n")
                except OSError:
                    pass

            self.logger.info("gemini_execution_complete", duration=round(duration, 1))
            return "".join(assistant_text), metadata

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            self.logger.error("gemini_timeout", timeout=config.timeout, duration=duration)

            if audit_log_path:
                try:
                    with audit_log_path.open("a") as f:
                        f.write(f"\n=== TIMEOUT EXCEEDED ({config.timeout}s, actual: {duration:.1f}s) ===\n")
                except OSError:
                    pass

            # Kill process
            if process and process.pid:
                import contextlib

                with contextlib.suppress(ProcessLookupError):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)

            raise AgentTimeoutError(timeout=config.timeout or 0, duration=duration, cmd=cmd) from e

        except FileNotFoundError as e:
            raise AgentCommandNotFoundError(cmd=cmd[0]) from e

    def execute_blocking(
        self,
        cmd: list[str],
        stdin_data: str | None,
        config: Any,
        cwd: Path | None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute Gemini with blocking (non-streaming) output.

        Gemini always returns JSON, so we parse the final response.

        Args:
            cmd: Gemini command
            stdin_data: Input data
            config: Agent configuration
            cwd: Working directory

        Returns:
            Tuple of (output text, metadata dict)
        """
        # Gemini CLI doesn't have a non-streaming mode - use streaming internally
        # but remove --output-format stream-json flag
        cmd_blocking = [arg for arg in cmd if arg not in ("--output-format", "stream-json")]

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd_blocking,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=config.timeout,
                cwd=cwd,
            )

            duration = time.time() - start_time

            if result.returncode != 0:
                raise AgentExecutionError(
                    exit_code=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    cmd=cmd_blocking,
                )

            # Parse JSON response
            response = json.loads(result.stdout)
            content = response.get("response", "")
            stats = response.get("stats", {})

            metadata = {"stats": stats, "duration": duration}

            return content, metadata

        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            raise AgentTimeoutError(timeout=config.timeout or 0, duration=duration, cmd=cmd_blocking) from e

        except FileNotFoundError as e:
            raise AgentCommandNotFoundError(cmd=cmd_blocking[0]) from e

    def map_tool_name(self, canonical_name: str) -> str:
        """Map Claude canonical names to Gemini snake_case.

        Args:
            canonical_name: Claude-style PascalCase (e.g., "Read", "Bash")

        Returns:
            Gemini snake_case (e.g., "read_file", "run_shell_command")
        """
        mapping = {
            "Read": "read_file",
            "Write": "write_file",
            "Edit": "edit",
            "Bash": "run_shell_command",
            "Grep": "search_file_content",
            "Glob": "glob",
            "WebSearch": "google_web_search",
            "WebFetch": "web_fetch",
            "TodoWrite": "write_todos",
        }
        return mapping.get(canonical_name, canonical_name.lower())

    def kill_current_process(self) -> bool:
        """Kill currently running Gemini subprocess.

        Returns:
            True if process killed, False otherwise
        """
        if not self._current_process or not self._current_process.pid:
            return False

        pid = self._current_process.pid
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
            self.logger.info("killed_hung_process", pid=pid)
            self._current_process = None
            return True
        except ProcessLookupError:
            self.logger.info("process_already_dead", pid=pid)
            self._current_process = None
            return False
        except (PermissionError, OSError) as e:
            self.logger.error("failed_to_kill_process", pid=pid, error=str(e))
            return False

    def _start_streaming_process(
        self,
        cmd: list[str],
        stdin_data: str | None,
        cwd: Path | None,
    ) -> subprocess.Popen[str]:
        """Start Gemini streaming process.

        Args:
            cmd: Gemini command
            stdin_data: Optional stdin
            cwd: Working directory

        Returns:
            Started process

        Raises:
            AgentExecutionError: If process fails immediately
        """
        self.logger.info("gemini_streaming_subprocess_starting")

        # Drop privileges if running as root via sudo
        preexec_fn = self._drop_privileges if os.environ.get("SUDO_USER") and os.geteuid() == 0 else None
        env = self._get_unprivileged_env()

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            start_new_session=True,
            preexec_fn=preexec_fn,
            env=env,
        )

        self.logger.info("gemini_streaming_subprocess_started", pid=process.pid)

        # Store process for cleanup
        self._current_process = process

        # Write stdin
        if process.stdin:
            if stdin_data:
                process.stdin.write(stdin_data)
            process.stdin.close()

        # Check for immediate exit
        time.sleep(0.1)
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            self.logger.error("gemini_immediate_exit", exit_code=process.returncode, stderr=stderr[:1000])
            raise AgentExecutionError(
                exit_code=process.returncode,
                stdout="",
                stderr=stderr,
                cmd=cmd,
            )

        return process

    def _read_streaming_line(
        self,
        process: subprocess.Popen[str],
        timeout_val: float,
        cmd: list[str],
    ) -> tuple[str | None, bool]:
        """Read single line from streaming Gemini process.

        Args:
            process: Running process
            timeout_val: Timeout for select
            cmd: Command being executed

        Returns:
            Tuple of (line, process_exited)
        """
        if not process.stdout:
            return None, True

        try:
            ready, _, _ = select.select([process.stdout.fileno()], [], [], timeout_val)
        except (OSError, ValueError) as e:
            self.logger.error("gemini_select_error", error=str(e))
            raise AgentExecutionError(exit_code=-1, stdout="", stderr=f"select() failed: {e}", cmd=cmd) from e

        if not ready:
            if process.poll() is not None:
                return None, True
            return None, False

        try:
            line = process.stdout.readline()
        except OSError as e:
            self.logger.error("gemini_readline_error", error=str(e))
            raise AgentExecutionError(exit_code=-1, stdout="", stderr=f"readline() failed: {e}", cmd=cmd) from e

        if not line:
            return None, True

        return line, False

    def _parse_gemini_message(
        self,
        line: str,
        cmd: list[str],
    ) -> tuple[str, dict[str, Any] | None]:
        """Parse Gemini streaming JSON message.

        Gemini format:
        {"type":"message","role":"assistant","content":"text","delta":true}
        {"type":"result","status":"success","stats":{...}}

        Args:
            line: JSON line
            cmd: Command (for error reporting)

        Returns:
            Tuple of (assistant text, metadata dict or None)

        Raises:
            AgentExecutionError: If JSON parsing fails
        """
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            self.logger.error("gemini_invalid_json", line=line[:200], error=str(e))
            raise AgentExecutionError(
                exit_code=-1,
                stdout="",
                stderr=f"Invalid JSON in Gemini output: {line[:200]}",
                cmd=cmd,
            ) from e

        # Extract assistant text
        if msg.get("type") == "message" and msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content:
                return content, None

        # Extract metadata from result
        if msg.get("type") == "result":
            metadata = {
                "status": msg.get("status"),
                "stats": msg.get("stats"),
            }
            return "", metadata

        return "", None

    def _drop_privileges(self) -> None:
        """Drop root privileges to original sudo user."""
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and os.geteuid() == 0:
            try:
                pw_record = pwd.getpwnam(sudo_user)
                os.setgid(pw_record.pw_gid)
                os.setuid(pw_record.pw_uid)
                self.logger.info("privileges_dropped", to_user=sudo_user)
            except (KeyError, OSError) as e:
                self.logger.warning("privilege_drop_failed", error=str(e))

    def _get_unprivileged_env(self) -> dict[str, str] | None:
        """Get environment for unprivileged user."""
        sudo_user = os.environ.get("SUDO_USER")
        if not sudo_user or os.geteuid() != 0:
            return None

        try:
            pw_record = pwd.getpwnam(sudo_user)
            env = os.environ.copy()
            env["HOME"] = pw_record.pw_dir
            env["USER"] = sudo_user
            env["LOGNAME"] = sudo_user
            return env
        except (KeyError, OSError):
            return None
```

### 2.4 Models (`providers/models.py`)

**NEW** - Model enums and validation

```python
"""CLI provider and model enums."""

from __future__ import annotations

from enum import Enum


class CLIProvider(Enum):
    """CLI provider selection."""

    CLAUDE = "claude"
    GEMINI = "gemini"


class ClaudeModels(Enum):
    """Claude model identifiers."""

    SONNET_4_5 = "claude-sonnet-4-5"
    SONNET_3_5 = "claude-sonnet-3-5"
    OPUS_4 = "claude-opus-4"
    HAIKU_3_5 = "claude-haiku-3-5"

    @classmethod
    def is_valid(cls, model: str) -> bool:
        """Check if model is valid Claude model."""
        return model in {m.value for m in cls}

    @classmethod
    def get_default(cls) -> str:
        """Get default Claude model."""
        return cls.SONNET_4_5.value


class GeminiModels(Enum):
    """Gemini model identifiers."""

    PRO_2_5 = "gemini-2.5-pro"
    FLASH_2_5 = "gemini-2.5-flash"
    PRO_2_0 = "gemini-2.0-pro"
    FLASH_2_0 = "gemini-2.0-flash"

    @classmethod
    def is_valid(cls, model: str) -> bool:
        """Check if model is valid Gemini model."""
        return model in {m.value for m in cls}

    @classmethod
    def get_default(cls) -> str:
        """Get default Gemini model."""
        return cls.PRO_2_5.value
```

### 2.5 Tool Mapping (`providers/tool_mapping.py`)

**NEW** - Centralized tool name mapping

```python
"""Tool name mapping between providers."""

from __future__ import annotations

# Canonical tool names (Claude PascalCase) -> Gemini snake_case
CLAUDE_TO_GEMINI = {
    "Read": "read_file",
    "Write": "write_file",
    "Edit": "edit",
    "Bash": "run_shell_command",
    "Grep": "search_file_content",
    "Glob": "glob",
    "WebSearch": "google_web_search",
    "WebFetch": "web_fetch",
    "TodoWrite": "write_todos",
    "BashOutput": "bash_output",
    "KillShell": "kill_shell",
    "NotebookEdit": "notebook_edit",
    "SlashCommand": "slash_command",
    "Task": "task",
    "ExitPlanMode": "exit_plan_mode",
}

# Reverse mapping
GEMINI_TO_CLAUDE = {v: k for k, v in CLAUDE_TO_GEMINI.items()}


def map_tool_claude_to_gemini(canonical_name: str) -> str:
    """Map Claude canonical name to Gemini snake_case.

    Args:
        canonical_name: Claude PascalCase tool name

    Returns:
        Gemini snake_case tool name
    """
    return CLAUDE_TO_GEMINI.get(canonical_name, canonical_name.lower())


def map_tool_gemini_to_claude(gemini_name: str) -> str:
    """Map Gemini snake_case to Claude canonical name.

    Args:
        gemini_name: Gemini snake_case tool name

    Returns:
        Claude PascalCase tool name
    """
    return GEMINI_TO_CLAUDE.get(gemini_name, gemini_name.title().replace("_", ""))
```

---

## Phase 3: Factory Pattern

### 3.1 Factory (`factory.py`)

```python
"""Factory for creating agent CLI instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.agents.core.base import AgentCLI
    from backend.agents.core.config import AgentConfig

from backend.agents.core.config import CLIProvider
from backend.agents.providers.claude import ClaudeAgentCLI
from backend.agents.providers.gemini import GeminiAgentCLI
from backend.agents.utils.config import get_config


def get_agent_cli(config: AgentConfig | None = None) -> AgentCLI:
    """Get agent CLI instance based on provider.

    Selection priority:
    1. config.provider (if config provided)
    2. Global config default (automation.yaml)
    3. Claude (fallback)

    Args:
        config: Optional agent configuration

    Returns:
        Agent CLI instance (ClaudeAgentCLI or GeminiAgentCLI)
    """
    # Determine provider
    if config:
        provider = config.provider
    else:
        # Load from global config
        global_config = get_config()
        provider_str = global_config.get("agent.provider", "claude")
        provider = CLIProvider.GEMINI if provider_str == "gemini" else CLIProvider.CLAUDE

    # Return appropriate implementation
    if provider == CLIProvider.GEMINI:
        return GeminiAgentCLI()
    return ClaudeAgentCLI()
```

---

## Phase 4: Hooks Framework Migration

### 4.1 Hook Base (`hooks/base.py`)

Extract from `scripts/automation/hooks.py:188-316`

- `HookInput` dataclass
- `HookResult` dataclass
- `HookValidator` ABC
- `prepare_moderator_context()` function
- `load_session_todos()` function

### 4.2 Validators (`hooks/validators.py`)

Extract from `scripts/automation/hooks.py:416-1558`

All validator classes:
- `MaliciousBehaviorValidator`
- `CommandValidator`
- `CoreQualityValidator`
- `PythonQualityValidator`
- `ShebangValidator`
- `ResponseScanner`
- `TodoValidatorHook`

### 4.3 Transcript Utils (`hooks/transcript.py`)

Extract from `scripts/automation/transcript.py`

- `format_messages_for_prompt()`
- `get_last_n_messages()`
- `is_actual_user_message()`

---

## Phase 5: Executors Migration

### 5.1 Audit Executor (`executors/audit.py`)

Extract from `scripts/automation/audit.py`

- `AuditEngine` class
- `AuditResult` dataclass
- Parallel audit execution
- Consolidated report generation

### 5.2 Task Executor (`executors/tasks.py`)

Extract from `scripts/automation/tasks.py`

- `TaskExecutor` class
- `TaskResult` dataclass
- Task file parsing
- Worker + moderator pattern

### 5.3 Sync Executor (`executors/sync.py`)

Extract from `scripts/automation/sync.py`

- `SyncExecutor` class
- `SyncResult` dataclass
- Git status checking
- Commit/push automation

### 5.4 Docs Executor (`executors/docs.py`)

Extract from `scripts/automation/docs.py`

- `DocsExecutor` class
- `DocsResult` dataclass
- Documentation maintenance
- Archive/update/delete logic

---

## Phase 6: Utilities

### 6.1 Config (`utils/config.py`)

Extract from `scripts/automation/config.py`

- `get_config()` function
- YAML loading
- Template substitution

### 6.2 Logger (`utils/logger.py`)

Extract from `scripts/automation/logger.py`

- `get_logger()` function
- Structured logging
- Session-based log files

### 6.3 Validators (`utils/validators.py`)

Extract from `scripts/automation/validators.py`

- `validate_diff_llm()` - LLM-based diff validation
- `run_moderator_with_retry()` - Hang detection + retry
- `parse_code_fence_output()` - Output parsing
- Pattern loading functions

---

## Phase 7: CLI Entry Point

### 7.1 Main Router (`cli/main.py`)

Extract from `scripts/automation/agent_main.py`

```python
"""AMI Agent CLI router."""

import argparse
import sys
from pathlib import Path

from backend.agents.executors.audit import AuditEngine
from backend.agents.executors.docs import DocsExecutor
from backend.agents.executors.sync import SyncExecutor
from backend.agents.executors.tasks import TaskExecutor
from backend.agents.hooks.validators import (
    CommandValidator,
    CoreQualityValidator,
    MaliciousBehaviorValidator,
    PythonQualityValidator,
    ResponseScanner,
    ShebangValidator,
    TodoValidatorHook,
)


def mode_interactive(continue_session: bool = False, resume: str | bool | None = None, fork_session: bool = False) -> int:
    """Interactive mode - Launch Claude Code with hooks."""
    # Implementation from agent_main.py:166-248


def mode_print(instruction_path: str) -> int:
    """Non-interactive mode - Run agent with --print."""
    # Implementation from agent_main.py:251-286


def mode_hook(validator_name: str) -> int:
    """Hook validator mode - Validate hook input from stdin."""
    validators = {
        "malicious-behavior": MaliciousBehaviorValidator,
        "command-guard": CommandValidator,
        "code-quality-core": CoreQualityValidator,
        "code-quality-python": PythonQualityValidator,
        "response-scanner": ResponseScanner,
        "shebang-check": ShebangValidator,
        "todo-validator": TodoValidatorHook,
    }
    # Implementation from agent_main.py:289-315


def mode_audit(directory_path: str, retry_errors: bool = False, user_instruction: str | None = None) -> int:
    """Batch audit mode."""
    # Implementation from agent_main.py:318-351


def mode_tasks(path: str, root_dir: str | None = None, parallel: bool = False, user_instruction: str | None = None) -> int:
    """Task execution mode."""
    # Implementation from agent_main.py:354-400


def mode_sync(module_path: str, user_instruction: str | None = None) -> int:
    """Git sync mode."""
    # Implementation from agent_main.py:403-434


def mode_docs(directory_path: str, root_dir: str | None = None, parallel: bool = False, user_instruction: str | None = None) -> int:
    """Documentation maintenance mode."""
    # Implementation from agent_main.py:437-489


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AMI Agent - Unified automation entry point")
    # Full argument parser from agent_main.py:492-612
    # Route to mode handlers


if __name__ == "__main__":
    sys.exit(main())
```

### 7.2 Wrapper Script (`scripts/ami-agent`)

Update wrapper to call new location:

```bash
#!/usr/bin/env bash
exec "$(dirname "$0")/ami-run.sh" "$(dirname "$0")/../backend/agents/cli/main.py" "$@"
```

---

## Phase 8: Testing Infrastructure

### 8.1 Unit Tests

```
tests/unit/backend/agents/
├── core/
│   ├── test_config.py              # AgentConfig tests
│   ├── test_presets.py             # Preset tests
│   └── test_exceptions.py          # Exception tests
├── providers/
│   ├── test_base.py                # Provider ABC tests
│   ├── test_claude.py              # Claude provider tests
│   ├── test_gemini.py              # Gemini provider tests (NEW)
│   ├── test_models.py              # Model enum tests
│   └── test_tool_mapping.py        # Tool name mapping tests
├── hooks/
│   ├── test_base.py                # Hook base classes
│   └── test_validators.py          # All validator tests
├── executors/
│   ├── test_audit.py
│   ├── test_tasks.py
│   ├── test_sync.py
│   └── test_docs.py
├── utils/
│   ├── test_config.py
│   ├── test_logger.py
│   └── test_validators.py
└── test_factory.py                 # Factory tests
```

### 8.2 Integration Tests

```
tests/integration/backend/agents/
├── test_claude_e2e.py              # Claude end-to-end
├── test_gemini_e2e.py              # Gemini end-to-end (NEW)
├── test_multi_provider.py          # Mixed provider workflows
├── test_hooks_e2e.py               # Hook validation end-to-end
└── test_streaming_hang_detection.py # Hang detection + retry (NEW)
```

### 8.3 Critical Test Cases for Gemini

**test_gemini_streaming.py**:
```python
def test_gemini_streaming_first_output_marker():
    """Verify Gemini streaming writes === FIRST OUTPUT: marker."""
    # Critical for hang detection in run_moderator_with_retry()

def test_gemini_streaming_parse_json():
    """Verify Gemini JSON format parsing."""
    # {"type":"message","role":"assistant","content":"..."}

def test_gemini_tool_restrictions():
    """Verify --allowed-tools format."""
    # Empty list: --allowed-tools ""
    # Some tools: --allowed-tools "read_file,write_file"

def test_gemini_kill_current_process():
    """Verify process cleanup for retry mechanism."""

def test_gemini_hang_detection():
    """Verify hang detection triggers on startup hang (no first output)."""

def test_gemini_analysis_hang_detection():
    """Verify hang detection on analysis hang (first output but no decision)."""
```

---

## Migration Execution Plan

### Step-by-Step Migration

1. **Create directory structure** (`backend/agents/` with all subdirectories)
2. **Phase 1: Core** (exceptions, base, config, presets)
3. **Phase 2: Providers** (base, Claude extract, **Gemini NEW**, models, tool_mapping)
4. **Phase 3: Factory** (get_agent_cli)
5. **Phase 4: Hooks** (base, validators, transcript)
6. **Phase 5: Executors** (audit, tasks, sync, docs)
7. **Phase 6: Utils** (config, logger, validators)
8. **Phase 7: CLI** (main router, wrapper update)
9. **Phase 8: Tests** (unit + integration)
10. **Validation** (run full test suite)
11. **Update imports** (11 call sites across codebase)
12. **End-to-end validation** (run actual workloads)
13. **Archive** (`/scripts/automation` → `/scripts/automation.archived`)

---

## Import Update Sites (11 locations)

From `scripts/automation/`:
1. `validators.py` - `get_agent_cli()`
2. `hooks.py` (3 locations) - `get_agent_cli()`
3. `docs.py` - `get_agent_cli()`
4. `sync.py` - `get_agent_cli()`
5. `agent_main.py` (2 locations) - `get_agent_cli()`
6. `tasks.py` - `get_agent_cli()`
7. `audit.py` (2 locations) - `get_agent_cli()`

Update all to:
```python
from backend.agents.factory import get_agent_cli
from backend.agents.core.config import AgentConfig, AgentConfigPresets
from backend.agents.core.exceptions import (
    AgentError,
    AgentTimeoutError,
    AgentExecutionError,
    AgentCommandNotFoundError,
)
```

---

## Rollback Strategy

If migration fails:
1. **`/scripts/automation` is untouched** - original code preserved
2. **Simply revert wrapper script** - `scripts/ami-agent` points back to old location
3. **Remove `/backend/agents`** - clean up new code
4. **No data loss** - all uncommitted work already lost (lesson learned)

---

## Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Gemini streaming executes with first-output markers
- [ ] Hang detection works for both Claude and Gemini
- [ ] Tool restrictions work for both providers
- [ ] Mixed provider workflows function correctly
- [ ] All 11 import sites updated and verified
- [ ] End-to-end audit/tasks/sync/docs workflows pass
- [ ] Hooks framework fully functional with new structure
- [ ] No regressions in existing Claude functionality

---

## Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import circular dependencies | High | Careful module structure, TYPE_CHECKING guards |
| Hook framework breaks during migration | High | Keep `/scripts` working, test incrementally |
| Gemini streaming implementation bugs | Medium | Comprehensive unit tests, real workload validation |
| Performance regressions | Low | Benchmark before/after, same execution paths |
| Missing edge cases in Gemini provider | Medium | Port all Claude logic, add Gemini-specific tests |

---

## Timeline Estimate

- **Phase 1-3** (Core + Providers): 4-6 hours
- **Phase 4-5** (Hooks + Executors): 3-4 hours
- **Phase 6-7** (Utils + CLI): 2-3 hours
- **Phase 8** (Tests): 4-5 hours
- **Validation + Import Updates**: 2-3 hours
- **Total**: ~15-20 hours of focused work

---

## Notes

- **CRITICAL**: GeminiProvider is 100% new code (~500 lines) - requires full implementation from scratch
- **Keep `/scripts/automation` intact** - this is your backup and reference
- **Test incrementally** - don't migrate everything at once
- **Gemini streaming format is different** - requires careful JSON parsing
- **First-output markers are CRITICAL** - hang detection depends on them
- **Tool restrictions format differs** - Claude uses space-separated, Gemini uses comma-separated
- **No hooks support in Gemini** - settings_file parameter ignored

---

**END OF SPECIFICATION**
