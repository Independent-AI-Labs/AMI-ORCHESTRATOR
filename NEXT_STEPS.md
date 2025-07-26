# Next Steps

## E2E Test Failure

The E2E test in `tests/e2e/test_sample_process_e2e.py` is currently failing with a `ConnectionRefusedError`. This is likely due to an issue with how the test environment is set up, specifically with how the orchestrator and worker processes are started.

### Steps to Reproduce

1. Run `pytest` in the `orchestrator` directory.

### Next Steps

- Investigate the cause of the `ConnectionRefusedError` in the E2E test.
- Fix the E2E test.
