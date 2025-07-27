# Gemini Development Guidelines for the Orchestrator

This document outlines the best practices and development guidelines for working on the Orchestrator project.

## 1. Testing and Verification

**Testing is a critical part of the development process.** Before any new feature is considered complete, it must be accompanied by a comprehensive suite of tests. This includes:

*   **Unit Tests:** Each module and function should be rigorously unit-tested to ensure it functions correctly in isolation.
*   **Integration Tests:** Tests should cover the interaction between different components of the orchestrator, such as the BPMN engine's interaction with the Dgraph client and the Worker Manager's interaction with the ACP.
*   **End-to-End (E2E) Tests:** These tests will execute complete BPMN process definitions, simulating real-world business scenarios involving multiple agents, gateways, and human tasks.

**All tests should be written using the `pytest` framework.**

## 2. Development Workflow

1.  **Plan and Confirm:** Before making any changes, thoroughly plan the approach. This includes identifying affected files, understanding existing patterns, and considering potential impacts. Confirm the plan with relevant stakeholders or by performing self-verification steps (e.g., outlining expected test outcomes).
2.  **Create/Update Tests:** Before writing any new code, first write the tests that will validate the new functionality. This ensures that the code is written with testability in mind and that the tests accurately reflect the requirements of the new feature.
3.  **Implement the Feature (Atomic Changes):** Write the code to make the tests pass, focusing on making small, atomic changes. Each change should be self-contained and address a single concern.
6. **Commit Changes (Thoroughly):** Before committing, always inspect the changes using `git diff --staged`. Stage all relevant changes using `git add .`. Write a clear and comprehensive commit message that accurately describes the changes made. Use a temporary commit message file for this purpose.
4.  **Run All Tests (Frequent Validation):** After each atomic change, run the relevant tests (unit, integration, E2E) to ensure immediate validation and catch regressions early. Before submitting any changes, run the entire test suite.
5.  **Update Documentation:** Update the `NEXT_STEPS.md` file and any other relevant documentation to reflect the changes.

## 3. Code Style and Linting

All code should adhere to the PEP 8 style guide. Pylint should be used to enforce this and to check for other code quality issues.

## 4. Agent-Coordinator Protocol (ACP)

The Agent-Coordinator Protocol (ACP) is a JSON-RPC based protocol that allows the orchestrator to communicate with various agents, including the Gemini CLI.

The `orchestrator/acp` directory contains the implementation of the ACP, including the protocol definition and the Gemini CLI adapter.

### Gemini CLI Integration

The Gemini CLI integration allows the orchestrator to use the Gemini CLI as an agent. The `GeminiCliAdapter` class in `orchestrator/acp/gemini_cli_adapter.py` implements the client side of the ACP and communicates with the Gemini CLI over stdin/stdout.

To use the Gemini CLI integration, you need to have the Gemini CLI installed and configured. You also need to provide the path to the Gemini CLI bundle in the `sample_adapter.py` file.
