import subprocess
import sys
import os
import time
import win32process
import win32con
from dotenv import load_dotenv

load_dotenv()

# Define the path to the log file
LOG_FILE = "uvicorn_startup.log"
LOCK_FILE = "orchestrator.lock" # Re-introduce a simple lock file for process management

def start_server():
    # Ensure the log file is empty before starting
    log_file_handle = open(LOG_FILE, "w")

    # Command to run the FastAPI server
    command = [
        sys.executable, "-m", "uvicorn", "orchestrator.api:app",
        "--host", "0.0.0.0", "--port", "8000"
    ]
    
    # Use subprocess.Popen to run the command in a detached process
    # Redirect stdout and stderr to the log file handle
    process = subprocess.Popen(
        command,
        stdout=log_file_handle,
        stderr=log_file_handle,
        creationflags=win32process.DETACHED_PROCESS | win32con.CREATE_NO_WINDOW,
        close_fds=True # Important for detached processes
    )
    
    # Store the PID in a lock file
    with open(LOCK_FILE, "w") as f:
        f.write(str(process.pid))
    
    print(f"Orchestrator start command sent. Check {LOG_FILE} for Uvicorn startup details.")
    print(f"PID stored in {LOCK_FILE}: {process.pid}")
    log_file_handle.close() # Close the file handle in the parent process

    # Give Uvicorn a moment to start and write to the log
    time.sleep(2)

def stop_server():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            pid = f.read().strip()
        try:
            # On Windows, taskkill is used to terminate processes by PID
            # /F forcefully terminates the process
            # /T terminates the process and any child processes started by it
            subprocess.run(["taskkill", "/F", "/T", "/PID", pid], check=True)
            print(f"Terminated process with PID: {pid}")
        except subprocess.CalledProcessError as e:
            print(f"Error terminating process {pid}: {e}")
        except ValueError:
            print(f"Invalid PID in {LOCK_FILE}")
        finally:
            os.remove(LOCK_FILE)
            print(f"Deleted lock file: {LOCK_FILE}")
    else:
        print("No running orchestrator found (lock file not present).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "start":
            start_server()
        elif action == "stop":
            stop_server()
        else:
            print("Usage: python -m orchestrator.main [start|stop]")
    else:
        print("Usage: python -m orchestrator.main [start|stop]")