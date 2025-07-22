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

# Configure logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# File paths for PID and logs
PID_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".mcp_server.pid"))
LOG_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "logs", "mcp_server.log")
)


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
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    def _read_pid(self) -> int | None:
        """Reads the PID from the PID file."""
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return None
        except (IOError, ValueError) as e:
            logger.error("Error reading PID file: %s", e)
            return None

    def _write_pid(self, pid: int):
        """Writes the PID to the PID file."""
        try:
            with open(PID_FILE, "w", encoding="utf-8") as f:
                f.write(str(pid))
        except IOError as e:
            logger.error("Error writing PID file: %s", e)
            raise

    def _terminate_process_windows(self, pid: int):
        """Terminates the process on Windows."""
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                check=True,
                capture_output=True,
            )
            logger.info(
                "Successfully sent termination signal to process group %d.", pid
            )
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
            pgid = os.getpgid(pid)  # pylint: disable=no-member
            os.killpg(pgid, signal.SIGTERM)  # pylint: disable=no-member
            logger.info(
                "Successfully sent termination signal to process group %d.", pgid
            )
        except (ProcessLookupError, PermissionError) as e:
            logger.warning(
                "Process with PID %d not found or permission denied: %s", pid, e
            )
        except OSError as e:
            logger.error("Error getting process group or killing process: %s", e)

    def start_server(self):
        """
        Starts the MCP server as a detached process.
        """
        if self.is_running():
            logger.info("MCP server is already running.")
            return

        logger.info("Starting MCP server: %s in %s", self.server_script_path, self.cwd)
        try:
            creation_flags = (
                subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            )
            preexec_fn = os.setsid if sys.platform != "win32" else None

            with open(LOG_FILE, "wb") as log_file:
                process = subprocess.Popen(
                    [sys.executable, self.server_script_path],
                    cwd=self.cwd,
                    creationflags=creation_flags,
                    preexec_fn=preexec_fn,
                    stdout=log_file,
                    stderr=log_file,
                )
            self._write_pid(process.pid)
            logger.info(
                "MCP server started with PID: %d. Logs are in %s",
                process.pid,
                LOG_FILE,
            )
        except (IOError, OSError) as e:
            logger.error("Error starting MCP server: %s", e)
            raise

    def start_server_for_testing(self):
        """
        Starts the MCP server for testing (not detached).
        Returns the Popen object for direct communication.
        """
        logger.info(
            "Starting MCP server for testing: %s in %s",
            self.server_script_path,
            self.cwd,
        )
        try:
            creation_flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )
            start_new_session = sys.platform != "win32"

            process = subprocess.Popen(
                [sys.executable, self.server_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                creationflags=creation_flags,
                start_new_session=start_new_session,
            )
            return process
        except (IOError, OSError) as e:
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
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        logger.info("MCP server stopped and PID file removed.")

    def is_running(self) -> bool:
        """Checks if the server process is running."""
        pid = self._read_pid()
        if not pid:
            return False

        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return str(pid) in result.stdout
            # On Unix, os.kill(pid, 0) checks if the process exists.
            os.kill(pid, 0)  # pylint: disable=no-member
            return True
        except (subprocess.CalledProcessError, OSError):
            return False


def main():
    """
    Command-line interface for managing the MCP server.
    """
    if len(sys.argv) < 3:
        print("Usage: python mcp_server_manager.py <command> <server_script_path>")
        print("Commands: start, stop")
        sys.exit(1)

    command = sys.argv[1]
    server_script = sys.argv[2]
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    manager = MCPServerManager(server_script, project_root)

    if command == "start":
        manager.start_server()
    elif command == "stop":
        manager.stop_server()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
