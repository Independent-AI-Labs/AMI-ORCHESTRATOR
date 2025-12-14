# Feature Development Process: Development Workflow

This document outlines the steps to safely develop, test, and validate a feature in the AMI Orchestrator system using the provided scripts while ensuring no regressions.

## Key Principle: No Cheating
You must properly develop features following the complete process. No taking shortcuts, bypassing quality checks, or skipping required steps.
- Never bypass quality checks - Always resolve issues properly
- No noqa, # pylint: disable, or other suppressions unless architecturally required
- Address root causes, not symptoms
- Always run complete test suites before pushing

## Phase 1: Assessment & Feature Implementation

1. **Navigate to Module**: Navigate to the module directory (e.g., /browser, /base, /nodes)

2. **Identify Requirements**:
   - Understand the feature requirements and specifications
   - Create detailed TODOs for each document, phase, section, or feature that needs to be implemented
   - Document the scope of the feature: new functionality, enhancements, integrations, etc.

3. **Create Development Plan**:
   - Break the feature into manageable tasks with clear milestones
   - Plan the implementation in phases: feature implementation, testing, validation, and verification

4. **Implement Feature Components**:
   - Write the core feature functionality following architectural patterns and standards
   - Create TODOs for each component being implemented to track progress
   - Ensure adherence to existing codebase patterns and conventions

## Phase 2: Test Creation & Validation

1. **Write Comprehensive Tests**:
   - Implement unit tests for all new feature components
   - Create integration tests to validate feature behavior across system boundaries
   - Add TODOs for each test file and test case being created
   - Ensure test coverage for positive and negative scenarios
   - **CRITICAL: For every feature, enhancement, or modification added, there MUST be comprehensive tests that validate functionality. No exceptions.**

2. **Handle Test Failures**:
   - If tests fail during development, create TODOs for all issues identified
   - Address test failures without cheating or skipping quality checks
   - Fix implementation based on test feedback
   - Iterate until all tests pass

3. **Execute Test Suite**:
   - Run the complete test suite for the module: scripts/ami-run base/scripts/run_tests.py path/to/module
   - Run specific tests for the new feature: scripts/ami-run base/scripts/run_tests.py path/to/feature_tests
   - **MANDATORY: All tests must pass before proceeding. No feature is complete without passing tests.**
   - Validate that all feature tests pass successfully

4. **Handle Test Failures**:
   - If tests fail during execution, create TODOs for all failing tests
   - Debug and fix both feature implementation and test issues
   - Return to step 1 and re-run tests after fixing
   - Iterate until all tests pass

## Phase 2.5: Test Coverage Verification (NEW - MANDATORY)
1. **Verify Test Coverage Requirements**:
   - **MANDATORY:** All new features must have 100% test coverage for critical paths
   - **MANDATORY:** At least 90% coverage for all new code (check with coverage tools)
   - **MANDATORY:** Integration tests must validate end-to-end functionality
   - **MANDATORY:** Negative test cases must be included for error handling
   - **MANDATORY:** Performance and load tests where applicable

2. **Run All Test Types**:
   - Unit tests for all new functions/classes
   - Integration tests for system interactions
   - End-to-end tests for complete workflows
   - Regression tests to ensure no existing functionality breaks
   - Performance/load tests for production features

3. **Documentation of Test Results**:
   - Document test coverage percentages
   - Document which test scenarios are covered
   - Document any exceptions or special cases handled
   - **CRITICAL: No feature is considered complete without documented test results**

## Phase 3: Regression Testing

1. **Run Complete Module Tests**:
   - Execute the full module test suite to ensure no regressions: scripts/ami-run base/scripts/run_tests.py module/
   - Verify that existing functionality remains intact after feature addition
   - Run specific integration and end-to-end tests to validate system-wide behavior

2. **Handle Regression Failures**:
   - If regression tests fail, create TODOs for all failing tests
   - Investigate whether failures are caused by the new feature
   - Fix implementation issues that cause regressions
   - Return to step 1 and rerun tests after fixing
   - Iterate until all tests pass and no regressions exist

## Quality Assurance Rules
1. Never bypass quality checks - Always resolve issues properly
2. Maintain architectural consistency - Follow existing patterns in the codebase
3. Fix root causes - Address actual problems, not symptoms
4. Security first - Address all security vulnerabilities before proceeding
5. Proper documentation - Maintain clear code comments and commit messages
6. No quality avoidance tricks - Never use noqa, # pylint: disable, or other suppressions except when architecturally required and extensive precedent has been set in the codebase
7. No regressions allowed - Ensure all existing functionality continues to work after feature implementation
8. **MANDATORY TESTING:** No code is complete without comprehensive tests covering all new functionality - Unit, Integration, and End-to-End tests required
9. **TEST COVERAGE:** All new code must have at least 90% test coverage with 100% coverage for critical paths
10. **TEST VALIDATION:** All tests must pass before any feature is considered complete - No exceptions
