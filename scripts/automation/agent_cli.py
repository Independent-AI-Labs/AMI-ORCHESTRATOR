"""Agent CLI abstraction for interactive and non-interactive operations.

AgentCLI defines the interface for agent interactions.
ClaudeAgentCLI implements this interface using the Claude Code CLI.
AgentConfig provides type-safe configuration.
"""

import json
import os
import pwd
import select
import signal
import subprocess
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

import yaml

from base.backend.workers.file_subprocess import FileSubprocessSync

from .config import get_config
from .logger import get_logger


# Custom exceptions for agent execution failures
class AgentError(Exception):
    """Base exception for all agent execution errors."""


class AgentTimeoutError(AgentError):
    """Agent execution exceeded timeout."""

    def __init__(self, timeout: int, cmd: list[str], duration: float | None = None):
        """Initialize timeout error.

        Args:
            timeout: Configured timeout in seconds
            cmd: Command that timed out
            duration: Actual duration before timeout (if known)
        """
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
        """Initialize command not found error.

        Args:
            cmd: Command that was not found
        """
        self.cmd = cmd
        super().__init__(f"Command not found: {cmd}")


class AgentExecutionError(AgentError):
    """Agent execution failed with non-zero exit code."""

    def __init__(self, exit_code: int, stdout: str, stderr: str, cmd: list[str]):
        """Initialize execution error.

        Args:
            exit_code: Process exit code
            stdout: Standard output
            stderr: Standard error
            cmd: Command that failed
        """
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        super().__init__(f"Agent execution failed with exit code {exit_code}")


class AgentProcessKillError(AgentError):
    """Failed to kill hung agent process."""

    def __init__(self, pid: int, reason: str):
        """Initialize process kill error.

        Args:
            pid: Process ID that couldn't be killed
            reason: Why the kill failed
        """
        self.pid = pid
        self.reason = reason
        super().__init__(f"Failed to kill hung process {pid}: {reason}")


@dataclass
class AgentConfig:
    """Configuration for an agent execution.

    Defines tools, model, hooks, timeout, and session settings for an agent.

    NOTE: disallowed_tools is NOT stored here - it's computed automatically
    by ClaudeAgentCLI.compute_disallowed_tools() as the complement of allowed_tools.
    """

    model: str
    session_id: str  # Claude Code session ID for execution tracking
    allowed_tools: list[str] | None = None  # None = all tools allowed
    enable_hooks: bool = True
    enable_streaming: bool = False  # Enable --resume and --output-format stream-json
    timeout: int | None = 180  # None = no timeout (interactive)
    mcp_servers: dict[str, Any] | None = None


