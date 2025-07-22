import os
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
            # Use DETACHED_PROCESS flag for Windows
            creationflags = subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            with open(LOG_FILE, 'wb') as log_file:
                process = subprocess.Popen(
                    [sys.executable, self.server_script_path],
                    cwd=self.cwd,
                    creationflags=creationflags,
                    close_fds=True,
                    stdout=log_file,
                    stderr=log_file
                )
            with open(PID_FILE, "w") as f:
                f.write(str(process.pid))
            print(f"MCP server started with PID: {process.pid}. Logs are in {LOG_FILE}")
        except Exception as e:
            print(f"Error starting MCP server: {e}")

    def stop_server(self):
        """
        Stops the running MCP server.

        Reads the PID from the PID file and attempts to terminate the process.
        Removes the PID file upon successful termination or if the process is not found.
        """
        if not os.path.exists(PID_FILE):
            print("MCP server is not running (no PID file).")
            return

        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())

        print(f"Stopping MCP server with PID: {pid}...")
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=True)
            else:
                os.kill(pid, 15)  # SIGTERM
            print("MCP server stopped.")
        except Exception as e:
            print(f"Error stopping MCP server: {e}")
        finally:
            os.remove(PID_FILE)

    def is_process_running(self, pid):
        """Checks if a process with the given PID is running."""
        if pid is None:
            return False
        try:
            if sys.platform == "win32":
                # Windows: tasklist command to check for PID
                result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
                return str(pid) in result.stdout
            else:
                # Unix-like: os.kill(pid, 0) checks if process exists
                os.kill(pid, 0)
                return True
        except OSError:
            return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mcp_server_manager.py <command> <server_script_path>")
        print("Commands: start, stop")
        sys.exit(1)

    command = sys.argv[1]
    server_script = sys.argv[2]
    cwd = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # Project root (AMI-SDA)

    manager = MCPServerManager(server_script, cwd)

    if command == "start":
        manager.start_server()
    elif command == "stop":
        manager.stop_server()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
