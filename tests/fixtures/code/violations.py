"""Python code with known violations for testing.

This file intentionally contains code quality violations to test detection.
All violations are marked with # test-fixture exemption codes.
"""


def process_data(data):  # test-fixture
    """Process data - intentionally has bare except."""
    try:
        result = parse_data(data)
        return result
    except:  # test-fixture
        return False  # test-fixture


def parse_data(data):  # test-fixture
    """Parse data - intentionally has exception->pass."""
    try:
        import json

        return json.loads(data)
    except Exception:  # test-fixture
        pass  # test-fixture


def buggy_function():  # test-fixture
    """Hardcoded credentials - intentional for testing."""
    password = "hardcoded_secret_123"  # test-fixture
    api_key = "sk-test12345678901234567890"  # test-fixture
    return password, api_key