class AgentConfigPresets:
    """Common agent configuration presets.

    Identifies patterns behind audit agents, code quality agents, worker agents, etc.
    """

    @staticmethod
    def audit(session_id: str) -> AgentConfig:
        """Code audit agent: WebSearch/WebFetch only, hooks disabled, high-quality model.

        Used for: Full file code audits, security analysis
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

    @staticmethod
    def audit_diff(session_id: str) -> AgentConfig:
        """Diff audit agent: For PreToolUse hooks checking code quality.

        Used for: Edit/Write validation, regression detection
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=60,  # Fast for hooks
        )

    @staticmethod
    def consolidate(session_id: str) -> AgentConfig:
        """Pattern consolidation agent: Read/Write/Edit for updating consolidated reports.

        Used for: Extracting patterns from failed audits
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["Read", "Write", "Edit", "WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=300,
        )

    @staticmethod
    def worker(session_id: str) -> AgentConfig:
        """General worker agent: Most tools except Task/TodoWrite, hooks enabled.

        Used for: General automation, --print mode with hooks
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=[
                "Bash",
                "BashOutput",
                "Edit",
                "ExitPlanMode",
                "Glob",
                "Grep",
                "KillShell",
                "NotebookEdit",
                "Read",
                "SlashCommand",
                "WebFetch",
                "WebSearch",
                "Write",
            ],
            enable_hooks=True,
            timeout=180,
        )

    @staticmethod
    def interactive(session_id: str, mcp_servers: dict[str, Any] | None = None) -> AgentConfig:
        """Interactive agent: Most tools except Task/TodoWrite, hooks enabled, MCP servers.

        Used for: Interactive sessions with user
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=[
                "Bash",
                "BashOutput",
                "Edit",
                "ExitPlanMode",
                "Glob",
                "Grep",
                "KillShell",
                "NotebookEdit",
                "Read",
                "SlashCommand",
                "WebFetch",
                "WebSearch",
                "Write",
            ],
            enable_hooks=True,
            timeout=None,  # No timeout
            mcp_servers=mcp_servers,
        )

    @staticmethod
    def task_worker(session_id: str) -> AgentConfig:
        """Task execution worker: Most tools except Task/TodoWrite, hooks enabled, no timeout.

        Used for: Executing .md task files with full capabilities
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=[
                "Bash",
                "BashOutput",
                "Edit",
                "ExitPlanMode",
                "Glob",
                "Grep",
                "KillShell",
                "NotebookEdit",
                "Read",
                "SlashCommand",
                "WebFetch",
                "WebSearch",
                "Write",
            ],
            enable_hooks=True,
            timeout=None,  # Task-level timeout instead
        )

    @staticmethod
    def task_moderator(session_id: str) -> AgentConfig:
        """Task validation moderator: Read-only tools, no hooks, fast timeout.

        Used for: Validating task completion after worker execution
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

    @staticmethod
    def sync_worker(session_id: str) -> AgentConfig:
        """Git sync worker: Most tools except Task/TodoWrite, hooks enabled, no timeout.

        Used for: Executing git commit/push operations with full capabilities
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=[
                "Bash",
                "BashOutput",
                "Edit",
                "ExitPlanMode",
                "Glob",
                "Grep",
                "KillShell",
                "NotebookEdit",
                "Read",
                "SlashCommand",
                "WebFetch",
                "WebSearch",
                "Write",
            ],
            enable_hooks=True,
            timeout=None,  # Sync-level timeout instead
        )

    @staticmethod
    def sync_moderator(session_id: str) -> AgentConfig:
        """Git sync moderator: Read-only + Bash tools, no hooks, fast timeout.

        Used for: Checking git status and validating sync completion
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=["Read", "Grep", "Glob", "Bash", "WebSearch", "WebFetch"],
            enable_hooks=False,
            timeout=180,
        )

    @staticmethod
    def completion_moderator(session_id: str) -> AgentConfig:
        """Completion validation moderator: No tools, analyzes conversation data only.

        Used for: Validating WORK DONE and FEEDBACK: completion markers

        Timeout is 100s to allow processing of large contexts (up to 100K tokens).
        Framework timeout is 120s, ensuring agent timeout triggers first for fail-closed behavior.
        This prevents silent failures where framework kills process without logging.
        """
        return AgentConfig(
            model="claude-sonnet-4-5",
            session_id=session_id,
            allowed_tools=[],
            enable_hooks=False,
            timeout=100,
        )


class AgentCLI(ABC):
    """Abstract interface for agent CLI operations."""

    @abstractmethod
    def run_interactive(
        self,
        instruction: str,
        agent_config: AgentConfig,
    ) -> int:
        """Run agent in interactive mode.

        Args:
            instruction: Initial instruction/prompt for the agent
            agent_config: Agent configuration (model, tools, hooks, MCP)

        Returns:
            Exit code (0=success, non-zero=failure)
        """

    @abstractmethod
    def run_print(
        self,
        instruction: str | None = None,
        instruction_file: Path | None = None,
        stdin: str | TextIO | None = None,
        agent_config: AgentConfig | None = None,
        cwd: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run agent in non-interactive (print) mode.

        Args:
            instruction: Instruction text
            instruction_file: Path to instruction file
            stdin: Input data
            agent_config: Agent configuration (defaults to worker preset)
            cwd: Working directory for agent execution (defaults to current directory)

        Returns:
            Tuple of (agent output text, execution metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentCommandNotFoundError: Claude CLI not found
            AgentExecutionError: Non-zero exit code
            AgentProcessKillError: Failed to kill hung process
        """


