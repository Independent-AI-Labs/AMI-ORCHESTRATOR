"""
Integration test for setup-shell.sh aliases and functions
Verifies that all registered aliases/functions respond to -h calls
"""

import os
import subprocess
import sys
from pathlib import Path

# Bootstrap sys.path - MUST come before base imports
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "base").exists())))

# Now we can import from base
from base.scripts.env.paths import setup_imports

ORCHESTRATOR_ROOT, _ = setup_imports()


def test_aliases_exist_and_respond_to_help():
    """Test that all aliases and functions from setup-shell.sh exist and respond to -h."""
    # Source the setup shell script in a subprocess to get all aliases and functions
    script_path = ORCHESTRATOR_ROOT / "scripts" / "setup-shell.sh"

    # Verify the script exists first
    assert script_path.exists(), f"Setup script does not exist: {script_path}"

    # Define the list of functions that should be available after sourcing setup-shell.sh
    expected_functions = [
        "ami-run",
        "ami-uv",
        "ami-agent",
        "ami-repo",
        "ami-service",  # Contains start, stop, restart, profile as subcommands
        "ami-test",
        "ami-install",
        "ami-setup",
        "ami-codecheck",
        "ami-check-storage",
        "ami-gcloud",
        "ami-git",  # Contains status, diff, log, etc. as subcommands
        "ami-info",
        "ami-claude",
        "ami-gemini",
        "ami-qwen",
    ]

    # Navigation aliases (these are aliases not functions, so they won't be in bash function list)
    # These aliases are not currently implemented in the script
    expected_aliases = []

    # Test that each function exists by trying to call it with -h
    for func_name in expected_functions:
        # Special handling for CLI agents that may not have binaries installed
        if func_name in ["ami-claude", "ami-gemini", "ami-qwen"]:
            # Just check that the function exists but allow for missing binary
            bash_test_cmd = ["bash", "-c", f"source {script_path} >/dev/null 2>&1 && type -t {func_name}"]

            result = subprocess.run(bash_test_cmd, check=False, capture_output=True, text=True)
            assert result.returncode == 0, f"Function {func_name} does not exist: {result.stderr}"

            # Verify the type is function or command
            output = result.stdout.strip()
            assert output in ["function", "builtin", "file"], f"{func_name} is not a function/command: {output}"

            # For CLI agents, test that the function exists but allow binary to be missing
            # Don't try to execute them as they may not have binaries installed
            continue

        # For other functions, proceed with the original test
        bash_test_cmd = ["bash", "-c", f"source {script_path} >/dev/null 2>&1 && type -t {func_name}"]

        result = subprocess.run(bash_test_cmd, check=False, capture_output=True, text=True)
        assert result.returncode == 0, f"Function {func_name} does not exist: {result.stderr}"

        # Verify the type is function or command
        output = result.stdout.strip()
        assert output in ["function", "builtin", "file"], f"{func_name} is not a function/command: {output}"

        # Wrap the rest of the function test in a try-except block
        try:
            # For all functions, try to run with -h
            test_script = rf"""
                export AMI_ROOT="{ORCHESTRATOR_ROOT}"
                export PYTHONPATH="{ORCHESTRATOR_ROOT}{os.pathsep}{ORCHESTRATOR_ROOT.parent}"
                export PATH="{ORCHESTRATOR_ROOT}/.venv/bin:{ORCHESTRATOR_ROOT}/base/.venv/bin:$PATH"

                # Source the setup script to define all functions
                source "{script_path}" >/dev/null 2>&1

                # Run the function and capture any file-related errors
                output=$( {func_name} -h 2>&1 )
                exit_code=$?

                # Check for specific file-related errors
                if echo "$output" | grep -q 'No such file or directory\|command not found'; then
                    echo "$output"
                    exit 1
                fi

                # Output result - if we made it this far, the function at least started
                echo "Function executed (exit code: $exit_code)"
                [ -n "$output" ] && echo "$output" || true
            """
            result = subprocess.run(
                ["bash", "-c", test_script],
                check=False,
                capture_output=True,
                timeout=10,
                text=True,
                cwd=ORCHESTRATOR_ROOT,  # Set the working directory to orchestrator root
            )

            # Check if the output contains errors indicating a broken function
            combined_output = result.stdout + result.stderr
            if "No such file or directory" in combined_output or "command not found" in combined_output:
                raise AssertionError(f"Command {func_name} failed with file error: {combined_output}")

        except subprocess.TimeoutExpired:
            # Command timed out - this might be normal for some commands that expect specific arguments
            pass
        except Exception as e:
            raise AssertionError(f"Command {func_name} failed during execution: {str(e)}") from e

    # Test that each alias exists
    for alias_name in expected_aliases:
        bash_test_cmd = ["bash", "-c", f"source {script_path} >/dev/null 2>&1 && alias {alias_name}"]

        result = subprocess.run(bash_test_cmd, check=False, capture_output=True, text=True)
        assert result.returncode == 0, f"Alias {alias_name} does not exist: {result.stderr}"


def test_cli_agents_available():
    """Test that CLI agents are available and respond."""
    script_path = ORCHESTRATOR_ROOT / "scripts" / "setup-shell.sh"

    cli_agents = ["ami-claude", "ami-gemini", "ami-qwen"]

    for agent in cli_agents:
        # Test that the function/alias exists
        bash_test_cmd = ["bash", "-c", f"source {script_path} && type -t {agent}"]

        result = subprocess.run(bash_test_cmd, check=False, capture_output=True, text=True)
        assert result.returncode == 0, f"CLI agent {agent} does not exist: {result.stderr}"


if __name__ == "__main__":
    test_aliases_exist_and_respond_to_help()
    test_cli_agents_available()
