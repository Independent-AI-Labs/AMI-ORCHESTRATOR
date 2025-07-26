import os
import subprocess
import sys

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python run_background.py <pid_file> <stdin_file> <stdout_file> <stderr_file> <command> [<args>...]")
        sys.exit(1)

    pid_file = sys.argv[1]
    stdin_file = sys.argv[2]
    stdout_file = sys.argv[3]
    stderr_file = sys.argv[4]
    command = sys.argv[5:]

    # Ensure log directory exists
    for f in [pid_file, stdout_file, stderr_file]:
        log_dir = os.path.dirname(f)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    # Touch stdin file if it doesn't exist
    if not os.path.exists(stdin_file):
        with open(stdin_file, "w") as f:
            pass

    stdin_f = open(stdin_file, "r")
    stdout_f = open(stdout_file, "a")  # Append to logs
    stderr_f = open(stderr_file, "a")  # Append to logs

    kwargs = {
        "stdin": stdin_f,
        "stdout": stdout_f,
        "stderr": stderr_f,
    }

    # Platform-specific process creation
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS
        kwargs["close_fds"] = False  # Must be false for redirection on Windows
    else:
        kwargs["preexec_fn"] = os.setsid
        kwargs["close_fds"] = True

    process = subprocess.Popen(command, **kwargs)

    with open(pid_file, "w") as f:
        f.write(str(process.pid))

    print(f"Process '{' '.join(command)}' started with PID: {process.pid}. PID written to {pid_file}")

    # The script exits, but the child process continues.
    # The file handles are duplicated for the child process, so we can close them here.
    stdin_f.close()
    stdout_f.close()
    stderr_f.close()
