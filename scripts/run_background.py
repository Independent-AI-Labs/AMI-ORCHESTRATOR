import os
import subprocess
import sys

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python run_background.py <pid_file> <stdin_file> <stdout_file> <stderr_file> <command> [<args>...]")
        sys.exit(1)

    pid_file_path = sys.argv[1]
    stdin_file_path = sys.argv[2]
    stdout_file_path = sys.argv[3]
    stderr_file_path = sys.argv[4]
    command = sys.argv[5:]

    # Ensure log directory exists
    for f_path in [pid_file_path, stdout_file_path, stderr_file_path]:
        log_dir = os.path.dirname(f_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    # Touch stdin file if it doesn't exist
    if not os.path.exists(stdin_file_path):
        with open(stdin_file_path, "w", encoding="utf-8") as f:
            pass

    with open(stdin_file_path, "r", encoding="utf-8") as stdin_f, open(stdout_file_path, "a", encoding="utf-8") as stdout_f, open(
        stderr_file_path, "a", encoding="utf-8"
    ) as stderr_f:
        creation_flags = 0
        preexec_fn_val = None
        close_fds_val = True

        # Platform-specific process creation
        if sys.platform == "win32":
            creation_flags = subprocess.DETACHED_PROCESS
            close_fds_val = False  # Must be false for redirection on Windows
        elif sys.platform != "win32":
            preexec_fn_val = os.setsid
            close_fds_val = True

        process = subprocess.Popen(
            command,
            stdin=stdin_f,
            stdout=stdout_f,
            stderr=stderr_f,
            creationflags=creation_flags,
            preexec_fn=preexec_fn_val,
            close_fds=close_fds_val,
        )

        with open(pid_file_path, "w", encoding="utf-8") as f:
            f.write(str(process.pid))

        print(f"Process '{' '.join(command)}' started with PID: {process.pid}. PID written to {pid_file_path}")

        # The script exits, but the child process continues.
        # The file handles are duplicated for the child process, so we can close them here.
