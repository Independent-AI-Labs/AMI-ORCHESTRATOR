# Gemini Development Guidelines for the Orchestrator

This document outlines the best practices and development guidelines for working on the Orchestrator project.

## 1. Testing and Verification

**Testing is a critical part of the development process.** Before any new feature is considered complete, it must be accompanied by a comprehensive suite of tests. This includes:

*   **Unit Tests:** Each module and function should be rigorously unit-tested to ensure it functions correctly in isolation.
*   **Integration Tests:** Tests should cover the interaction between different components of the orchestrator, such as the BPMN engine's interaction with the Dgraph client and the Worker Manager's interaction with the ACP.
*   **End-to-End (E2E) Tests:** These tests will execute complete BPMN process definitions, simulating real-world business scenarios involving multiple agents, gateways, and human tasks.

**All tests should be written using the `pytest` framework.**

## 2. Development Workflow

1.  **Create/Update Tests:** Before writing any new code, first write the tests that will validate the new functionality. This ensures that the code is written with testability in mind and that the tests accurately reflect the requirements of the new feature.
2.  **Implement the Feature:** Write the code to make the tests pass.
3.  **Run All Tests:** Before submitting any changes, run the entire test suite to ensure that the new code has not introduced any regressions.
4.  **Update Documentation:** Update the `NEXT_STEPS.md` file and any other relevant documentation to reflect the changes.

## 3. Code Style and Linting

All code should adhere to the PEP 8 style guide. Pylint should be used to enforce this and to check for other code quality issues.
