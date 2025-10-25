"""Clean Python code with no violations."""


def calculate_sum(numbers: list[int]) -> int:
    """Calculate sum of numbers.

    Args:
        numbers: List of integers

    Returns:
        Sum of all numbers
    """
    return sum(numbers)


def validate_email(email: str) -> bool:
    """Validate email format.

    Args:
        email: Email address to validate

    Returns:
        True if valid format, False otherwise
    """
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
