"""Integration tests for agent CLI timeout with real processes.

These tests use actual hanging processes to verify that the timeout
mechanism works correctly in production scenarios.
"""

import time

import pytest

from scripts.automation.agent_cli import AgentConfig, AgentTimeoutError, ClaudeAgentCLI


@pytest.mark.integration
class TestRealProcessTimeout:
    """Tests with actual hanging processes to verify timeout enforcement."""

    def test_real_timeout_with_sleep_process(self, tmp_path):
        """Real process that sleeps longer than timeout is terminated."""
        # Create a test script that sleeps
        test_script = tmp_path / "hang_test.py"
        test_script.write_text(
            "#!/usr/bin/env python3\nimport time\nprint('Starting sleep...')\ntime.sleep(300)  # 5 minute sleep\nprint('Should never reach here')\n"
        )
        test_script.chmod(0o755)

        # Create a fake Claude CLI that just runs the hanging script
        fake_claude = tmp_path / "fake_claude"
        fake_claude.write_text(f"#!/usr/bin/env python3\nimport subprocess\nimport sys\nsubprocess.run(['{test_script}'])\n")
        fake_claude.chmod(0o755)

        # Configure agent to use fake CLI with short timeout
        cli = ClaudeAgentCLI()
        cli.config._data["claude_cli"] = {"command": str(fake_claude)}

        config = AgentConfig(model="test", timeout=2)  # 2 second timeout
        start = time.time()

        # Verify timeout exception is raised
        with pytest.raises(AgentTimeoutError) as exc_info:
            cli.run_print(instruction="test", agent_config=config)

        duration = time.time() - start

        # Verify timeout was enforced (within 0.5s tolerance)
        assert 1.5 <= duration <= 2.5, f"Timeout took {duration}s, expected ~2s"

        # Verify exception has correct timeout value
        assert exc_info.value.timeout == 2
        assert exc_info.value.duration is not None
        assert 1.5 <= exc_info.value.duration <= 2.5

    def test_fast_process_completes_before_timeout(self, tmp_path):
        """Process that completes quickly doesn't trigger timeout."""
        # Create a script that finishes quickly
        fast_script = tmp_path / "fast.py"
        fast_script.write_text("#!/usr/bin/env python3\nprint('PASS')\n")
        fast_script.chmod(0o755)

        fake_claude = tmp_path / "fake_claude"
        fake_claude.write_text(f"#!/usr/bin/env python3\nimport subprocess\nsubprocess.run(['{fast_script}'])\n")
        fake_claude.chmod(0o755)

        # Run with generous timeout
        cli = ClaudeAgentCLI()
        cli.config._data["claude_cli"] = {"command": str(fake_claude)}

        config = AgentConfig(model="test", timeout=10)
        start = time.time()

        # Should complete without timeout
        result = cli.run_print(instruction="test", agent_config=config)

        duration = time.time() - start

        # Verify completed quickly
        assert duration < 2.0, f"Fast process took {duration}s"
        assert "PASS" in result

    def test_timeout_duration_tracking_accuracy(self, tmp_path):
        """Timeout exception contains accurate duration measurement."""
        # Create script that sleeps exactly 5 seconds
        sleep_script = tmp_path / "sleep5.py"
        sleep_script.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(5)\n")
        sleep_script.chmod(0o755)

        fake_claude = tmp_path / "fake_claude"
        fake_claude.write_text(f"#!/usr/bin/env python3\nimport subprocess\nsubprocess.run(['{sleep_script}'])\n")
        fake_claude.chmod(0o755)

        # Set timeout to 3 seconds (will fire during 5s sleep)
        cli = ClaudeAgentCLI()
        cli.config._data["claude_cli"] = {"command": str(fake_claude)}

        config = AgentConfig(model="test", timeout=3)

        with pytest.raises(AgentTimeoutError) as exc_info:
            cli.run_print(instruction="test", agent_config=config)

        # Duration should be ~3 seconds (the timeout value)
        assert exc_info.value.duration is not None
        assert 2.5 <= exc_info.value.duration <= 3.5, f"Duration {exc_info.value.duration} outside expected range"
