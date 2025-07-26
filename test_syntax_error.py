import os
import signal
import subprocess
import sys

PID_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".mcp_server.pid"))
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".mcp_server.log"))


class MCPServerManager:
    """
    Manages the lifecycle of an MCP (Model-Controller-Presenter) server.

    This class provides functionality to start and stop a given Python server script
    as a detached process, managing its PID and logging its output.
    """

    def __init__(self, server_script_path: str, cwd: str):
        """
        Initializes the MCPServerManager.

        Args:
            server_script_path (str): The absolute path to the Python script that runs the MCP server.
            cwd (str): The current working directory to run the server script from.
        """
        self.server_script_path = server_script_path
        self.cwd = cwd

    def start_server(self):
        """
        Starts the MCP server as a detached process.

        If a PID file exists, it assumes the server is already running.
        The server's output is redirected to a log file.
        """
        if os.path.exists(PID_FILE):
            print("MCP server is already running (PID file exists).")
            return

        print(f"Starting MCP server: {self.server_script_path} in {self.cwd}")
        try:
            creation_flags = subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            preexec_fn = os.setsid if sys.platform != "win32" else None

            with open(LOG_FILE, "wb") as log_file:
                process = subprocess.Popen(
                    [sys.executable, self.server_script_path],
                    cwd=self.cwd,
                    creationflags=creation_flags,
                    preexec_fn=preexec_fn,  # nosec B603, B607
                    stdout=log_file,
                    stderr=log_file,
                )
            with open(PID_FILE, "w", encoding="utf-8") as f:
                f.write(str(process.pid))
            print(f"MCP server started with PID: {process.pid}. Logs are in {LOG_FILE}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error starting MCP server: {e}")
            raise

    def start_server_for_testing(self):
        """
        Starts the MCP server for testing purposes (not detached, with pipes).
        Returns the Popen object for direct communication.
        """
        print(f"Starting MCP server for testing: {self.server_script_path} in {self.cwd}")
        try:
            creation_flags = 0
            start_new_session = False
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                start_new_session = True

            process = subprocess.Popen(
                [sys.executable, self.server_script_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # Capture stderr separately
                cwd=self.cwd,
                creationflags=creation_flags,
                start_new_session=start_new_session,  # nosec B603, B607
            )
            return process
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error starting MCP server for testing: {e}")
            raise

    def stop_server(self):
        """
        Stops the running MCP server.

        Reads the PID from the PID file and attempts to terminate the process group.
        Removes the PID file upon successful termination or if the process is not found.
        """
        if not os.path.exists(PID_FILE):
            print("MCP server is not running (no PID file).")
            return

        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
        except FileNotFoundError:
            print("MCP server is not running (no PID file).")
            return
        except (IOError, ValueError) as e:  # pylint: disable=broad-exception-caught
            print(f"Error reading PID file: {e}")
            return

        print(f"Stopping MCP server with PID: {pid}...")
        try:
            if sys.platform == "win32":
                # Use taskkill on Windows
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    check=True,
                    capture_output=True,
                    shell=False,  # nosec B603, B607
                )
            else:
                # Use os.killpg on Unix-like systems
                try:
                    # pylint: disable=no-member
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGTERM)  # pylint: disable=no-member
                except OSError as ose:
                    print(f"Error getting process group or killing process: {ose}")
            print("MCP server stopped.")
        except subprocess.CalledProcessError as e:
            # This can happen if the process is already gone
            if "not found" in e.stderr.decode(errors="ignore").lower():
                print(f"Process with PID {pid} was not found.")
            else:
                print(f"Error stopping MCP server with taskkill: {e.stderr.decode(errors='ignore')}")
        except (ProcessLookupError, PermissionError) as e:
            print(f"Process with PID {pid} not found or permission denied: {e}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"An unexpected error occurred while stopping the server: {e}")
        finally:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)

    def is_process_running(self, pid):
        """Checks if a process with the given PID is running."""
        if pid is None:
            return False
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=False,  # nosec B603, B607
                )
                return str(pid) in result.stdout
            os.kill(pid, 0)
            return True
        except (OSError, subprocess.CalledProcessError):
            return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mcp_server_manager.py <command> <server_script_path>")
        print("Commands: start, stop")
        sys.exit(1)

    command = sys.argv[1]
    server_script = sys.argv[2]
    # pylint: disable=redefined-outer-name
    current_working_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # Project root (AMI-SDA)
    # pylint: enable=redefined-outer-name

    manager = MCPServerManager(server_script, current_working_dir)

    if command == "start":
        manager.start_server()
    elif command == "stop":
        manager.stop_server()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
