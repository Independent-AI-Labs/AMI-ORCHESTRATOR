"""End-to-end tests for completion moderator using real transcript fixtures.

These tests use REAL conversation segments extracted from actual Claude Code sessions
to verify that the completion moderator validates work correctly and doesn't hallucinate
requirements from conversation summaries or historical context.

Fixtures are raw JSONL transcripts truncated AT "WORK DONE" marker (inclusive).
Tests use the SAME extraction logic as the real moderator.

Test categories:
1. Infrastructure tests: Verify extraction/formatting (fast)
2. Moderator behavior tests: Actually run moderator agent (slow, marked with @pytest.mark.slow)
"""

import json
from pathlib import Path

import pytest

from scripts.automation.agent_cli import AgentConfigPresets, get_agent_cli
from scripts.automation.hooks import prepare_moderator_context


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to test fixtures directory containing real transcript segments."""
    return Path(__file__).parent / "fixtures" / "transcripts"


@pytest.fixture
def orchestrator_root() -> Path:
    """Path to orchestrator root directory."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def moderator_prompt(orchestrator_root: Path) -> Path:
    """Path to completion moderator prompt file."""
    return orchestrator_root / "scripts" / "config" / "prompts" / "completion_moderator.txt"


class TestTranscriptContextExtraction:
    """Test that we correctly extract context from real transcripts.

    These tests verify that prepare_moderator_context() function
    properly extracts conversation context that will be sent to the completion moderator.
    """

    def test_extract_context_from_real_fixture(self, fixtures_dir: Path) -> None:
        """Extract context from first real transcript fixture using production function."""
        fixture_files = sorted(fixtures_dir.glob("real_case_*.jsonl"))
        assert len(fixture_files) > 0, "No real transcript fixtures found"

        fixture = fixture_files[0]

        # Use PRODUCTION function that applies 100K token truncation
        context = prepare_moderator_context(fixture)

        # Verify we got context
        assert len(context) > 0, f"No context extracted from {fixture.name}"
        assert "<message role=" in context, "Context should contain formatted messages"

    def test_format_messages_for_moderator(self, fixtures_dir: Path) -> None:
        """Format extracted messages for moderator prompt using production function."""
        fixture_files = sorted(fixtures_dir.glob("real_case_*.jsonl"))
        assert len(fixture_files) > 0, "No real transcript fixtures found"

        fixture = fixture_files[0]

        # Use PRODUCTION function
        context = prepare_moderator_context(fixture)

        # Verify formatting
        assert isinstance(context, str), "Context should be string"
        assert len(context) > 0, "Context should not be empty"
        assert "<message role=" in context, "Context should contain message tags"

    def test_extract_from_multiple_fixtures(self, fixtures_dir: Path) -> None:
        """Verify all fixtures can be processed using production function."""
        fixture_files = sorted(fixtures_dir.glob("real_case_*.jsonl"))
        assert len(fixture_files) >= 1, f"Expected at least 1 fixture, found {len(fixture_files)}"

        for fixture in fixture_files:
            # Should not raise exceptions
            context = prepare_moderator_context(fixture)

            # Each fixture should have extracted context
            assert len(context) > 0, f"No context from {fixture.name}"
            assert "<message role=" in context, f"Invalid context from {fixture.name}"

    def test_fixture_contains_valid_json(self, fixtures_dir: Path) -> None:
        """Verify fixtures contain valid JSONL format."""
        fixture_files = sorted(fixtures_dir.glob("real_case_*.jsonl"))
        assert len(fixture_files) > 0, "No real transcript fixtures found"

        for fixture in fixture_files:
            with fixture.open(encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) > 0, f"Empty fixture file: {fixture.name}"

            # Each line should be valid JSON
            for i, line in enumerate(lines):
                try:
                    msg = json.loads(line)
                    assert isinstance(msg, dict), f"Line {i} is not a dict: {fixture.name}"
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON at line {i} in {fixture.name}: {e}")


class TestModeratorValidationScenarios:
    """Test moderator validation on real transcript segments.

    These tests document expected moderator behavior:
    - ALLOW: Work complete for latest user request
    - BLOCK: Work incomplete, hallucinated requirements, or invalid FEEDBACK

    Note: These tests verify fixture structure and document expected behavior.
    Full moderator validation requires agent execution which is tested separately.
    """

    def test_fixture_represents_work_complete_scenario(self, fixtures_dir: Path) -> None:
        """Fixture should represent a scenario where work is actually complete.

        Expected moderator behavior: ALLOW
        - User made a specific request
        - Assistant completed that request
        - No hallucination from conversation context
        """
        fixture = fixtures_dir / "real_case_1_0e02ced7-827.jsonl"
        if not fixture.exists():
            pytest.skip(f"Fixture not found: {fixture.name}")

        context = prepare_moderator_context(fixture)

        # Verify we got valid context
        assert len(context) > 0, "Should have extracted context"
        assert "<message role=" in context, "Should have formatted messages"

        # Document expected behavior
        # Moderator should validate ONLY the latest user request
        # Should NOT hallucinate requirements from earlier conversation context

    def test_all_fixtures_extractable_by_moderator_function(self, fixtures_dir: Path) -> None:
        """All fixtures should be processable by production moderator function."""
        fixture_files = sorted(fixtures_dir.glob("real_case_*.jsonl"))

        for fixture in fixture_files:
            # This is the EXACT function the moderator uses
            context = prepare_moderator_context(fixture)

            # Should extract valid context
            assert len(context) > 0, f"Failed to extract from {fixture.name}"
            assert "<message role=" in context, f"Failed to format {fixture.name}"


