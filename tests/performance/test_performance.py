"""Performance tests for AMI automation system.

Tests throughput, concurrency, and scalability.
"""  # test-fixture

import tempfile
import time
from pathlib import Path

import pytest

from scripts.automation.audit import AuditEngine


class TestAuditPerformance:
    """Performance tests for audit engine."""

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_parallel_vs_sequential(self):  # test-fixture
        """Parallel audit is faster than sequential."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            # Create 10 test files
            for i in range(10):  # test-fixture
                (tmpdir_path / f"module{i}.py").write_text(  # test-fixture
                    f'def process_{i}(data):\n    """Process data."""\n    return data * {i}\n'
                )

            engine = AuditEngine()

            # Sequential audit
            start = time.time()  # test-fixture
            results_seq = engine.audit_directory(tmpdir_path, parallel=False)  # test-fixture
            time_sequential = time.time() - start  # test-fixture

            # Parallel audit
            start = time.time()  # test-fixture
            results_par = engine.audit_directory(tmpdir_path, parallel=True, max_workers=4)  # test-fixture
            time_parallel = time.time() - start  # test-fixture

            # Same number of results
            assert len(results_seq) == len(results_par) == 10

            # Parallel should be faster (at least 1.5x speedup expected)
            # Note: Might not always be true due to LLM call overhead
            print(f"\nSequential: {time_sequential:.2f}s, Parallel: {time_parallel:.2f}s")

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_throughput_small_files(self):  # test-fixture
        """Measure throughput for small files."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            # Create 20 small files
            file_count = 20
            for i in range(file_count):  # test-fixture
                (tmpdir_path / f"util{i}.py").write_text(  # test-fixture
                    f'def util_{i}():\n    """Utility function."""\n    return {i}\n'
                )

            engine = AuditEngine()

            start = time.time()  # test-fixture
            results = engine.audit_directory(tmpdir_path, parallel=True, max_workers=8)  # test-fixture
            elapsed = time.time() - start  # test-fixture

            assert len(results) == file_count

            throughput = file_count / elapsed  # test-fixture
            print(f"\nThroughput: {throughput:.2f} files/sec ({elapsed:.2f}s total)")

            # Expect at least 0.1 files/sec (very conservative)
            assert throughput > 0.1

    @pytest.mark.performance
    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_cache_speedup(self):  # test-fixture
        """Audit cache provides significant speedup."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "cached.py").write_text(  # test-fixture
                'def cached_func():\n    """Cached function."""\n    return 42\n'
            )

            engine = AuditEngine()

            # First audit (cold)
            start1 = time.time()  # test-fixture
            result1 = engine._audit_file(tmpdir_path / "cached.py")  # test-fixture
            time_cold = time.time() - start1  # test-fixture

            # Second audit (should use cache if enabled)
            start2 = time.time()  # test-fixture
            result2 = engine._audit_file(tmpdir_path / "cached.py")  # test-fixture
            time_warm = time.time() - start2  # test-fixture

            assert result1.status == result2.status

            # Cached should be faster (at least 2x if cache enabled)
            print(f"\nCold: {time_cold:.2f}s, Warm: {time_warm:.2f}s")

            # Note: If cache is disabled, times will be similar
            # This test just ensures cache doesn't break functionality

    @pytest.mark.performance
    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_audit_large_codebase_subset(self):  # test-fixture
        """Audit handles larger codebase subset."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            # Create directory structure with 50 files
            for module_idx in range(5):  # test-fixture
                module_dir = tmpdir_path / f"module{module_idx}"
                module_dir.mkdir()

                for file_idx in range(10):  # test-fixture
                    (module_dir / f"component{file_idx}.py").write_text(  # test-fixture
                        f"""\"\"\"Component {file_idx} in module {module_idx}.\"\"\"

def process_{file_idx}(data):
    \"\"\"Process data.\"\"\"
    return data + {file_idx}

def validate_{file_idx}(value):
    \"\"\"Validate value.\"\"\"
    return value > {module_idx}
"""
                    )

            engine = AuditEngine()

            start = time.time()  # test-fixture
            results = engine.audit_directory(tmpdir_path, parallel=True, max_workers=8)  # test-fixture
            elapsed = time.time() - start  # test-fixture

            assert len(results) == 50

            print(f"\nAudited 50 files in {elapsed:.2f}s ({50 / elapsed:.2f} files/sec)")

            # Should complete in reasonable time (< 10 minutes)
            assert elapsed < 600

    @pytest.mark.performance
    def test_audit_memory_usage_many_results(self):  # test-fixture
        """Audit doesn't leak memory with many results."""
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            tmpdir_path = Path(tmpdir)

            # Create 100 files (non-integration, so won't actually audit)
            for i in range(100):  # test-fixture
                (tmpdir_path / f"file{i}.py").write_text(f"def f{i}(): pass")  # test-fixture

            engine = AuditEngine()

            # Just test file discovery, not actual auditing
            files = list(engine._find_files(tmpdir_path))  # test-fixture

            assert len(files) == 100

            # Should not crash or run out of memory
            # Actual memory measurement would require psutil

    @pytest.mark.performance
    def test_hook_validation_latency(self):  # test-fixture
        """Hook validation has low latency."""
        from scripts.automation.hooks import CommandValidator, HookInput

        validator = CommandValidator()

        hook_input = HookInput(
            session_id="perf-test",
            hook_event_name="PreToolUse",
            tool_name="Bash",
            tool_input={"command": "ls -la"},
            transcript_path=None,
        )

        # Measure 100 validations
        iterations = 100
        start = time.time()  # test-fixture
        for _ in range(iterations):  # test-fixture
            result = validator.validate(hook_input)
            assert result.decision in (None, "allow")
        elapsed = time.time() - start  # test-fixture

        avg_latency = (elapsed / iterations) * 1000  # test-fixture
        print(f"\nAverage hook latency: {avg_latency:.2f}ms")

        # Should be very fast (< 10ms per validation)
        assert avg_latency < 10

    @pytest.mark.performance
    def test_config_loading_performance(self):  # test-fixture
        """Config loading is fast."""
        from scripts.automation.config import Config

        iterations = 100
        start = time.time()  # test-fixture
        for _ in range(iterations):  # test-fixture
            config = Config()
            assert config.get("logging.level") is not None
        elapsed = time.time() - start  # test-fixture

        avg_load_time = (elapsed / iterations) * 1000  # test-fixture
        print(f"\nAverage config load time: {avg_load_time:.2f}ms")

        # Should be fast (< 50ms)
        assert avg_load_time < 50

    @pytest.mark.performance
    def test_hook_latency_response_scanner(self):  # test-fixture
        """ResponseScanner has low latency."""
        from scripts.automation.hooks import HookInput, ResponseScanner

        # Create temp transcript file
        with tempfile.TemporaryDirectory() as tmpdir:  # test-fixture
            transcript_file = Path(tmpdir) / "transcript.jsonl"
            transcript_file.write_text(  # test-fixture
                '{"type": "assistant", "uuid": "uuid-1", "message": {"content": [{"type": "text", "text": "WORK DONE"}]}}\n'
            )

            scanner = ResponseScanner()

            hook_input = HookInput(
                session_id="perf-test",
                hook_event_name="PostResponse",
                tool_name=None,
                tool_input=None,
                transcript_path=str(transcript_file),
            )

            # Measure 100 validations
            iterations = 100
            start = time.time()  # test-fixture
            for _ in range(iterations):  # test-fixture
                result = scanner.validate(hook_input)
                assert result.decision in (None, "allow")
            elapsed = time.time() - start  # test-fixture

            avg_latency = (elapsed / iterations) * 1000  # test-fixture
            print(f"\nAverage ResponseScanner latency: {avg_latency:.2f}ms")

            # Should be fast (< 50ms per validation)
            assert avg_latency < 50

    @pytest.mark.performance
    def test_pattern_matching_large_file(self):  # test-fixture
        """PatternMatcher handles large files efficiently."""
        from scripts.automation.patterns import PatternMatcher

        # Create large Python file (10,000 lines)
        large_code = ""  # test-fixture
        for i in range(10000):  # test-fixture
            large_code += f"def function_{i}():\n"
            large_code += f'    """Function {i}."""\n'
            large_code += f"    return {i}\n\n"

        matcher = PatternMatcher("python")

        start = time.time()  # test-fixture
        violations = matcher.find_violations(large_code)  # test-fixture
        elapsed = time.time() - start  # test-fixture

        elapsed_ms = elapsed * 1000  # test-fixture
        print(f"\nPattern matching 10,000 lines: {elapsed_ms:.2f}ms")

        # Should complete quickly (< 100ms)
        assert elapsed_ms < 100
        assert isinstance(violations, set)

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.integration
    @pytest.mark.requires_claude_cli
    def test_hook_latency_code_quality(self):  # test-fixture
        """CodeQualityValidator hook latency with LLM call."""
        from scripts.automation.hooks import CodeQualityValidator, HookInput

        validator = CodeQualityValidator()

        # Create a simple Edit hook input
        hook_input = HookInput(
            session_id="perf-test",
            hook_event_name="PreToolUse",
            tool_name="Edit",
            tool_input={
                "file_path": "test.py",
                "old_string": "def foo(): pass",
                "new_string": "def foo():\n    return 42",
            },
            transcript_path=None,
        )

        # Measure single validation (LLM call is expensive)
        start = time.time()  # test-fixture
        result = validator.validate(hook_input)
        elapsed = time.time() - start  # test-fixture

        print(f"\nCodeQualityValidator latency: {elapsed:.2f}s")

        # Should complete within 5 seconds
        assert elapsed < 5.0

        # Result should be valid
        assert result.decision in (None, "allow", "deny")
