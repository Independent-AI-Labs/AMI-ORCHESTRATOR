# Task Fixtures

Test fixtures for TaskExecutor and ami-agent --tasks mode.

## Files

- `simple-success.md` - Simple task that should complete successfully (outputs WORK DONE)
- `request-feedback.md` - Task that requests feedback (outputs FEEDBACK: ...)

## Usage

These fixtures can be used in integration tests by copying them to temporary directories or referencing them directly.

Example:
```python
fixtures_dir = Path(__file__).parent.parent / "fixtures" / "tasks"
task_file = fixtures_dir / "simple-success.md"
```

## Notes

- Fixture files should NOT be excluded by task executor (they don't match feedback-* or progress-* patterns)
- This README.md WILL be excluded (matches default exclusion pattern)
