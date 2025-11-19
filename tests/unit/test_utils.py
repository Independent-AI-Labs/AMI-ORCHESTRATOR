"""Unit tests for automation.common.utils module."""

from pathlib import Path

import pytest

# Import the utils module
try:
    from scripts.agents.core.utils import detect_language
except ImportError:
    detect_language = None


class TestDetectLanguage:
    """Unit tests for detect_language function."""

    @pytest.mark.skipif(detect_language is None, reason="detect_language not available")
    def test_detect_language_python(self):
        """detect_language() detects Python files."""
        lang = detect_language(Path("/test/file.py"))

        assert lang == "python"

    @pytest.mark.skipif(detect_language is None, reason="detect_language not available")
    def test_detect_language_javascript(self):
        """detect_language() detects JavaScript files."""
        lang = detect_language(Path("/test/file.js"))

        assert lang == "javascript"

    @pytest.mark.skipif(detect_language is None, reason="detect_language not available")
    def test_detect_language_typescript(self):
        """detect_language() detects TypeScript files."""
        lang = detect_language(Path("/test/file.ts"))

        assert lang == "typescript"

    @pytest.mark.skipif(detect_language is None, reason="detect_language not available")
    def test_detect_language_unknown(self):
        """detect_language() returns None for unknown files."""
        lang = detect_language(Path("/test/file.txt"))

        assert lang is None
