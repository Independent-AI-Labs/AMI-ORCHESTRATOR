# Test Running Process: Development Workflow

This document outlines the only proper way to run tests in the AMI Orchestrator system.

## Key Principle: No Cheating
You must properly run tests using approved commands only. No taking shortcuts, bypassing quality checks, or skipping required steps.
- Never bypass quality checks - Always resolve issues properly
- No alternative test execution methods
- Address root causes, not symptoms

## Phase 1: Test Execution

1. **Proper Test Command**:
   - There is only one proper way to run tests:
   - RUN: scripts/ami-run base/scripts/run_tests.py path/to/your_test.py

2. **Module Test Execution**:
   - To run all tests in a module:
   - RUN: scripts/ami-run base/scripts/run_tests.py module/

3. **Specific Test Execution**:
   - To run a specific test:
   - RUN: scripts/ami-run base/scripts/run_tests.py module/path/to/your_test.py::the_actual_test

## Phase 2: Execution Process

1. **Use Only Approved Commands**:
   - Execute tests using only the approved command format above
   - Never use other test execution methods
   - Do not change directories before running tests

2. **Verify Test Results**:
   - Check that tests pass completely
   - Address any failing tests properly
   - Never bypass test failures

## Phase 3: Test Failure Resolution

1. **Document All Failures**:
   - Create detailed TODOs for every failing test
   - Document the specific failure reason and location
   - Track each failing test individually with clear action items

2. **Fix Systematically**:
   - Address root causes rather than symptoms
   - Create specific action plans for each test failure
   - Follow architectural patterns and conventions when fixing

3. **Re-test After Fixes**:
   - Re-run the same tests after implementing fixes
   - Ensure no regressions are introduced
   - Verify all originally failing tests now pass

## Quality Assurance Rules
1. Always use approved test execution commands
2. Never bypass quality checks - Always resolve issues properly
3. Fix root causes - Address actual problems, not symptoms
4. Proper verification - Ensure all tests pass before proceeding
5. No cheating - Never use skip decorators or other bypass methods