class TestModeratorHallucinationPrevention:
    """Test cases for preventing moderator hallucinations.

    Documents scenarios where moderator might incorrectly validate against
    historical context instead of latest request.
    """

    def test_fixture_documents_hallucination_risk(self, fixtures_dir: Path) -> None:
        """Fixtures should represent scenarios with hallucination risk.

        Hallucination pattern:
        - Conversation summary mentions topic X
        - User's LATEST request is about topic Y
        - Moderator should validate Y, NOT X

        Example:
        - Summary: "Fixed mypy errors earlier"
        - Latest request: "Add docstrings"
        - Moderator should validate docstrings were added
        - Should NOT require mypy fixes (that was historical context)
        """
        fixture_files = sorted(fixtures_dir.glob("real_case_*.jsonl"))
        assert len(fixture_files) > 0, "Need fixtures to test"

        # All fixtures extracted from real sessions provide test cases
        # for moderator validation behavior
        for fixture in fixture_files:
            context = prepare_moderator_context(fixture)

            # Verify we have valid context
            assert len(context) > 0, f"No context from {fixture.name}"
            assert "<message role=" in context, f"Invalid context from {fixture.name}"

            # Document: Moderator should analyze FINAL messages in context
            # NOT hallucinate from historical context


@pytest.mark.slow
class TestModeratorAgentBehavior:
    """Test actual moderator agent decisions on real transcripts.

    These tests invoke the full moderator agent, so they are slow and marked with @pytest.mark.slow.
    Run with: pytest -v -m slow tests/integration/test_completion_moderator_e2e.py

    All fixtures are real cases where:
    - Assistant completed the requested work
    - Assistant output "WORK DONE"
    - Moderator INCORRECTLY blocked (false positive)

    Expected behavior: Moderator should output ALLOW (work is complete)
    """

    def _run_moderator(self, fixture_path: Path, moderator_prompt: Path, orchestrator_root: Path) -> str:
        """Run moderator agent on a fixture and return output.

        Args:
            fixture_path: Path to transcript fixture
            moderator_prompt: Path to moderator prompt file
            orchestrator_root: Path to orchestrator root

        Returns:
            Moderator agent output
        """
        # Extract and format messages using PRODUCTION function (hooks.py:prepare_moderator_context)
        # This applies token truncation via binary search if needed
        conversation_context = prepare_moderator_context(fixture_path)

        # Run moderator agent using EXACT same method as production
        cli = get_agent_cli()
        return cli.run_print(
            instruction_file=moderator_prompt,
            stdin=conversation_context,
            agent_config=AgentConfigPresets.completion_moderator(session_id="test-moderator-e2e"),
        )

    def test_moderator_allows_completed_work_fixture_1(self, fixtures_dir: Path, moderator_prompt: Path, orchestrator_root: Path) -> None:
        """Moderator should ALLOW work that is legitimately complete (fixture 1)."""
        fixture = fixtures_dir / "real_case_1_0e02ced7-827.jsonl"
        if not fixture.exists():
            pytest.skip(f"Fixture not found: {fixture.name}")

        output = self._run_moderator(fixture, moderator_prompt, orchestrator_root)

        assert "ALLOW" in output, f"Expected ALLOW but got: {output}\n\nThis indicates moderator is hallucinating requirements from context."

    def test_moderator_allows_completed_work_fixture_2(self, fixtures_dir: Path, moderator_prompt: Path, orchestrator_root: Path) -> None:
        """Moderator should ALLOW work that is legitimately complete (fixture 2)."""
        fixture = fixtures_dir / "real_case_2_0383a6b1-e47.jsonl"
        if not fixture.exists():
            pytest.skip(f"Fixture not found: {fixture.name}")

        output = self._run_moderator(fixture, moderator_prompt, orchestrator_root)

        assert "ALLOW" in output, f"Expected ALLOW but got: {output}\n\nThis indicates moderator is hallucinating requirements from context."

    @pytest.mark.xfail(
        reason=(
            "Moderator agent has non-deterministic behavior on this fixture (~66% pass rate). "
            "Sometimes outputs ALLOW, sometimes BLOCK with meta-conversation explanation. "
            "Hallucination is reduced but not eliminated."
        )
    )
    def test_moderator_allows_completed_work_fixture_3(self, fixtures_dir: Path, moderator_prompt: Path, orchestrator_root: Path) -> None:
        """Moderator should ALLOW work that is legitimately complete (fixture 3).

        Note: This test is flaky due to LLM non-determinism. The moderator correctly
        identifies "work complete but followed by meta-conversation" but sometimes
        outputs BLOCK instead of ALLOW despite the prompt rules.
        """
        fixture = fixtures_dir / "real_case_3_665ffab0-fdb.jsonl"
        if not fixture.exists():
            pytest.skip(f"Fixture not found: {fixture.name}")

        output = self._run_moderator(fixture, moderator_prompt, orchestrator_root)

        assert "ALLOW" in output, f"Expected ALLOW but got: {output}\n\nThis indicates moderator is hallucinating requirements from context."
