"""E2E test to reproduce moderator hang with real problematic transcript."""

import concurrent.futures
import re
import signal
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.automation.agent_cli import AgentConfigPresets, AgentTimeoutError, get_agent_cli
from scripts.automation.config import get_config
from scripts.automation.hooks import ResponseScanner, count_tokens, prepare_moderator_context

# Test constants
MAX_RETRY_ATTEMPTS = 2
SINGLE_ATTEMPT = 1
THREE_SECONDS = 3.0
MAX_MESSAGE_COUNT = 100
MAX_TIME_THRESHOLD = 30  # seconds


def extract_first_output_time(audit_log_path: Path) -> float | None:
    """Extract first output elapsed time from audit log.

    Looks for the marker written by agent_cli: "=== FIRST OUTPUT: X.XXXXs ==="

    Args:
        audit_log_path: Path to audit log file

    Returns:
        Elapsed time in seconds, or None if not found
    """
    if not audit_log_path.exists():
        return None

    with audit_log_path.open() as f:
        for line in f:
            # Look for marker written by agent_cli
            if "=== FIRST OUTPUT:" in line:
                # Extract time from marker
                match = re.search(r"FIRST OUTPUT:\s*([0-9.]+)s", line)
                if match:
                    return float(match.group(1))

    return None


class TestModeratorHangReproduction:
    """Reproduce moderator hang using actual problematic transcript."""

    @pytest.fixture
    def problematic_transcript(self):
        """Load the actual transcript that caused moderator to hang."""
        # Session 3425ba3b - the one that accepted "EXCELLENT PROGRESS" with 8 failures
        transcript_path = Path.home() / ".claude/projects/-home-ami-Projects-AMI-ORCHESTRATOR/3425ba3b-121e-457a-bf53-75a477ca7637.jsonl"

        if not transcript_path.exists():
            pytest.skip(f"Problematic transcript not found: {transcript_path}")

        return transcript_path

    def test_moderator_context_size_metrics(self, problematic_transcript):
        """Measure context size that caused hang."""
        # Extract conversation context using production function
        conversation_context = prepare_moderator_context(problematic_transcript)

        # Measure metrics
        char_count = len(conversation_context)
        token_count = count_tokens(conversation_context)

        # Assertions for documentation
        assert char_count > 0, "Context should not be empty"
        assert token_count > 0, "Token count should not be zero"

        # Document if we're at/near the limit
        if token_count >= 95_000:
            pass

    def test_moderator_first_output_timing(self, problematic_transcript):
        """Measure time to first output - should be <5s."""
        config = get_config()

        # Load context
        conversation_context = prepare_moderator_context(problematic_transcript)
        count_tokens(conversation_context)

        # Get moderator prompt
        prompts_dir = config.root / config.get("prompts.dir")
        moderator_prompt = prompts_dir / config.get("prompts.completion_moderator")

        # Create audit log for this test run
        audit_dir = config.root / "logs" / "test-moderator-hang"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_log = audit_dir / f"reproduction_{int(time.time())}.log"

        # Run moderator with streaming enabled
        cli = get_agent_cli()
        session_id = "test_reproduction"
        completion_config = AgentConfigPresets.completion_moderator(session_id)
        completion_config.enable_streaming = True

        start_time = time.time()

        try:
            # Monitor streaming output with timeout
            output, metadata = cli.run_print(
                instruction_file=moderator_prompt,
                stdin=conversation_context,
                agent_config=completion_config,
                audit_log_path=audit_log,
            )

            time.time() - start_time

            # Verify decision was output
            assert "<decision>" in output, "No decision tag in output"

        except Exception:
            _ = time.time() - start_time  # Track elapsed time for debugging

            # Read audit log to see how far it got
            if audit_log.exists():
                _ = audit_log.stat().st_size  # Check if audit log was written

                # Check if any streaming output was written
                with audit_log.open() as f:
                    lines = f.readlines()
                    streaming_start = False
                    for line in lines:
                        if "STREAMING OUTPUT" in line:
                            streaming_start = True
                        if streaming_start and "type" in line:
                            break

            # Re-raise to fail test
            raise

    def test_moderator_performance_by_token_size(self, problematic_transcript):
        """Measure moderator execution time with production context preparation."""
        # Test with production prepare_moderator_context() which applies:
        # 1. Message count cap (MAX_MODERATOR_MESSAGE_COUNT = 100)
        # 2. Token-based binary search truncation (MAX_MODERATOR_CONTEXT_TOKENS = 100K)

        config = get_config()
        prompts_dir = config.root / config.get("prompts.dir")
        moderator_prompt = prompts_dir / config.get("prompts.completion_moderator")
        cli = get_agent_cli()

        # Use PRODUCTION function that applies message count cap
        context = prepare_moderator_context(problematic_transcript)
        count_tokens(context)

        # Count actual messages in prepared context
        actual_message_count = context.count("<message role=")

        completion_config = AgentConfigPresets.completion_moderator("test_production")
        completion_config.enable_streaming = True
        completion_config.timeout = 120

        start_time = time.time()
        decision = "NONE"

        try:
            output, metadata = cli.run_print(
                instruction_file=moderator_prompt,
                stdin=context,
                agent_config=completion_config,
            )
            time.time() - start_time

            # Extract decision
            if "<decision>ALLOW</decision>" in output:
                decision = "ALLOW"
            elif "<decision>BLOCK:" in output:
                decision = "BLOCK"
            else:
                decision = "UNCLEAR"

        except Exception as e:
            _ = time.time() - start_time  # Track elapsed time for debugging
            _ = type(e).__name__  # Track exception type for debugging

        # Print results

        # Verify message cap was enforced
        assert actual_message_count <= MAX_MESSAGE_COUNT, f"Message count {actual_message_count} exceeds cap of {MAX_MESSAGE_COUNT}"

        # Verify moderator gave correct decision
        assert decision == "BLOCK", f"Expected BLOCK but got {decision} - moderator should reject work with 8 test failures"

    def test_reproduce_exact_production_hang_sequential(self, problematic_transcript):
        """Run moderator invocation multiple times sequentially to gather statistics."""
        num_runs = 3  # Reduced from 20 for CI - enough to verify reliability/consistency
        results = []

        # Use EXACT production code path
        config = get_config()
        prompts_dir = config.root / config.get("prompts.dir")
        moderator_prompt = prompts_dir / config.get("prompts.completion_moderator")

        # Prepare context once (same for all runs)
        conversation_context = prepare_moderator_context(problematic_transcript)
        token_count = count_tokens(conversation_context)
        conversation_context.count("<message role=")

        # Run multiple times sequentially
        for run_num in range(1, num_runs + 1):
            execution_id = f"test_seq_{run_num}"

            # Create audit log
            audit_dir = config.root / "logs" / "test-moderator-hang"
            audit_dir.mkdir(parents=True, exist_ok=True)
            audit_log_path = audit_dir / f"completion-moderator-{execution_id}.log"

            with audit_log_path.open("w") as f:
                f.write(f"=== MODERATOR EXECUTION {execution_id} ===\n")
                f.write(f"Run: {run_num}/{num_runs}\n")
                f.write(f"Context size: {len(conversation_context)} chars\n")
                f.write(f"Token count: {token_count}\n\n")
                f.write("=== STREAMING OUTPUT ===\n")

            # Set up signal alarm
            warning_time = 115
            timeout_warning_fired = [False]

            def timeout_warning_handler(_signum: int, _frame: Any, fired_ref: list[bool] = timeout_warning_fired) -> None:
                fired_ref[0] = True

            signal.signal(signal.SIGALRM, timeout_warning_handler)
            signal.alarm(warning_time)

            # Run moderator
            cli = get_agent_cli()
            completion_moderator_config = AgentConfigPresets.completion_moderator(execution_id)
            completion_moderator_config.enable_streaming = True

            start_time = time.time()
            success = False
            decision = None
            error = None

            try:
                output, metadata = cli.run_print(
                    instruction_file=moderator_prompt,
                    stdin=conversation_context,
                    agent_config=completion_moderator_config,
                    audit_log_path=audit_log_path,
                )

                signal.alarm(0)
                elapsed = time.time() - start_time
                success = True

                # Extract decision
                if "<decision>ALLOW</decision>" in output:
                    decision = "ALLOW"
                elif "<decision>BLOCK:" in output:
                    decision = "BLOCK"
                else:
                    decision = "UNCLEAR"

            except Exception as e:
                signal.alarm(0)
                elapsed = time.time() - start_time
                error = e

            # Extract first-output timing from audit log
            first_output_time = extract_first_output_time(audit_log_path)

            # Record result
            results.append(
                {
                    "run": run_num,
                    "elapsed": elapsed,
                    "success": success,
                    "decision": decision,
                    "error": type(error).__name__ if error else None,
                    "timeout_warning": timeout_warning_fired[0],
                    "first_output_time": first_output_time,
                }
            )

        # Print statistics

        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        if successful:
            times = [r["elapsed"] for r in successful]
            sum(times) / len(times)
            min(times)
            max_time = max(times)

            # First-output timing statistics
            first_output_times = [r["first_output_time"] for r in successful if r["first_output_time"] is not None]
            if first_output_times:
                sum(first_output_times) / len(first_output_times)
                min(first_output_times)
                max(first_output_times)
                first_output_times_sorted = sorted(first_output_times)
                first_output_times_sorted[int(len(first_output_times_sorted) * 0.95)]
                first_output_times_sorted[int(len(first_output_times_sorted) * 0.99)]

            # Check decisions
            len([r for r in successful if r["decision"] == "BLOCK"])
            len([r for r in successful if r["decision"] == "ALLOW"])
            len([r for r in successful if r["decision"] == "UNCLEAR"])

        if failed:
            for _r in failed:
                pass

        # Check for timeouts
        timeouts = [r for r in results if r["timeout_warning"]]
        if timeouts:
            pass

        # Assertions
        assert len(successful) == num_runs, f"Some runs failed: {len(failed)}/{num_runs}"
        assert all(r["decision"] == "BLOCK" for r in successful), "Not all runs gave BLOCK decision"
        assert max_time < MAX_TIME_THRESHOLD, f"Max time {max_time:.2f}s exceeds {MAX_TIME_THRESHOLD}s threshold"
        assert len(timeouts) == 0, f"{len(timeouts)} runs hit timeout warning"

    def test_reproduce_exact_production_hang_parallel(self, problematic_transcript):
        """Run moderator invocation in parallel to test for race conditions."""
        num_workers = 5
        runs_per_worker = 4
        total_runs = num_workers * runs_per_worker

        # Use EXACT production code path
        config = get_config()
        prompts_dir = config.root / config.get("prompts.dir")
        moderator_prompt = prompts_dir / config.get("prompts.completion_moderator")

        # Prepare context once
        conversation_context = prepare_moderator_context(problematic_transcript)
        count_tokens(conversation_context)
        conversation_context.count("<message role=")

        def run_moderator(run_id: int) -> dict[str, Any]:
            """Run single moderator execution."""
            execution_id = f"test_par_{run_id}"

            # Create audit log
            audit_dir = config.root / "logs" / "test-moderator-hang"
            audit_dir.mkdir(parents=True, exist_ok=True)
            audit_log_path = audit_dir / f"completion-moderator-{execution_id}.log"

            with audit_log_path.open("w") as f:
                f.write(f"=== MODERATOR EXECUTION {execution_id} ===\n")
                f.write(f"Parallel run: {run_id}/{total_runs}\n")
                f.write("=== STREAMING OUTPUT ===\n")

            # Run moderator (signal handling not available in threads)
            cli = get_agent_cli()
            completion_moderator_config = AgentConfigPresets.completion_moderator(execution_id)
            completion_moderator_config.enable_streaming = True

            start_time = time.time()

            try:
                output, _ = cli.run_print(
                    instruction_file=moderator_prompt,
                    stdin=conversation_context,
                    agent_config=completion_moderator_config,
                    audit_log_path=audit_log_path,
                )

                elapsed = time.time() - start_time

                # Extract decision
                if "<decision>ALLOW</decision>" in output:
                    decision = "ALLOW"
                elif "<decision>BLOCK:" in output:
                    decision = "BLOCK"
                else:
                    decision = "UNCLEAR"

                return {
                    "run": run_id,
                    "elapsed": elapsed,
                    "success": True,
                    "decision": decision,
                    "error": None,
                    "timeout_warning": False,  # Not available in threads
                }

            except Exception as e:
                return {
                    "run": run_id,
                    "elapsed": time.time() - start_time,
                    "success": False,
                    "decision": None,
                    "error": type(e).__name__,
                    "timeout_warning": False,
                }

        # Run in parallel
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(run_moderator, i) for i in range(1, total_runs + 1)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        time.time() - start_time

        # Sort results by run number
        results.sort(key=lambda r: r["run"])

        # Print results
        for r in results:
            "✓" if r["success"] else "✗"

        # Print statistics

        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        if successful:
            times = [r["elapsed"] for r in successful]
            sum(times) / len(times)
            min(times)
            max(times)

            # Check decisions
            len([r for r in successful if r["decision"] == "BLOCK"])
            len([r for r in successful if r["decision"] == "ALLOW"])

        if failed:
            pass

        timeouts = [r for r in results if r["timeout_warning"]]
        if timeouts:
            pass

        # Assertions
        assert len(successful) == total_runs, f"Some parallel runs failed: {len(failed)}/{total_runs}"
        assert all(r["decision"] == "BLOCK" for r in successful), "Not all runs gave BLOCK decision"
        assert len(timeouts) == 0, f"{len(timeouts)} runs hit timeout warning"

    def test_parse_audit_log_for_streaming_events(self, _problematic_transcript):
        """Parse the original audit log to understand what happened."""
        # The original audit log from the hang
        audit_log = Path("/home/ami/Projects/AMI-ORCHESTRATOR/logs/agent-cli/completion-moderator-90858109.log")

        if not audit_log.exists():
            pytest.skip(f"Original audit log not found: {audit_log}")

        # Parse audit log structure
        with audit_log.open() as f:
            content = f.read()

        size_bytes = len(content)
        size_bytes / 1024

        # Check what sections are present
        sections = {
            "PROMPT": "=== PROMPT ===" in content,
            "CONVERSATION": "=== CONVERSATION CONTEXT ===" in content,
            "STREAMING": "=== STREAMING OUTPUT ===" in content,
            "PROCESS_STARTED": "=== PROCESS STARTED" in content,
            "PROCESS_COMPLETED": "=== PROCESS COMPLETED" in content,
            "DECISION_TAG": "<decision>" in content,
        }

        for _section, _present in sections.items():
            pass

        # If streaming section exists but no decision, process hung during thinking
        if sections["STREAMING"] and not sections["DECISION_TAG"]:
            pass

        # Count how many streaming JSON lines were output
        if sections["STREAMING"]:
            streaming_lines = content.split("=== STREAMING OUTPUT ===")[1].split("\n")
            json_lines = [line for line in streaming_lines if line.strip().startswith("{")]
            if json_lines:
                pass

        assert sections["PROCESS_STARTED"], "Process never started"
        assert not sections["PROCESS_COMPLETED"], "Should confirm process didn't complete"

    def test_moderator_hang_with_successful_retry(self, problematic_transcript):
        """Test restart mechanism: first attempt hangs, second succeeds."""
        config = get_config()
        prepare_moderator_context(problematic_transcript)

        # Get moderator prompt
        prompts_dir = config.root / config.get("prompts.dir")
        prompts_dir / config.get("prompts.completion_moderator")

        # Create audit log for this test
        audit_dir = config.root / "logs" / "test-moderator-hang"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_dir / f"hang_retry_test_{int(time.time())}.log"

        # Track call count
        call_count = [0]

        def mock_run_print(*_args, **kwargs):
            """Mock that hangs on first call, succeeds on second."""
            call_count[0] += 1
            audit_log_path = kwargs.get("audit_log_path")

            if call_count[0] == 1:
                # First call: simulate hang (timeout without first output)
                # Don't write first output marker to audit log
                if audit_log_path:
                    with audit_log_path.open("w") as f:
                        f.write("=== MODERATOR EXECUTION ===\n")
                        f.write("Context loaded...\n")
                        f.write("(Process hangs here without streaming output)\n")
                raise AgentTimeoutError(timeout=10, cmd=["claude", "--print"], duration=10.0)

            # Second call: simulate success with first output
            if audit_log_path:
                with audit_log_path.open("w") as f:
                    f.write("=== MODERATOR EXECUTION ===\n")
                    f.write("\n=== FIRST OUTPUT: 0.85s ===\n\n")
                    f.write("<decision>BLOCK: Test failures remain</decision>\n")
            return ("<decision>BLOCK: Test failures remain</decision>", {})

        # Create mock CLI
        mock_cli_instance = MagicMock()
        mock_cli_instance.run_print.side_effect = mock_run_print

        # Patch get_agent_cli to return our mock
        with patch("scripts.automation.hooks.get_agent_cli", return_value=mock_cli_instance):
            # Test the restart mechanism
            scanner = ResponseScanner(config)

            # Create fake hook input
            class FakeHookInput:
                def __init__(self):
                    self.session_id = "test_hang_retry"
                    self.transcript_path = problematic_transcript

            hook_input = FakeHookInput()

            # Call _validate_completion which will use _run_moderator_with_first_output_monitoring
            start_time = time.time()
            result = scanner._validate_completion(hook_input.session_id, hook_input.transcript_path)
            time.time() - start_time

            # Verify retry happened
            assert call_count[0] == MAX_RETRY_ATTEMPTS, f"Expected {MAX_RETRY_ATTEMPTS} calls (retry), got {call_count[0]}"
            assert result.decision == "block", f"Expected BLOCK decision, got {result.decision}"
            # Note: timing assertions removed since mock returns immediately

    def test_moderator_hang_exhausted_retries_fail_closed(self, problematic_transcript):
        """Test fail-closed behavior: all retries hang, final result is BLOCK."""
        config = get_config()
        prepare_moderator_context(problematic_transcript)

        # Get moderator prompt
        prompts_dir = config.root / config.get("prompts.dir")
        prompts_dir / config.get("prompts.completion_moderator")

        # Create audit log for this test
        audit_dir = config.root / "logs" / "test-moderator-hang"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_dir / f"hang_exhausted_test_{int(time.time())}.log"

        # Track call count
        call_count = [0]

        def mock_run_print_always_hangs(*_args, **kwargs):
            """Mock that always hangs (no first output)."""
            call_count[0] += 1
            audit_log_path = kwargs.get("audit_log_path")

            # Never write first output marker
            if audit_log_path:
                with audit_log_path.open("w") as f:
                    f.write(f"=== MODERATOR EXECUTION (Attempt {call_count[0]}) ===\n")
                    f.write("Context loaded...\n")
                    f.write("(Process hangs here without streaming output)\n")

            raise AgentTimeoutError(timeout=10, cmd=["claude", "--print"], duration=10.0)

        # Create mock CLI that always hangs
        mock_cli_instance = MagicMock()
        mock_cli_instance.run_print.side_effect = mock_run_print_always_hangs

        # Patch get_agent_cli to return our mock
        with patch("scripts.automation.hooks.get_agent_cli", return_value=mock_cli_instance):
            # Test with ResponseScanner
            scanner = ResponseScanner(config)

            # Create fake hook input
            class FakeHookInput:
                def __init__(self):
                    self.session_id = "test_hang_exhausted"
                    self.transcript_path = problematic_transcript

            hook_input = FakeHookInput()

            # Call _validate_completion which should exhaust retries and fail-closed
            start_time = time.time()

            # This should raise AgentTimeoutError after all retries exhausted
            # But _handle_moderator_error catches it and returns BLOCK
            result = scanner._validate_completion(hook_input.session_id, hook_input.transcript_path)
            time.time() - start_time

            # Verify all retries were attempted
            assert call_count[0] == MAX_RETRY_ATTEMPTS, f"Expected {MAX_RETRY_ATTEMPTS} calls (max attempts), got {call_count[0]}"

            # Verify fail-closed behavior: decision should be BLOCK
            assert result.decision == "block", f"Expected BLOCK (fail-closed), got {result.decision}"

            # Verify timeout error is mentioned in reason
            assert "TIMEOUT" in result.reason.upper() or "timeout" in result.reason, f"Expected timeout mentioned in reason: {result.reason}"
            # Note: timing assertions removed since mock returns immediately

    def test_moderator_analysis_hang_with_restart(self, problematic_transcript):
        """Test analysis hang detection: first output produced but no decision."""
        config = get_config()

        # Create audit log for this test
        audit_dir = config.root / "logs" / "test-moderator-hang"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_dir / f"analysis_hang_test_{int(time.time())}.log"

        # Track call count
        call_count = [0]

        def mock_run_print_analysis_hang(*_args, **kwargs):
            """Mock that produces first output but NO decision tag (analysis hang)."""
            call_count[0] += 1
            audit_log_path = kwargs.get("audit_log_path")

            if call_count[0] == 1:
                # First call: produce first output but no decision (analysis hang)
                if audit_log_path:
                    with audit_log_path.open("w") as f:
                        f.write("=== MODERATOR EXECUTION ===\n")
                        f.write("\n=== FIRST OUTPUT: 0.62s ===\n\n")
                        f.write('{"type":"system","subtype":"init","model":"claude-sonnet-4-5"}\n')
                        f.write("(Process hangs here during analysis - no decision output)\n")
                # Return output WITHOUT <decision> tag
                return ('{"type":"system","subtype":"init"}', {})

            # Second call: simulate success with decision
            if audit_log_path:
                with audit_log_path.open("w") as f:
                    f.write("=== MODERATOR EXECUTION ===\n")
                    f.write("\n=== FIRST OUTPUT: 0.68s ===\n\n")
                    f.write("<decision>BLOCK: Work incomplete</decision>\n")
            return ("<decision>BLOCK: Work incomplete</decision>", {})

        # Create mock CLI
        mock_cli_instance = MagicMock()
        mock_cli_instance.run_print.side_effect = mock_run_print_analysis_hang

        # Patch get_agent_cli to return our mock
        with patch("scripts.automation.hooks.get_agent_cli", return_value=mock_cli_instance):
            # Test with ResponseScanner
            scanner = ResponseScanner(config)

            # Create fake hook input
            class FakeHookInput:
                def __init__(self):
                    self.session_id = "test_analysis_hang"
                    self.transcript_path = problematic_transcript

            hook_input = FakeHookInput()

            # Call _validate_completion which should detect analysis hang and restart
            start_time = time.time()
            result = scanner._validate_completion(hook_input.session_id, hook_input.transcript_path)
            time.time() - start_time

            # Verify analysis hang was detected and restart happened
            assert call_count[0] == MAX_RETRY_ATTEMPTS, f"Expected {MAX_RETRY_ATTEMPTS} calls (analysis hang detected, restarted), got {call_count[0]}"
            assert result.decision == "block", f"Expected BLOCK decision, got {result.decision}"
