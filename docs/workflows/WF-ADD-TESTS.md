# Test Writing Process: Development Workflow

This document outlines the steps to safely write tests for the AMI Orchestrator system following established patterns and quality standards.

## Key Principle: No Cheating
You must properly write tests following established patterns. No taking shortcuts, bypassing quality checks, or skipping required steps.
- Never bypass quality checks - Always resolve issues properly
- Never use skip decorators or other bypass methods
- Follow established test patterns in the codebase
- Address root causes, not symptoms

## Phase 1: Assessment & Preparation

1. **Read Existing Tests**:
   - Navigate to the tests directory (`/tests`)
   - Examine existing test files in the relevant module
   - Identify established patterns for test structure, naming, and organization
   - Study quality guidelines followed in existing tests

2. **Classify Your Test**:
   - Determine if your test is **UNIT** (testing individual functions/components)
   - Determine if your test is **INTEGRATION** (testing interactions between components)
   - Determine if your test is **E2E** (testing complete user workflows)
   - Each test must be properly classified according to its scope

3. **Establish Test Requirements**:
   - Document what functionality needs to be tested by referencing the specification
   - Identify test groups from the specification (e.g., "Phase 1: Pattern-Based Architecture Foundation Tests")
   - **CRITICAL**: Add a TODO for each test group with explicit instruction in the TODO text to never touch this TODO unless the work is actually done
   - Each test file must pass in full before moving on

## Phase 2: Test Development Process

1. **Follow Established Patterns**:
   - Match naming conventions used in existing tests
   - Use the same assertion styles and test structure patterns
   - Follow the same mocking and fixture approaches
   - Maintain consistent code style and formatting

2. **Write Quality Test Code**:
   - Each test function should have a clear, descriptive name
   - Include proper docstrings explaining what is being tested
   - Use appropriate test fixtures and parameterization
   - Ensure tests are isolated and don't depend on each other
   - Follow the AAA pattern (Arrange, Act, Assert)
   - Never use skip decorators or skip functions

## Phase 3: Test Execution Process

1. **Approved Test Running Methods**:
   - Use `scripts/ami-run base/scripts/run_tests.py path/to/your_test.py` for individual test files
   - Use `scripts/ami-run base/scripts/run_tests.py module` for entire modules
   - These are the ONLY acceptable ways of running tests
   - Never use other test execution methods

2. **Verification Process**:
   - Run your individual test file in isolation first
   - Verify that your test passes consistently
   - Check that your test fails appropriately when expected behavior changes
   - Run the entire module to ensure no regressions

## Quality Assurance Rules

1. **Test Classification**: Every test must be properly classified as UNIT, INTEGRATION, or E2E - no exceptions
2. **Pattern Consistency**: Read existing tests before writing any code and make sure to follow all established patterns
3. **Approved Execution**: Use only `scripts/ami-run base/scripts/run_tests.py path/to/your_test.py` or `scripts/ami-run base/scripts/run_tests.py module` to run tests
4. **Pass Before Progress**: Each test file you create must fully pass before moving on to the next one
5. **No Bypassing**: Never bypass quality checks - always resolve issues properly
6. **No Cheating**: Never use skip decorators, pytest.skip(), or conditional logic to bypass test execution
7. **Quality First**: Maintain the same quality standards as the rest of the codebase
8. **Proper Documentation**: Include clear docstrings and comments where necessary
9. **Root Cause Fixing**: Address actual problems, not symptoms