class ClaudeAgentCLI(AgentCLI):
    """Claude Code CLI implementation.

    Manages Claude Code CLI tool restrictions by maintaining a canonical list
    of all available tools and computing disallowed tools from allowed tools.
    """

    # Canonical list of ALL Claude Code tools (as of Claude Code v0.x)
    # Source: https://docs.claude.com/en/docs/claude-code/tools.md
    ALL_TOOLS = [
        "Bash",
        "BashOutput",
        "Edit",
        "ExitPlanMode",
        "Glob",
        "Grep",
        "KillShell",
        "NotebookEdit",
        "Read",
        "SlashCommand",
        "Task",
        "TodoWrite",
        "WebFetch",
        "WebSearch",
        "Write",
    ]

    def __init__(self) -> None:
        """Initialize Claude Agent CLI."""
        self.config = get_config()
        self.logger = get_logger("agent-cli")
        self._current_process: subprocess.Popen[str] | None = None  # Track running process for cleanup

    def kill_current_process(self) -> bool:
        """Kill currently running subprocess if exists.

        Returns:
            True if process was killed, False if no process or kill failed
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
            # Process already dead
            self.logger.info("process_already_dead", pid=pid)
            self._current_process = None
            return False
        except (PermissionError, OSError) as e:
            self.logger.error("failed_to_kill_process", pid=pid, error=str(e))
            return False

    @staticmethod
    def compute_disallowed_tools(allowed_tools: list[str] | None) -> list[str]:
        """Compute disallowed tools as complement of allowed tools.

        Args:
            allowed_tools: List of allowed tool names, or None for all tools

        Returns:
            List of disallowed tool names (empty if allowed_tools is None)

        Raises:
            ValueError: If unknown tools in allowed_tools

        Example:
            # Audit agent: only web tools
            allowed = ["WebSearch", "WebFetch"]
            disallowed = compute_disallowed_tools(allowed)
            # Returns: ["Bash", "Read", "Write", ...]
        """
        if allowed_tools is None:
            return []  # All tools allowed, nothing disallowed

        allowed_set = set(allowed_tools)
        all_set = set(ClaudeAgentCLI.ALL_TOOLS)

        # Validate that allowed tools are in the canonical list
        unknown = allowed_set - all_set
        if unknown:
            raise ValueError(f"Unknown tools in allowed_tools: {unknown}")

        # Return complement
        return sorted(all_set - allowed_set)

    def run_interactive(
        self,
        instruction: str,
        agent_config: AgentConfig,
    ) -> int:
        """Run Claude Code in interactive mode.

        Args:
            instruction: Initial instruction/prompt
            agent_config: Agent configuration

        Returns:
            Exit code from claude process
        """
        # Implementation would go here
        # For now, placeholder since we're focused on run_print for hooks
        raise NotImplementedError("Interactive mode not yet implemented")

    def _build_claude_command(
        self,
        instruction_text: str,
        agent_config: AgentConfig,
        settings_file: Path | None,
    ) -> list[str]:
        """Build Claude CLI command with all arguments.

        Args:
            instruction_text: Instruction for Claude
            agent_config: Agent configuration
            settings_file: Optional settings file path

        Returns:
            Command list ready for subprocess execution
        """
        claude_cmd = self.config.get("claude_cli.command", "claude")
        cmd = [claude_cmd, "--print"]

        # Model
        cmd.extend(["--model", agent_config.model])

        # Conditional streaming support
        if agent_config.enable_streaming:
            # Streaming JSON output for real-time log forwarding
            cmd.extend(["--output-format", "stream-json"])
            # stream-json requires --verbose in --print mode
            cmd.append("--verbose")

        # Tool restrictions - ALWAYS provide both allowed and disallowed
        if agent_config.allowed_tools is not None:
            disallowed = self.compute_disallowed_tools(agent_config.allowed_tools)
            cmd.extend(["--allowed-tools", " ".join(agent_config.allowed_tools)])
            cmd.extend(["--disallowed-tools", " ".join(disallowed)])

        cmd.append("--dangerously-skip-permissions")

        # Settings file (hooks)
        if settings_file:
            cmd.extend(["--settings", str(settings_file)])

        cmd.extend(["--", instruction_text])
        return cmd

    def _drop_privileges(self) -> None:
        """Drop root privileges to original sudo user.

        This allows ami-agent to run with sudo for file locking while
        Claude CLI subprocess runs as the original user to avoid
        --dangerously-skip-permissions blocking.
        """
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user and os.geteuid() == 0:
            try:
                pw_record = pwd.getpwnam(sudo_user)
                os.setgid(pw_record.pw_gid)
                os.setuid(pw_record.pw_uid)
                self.logger.info(
                    "privileges_dropped",
                    from_user="root",
                    to_user=sudo_user,
                    uid=pw_record.pw_uid,
                    gid=pw_record.pw_gid,
                )
            except (KeyError, OSError) as e:
                self.logger.warning("privilege_drop_failed", error=str(e))

    def _get_unprivileged_env(self) -> dict[str, str] | None:
        """Get environment variables for unprivileged user.

        Returns:
            Environment dict with corrected HOME/USER/LOGNAME if running as sudo, None otherwise
        """
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

    def _start_streaming_process(self, cmd: list[str], stdin_data: str | None, cwd: Path | None) -> subprocess.Popen[str]:
        """Start subprocess for streaming execution.

        Args:
            cmd: Command to execute
            stdin_data: Optional stdin input
            cwd: Working directory

        Returns:
            Started process handle

        Raises:
            AgentExecutionError: If process fails immediately
        """
        self.logger.info("agent_streaming_subprocess_starting")

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

        self.logger.info("agent_streaming_subprocess_started", pid=process.pid)

        # Store process reference for cleanup on retry
        self._current_process = process

        # Write stdin and close
        if process.stdin:
            if stdin_data:
                process.stdin.write(stdin_data)
            process.stdin.close()
            self.logger.info("agent_streaming_stdin_closed")

        # Check for immediate exit
        time.sleep(0.1)
        poll_result = process.poll()
        if poll_result is not None:
            stderr_output = process.stderr.read() if process.stderr else ""
            self.logger.error("agent_streaming_immediate_exit", exit_code=poll_result, stderr=stderr_output[:1000])
            raise AgentExecutionError(
                exit_code=poll_result,
                stdout="",
                stderr=stderr_output,
                cmd=cmd,
            )

        return process

    def _read_streaming_line(self, process: subprocess.Popen[str], timeout_val: float, cmd: list[str]) -> tuple[str | None, bool]:
        """Read single line from streaming process.

        Args:
            process: Running process
            timeout_val: Timeout for select
            cmd: Command being executed

        Returns:
            Tuple of (line, process_exited). Line is None if timeout or EOF.

        Raises:
            AgentExecutionError: If select/readline fails
        """
        if not process.stdout:
            return None, True

        try:
            ready, _, _ = select.select([process.stdout.fileno()], [], [], timeout_val)
        except (OSError, ValueError) as e:
            self.logger.error("agent_streaming_select_error", error=str(e))
            raise AgentExecutionError(exit_code=-1, stdout="", stderr=f"select() failed: {e}", cmd=cmd) from e

        if not ready:
            poll_result = process.poll()
            if poll_result is not None:
                try:
                    remaining_stderr = process.stderr.read() if process.stderr else ""
                except OSError as e:
                    remaining_stderr = f"<failed to read stderr: {e}>"
                self.logger.info("agent_streaming_process_exited_in_select", exit_code=poll_result, stderr=remaining_stderr[:1000])
                return None, True
            return None, False

        try:
            line = process.stdout.readline()
        except OSError as e:
            self.logger.error("agent_streaming_readline_error", error=str(e))
            raise AgentExecutionError(exit_code=-1, stdout="", stderr=f"readline() failed: {e}", cmd=cmd) from e

        if not line:
            self.logger.info("agent_streaming_eof")
            return None, True

        return line, False

    def _parse_stream_message(self, line: str, cmd: list[str], line_count: int, agent_config: AgentConfig) -> tuple[str, dict[str, Any] | None]:
        """Parse streaming JSON message and extract assistant text and metadata.

        Args:
            line: JSON line from stream
            cmd: Command being executed
            line_count: Current line number
            agent_config: Agent configuration

        Returns:
            Tuple of (extracted assistant text, metadata dict or None)

        Raises:
            AgentExecutionError: If JSON parsing fails
        """
        # Print raw JSON

        if line_count == 1:
            self.logger.info("agent_streaming_first_line_received")

        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            self.logger.error("agent_stream_invalid_json", line=line[:200], error=str(e))
            raise AgentExecutionError(
                exit_code=-1,
                stdout="",
                stderr=f"Invalid JSON in streaming output: {line[:200]}",
                cmd=cmd,
            ) from e

        self.logger.info("agent_stream_message", session_id=agent_config.session_id, msg_type=msg.get("type"))

        # Extract metadata from result message
        if msg.get("type") == "result":
            metadata = {
                "cost_usd": msg.get("total_cost_usd"),
                "duration_ms": msg.get("duration_ms"),
                "duration_api_ms": msg.get("duration_api_ms"),
                "num_turns": msg.get("num_turns"),
                "usage": msg.get("usage"),
                "model_usage": msg.get("modelUsage"),
            }
            return "", metadata

        # Extract assistant text
        if msg.get("type") == "assistant":
            text_parts = []
            for content in msg.get("message", {}).get("content", []):
                if content.get("type") == "text":
                    text = content.get("text", "")
                    if text:
                        text_parts.append(text)
            return "".join(text_parts), None

        return "", None

    def _calculate_stream_timeout(
        self, agent_config: AgentConfig, last_log_time: float, line_count: int, elapsed: float, iterations: int
    ) -> tuple[float, float]:
        """Calculate timeout value and update logging.

        Args:
            agent_config: Agent configuration
            last_log_time: Last log time
            line_count: Current line count
            elapsed: Elapsed time
            iterations: Loop iterations

        Returns:
            Tuple of (timeout_val, new_last_log_time)

        Raises:
            subprocess.TimeoutExpired: If timeout exceeded
        """
        log_interval_seconds = 10

        if agent_config.timeout:
            remaining = agent_config.timeout - elapsed
            if remaining <= 0:
                self.logger.error("agent_streaming_timeout_in_loop", line_count=line_count, elapsed=elapsed, iterations=iterations)
                raise subprocess.TimeoutExpired([], agent_config.timeout)

            if time.time() - last_log_time > log_interval_seconds:
                self.logger.info("agent_streaming_still_waiting", line_count=line_count, elapsed=elapsed, iterations=iterations)
                return min(1.0, remaining), time.time()

            return min(1.0, remaining), last_log_time

        # No timeout configured
        if time.time() - last_log_time > log_interval_seconds:
            self.logger.info("agent_streaming_still_waiting_no_timeout", line_count=line_count, elapsed=elapsed, iterations=iterations)
            return 1.0, time.time()

        return 1.0, last_log_time

    def _execute_streaming(
        self,
        cmd: list[str],
        stdin_data: str | None,
        agent_config: AgentConfig,
        cwd: Path | None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute command with streaming JSON output parsing.

        Args:
            cmd: Command to execute
            stdin_data: Optional stdin input
            agent_config: Agent configuration
            cwd: Working directory
            audit_log_path: Optional path to write streaming output for audit/debugging

        Returns:
            Tuple of (accumulated assistant text, metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentExecutionError: Non-zero exit code
        """
        start_time = time.time()
        process = None
        assistant_text: list[str] = []
        metadata: dict[str, Any] | None = None
        first_output_timeout = 30  # Warn if no output after 30s

        try:
            process = self._start_streaming_process(cmd, stdin_data, cwd)

            # Write process start marker to audit log
            if audit_log_path:
                try:
                    with audit_log_path.open("a") as f:
                        f.write(f"\n=== PROCESS STARTED (PID: {process.pid}) ===\n")
                except OSError as e:
                    self.logger.warning("audit_log_write_failed", path=str(audit_log_path), error=str(e))

            # Read loop
            line_count = 0
            last_log_time = time.time()
            loop_iterations = 0
            first_output_received = False

            self.logger.info("agent_streaming_entering_loop", has_timeout=agent_config.timeout is not None, pid=process.pid)

            while True:
                loop_iterations += 1
                elapsed = time.time() - start_time

                # Check for first output timeout
                if not first_output_received and elapsed > first_output_timeout:
                    # Check if process is still alive
                    if process.poll() is not None:
                        # Process exited without producing output - capture stderr
                        stderr = process.stderr.read() if process.stderr else ""
                        self.logger.error(
                            "agent_streaming_no_output_process_died",
                            elapsed=elapsed,
                            exit_code=process.returncode,
                            stderr_preview=stderr[:2000] if stderr else "",
                        )
                        if audit_log_path:
                            try:
                                with audit_log_path.open("a") as f:
                                    f.write(f"\n=== PROCESS DIED WITHOUT OUTPUT (exit code: {process.returncode}) ===\n")
                                    if stderr:
                                        f.write(f"STDERR:\n{stderr}\n")
                            except OSError:
                                pass
                        raise AgentExecutionError(
                            exit_code=process.returncode,
                            stdout="",
                            stderr=f"Process exited without producing streaming output after {elapsed:.1f}s\n\nSTDERR:\n{stderr}",
                            cmd=cmd,
                        )

                    # Process still alive but no output
                    self.logger.warning(
                        "agent_streaming_no_output_still_alive",
                        elapsed=elapsed,
                        iterations=loop_iterations,
                        pid=process.pid,
                    )
                    first_output_received = True  # Only warn once

                # Calculate timeout
                timeout_val, last_log_time = self._calculate_stream_timeout(agent_config, last_log_time, line_count, elapsed, loop_iterations)

                # Read line
                line, process_exited = self._read_streaming_line(process, timeout_val, cmd)

                if process_exited:
                    # Capture stderr on exit
                    stderr = ""
                    if process and process.stderr:
                        try:
                            stderr = process.stderr.read()
                        except OSError as e:
                            stderr = f"<failed to read stderr: {e}>"

                    if stderr and audit_log_path:
                        try:
                            with audit_log_path.open("a") as f:
                                f.write(f"\n=== PROCESS STDERR ===\n{stderr}\n")
                        except OSError:
                            pass

                    self.logger.info(
                        "agent_streaming_loop_exit",
                        line_count=line_count,
                        iterations=loop_iterations,
                        stderr_preview=stderr[:1000] if stderr else "",
                    )
                    break

                if line:
                    if not first_output_received:
                        first_output_received = True
                        self.logger.info("agent_streaming_first_output", elapsed=elapsed)

                        # Write timing marker to audit log for test extraction
                        if audit_log_path:
                            try:
                                with audit_log_path.open("a") as f:
                                    f.write(f"\n=== FIRST OUTPUT: {elapsed:.4f}s ===\n\n")
                            except Exception:
                                pass  # Don't fail if audit log write fails

                    line_count += 1

                    # Write to audit log BEFORE parsing (captures raw streaming output)
                    if audit_log_path:
                        try:
                            with audit_log_path.open("a") as f:
                                f.write(line)
                        except OSError as e:
                            self.logger.warning("audit_log_write_failed", path=str(audit_log_path), error=str(e))

                    text, msg_metadata = self._parse_stream_message(line, cmd, line_count, agent_config)
                    if text:
                        assistant_text.append(text)
                    if msg_metadata:
                        metadata = msg_metadata

            # Wait for process completion
            process.wait(timeout=10)
            duration = time.time() - start_time

            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else ""
                if audit_log_path:
                    try:
                        with audit_log_path.open("a") as f:
                            f.write(f"\n=== PROCESS FAILED (exit code: {process.returncode}) ===\n")
                            if stderr:
                                f.write(f"STDERR:\n{stderr}\n")
                    except OSError:
                        pass
                self.logger.info(
                    "agent_print_complete",
                    exit_code=process.returncode,
                    duration=round(duration, 1),
                    stderr=stderr[:1000] if stderr else "",
                )
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

            self.logger.info("agent_print_complete", exit_code=process.returncode, duration=round(duration, 1))
            return "".join(assistant_text), metadata

        except subprocess.TimeoutExpired as timeout_err:
            duration = time.time() - start_time
            self.logger.error("agent_print_timeout", timeout=agent_config.timeout, duration=round(duration, 1))

            if audit_log_path:
                try:
                    with audit_log_path.open("a") as f:
                        f.write(f"\n=== TIMEOUT EXCEEDED ({agent_config.timeout}s, actual: {duration:.1f}s) ===\n")
                except OSError:
                    pass

            if process and process.pid:
                import contextlib

                with contextlib.suppress(ProcessLookupError):
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)

            raise AgentTimeoutError(timeout=agent_config.timeout or 0, duration=duration, cmd=cmd) from timeout_err

        except FileNotFoundError as e:
            raise AgentCommandNotFoundError(cmd=cmd[0]) from e

    def _execute_with_timeout(
        self,
        cmd: list[str],
        stdin_data: str | None,
        agent_config: AgentConfig,
        cwd: Path | None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Execute command with timeout handling.

        Args:
            cmd: Command to execute
            stdin_data: Optional stdin input
            agent_config: Agent configuration for timeout
            cwd: Working directory
            audit_log_path: Optional path to write streaming output for audit/debugging

        Returns:
            Tuple of (command stdout, metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentCommandNotFoundError: Claude CLI not found
            AgentExecutionError: Non-zero exit code
            AgentProcessKillError: Failed to kill hung process
        """
        # Route to streaming execution if enabled
        if agent_config.enable_streaming:
            self.logger.info("agent_using_streaming_path")
            return self._execute_streaming(cmd, stdin_data, agent_config, cwd, audit_log_path)

        # Use FileSubprocessSync for reliable non-streaming execution
        start_time = time.time()
        env = self._get_unprivileged_env()

        # Execute using FileSubprocessSync
        executor = FileSubprocessSync(work_dir=cwd)
        result = executor.run(
            cmd=cmd,
            input_text=stdin_data,
            timeout=float(agent_config.timeout) if agent_config.timeout else None,
            env=env,
        )

        duration = time.time() - start_time

        # Check for timeout
        if result.get("timeout"):
            self.logger.error(
                "agent_print_timeout",
                timeout=agent_config.timeout,
                duration=round(duration, 1),
            )
            raise AgentTimeoutError(
                timeout=agent_config.timeout or 0,
                duration=duration,
                cmd=cmd,
            )

        # Check for execution error
        if not result["success"]:
            returncode = result["returncode"]
            stdout = result["stdout"]
            stderr = result["stderr"]

            self.logger.info(
                "agent_print_complete",
                exit_code=returncode,
                duration=round(duration, 1),
                stdout_preview=stdout[:1000] if stdout else "",
                stderr=stderr[:1000] if stderr else "",
            )

            if returncode == -1 and "not found" in stderr.lower():
                raise AgentCommandNotFoundError(cmd=cmd[0])

            raise AgentExecutionError(
                exit_code=returncode,
                stdout=stdout,
                stderr=stderr,
                cmd=cmd,
            )

        # Success case
        stdout = result["stdout"]
        self.logger.info(
            "agent_print_complete",
            exit_code=result["returncode"],
            duration=round(duration, 1),
        )

        return stdout, None  # No metadata in non-streaming mode

    def run_print(
        self,
        instruction: str | None = None,
        instruction_file: Path | None = None,
        stdin: str | TextIO | None = None,
        agent_config: AgentConfig | None = None,
        cwd: Path | None = None,
        audit_log_path: Path | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        """Run Claude Code in --print mode (non-interactive).

        Args:
            instruction: Instruction text
            instruction_file: Path to instruction file
            stdin: Input data
            agent_config: Agent configuration (defaults to worker preset)
            cwd: Working directory for agent execution (defaults to current directory)
            audit_log_path: Optional path to write streaming output for audit/debugging

        Returns:
            Tuple of (agent output text, execution metadata dict or None)

        Raises:
            AgentTimeoutError: Execution exceeded timeout
            AgentCommandNotFoundError: Claude CLI not found
            AgentExecutionError: Non-zero exit code
            AgentProcessKillError: Failed to kill hung process
        """
        # Default to worker preset if no config provided
        if agent_config is None:
            agent_config = AgentConfigPresets.worker(session_id=str(uuid.uuid4()))

        # Load instruction
        if instruction_file:
            instruction_text = self._load_instruction(instruction_file)
        elif instruction:
            instruction_text = instruction
        else:
            raise ValueError("Either instruction or instruction_file required")

        # Prepare stdin input
        stdin_data = None
        if stdin:
            stdin_data = stdin if isinstance(stdin, str) else stdin.read()

        # Create temp settings file based on hook configuration
        # SECURITY: Bash command guard ALWAYS enabled (either full hooks or bash-only)
        settings_file = self._create_full_hooks_file() if agent_config.enable_hooks else self._create_bash_only_hooks_file()

        # Build command from agent_config
        cmd = self._build_claude_command(instruction_text, agent_config, settings_file)

        # Execute
        self.logger.info(
            "agent_print_start",
            model=agent_config.model,
            hooks=agent_config.enable_hooks,
            stdin_size=len(stdin_data) if stdin_data else 0,
            streaming=agent_config.enable_streaming,
            command=" ".join(cmd),
        )

        try:
            return self._execute_with_timeout(cmd, stdin_data, agent_config, cwd, audit_log_path)
        finally:
            # Always cleanup temp files
            if settings_file and settings_file.exists():
                settings_file.unlink()

    def _create_bash_only_hooks_file(self) -> Path:
        """Create temp settings file with bash command guard only.

        SECURITY: Bash command guard ALWAYS enabled for all agents regardless
        of enable_hooks setting to prevent dangerous command execution.

        Returns:
            Path to temp settings file with bash guard hook

        Raises:
            RuntimeError: If hooks.yaml not found or invalid
        """
        hooks_yaml_path = self.config.root / self.config.get("hooks.file")
        if not hooks_yaml_path.exists():
            raise RuntimeError(f"hooks.yaml not found: {hooks_yaml_path}")

        # Load hooks.yaml
        with hooks_yaml_path.open("r") as f:
            hooks_config = yaml.safe_load(f)

        # Extract bash command guard hook
        bash_hook = None
        for hook in hooks_config.get("hooks", []):
            if hook.get("event") == "PreToolUse" and hook.get("matcher") == "Bash":
                bash_hook = hook
                break

        if not bash_hook:
            raise RuntimeError("Bash command guard hook not found in hooks.yaml")

        # Create temp settings file with bash hook only
        settings_fd, settings_path = tempfile.mkstemp(suffix=".json")
        settings_path_obj = Path(settings_path)

        settings_path_obj.write_text(json.dumps({"hooks": {"PreToolUse": [bash_hook]}}))

        os.close(settings_fd)

        return settings_path_obj

    def _create_full_hooks_file(self) -> Path:
        """Create temp settings file with all hooks from hooks.yaml.

        Returns:
            Path to temp settings file with full hook configuration

        Raises:
            RuntimeError: If hooks.yaml not found or settings file write fails
        """
        # Load hooks from config
        hooks_file = self.config.root / self.config.get("hooks.file")
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
                "command": f"{self.config.root}/scripts/ami-agent --hook {hook['command']}",
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
                json.dump(settings, settings_file, indent=2)
                file_name = settings_file.name

            self.logger.info("agent_settings_file_created", path=file_name, hooks_count=sum(len(v) for v in settings.get("hooks", {}).values()))
            return Path(file_name)
        except (OSError, TypeError) as e:
            # Clean up file if it was created
            if "settings_file" in locals() and hasattr(settings_file, "name"):
                Path(settings_file.name).unlink(missing_ok=True)
            raise RuntimeError(f"Failed to write settings file: {e}") from e

    def _load_instruction(self, instruction_file: Path) -> str:
        """Load instruction from file with template substitution.

        Args:
            instruction_file: Path to instruction file

        Returns:
            Instruction text with templates substituted
        """
        content = instruction_file.read_text()

        # Inject patterns if {PATTERNS} placeholder present
        if "{PATTERNS}" in content:
            patterns_file = instruction_file.parent / "patterns_core.txt"
            if patterns_file.exists():
                patterns_content = patterns_file.read_text()
                content = content.replace("{PATTERNS}", patterns_content)

        # Use str.replace() instead of .format() to avoid conflicts with code examples containing braces
        return content.replace("{date}", datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"))


def get_agent_cli() -> "ClaudeAgentCLI":
    """Factory function to get agent CLI instance.

    Returns ClaudeAgentCLI by default.
    Future: Can return different implementations based on config.

    Returns:
        Agent CLI instance
    """
    return ClaudeAgentCLI()
