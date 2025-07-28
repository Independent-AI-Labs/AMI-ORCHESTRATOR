"""
Manages the lifecycle of an MCP (Model-Controller-Presenter) server.

This script provides the MCPServerManager class to start, stop, and check the status
of a detached MCP server process. It is designed to be used as a command-line
tool or imported as a module.
"""

import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

# Configure logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# File paths for PID and logs
PID_FILE = Path(__file__).resolve().parent / ".mcp_server.pid"
LOG_FILE = Path(__file__).resolve().parent / "logs" / "mcp_server.log"


class MCPServerManager:
    """
    Manages the lifecycle of a detached MCP server process.

    Provides methods to start, stop, and check the status of the server,
    handling PID file management and logging.
    """

    def __init__(self, server_script_path: str, cwd: str):
        """
        Initializes the MCPServerManager.

        Args:
            server_script_path (str): Absolute path to the server script.
            cwd (str): The working directory to run the script from.
        """
        self.server_script_path = server_script_path
        self.cwd = cwd
        Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    def _read_pid(self) -> int | None:
        """Reads the PID from the PID file."""
        try:
            return int(PID_FILE.read_text(encoding="utf-8").strip())
        except FileNotFoundError:
            return None
        except (OSError, ValueError) as e:
            logger.error("Error reading PID file: %s", e)
            return None

    def _write_pid(self, pid: int):
        """Writes the PID to the PID file."""
        try:
            PID_FILE.write_text(str(pid), encoding="utf-8")
        except OSError as e:
            logger.error("Error writing PID file: %s", e)
            raise

    def _terminate_process_windows(self, pid: int):
        """Terminates the process on Windows."""
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],  # noqa: S603, S607
                check=True,
                capture_output=True,
            )
            logger.info("Successfully sent termination signal to process group %d.", pid)
        except subprocess.CalledProcessError as e:
            if "not found" in e.stderr.decode(errors="ignore").lower():
                logger.warning("Process with PID %d was not found.", pid)
            else:
                logger.error(
                    "Error stopping server with taskkill: %s",
                    e.stderr.decode(errors="ignore"),
                )

    def _terminate_process_unix(self, pid: int):
        """Terminates the process on Unix-like systems."""
        try:
            # Use os.kill to send SIGTERM to the process group
            # On Unix, os.setsid makes the process a session leader, and its PID is also its PGID.
            os.kill(pid, signal.SIGTERM)
            logger.info("Successfully sent termination signal to process %d.", pid)
        except (ProcessLookupError, PermissionError) as e:
            logger.warning("Process with PID %d not found or permission denied: %s", pid, e)
        except OSError as e:
            logger.error("Error killing process: %s", e)

    def start_server(self):
        """
        Starts the MCP server as a detached process.
        """
        if self.is_running():
            logger.info("MCP server is already running.")
            return

        logger.info("Starting MCP server: %s in %s", self.server_script_path, self.cwd)
        try:
            creation_flags = subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            preexec_fn = os.setsid if sys.platform != "win32" else None  # noqa: PLW1509
            # This is safe as it's only applied on Unix-like systems and does not interact with threads in an unsafe manner.

            final_env = os.environ.copy()
            project_root = Path(self.cwd).resolve()
            if "PYTHONPATH" in final_env:
                final_env["PYTHONPATH"] = f"{project_root}{os.pathsep}{final_env['PYTHONPATH']}"
            else:
                final_env["PYTHONPATH"] = str(project_root)

            process = subprocess.Popen(
                [sys.executable, self.server_script_path],  # noqa: S603, S607
                cwd=self.cwd,
                creationflags=creation_flags,
                preexec_fn=preexec_fn,  # noqa: PLW1509
                stdin=subprocess.DEVNULL if sys.platform == "win32" else None,
                stdout=LOG_FILE.open("wb"),
                stderr=subprocess.STDOUT,
                env=final_env,
            )
            self._write_pid(process.pid)
            logger.info(
                "MCP server started with PID: %d. Logs are in %s",
                process.pid,
                LOG_FILE,
            )
        except OSError as e:
            logger.error("Error starting MCP server: %s", e)
            raise

    def start_server_for_testing(self, cwd: str, env: dict | None = None, capture_stderr: bool = False):
        """
        Starts the MCP server for testing (not detached).
        Returns the Popen object for direct communication.
        """
        logger.info(
            "Starting MCP server for testing: %s in %s",
            self.server_script_path,
            cwd,
        )
        try:
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            start_new_session = sys.platform != "win32"

            final_env = os.environ.copy()
            if env:
                final_env.update(env)

            # Set PYTHONPATH for the subprocess to include the project root
            # Set PYTHONPATH for the subprocess to include the project root
            # This is necessary for the server script to find its modules
            final_env["PYTHONPATH"] = str(Path(self.server_script_path).parents[4])

            stderr_dest = subprocess.PIPE if capture_stderr else subprocess.DEVNULL

            return subprocess.Popen(
                [sys.executable, "-m", "orchestrator.mcp.servers.localfs.local_file_server"],  # noqa: S603, S607
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_dest,
                cwd=self.cwd,
                creationflags=creation_flags,
                start_new_session=start_new_session,
                env=final_env,
                shell=False,  # Explicitly not using shell
            )
        except OSError as e:
            logger.error("Error starting MCP server for testing: %s", e)
            raise

    def stop_server(self):
        """
        Stops the running MCP server.
        """
        pid = self._read_pid()
        if not pid:
            logger.info("MCP server is not running (no PID file).")
            return

        logger.info("Stopping MCP server with PID: %d...", pid)
        if sys.platform == "win32":
            self._terminate_process_windows(pid)
        else:
            self._terminate_process_unix(pid)

        # Clean up PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("MCP server stopped and PID file removed.")

    def is_running(self) -> bool:
        """Checks if the server process is running."""
        pid = self._read_pid()
        if not pid:
            return False

        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],  # noqa: S603, S607
                    check=True,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # Hide the console window
                )
                return str(pid) in result.stdout
            # On Unix, os.kill(pid, 0) checks if the process exists.
            if sys.platform != "win32":
                os.kill(pid, 0)  # pylint: disable=no-member
                return True

            return False
        except (subprocess.CalledProcessError, OSError):
            return False


def main():
    """
    Command-line interface for managing the MCP server.
    """
    if len(sys.argv) < MIN_ARGS_COUNT:
        print("Usage: python mcp_server_manager.py <command> <server_script_path>")
        print("Commands: start, stop")
        sys.exit(1)

    command = sys.argv[1]
    server_script = sys.argv[2]
    project_root = Path(__file__).resolve().parent.parent.parent

    manager = MCPServerManager(server_script, project_root)

    if command == "start":
        manager.start_server()
    elif command == "stop":
        manager.stop_server()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    MIN_ARGS_COUNT = 3
    main()
