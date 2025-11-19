"""Custom exception classes for agent execution failures."""


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
        super().__init__(f"Agent command timed out after {timeout}s: {' '.join(cmd)}" + (f" (actual duration: {duration}s)" if duration is not None else ""))


class AgentCommandNotFoundError(AgentError):
    """Claude Code CLI not found in PATH."""

    def __init__(self, cmd: str):
        """Initialize command not found error.

        Args:
            cmd: Command that was not found
        """
        self.cmd = cmd
        super().__init__(f"Agent CLI command not found: {cmd}")


class AgentExecutionError(AgentError):
    """Agent command failed during execution."""

    def __init__(self, exit_code: int, stdout: str, stderr: str, cmd: list[str]):
        """Initialize execution error.

        Args:
            exit_code: Process exit code
            stdout: Process stdout output
            stderr: Process stderr output
            cmd: Command that failed
        """
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        super().__init__(f"Agent command failed with exit code {exit_code}:\nCommand: {' '.join(cmd)}\nStdout: {stdout}\nStderr: {stderr}")


class AgentProcessKillError(AgentError):
    """Failed to kill hung agent process."""

    def __init__(self, pid: int, reason: str):
        """Initialize process kill error.

        Args:
            pid: Process ID that couldn't be killed
            reason: Reason for kill failure
        """
        self.pid = pid
        self.reason = reason
        super().__init__(f"Failed to kill hung process {pid}: {reason}")
