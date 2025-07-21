import subprocess
import sys
import os
import time

PID_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".mcp_server.pid"))
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".mcp_server.log"))

class MCPServerManager:
    def __init__(self, server_script_path: str, cwd: str):
        self.server_script_path = server_script_path
        self.cwd = cwd

    def start_server(self):
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
                os.kill(pid, 15) # SIGTERM
            print("MCP server stopped.")
        except Exception as e:
            print(f"Error stopping MCP server: {e}")
        finally:
            os.remove(PID_FILE)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mcp_server_manager.py <command>")
        print("Commands: start, stop")
        sys.exit(1)

    command = sys.argv[1]
    server_script = os.path.join(os.path.dirname(__file__), "file_manipulation_server.py")
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # Project root

    manager = MCPServerManager(server_script, cwd)

    if command == "start":
        manager.start_server()
    elif command == "stop":
        manager.stop_server()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
